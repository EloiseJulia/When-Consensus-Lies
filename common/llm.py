"""LLM client with offline mock mode, caching, retry, and cost logging.

DEFAULT OFFLINE MOCK MODE: deterministic output derived from hash(role, prompt, seed).
No API key required. Works entirely offline.
"""

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any


@dataclass
class Completion:
    """LLM completion result."""
    text: str
    model: str
    tokens_in: int
    tokens_out: int
    cost_usd: float


class LLMClient:
    """Multi-provider LLM client with role-based routing.
    
    Operates in offline mock mode by default (no API key needed).
    Mock outputs are deterministic, keyed by (role, prompt, seed).
    """
    
    def __init__(self, config: Dict[str, Any], cache_dir: str = ".llm_cache", offline: bool = True):
        """Initialize LLM client.
        
        Args:
            config: Loaded config dict (from config.py)
            cache_dir: Directory for disk cache
            offline: If True, use deterministic mock mode (default)
        """
        self.config = config
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.offline = offline
        self.cost_log_path = self.cache_dir / "cost_log.jsonl"
        
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
            except NotImplementedError:
                raise  # permanent (e.g. online mode deferred) — never retry
            except Exception:
                if attempt == max_retries - 1:
                    raise
                time.sleep(2 ** attempt)  # Exponential backoff
        
        raise RuntimeError("Max retries exceeded")
    
    def _generate(self, role: str, prompt: str, seed: int, family: Optional[str] = None, model: Optional[str] = None) -> Completion:
        """Generate completion (offline mock mode by default)."""
        if self.offline:
            return self._mock_generate(role, prompt, seed, family, model)
        else:
            # Real API calls would go here (Phase 1+)
            raise NotImplementedError("Online mode deferred to Phase 1")
    
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
                return Completion(**data)
        return None
    
    def _write_cache(self, cache_key: str, completion: Completion) -> None:
        """Write to disk cache."""
        cache_file = self.cache_dir / f"{cache_key}.json"
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(completion.__dict__, f)
    
    def _log_cost(self, role: str, prompt: str, completion: Completion) -> None:
        """Log API call cost."""
        log_entry = {
            "timestamp": time.time(),
            "role": role,
            "model": completion.model,
            "tokens_in": completion.tokens_in,
            "tokens_out": completion.tokens_out,
            "cost_usd": completion.cost_usd,
            "prompt_len": len(prompt),
        }
        with open(self.cost_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
