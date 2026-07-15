"""LLM client with offline mock mode, caching, retry, and cost logging.

DEFAULT OFFLINE MOCK MODE: deterministic output derived from hash(role, prompt, seed).
No API key required. Works entirely offline.
"""

import collections
import hashlib
import json
import math
import os
import random
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Deque, Optional, Dict, Any


class BudgetExceeded(Exception):
    """Raised when the configured spend cap is exceeded.

    This is a permanent stop condition — it must NEVER be retried.
    """


class _OnlineModeError(RuntimeError):
    """Internal marker: a fatal error from _generate_online.

    All errors that escape the inner HTTP-retry loop are re-raised as this
    type so the outer retry loop in complete() treats them as permanent.
    This prevents the outer loop from re-entering an exhausted inner loop.
    """


@dataclass
class Completion:
    """LLM completion result."""
    text: str
    model: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    # logit_conf: populated from token logprobs for OpenAI slugs only.
    # None for all other families (logprobs not exposed on GitHub Models).
    logit_conf: Optional[float] = None


class LLMClient:
    """Multi-provider LLM client with role-based routing.
    
    Operates in offline mock mode by default (no API key needed).
    Mock outputs are deterministic, keyed by (role, prompt, seed).
    """
    
    def __init__(
        self,
        config: Dict[str, Any],
        cache_dir: str = ".llm_cache",
        offline: bool = True,
        base_url: str = "https://models.github.ai/inference",
        max_budget_usd: Optional[float] = None,
        max_requests_per_min: Optional[int] = None,
    ):
        """Initialize LLM client.

        Args:
            config: Loaded config dict (from config.py)
            cache_dir: Directory for disk cache
            offline: If True, use deterministic mock mode (default)
            base_url: Base URL for the OpenAI-compatible API endpoint
            max_budget_usd: Hard spend cap in USD; raises BudgetExceeded when exceeded
            max_requests_per_min: Max API calls per 60-second sliding window
        """
        self.config = config
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.offline = offline
        self.base_url = base_url.rstrip("/")
        self.max_budget_usd = max_budget_usd
        self.max_requests_per_min = max_requests_per_min
        self.cost_log_path = self.cache_dir / "cost_log.jsonl"
        # Mutable budget and rate-limit state
        self._total_cost_usd: float = 0.0
        self._request_times: Deque[float] = collections.deque()
        
    def complete(
        self,
        role: str,
        prompt: str,
        seed: Optional[int] = None,
        max_retries: int = 3,
        family: Optional[str] = None,
        model: Optional[str] = None
    ) -> Completion:
        """Generate completion for a given role and prompt.
        
        Args:
            role: Model role (e.g., 'constructor', 'judge', 'tested_agents')
            prompt: Input prompt
            seed: Random seed for reproducibility (uses global seed if None)
            max_retries: Number of retry attempts on failure
            family: Optional explicit model family (overrides role-based routing)
            model: Optional explicit model name (overrides role-based routing)
        
        Returns:
            Completion object with text and metadata
        """
        if seed is None:
            seed = self.config["seeds"]["global"]
        
        # Check cache first
        cache_key = self._cache_key(role, prompt, seed, family, model)
        cached = self._read_cache(cache_key)
        if cached:
            return cached
        
        # Generate completion (with retry wrapper for TRANSIENT errors only)
        for attempt in range(max_retries):
            try:
                completion = self._generate(role, prompt, seed, family, model)
                self._write_cache(cache_key, completion)
                self._log_cost(role, prompt, completion)
                return completion
            except (NotImplementedError, BudgetExceeded, _OnlineModeError):
                raise  # permanent — never retry
            except Exception:
                if attempt == max_retries - 1:
                    raise
                time.sleep(2 ** attempt)  # Exponential backoff
        
        raise RuntimeError("Max retries exceeded")
    
    def _generate(self, role: str, prompt: str, seed: int, family: Optional[str] = None, model: Optional[str] = None) -> Completion:
        """Generate completion. Offline (mock) by default; online via GitHub Models."""
        if self.offline:
            return self._mock_generate(role, prompt, seed, family, model)
        else:
            return self._generate_online(role, prompt, seed, family, model)
    
    def _mock_generate(self, role: str, prompt: str, seed: int, family: Optional[str] = None, model: Optional[str] = None) -> Completion:
        """Deterministic mock generation for offline operation.
        
        Output is a stable hash of (family, model, prompt, seed) to ensure reproducibility
        and proper heterogeneous provenance (different models → different outputs).
        """
        # Resolve model info (explicit params override role-based routing)
        if family is not None and model is not None:
            model_family = family
            model_name = model
        else:
            from common.config import model_for_role
            model_info = model_for_role(role, self.config)
            model_family = model_info["family"]
            model_name = model_info["model"]
        
        # Derive deterministic output from inputs INCLUDING family/model
        # (critical for heterogeneous provenance: different models must yield different outputs)
        content = f"{model_family}|{model_name}|{prompt}|{seed}"
        hash_obj = hashlib.sha256(content.encode('utf-8'))
        hash_hex = hash_obj.hexdigest()
        
        # Generate mock output that varies by hash
        mock_text = f"MOCK_OUTPUT_{hash_hex[:16]}"
        
        return Completion(
            text=mock_text,
            model=model_name,
            tokens_in=len(prompt.split()),
            tokens_out=len(mock_text.split("_")),
            cost_usd=0.0  # Mock mode is free
        )
    
    def _role_identity(self, role: str) -> str:
        """Resolved family:model for a role, so the cache key is provenance-aware.

        Raises on unknown roles (fail fast — no fabricated fallback provenance).
        """
        from common.config import model_for_role
        info = model_for_role(role, self.config)
        return f"{info['family']}:{info['model']}"

    def _cache_key(self, role: str, prompt: str, seed: int, family: Optional[str] = None, model: Optional[str] = None) -> str:
        """Generate cache key from inputs.

        Includes the execution mode (offline vs online) and the resolved
        family:model identity so the cache can never (a) serve an offline mock
        to an online client, or (b) return a stale model id after the role's
        configured model/family changes — either would corrupt AgentRun.model_id
        provenance.
        """
        mode = "offline" if self.offline else "online"
        
        # Use explicit family/model if provided, otherwise resolve from role
        if family is not None and model is not None:
            identity = f"{family}:{model}"
        else:
            identity = self._role_identity(role)
        
        content = f"{mode}|{identity}|{role}|{prompt}|{seed}"
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def _read_cache(self, cache_key: str) -> Optional[Completion]:
        """Read from disk cache."""
        cache_file = self.cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Backward-compat: cache files written before logit_conf was added
                # lack that key; default it to None rather than raising TypeError.
                data.setdefault("logit_conf", None)
                return Completion(**data)
        return None
    
    def _write_cache(self, cache_key: str, completion: Completion) -> None:
        """Write to disk cache."""
        cache_file = self.cache_dir / f"{cache_key}.json"
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(completion.__dict__, f)
    
    def _log_cost(self, role: str, prompt: str, completion: Completion) -> None:
        """Log API call cost. The API token is NEVER included here."""
        log_entry = {
            "timestamp": time.time(),
            "role": role,
            "model": completion.model,
            "tokens_in": completion.tokens_in,
            "tokens_out": completion.tokens_out,
            "cost_usd": completion.cost_usd,
            "accumulated_cost_usd": self._total_cost_usd,
            "prompt_len": len(prompt),
        }
        with open(self.cost_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")

    # ── Online-mode helpers (Phase 3) ─────────────────────────────────────────

    # Per-model pricing (USD / 1K tokens: input, output). Approximate estimates
    # from OpenAI / GitHub Models public pages (2025-07). Used ONLY for budget
    # enforcement and cost logging; not part of any scientific measurement.
    _MODEL_PRICING: Dict[str, tuple] = {
        "openai/gpt-4o-mini":               (0.000150, 0.000600),
        "openai/gpt-4.1-nano":              (0.000100, 0.000400),
        "openai/gpt-4.1-mini":              (0.000400, 0.001600),
        "openai/gpt-4.1":                   (0.002000, 0.008000),
        "openai/gpt-4o":                    (0.002500, 0.010000),
        "openai/gpt-5":                     (0.010000, 0.040000),
        "meta/llama-3.3-70b-instruct":      (0.000900, 0.000900),
        "meta/llama-4-scout-17b-16e-instruct": (0.000500, 0.000500),
        "mistral-ai/mistral-small-2503":    (0.000200, 0.000600),
        "mistral-ai/mistral-medium-2505":   (0.000400, 0.002000),
        "deepseek/deepseek-v3-0324":        (0.000280, 0.001100),
        "deepseek/deepseek-r1":             (0.000550, 0.002190),
        "microsoft/phi-4":                  (0.000125, 0.000500),
        "cohere/cohere-command-a":          (0.002500, 0.010000),
    }
    _DEFAULT_PRICING = (0.001000, 0.003000)  # conservative fallback for unknown slugs

    def _generate_online(
        self,
        role: str,
        prompt: str,
        seed: int,
        family: Optional[str],
        model: Optional[str],
    ) -> Completion:
        """Call the GitHub Models API (OpenAI-compatible chat/completions).

        Token source (tried in order):
          1. GITHUB_MODELS_TOKEN env var
          2. GH_MODELS_TOKEN env var
        The token is NEVER logged, printed, or included in any error message.

        logprobs:
          - openai/* slugs: logprobs=True requested → logit_conf populated from
            exp(mean(first-5-token logprobs)).
          - All other families (meta, mistral-ai, deepseek, microsoft, cohere):
            logprobs not exposed on GitHub Models → logit_conf=None; rely on
            verbalized confidence. Documented capability table:
              openai/*          logit_conf: ✓ (logprobs supported)
              meta/*            logit_conf: ✗ (not exposed)
              mistral-ai/*      logit_conf: ✗ (not exposed)
              deepseek/*        logit_conf: ✗ (not exposed)
              microsoft/*       logit_conf: ✗ (not exposed)
              cohere/*          logit_conf: ✗ (not exposed)

        Retry policy (bounded — no infinite loops):
          HTTP 429 / 5xx  → exponential backoff with jitter, up to _MAX_HTTP_RETRIES
          HTTP 4xx ≠ 429  → fail loud immediately (no retry)
          BudgetExceeded  → permanent stop, not retried (outer complete() checks)
          Missing token   → permanent error, not retried
        """
        # ── Resolve slug ───────────────────────────────────────────────────────
        if family is not None and model is not None:
            slug = model  # explicit override (e.g. heterogeneous-MAD passes full slug)
        else:
            from common.config import model_for_role
            info = model_for_role(role, self.config)
            slug = info["model"]
            family = info["family"]

        is_openai = slug.startswith("openai/")

        # ── Token — read from env; never log / print / write ──────────────────
        token = (
            os.environ.get("GITHUB_MODELS_TOKEN")
            or os.environ.get("GH_MODELS_TOKEN")
            or ""
        )
        if not token:
            raise RuntimeError(
                "Online mode requires an API token. "
                "Set GITHUB_MODELS_TOKEN or GH_MODELS_TOKEN environment variable."
            )

        # ── Hard budget check BEFORE the call ─────────────────────────────────
        if self.max_budget_usd is not None and self._total_cost_usd >= self.max_budget_usd:
            raise BudgetExceeded(
                f"Budget cap of ${self.max_budget_usd:.4f} USD exceeded "
                f"(accumulated ${self._total_cost_usd:.4f})"
            )

        # ── Rate-limit enforcement ─────────────────────────────────────────────
        self._enforce_rate_limit()

        # ── Build request ──────────────────────────────────────────────────────
        payload: Dict[str, Any] = {
            "model": slug,
            "messages": [{"role": "user", "content": prompt}],
            "seed": seed,
        }
        if is_openai:
            payload["logprobs"] = True
            payload["top_logprobs"] = 1

        # Authorization header carries the token; never echoed back in logs or errors
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }

        url = f"{self.base_url}/chat/completions"
        body_bytes = json.dumps(payload).encode("utf-8")

        # ── HTTP call with bounded 429/5xx retry (exponential backoff + jitter) ─
        _MAX_HTTP_RETRIES = 6
        resp_data: Dict[str, Any] = {}
        for attempt in range(_MAX_HTTP_RETRIES):
            req = urllib.request.Request(
                url, data=body_bytes, headers=headers, method="POST"
            )
            try:
                with urllib.request.urlopen(req) as resp:
                    resp_data = json.loads(resp.read())
                break  # success — exit retry loop
            except urllib.error.HTTPError as exc:
                status = exc.code
                if status == 429 or (500 <= status < 600):
                    if attempt == _MAX_HTTP_RETRIES - 1:
                        raise _OnlineModeError(
                            f"HTTP {status}: gave up after {_MAX_HTTP_RETRIES} retries"
                        ) from exc
                    backoff = min(2.0 ** attempt + random.uniform(0.0, 1.0), 60.0)
                    time.sleep(backoff)
                    continue
                else:
                    # 4xx (non-429): fail loud — one attempt only
                    try:
                        err_body = exc.read().decode("utf-8", errors="replace")
                    except Exception:
                        err_body = "(unreadable error body)"
                    # Scrub token from error message before raising
                    err_body = err_body.replace(token, "[REDACTED]")
                    raise _OnlineModeError(
                        f"HTTP {status} error from API: {err_body}"
                    ) from None

        # ── Record request time for rate-limit window ──────────────────────────
        self._record_request_time()

        # ── Parse response ─────────────────────────────────────────────────────
        choice = resp_data["choices"][0]
        text = choice["message"]["content"]
        usage = resp_data.get("usage", {})
        tokens_in = int(usage.get("prompt_tokens", 0))
        tokens_out = int(usage.get("completion_tokens", 0))

        # ── Cost estimate + budget accumulation ───────────────────────────────
        cost_usd = self._estimate_cost(slug, tokens_in, tokens_out)
        self._total_cost_usd += cost_usd

        # ── logit_conf (OpenAI only) ───────────────────────────────────────────
        logit_conf: Optional[float] = self._extract_logit_conf(choice) if is_openai else None

        return Completion(
            text=text,
            model=slug,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost_usd,
            logit_conf=logit_conf,
        )

    def _extract_logit_conf(self, choice: Dict[str, Any]) -> Optional[float]:
        """Extract a confidence signal from OpenAI token logprobs.

        Uses exp(mean(logprob)) over the first min(5, n) generated tokens.
        Returns None on any missing or malformed data rather than raising.
        """
        try:
            lp_data = choice.get("logprobs") or {}
            content = lp_data.get("content") or []
            if not content:
                return None
            logprobs = [tok["logprob"] for tok in content[:5] if "logprob" in tok]
            if not logprobs:
                return None
            return math.exp(sum(logprobs) / len(logprobs))
        except Exception:
            return None

    def _estimate_cost(self, slug: str, tokens_in: int, tokens_out: int) -> float:
        """Estimate USD cost from token counts using the pricing table."""
        price_in, price_out = self._MODEL_PRICING.get(slug, self._DEFAULT_PRICING)
        return (tokens_in * price_in + tokens_out * price_out) / 1000.0

    def _enforce_rate_limit(self) -> None:
        """Block until the rolling 60-second request count is below the cap."""
        if self.max_requests_per_min is None:
            return
        now = time.time()
        cutoff = now - 60.0
        while self._request_times and self._request_times[0] < cutoff:
            self._request_times.popleft()
        if len(self._request_times) >= self.max_requests_per_min:
            wait_time = 60.0 - (now - self._request_times[0]) + 0.05
            if wait_time > 0:
                time.sleep(wait_time)
            now = time.time()
            cutoff = now - 60.0
            while self._request_times and self._request_times[0] < cutoff:
                self._request_times.popleft()

    def _record_request_time(self) -> None:
        """Append the current timestamp to the rate-limit tracking window."""
        self._request_times.append(time.time())
