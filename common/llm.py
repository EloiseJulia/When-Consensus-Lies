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


class DayCapped(Exception):
    """Raised when a model's daily request cap is hit (x-ratelimit-type=UserByModelByDay).

    This is a permanent stop condition within the day — do NOT retry.
    Callers should stop all jobs for this model and resume after the ~24h cap reset.
    """

    def __init__(self, model_slug: str) -> None:
        self.model_slug = model_slug
        super().__init__(
            f"Daily request cap hit for model {model_slug!r}; "
            "resume after ~24h reset (x-ratelimit-type=UserByModelByDay)"
        )


class _OnlineModeError(RuntimeError):
    """Internal marker: a fatal error from _generate_online.

    All errors that escape the inner HTTP-retry loop are re-raised as this
    type so the outer retry loop in complete() treats them as permanent.
    This prevents the outer loop from re-entering an exhausted inner loop.
    """


# Reasoning / o-series models that require special request handling:
#   - send max_completion_tokens (NOT max_tokens)
#   - do NOT send logprobs / top_logprobs  (causes HTTP 400)
#   - do NOT send temperature              (ignored / causes 400)
# Edit this list when new reasoning-class slugs are released.
_REASONING_PREFIXES = (
    "openai/o1",
    "openai/o3",
    "openai/o4",
    "openai/gpt-5",
)


def is_reasoning_model(slug: str) -> bool:
    """Return True when *slug* identifies an o-series / reasoning-class model.

    Matches ``openai/o1*``, ``openai/o3*``, ``openai/o4*``, ``openai/gpt-5*``.
    The prefix list ``_REASONING_PREFIXES`` is the single source of truth and is
    easily editable as new model families are released.

    NOTE: this classifier is for the GITHUB_MODELS provider (family-prefixed slugs
    such as ``openai/gpt-5``). It is intentionally NOT used by the copilot_proxy
    provider, whose request shape is handled separately (see ``_build_proxy_payload``)
    because the proxy exposes bare, un-prefixed slugs (``gpt-5.4``) with different
    per-slug parameter support empirically probed against the live endpoint.
    """
    return any(slug.startswith(p) for p in _REASONING_PREFIXES)


# ── Provider abstraction ───────────────────────────────────────────────────────
# The client can target either the GitHub Models inference endpoint (default,
# token-authenticated) or a LOCAL, OpenAI-compatible GitHub Copilot API proxy
# (``ghc-api``) that requires NO auth token and serves frontier models across
# families. Selection is via the ``provider`` constructor arg and/or a config
# ``providers:`` block. The offline mock default and the GitHub Models online path
# are behavior-preserving; only ``provider="copilot_proxy"`` changes the request
# shape / auth.
PROVIDER_GITHUB_MODELS = "github_models"
PROVIDER_COPILOT_PROXY = "copilot_proxy"

GITHUB_MODELS_BASE_URL = "https://models.github.ai/inference"
COPILOT_PROXY_BASE_URL = "http://127.0.0.1:8313/v1"

# Per-provider default base URL and whether an Authorization token is required.
_PROVIDER_DEFAULTS: Dict[str, Dict[str, Any]] = {
    PROVIDER_GITHUB_MODELS: {"base_url": GITHUB_MODELS_BASE_URL, "require_auth": True},
    PROVIDER_COPILOT_PROXY: {"base_url": COPILOT_PROXY_BASE_URL, "require_auth": False},
}

# Copilot-proxy request-shape findings (empirically probed against the live local
# proxy on 2026-07-17; see paper/research if promoted). Substring match on the bare
# proxy slug. These slugs reject a ``temperature`` field with HTTP 400
# ("Unsupported parameter: 'temperature' is not supported with this model"), so it
# must be OMITTED for them. All other observed slugs (gpt-4o-mini, gpt-5.4,
# claude-*, gemini-*) accept temperature.
_PROXY_NO_TEMPERATURE_DEFAULT = (
    "gpt-5.6",   # gpt-5.6-sol / -terra / -luna reject temperature
    "mai-code",  # mai-code-1-flash-picker rejects temperature
)


def proxy_omits_temperature(slug: str, patterns=_PROXY_NO_TEMPERATURE_DEFAULT) -> bool:
    """Return True when the copilot-proxy *slug* rejects a ``temperature`` field.

    Empirically, most proxy models accept ``temperature`` but a few frontier /
    picker slugs return HTTP 400 for it. ``patterns`` is a substring allow-list of
    slugs that must have ``temperature`` omitted; it is configurable so the roster
    can evolve without code changes.
    """
    return any(p in slug for p in patterns)


def resolve_provider_config(
    config: Dict[str, Any],
    provider: Optional[str] = None,
    base_url: Optional[str] = None,
    require_auth: Optional[bool] = None,
    no_temperature_models: Optional[tuple] = None,
) -> Dict[str, Any]:
    """Resolve provider settings from explicit params, config, then built-in defaults.

    Single source of truth for provider resolution, shared by ``LLMClient.__init__``
    and the CLI live-guard (so the runner can decide whether a token is required
    BEFORE constructing a client). Resolution order per field: explicit param >
    config ``providers[provider]`` > config ``providers.default`` (for the provider
    name only) > built-in provider default.

    Returns a dict with keys ``provider``, ``base_url`` (trailing slash stripped),
    ``require_auth`` (bool), ``no_temperature_models`` (tuple).
    """
    providers_cfg = config.get("providers", {}) if isinstance(config, dict) else {}
    if not isinstance(providers_cfg, dict):
        providers_cfg = {}
    if provider is None:
        provider = providers_cfg.get("default", PROVIDER_GITHUB_MODELS)
    if provider not in _PROVIDER_DEFAULTS:
        raise ValueError(
            f"Unknown provider {provider!r}; expected one of "
            f"{sorted(_PROVIDER_DEFAULTS)}"
        )
    defaults = _PROVIDER_DEFAULTS[provider]
    conf = providers_cfg.get(provider, {})
    if not isinstance(conf, dict):
        conf = {}
    if base_url is None:
        base_url = conf.get("base_url", defaults["base_url"])
    if require_auth is None:
        require_auth = conf.get("require_auth", defaults["require_auth"])
    if no_temperature_models is None:
        no_temperature_models = tuple(
            conf.get("no_temperature_models", _PROXY_NO_TEMPERATURE_DEFAULT)
        )
    return {
        "provider": provider,
        "base_url": base_url.rstrip("/"),
        "require_auth": bool(require_auth),
        "no_temperature_models": tuple(no_temperature_models),
    }


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
        base_url: Optional[str] = None,
        max_budget_usd: Optional[float] = None,
        max_requests_per_min: Optional[int] = None,
        http_timeout: float = 60.0,
        max_tokens_per_call: int = 4096,
        provider: Optional[str] = None,
        require_auth: Optional[bool] = None,
        no_temperature_models: Optional[tuple] = None,
    ):
        """Initialize LLM client.

        Args:
            config: Loaded config dict (from config.py)
            cache_dir: Directory for disk cache
            offline: If True, use deterministic mock mode (default)
            base_url: Base URL for the OpenAI-compatible API endpoint. When None
                (default) it is resolved from the selected provider (GitHub Models
                for ``github_models``; ``http://127.0.0.1:8313/v1`` for
                ``copilot_proxy``). An explicit value always wins so the proxy
                host/port is fully configurable.
            max_budget_usd: Hard spend cap in USD; raises BudgetExceeded when exceeded
            max_requests_per_min: Max API calls per 60-second sliding window
            http_timeout: Socket timeout (seconds) for each urlopen call (MAJOR 5)
            max_tokens_per_call: Assumed worst-case output tokens for budget pre-auth
            provider: ``"github_models"`` (default) or ``"copilot_proxy"``. Selects
                the base URL default, whether an auth token is required, and the
                per-request payload shape. When None, resolved from a config
                ``providers.default`` key if present, else ``github_models``.
            require_auth: Whether an Authorization token is required/sent. When None,
                resolved from the provider (True for GitHub Models, False for the
                local proxy, which needs no token).
            no_temperature_models: Optional substring allow-list of proxy slugs that
                reject a ``temperature`` field (proxy provider only). When None,
                resolved from config or the built-in default.
        """
        self.config = config

        # ── Resolve provider settings (param > config > default) ──────────────
        resolved = resolve_provider_config(
            config if isinstance(config, dict) else {},
            provider=provider,
            base_url=base_url,
            require_auth=require_auth,
            no_temperature_models=no_temperature_models,
        )
        self.provider = resolved["provider"]
        self.base_url = resolved["base_url"]
        self.require_auth = resolved["require_auth"]
        self.no_temperature_models = resolved["no_temperature_models"]

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.offline = offline
        self.max_budget_usd = max_budget_usd
        self.max_requests_per_min = max_requests_per_min
        self.cost_log_path = self.cache_dir / "cost_log.jsonl"
        # Mutable budget and rate-limit state
        self._total_cost_usd: float = 0.0
        self._request_times: Deque[float] = collections.deque()
        self._http_timeout: float = http_timeout           # MAJOR 5
        self._max_tokens_per_call: int = max_tokens_per_call  # BLOCKER 2 pre-auth

    @property
    def max_tokens_per_call(self) -> int:
        """Per-call output-token budget (drives max_completion_tokens/max_tokens in the
        request payload AND the budget pre-authorization). Exposed read-only so the
        Runner can propagate it to per-job client reconstructions (a raised reasoner
        budget must not silently revert to the 4096 default)."""
        return self._max_tokens_per_call

    def complete(
        self,
        role: str,
        prompt: str,
        seed: Optional[int] = None,
        max_retries: int = 3,
        family: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> Completion:
        """Generate completion for a given role and prompt.
        
        Args:
            role: Model role (e.g., 'constructor', 'judge', 'tested_agents')
            prompt: Input prompt
            seed: Random seed for reproducibility (uses global seed if None)
            max_retries: Number of retry attempts on failure
            family: Optional explicit model family (overrides role-based routing)
            model: Optional explicit model name (overrides role-based routing)
            temperature: Sampling temperature (None = API default). Omitted for
                reasoning models (o-series/gpt-5*) regardless of this value.
                Included in the cache key so different temperatures cache separately.
        
        Returns:
            Completion object with text and metadata
        """
        if seed is None:
            seed = self.config["seeds"]["global"]
        
        # Check cache first
        cache_key = self._cache_key(role, prompt, seed, family, model, temperature)
        cached = self._read_cache(cache_key)
        if cached:
            return cached
        
        # Generate completion (with retry wrapper for TRANSIENT errors only).
        # MAJOR 4 FIX: _write_cache / _log_cost are OUTSIDE this loop so that
        # a persistence OSError never causes the loop to re-call the paid API.
        completion = None
        for attempt in range(max_retries):
            try:
                completion = self._generate(role, prompt, seed, family, model, temperature)
                break  # generation succeeded; exit retry loop
            except (NotImplementedError, BudgetExceeded, _OnlineModeError, DayCapped):
                raise  # permanent — never retry
            except Exception:
                if attempt == max_retries - 1:
                    raise
                time.sleep(2 ** attempt)  # Exponential backoff

        # Persist OUTSIDE the generation retry loop.
        # Failures here are non-fatal and must NEVER trigger another API call.
        try:
            self._write_cache(cache_key, completion)
        except Exception:
            pass  # non-fatal: caller gets the result; next call will re-fetch

        try:
            self._log_cost(role, prompt, completion)
        except Exception:
            pass  # non-fatal: cost tracking is best-effort

        return completion
    
    def _generate(self, role: str, prompt: str, seed: int, family: Optional[str] = None, model: Optional[str] = None, temperature: Optional[float] = None) -> Completion:
        """Generate completion. Offline (mock) by default; online via GitHub Models."""
        if self.offline:
            return self._mock_generate(role, prompt, seed, family, model, temperature)
        else:
            return self._generate_online(role, prompt, seed, family, model, temperature)
    
    def _mock_generate(self, role: str, prompt: str, seed: int, family: Optional[str] = None, model: Optional[str] = None, temperature: Optional[float] = None) -> Completion:
        """Deterministic mock generation for offline operation.
        
        Output is a stable hash of (family, model, prompt, seed, temperature) to ensure
        reproducibility and proper heterogeneous provenance (different models → different
        outputs). Temperature is included so different temperatures hash differently,
        making offline behavior temperature-aware.
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
        
        # Derive deterministic output from inputs INCLUDING family/model AND temperature
        # (critical for heterogeneous provenance: different models must yield different outputs;
        #  temperature is included so different temperatures produce distinct mock outputs)
        content = f"{model_family}|{model_name}|{prompt}|{seed}|{temperature}"
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

    def _cache_key(self, role: str, prompt: str, seed: int, family: Optional[str] = None, model: Optional[str] = None, temperature: Optional[float] = None) -> str:
        """Generate cache key from inputs.

        Includes the execution mode (offline vs online), the PROVIDER + base_url
        (so a copilot_proxy result can never be served to a github_models client or
        vice-versa even for the same slug/prompt), the resolved family:model
        identity, and the temperature so the cache can never (a) serve an offline
        mock to an online client, (b) return a stale model id after the role's
        configured model/family changes, (c) collide across providers/endpoints, or
        (d) collide across different temperatures — any of which would corrupt
        AgentRun provenance or produce incorrect cached responses.
        """
        mode = "offline" if self.offline else "online"
        
        # Use explicit family/model if provided, otherwise resolve from role
        if family is not None and model is not None:
            identity = f"{family}:{model}"
        else:
            identity = self._role_identity(role)
        
        content = (
            f"{mode}|{self.provider}|{self.base_url}|{identity}|"
            f"{role}|{prompt}|{seed}|{temperature}"
        )
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
        temperature: Optional[float] = None,
    ) -> Completion:
        """Call the GitHub Models API (OpenAI-compatible chat/completions).

        Token source (tried in order):
          1. GITHUB_MODELS_TOKEN env var
          2. GH_MODELS_TOKEN env var
        The token is NEVER logged, printed, or included in any error message.

        logprobs:
          - Non-reasoning openai/* slugs: logprobs=True requested → logit_conf populated
            from exp(mean(first-5-token logprobs)).
          - Reasoning models (o1*, o3*, o4*, gpt-5*): logprobs NOT sent (HTTP 400);
            logit_conf=None; verbalized confidence only.
          - All other families (meta, mistral-ai, deepseek, microsoft, cohere):
            logprobs not exposed on GitHub Models → logit_conf=None; rely on
            verbalized confidence. Documented capability table:
              openai/* (non-reasoning)  logit_conf: ✓ (logprobs supported)
              openai/* (reasoning)      logit_conf: ✗ (logprobs rejected)
              meta/*                    logit_conf: ✗ (not exposed)
              mistral-ai/*              logit_conf: ✗ (not exposed)
              deepseek/*                logit_conf: ✗ (not exposed)
              microsoft/*               logit_conf: ✗ (not exposed)
              cohere/*                  logit_conf: ✗ (not exposed)

        temperature:
          - Passed as ``temperature`` in the payload for non-reasoning models when provided.
          - Omitted for reasoning models (o-series/gpt-5*) — these models do not accept it.

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
        is_reasoning = is_reasoning_model(slug)
        is_proxy = self.provider == PROVIDER_COPILOT_PROXY

        # ── Token — read from env; never log / print / write ──────────────────
        # Required for GitHub Models; the local copilot_proxy needs NO token
        # (require_auth=False) so a missing token is NOT an error there.
        token = (
            os.environ.get("GITHUB_MODELS_TOKEN")
            or os.environ.get("GH_MODELS_TOKEN")
            or ""
        )
        if self.require_auth and not token:
            raise RuntimeError(
                "Online mode requires an API token. "
                "Set GITHUB_MODELS_TOKEN or GH_MODELS_TOKEN environment variable."
            )

        # ── Pre-authorization budget check (BLOCKER 2 fix) ────────────────────
        # Estimate worst-case cost for THIS call and refuse BEFORE making any
        # HTTP request. Never returns an over-budget completion. The local proxy
        # is free/unlimited → worst-case cost is 0.0 and never blocks.
        if self.max_budget_usd is not None:
            # Use UTF-8 byte length as a GUARANTEED upper bound on input tokens.
            # For byte-level BPE tokenizers (GPT-4o, GPT-4.1, etc.) each token
            # encodes at least one byte, so token_count ≤ utf8_byte_count.
            # This holds for ALL text including multi-byte Unicode / emoji /
            # ZWJ sequences where char count << byte count. Add 64 for
            # message-framing / system-prompt overhead.
            tokens_in_upper = len(prompt.encode("utf-8")) + 64
            worst_case_cost = self._estimate_cost_for(
                slug, tokens_in_upper, self._max_tokens_per_call
            )
            if self._total_cost_usd + worst_case_cost > self.max_budget_usd:
                raise BudgetExceeded(
                    f"Pre-authorization: worst-case cost ${worst_case_cost:.6f} "
                    f"would exceed remaining budget "
                    f"${max(0.0, self.max_budget_usd - self._total_cost_usd):.6f}"
                )

        # ── Build request ──────────────────────────────────────────────────────
        if is_proxy:
            payload = self._build_proxy_payload(slug, prompt, seed, temperature)
        else:
            payload = self._build_github_models_payload(
                slug, prompt, seed, temperature, is_openai, is_reasoning
            )

        # Authorization header carries the token when auth is required; never
        # echoed back in logs or errors. For the no-auth proxy, no Authorization
        # header is sent at all (the proxy accepts requests without one).
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self.require_auth:
            headers["Authorization"] = f"Bearer {token}"

        url = f"{self.base_url}/chat/completions"
        body_bytes = json.dumps(payload).encode("utf-8")

        # ── HTTP retry loop ─────────────────────────────────────────────────────
        # TOKEN-SAFETY INVARIANT (BLOCKER fix):
        #   Python sets __context__ on a raised exception to the currently-handled
        #   exception even when using `from None` (which only clears __cause__).
        #   A urllib HTTPError can carry the API token in its body/headers, so any
        #   raise INSIDE an `except HTTPError` block leaks the token via __context__.
        #   Fix: inside each except block we drain+discard response data and copy
        #   ONLY the integer status code to a local variable, then exit the except
        #   scope via break/continue WITHOUT raising. All _OnlineModeError raises
        #   happen AFTER the loop, outside any except scope, guaranteeing
        #   __context__ = None on the terminal exception.
        #
        # MAJOR 3 fix: _record_request_time() is in `finally` so every urlopen
        #   attempt — including URLError/timeout — is counted in the rate-limit window.
        # MAJOR 5: urlopen receives a finite, configurable timeout.
        _MAX_HTTP_RETRIES = 6
        resp_data: Dict[str, Any] = {}
        _http_success: bool = False
        _last_status: Optional[int] = None      # last retriable status (429/5xx)
        _terminal_status: Optional[int] = None  # terminal 4xx status
        _terminal_body: str = ""                # scrubbed terminal error body
        _had_transport_error: bool = False       # URLError / timeout
        _day_cap_hit: bool = False               # x-ratelimit-type=UserByModelByDay detected

        for attempt in range(_MAX_HTTP_RETRIES):
            self._enforce_rate_limit()            # throttle EVERY attempt (MAJOR 3)

            req = urllib.request.Request(
                url, data=body_bytes, headers=headers, method="POST"
            )
            _attempt_status: Optional[int] = None
            _is_transport: bool = False
            _is_day_cap: bool = False  # set if this attempt hit the day cap
            _scrubbed_body: str = ""

            try:
                with urllib.request.urlopen(req, timeout=self._http_timeout) as resp:
                    resp_data = json.loads(resp.read())
                _http_success = True
            except urllib.error.HTTPError as exc:
                # ── Drain+discard exc; copy ONLY the int status ────────────────
                # Nothing that references `exc` beyond this block.
                _attempt_status = exc.code
                # Check for day-cap header BEFORE reading/closing the response.
                # Day-cap (UserByModelByDay) is permanent — do not retry.
                # Read the header flag here so we can decide outside the except scope.
                if _attempt_status == 429:
                    try:
                        _is_day_cap = (
                            exc.headers.get("x-ratelimit-type", "") == "UserByModelByDay"
                        )
                    except Exception:
                        pass  # headers inaccessible — treat as regular 429
                _is_retriable = (_attempt_status == 429 or 500 <= _attempt_status < 600)
                if not _is_retriable:
                    # Terminal: read body once, scrub token, store
                    try:
                        _scrubbed_body = exc.read().decode("utf-8", errors="replace")
                        # Guard: never call str.replace("", ...) — an empty token
                        # (proxy provider has none) would otherwise splice
                        # "[REDACTED]" between every character of the body.
                        if token:
                            _scrubbed_body = _scrubbed_body.replace(token, "[REDACTED]")
                    except Exception:
                        _scrubbed_body = "(unreadable)"
                else:
                    # Retriable: drain body without saving
                    try:
                        exc.read()
                    except Exception:
                        pass
                try:
                    exc.close()
                except Exception:
                    pass
                # exc is fully drained/closed; nothing below this line holds a ref to it
            except urllib.error.URLError:
                # Network errors (DNS failure, connection refused, timeout wrapper)
                _is_transport = True
            finally:
                # Record EVERY attempt regardless of outcome (MAJOR 3 fix)
                self._record_request_time()

            # ── Decision logic: OUTSIDE all except scopes ─────────────────────
            # No exception is being handled here.  Any raise below will have
            # __context__ = None because there is no active exception in scope.
            if _http_success:
                break

            # Day-cap is permanent (daily quota; ~24h reset) — do not retry.
            # Raise DayCapped AFTER the loop so __context__ is guaranteed None.
            if _is_day_cap:
                _day_cap_hit = True
                break

            if _is_transport:
                _had_transport_error = True
                if attempt < _MAX_HTTP_RETRIES - 1:
                    time.sleep(min(2.0 ** attempt + random.uniform(0.0, 1.0), 60.0))
                    continue
                break  # exhausted — raise below

            # _attempt_status is set
            if _attempt_status == 429 or (500 <= _attempt_status < 600):
                _last_status = _attempt_status
                if attempt < _MAX_HTTP_RETRIES - 1:
                    time.sleep(min(2.0 ** attempt + random.uniform(0.0, 1.0), 60.0))
                    continue
                break  # exhausted — raise below
            else:
                # 4xx non-429: fail immediately
                _terminal_status = _attempt_status
                _terminal_body = _scrubbed_body
                break  # raise below

        # ── Raise AFTER loop — no active exception → __context__ is None ───────
        # Day-cap: permanent within the day; raise before generic error handling.
        if _day_cap_hit:
            raise DayCapped(slug)  # __context__ = None (outside all except scopes)

        if not _http_success:
            if _terminal_status is not None:
                raise _OnlineModeError(
                    f"HTTP {_terminal_status} error from API: {_terminal_body}"
                )
            if _had_transport_error:
                raise _OnlineModeError(
                    f"Transport error: gave up after {_MAX_HTTP_RETRIES} retries"
                )
            raise _OnlineModeError(
                f"HTTP {_last_status}: gave up after {_MAX_HTTP_RETRIES} retries"
            )

        # ── Parse response ─────────────────────────────────────────────────────
        choice = resp_data["choices"][0]
        text = choice["message"]["content"]
        usage = resp_data.get("usage", {})
        tokens_in = int(usage.get("prompt_tokens", 0))
        tokens_out = int(usage.get("completion_tokens", 0))

        # ── Cost estimate + budget accumulation ───────────────────────────────
        # Proxy is free/unlimited → 0.0; GitHub Models uses the pricing table.
        cost_usd = self._estimate_cost_for(slug, tokens_in, tokens_out)
        self._total_cost_usd += cost_usd

        # ── logit_conf ─────────────────────────────────────────────────────────
        # GitHub Models: only non-reasoning openai/* slugs expose logprobs.
        # Copilot proxy: logprobs are requested for every slug (harmless — no slug
        #   rejects the field) and _extract_logit_conf returns the signal ONLY when
        #   the response actually carries logprobs. Empirically that is the OpenAI
        #   families (gpt-4o-mini, gpt-5.4 → logprobs returned); Anthropic / Google /
        #   mai return none → logit_conf is None and callers fall back to verbalized
        #   confidence, exactly as reasoning models already do.
        if is_proxy:
            logit_conf: Optional[float] = self._extract_logit_conf(choice)
        else:
            logit_conf = (
                self._extract_logit_conf(choice)
                if (is_openai and not is_reasoning)
                else None
            )

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

    def _estimate_cost_for(self, slug: str, tokens_in: int, tokens_out: int) -> float:
        """Provider-aware cost estimate.

        The local copilot_proxy is free / unlimited, so its per-call cost is 0.0 —
        this keeps budget pre-authorization and accumulation consistent with reality
        (a budget cap never spuriously blocks proxy calls). GitHub Models uses the
        pricing table via :meth:`_estimate_cost`.
        """
        if self.provider == PROVIDER_COPILOT_PROXY:
            return 0.0
        return self._estimate_cost(slug, tokens_in, tokens_out)

    # ── Per-provider request-shape builders ───────────────────────────────────

    def _build_github_models_payload(
        self,
        slug: str,
        prompt: str,
        seed: int,
        temperature: Optional[float],
        is_openai: bool,
        is_reasoning: bool,
    ) -> Dict[str, Any]:
        """Build the GitHub Models chat/completions payload (UNCHANGED behavior).

        Reasoning models (o-series / gpt-5*) use ``max_completion_tokens`` and send
        neither ``logprobs`` nor ``temperature``. Non-reasoning models use
        ``max_tokens``; ``temperature`` is included when provided; ``logprobs`` is
        requested only for openai/* slugs.
        """
        payload: Dict[str, Any] = {
            "model": slug,
            "messages": [{"role": "user", "content": prompt}],
            "seed": seed,
        }
        if is_reasoning:
            # o-series / gpt-5*: use max_completion_tokens (not max_tokens);
            # do NOT send logprobs (HTTP 400) or temperature (not accepted).
            payload["max_completion_tokens"] = self._max_tokens_per_call
        else:
            # All non-reasoning models: max_tokens enforces the output cap.
            payload["max_tokens"] = self._max_tokens_per_call
            # Include temperature when caller provided one (never for reasoning models).
            if temperature is not None:
                payload["temperature"] = temperature
            if is_openai:
                # Non-reasoning OpenAI: logprobs supported → logit_conf populated.
                payload["logprobs"] = True
                payload["top_logprobs"] = 1
        return payload

    def _build_proxy_payload(
        self,
        slug: str,
        prompt: str,
        seed: int,
        temperature: Optional[float],
    ) -> Dict[str, Any]:
        """Build the copilot_proxy chat/completions payload.

        Request shape determined empirically by live-probing the local proxy
        (OpenAI-compatible ``/v1/chat/completions``) on 2026-07-17:

          * ``max_completion_tokens`` is accepted by EVERY probed family
            (gpt-4o-mini, gpt-5.x, claude-*, gemini-*, mai-code) whereas
            ``max_tokens`` returns HTTP 400 for gpt-5.x. We therefore ALWAYS use
            ``max_completion_tokens`` — the single universally-accepted output cap.
          * ``logprobs``/``top_logprobs`` are accepted (never 400) by every family;
            only the OpenAI families actually RETURN logprobs (gpt-4o-mini, gpt-5.4),
            so we request them unconditionally and extract logit_conf when present
            (None otherwise → verbalized-confidence fallback).
          * ``temperature`` is accepted by most slugs but rejected with HTTP 400 by a
            few frontier / picker slugs (gpt-5.6-*, mai-code-*). It is omitted for
            any slug matching the configurable ``no_temperature_models`` allow-list.
          * ``seed`` is accepted by every family.
        """
        payload: Dict[str, Any] = {
            "model": slug,
            "messages": [{"role": "user", "content": prompt}],
            "seed": seed,
            "max_completion_tokens": self._max_tokens_per_call,
            "logprobs": True,
            "top_logprobs": 1,
        }
        if temperature is not None and not proxy_omits_temperature(
            slug, self.no_temperature_models
        ):
            payload["temperature"] = temperature
        return payload


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
