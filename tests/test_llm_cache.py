"""Cache-integrity tests for common.llm.LLMClient.

Guards the round-3 provenance bug: the cache must not cross-serve an offline
mock to an online client, and the cache key must be mode/model aware.
"""

import pytest
from common.config import load_config
from common.llm import LLMClient


def test_offline_cache_hit_is_deterministic(tmp_path):
    cfg = load_config()
    c1 = LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=True)
    first = c1.complete(role="tested_agents", prompt="p", seed=1)
    # Fresh client, same cache dir -> should read the cached entry, same text.
    c2 = LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=True)
    second = c2.complete(role="tested_agents", prompt="p", seed=1)
    assert first.text == second.text
    assert first.cost_usd == 0.0


def test_online_client_not_served_offline_mock(tmp_path):
    """offline=False must NOT return an offline-cached mock; online is deferred."""
    cfg = load_config()
    cache = str(tmp_path / "c")
    # Warm the offline cache for this exact (role, prompt, seed).
    LLMClient(cfg, cache_dir=cache, offline=True).complete(
        role="tested_agents", prompt="p", seed=1
    )
    online = LLMClient(cfg, cache_dir=cache, offline=False)
    with pytest.raises(NotImplementedError):
        online.complete(role="tested_agents", prompt="p", seed=1)


def test_cache_key_is_mode_and_model_aware(tmp_path):
    cfg = load_config()
    client = LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=True)
    offline_key = client._cache_key("tested_agents", "p", 1, None, None)
    client.offline = False
    online_key = client._cache_key("tested_agents", "p", 1, None, None)
    assert offline_key != online_key


def test_unknown_role_fails_fast(tmp_path):
    """A typoed role must raise, not fabricate mock-model provenance."""
    cfg = load_config()
    client = LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=True)
    with pytest.raises(ValueError):
        client.complete(role="typo_role", prompt="p", seed=1)

