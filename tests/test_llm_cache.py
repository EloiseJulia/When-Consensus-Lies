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


def test_online_client_not_served_offline_mock(tmp_path, monkeypatch):
    """offline=False must NOT serve an offline-cached mock.

    After Phase 3 online mode is implemented this test verifies the behaviour by
    mocking the HTTP layer: the online client must call the API and return the
    network response, NOT the previously-cached offline mock.
    """
    import io
    import json
    import urllib.error

    cfg = load_config()
    cache = str(tmp_path / "c")

    # Warm the offline cache for this exact (role, prompt, seed).
    offline_result = LLMClient(cfg, cache_dir=cache, offline=True).complete(
        role="tested_agents", prompt="p", seed=1
    )

    # Mock HTTP: any POST → return a known "ONLINE_RESULT" response
    online_text = "ONLINE_RESULT_DISTINCT_FROM_MOCK"
    mock_resp_bytes = json.dumps({
        "choices": [{"message": {"content": online_text}, "logprobs": None,
                     "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 2, "completion_tokens": 4},
        "model": "openai/gpt-4o-mini",
    }).encode("utf-8")

    class _FakeHTTPResponse:
        def read(self):
            return mock_resp_bytes
        def __enter__(self):
            return self
        def __exit__(self, *_):
            pass

    monkeypatch.setenv("GITHUB_MODELS_TOKEN", "fake-token-for-test")
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **kw: _FakeHTTPResponse())

    online = LLMClient(cfg, cache_dir=cache, offline=False)
    result = online.complete(role="tested_agents", prompt="p", seed=1)

    # Online result must be the network response, NOT the offline mock
    assert result.text == online_text, (
        f"Online client returned offline mock '{result.text}' instead of '{online_text}'"
    )
    assert result.text != offline_result.text


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

