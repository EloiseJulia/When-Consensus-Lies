"""Provider-abstraction tests for common/llm.py (copilot_proxy vs github_models).

OFFLINE tests mock urllib.request.urlopen — no network. They verify:
  * provider selection resolves base_url + auth defaults (param / config / default)
  * the copilot_proxy request shape (max_completion_tokens always; logprobs always;
    temperature gated by the no_temperature_models allow-list)
  * NO Authorization header + no token requirement for the proxy
  * the GitHub Models path is byte-for-byte unchanged (max_tokens, Bearer header)
  * the cache key separates providers / base_urls
  * proxy cost is 0.0

A GUARDED LIVE smoke (RUN_PROXY_SMOKE=1) hits the real local proxy and records the
per-family request-shape findings.
"""

import io
import json
import os
import urllib.error
import urllib.request

import pytest

from common.config import load_config
from common.llm import (
    COPILOT_PROXY_BASE_URL,
    GITHUB_MODELS_BASE_URL,
    PROVIDER_COPILOT_PROXY,
    PROVIDER_GITHUB_MODELS,
    Completion,
    LLMClient,
    proxy_omits_temperature,
)

FAKE_TOKEN = "FAKE_TEST_TOKEN_NEVER_USE_IN_PRODUCTION_XYZ123"


@pytest.fixture
def cfg():
    return load_config()


def _ok_response(text="OK", model="gpt-4o-mini", tokens_in=3, tokens_out=1,
                 logprobs_content=None):
    return json.dumps({
        "choices": [{
            "message": {"content": text},
            "logprobs": ({"content": logprobs_content}
                         if logprobs_content is not None else None),
            "finish_reason": "stop",
        }],
        "usage": {"prompt_tokens": tokens_in, "completion_tokens": tokens_out},
        "model": model,
    }).encode("utf-8")


class _FakeResp:
    def __init__(self, body):
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass


def _capture_urlopen(store):
    def mock(request, *a, **kw):
        store["headers"] = dict(request.headers)
        store["body"] = json.loads(request.data.decode("utf-8"))
        store["url"] = request.full_url
        return _FakeResp(_ok_response())
    return mock


# ── Provider resolution ────────────────────────────────────────────────────────

def test_default_provider_is_github_models(tmp_path, cfg):
    client = LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=True)
    assert client.provider == PROVIDER_GITHUB_MODELS
    assert client.base_url == GITHUB_MODELS_BASE_URL
    assert client.require_auth is True


def test_proxy_provider_resolves_base_url_and_no_auth(tmp_path, cfg):
    client = LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=True,
                       provider=PROVIDER_COPILOT_PROXY)
    assert client.provider == PROVIDER_COPILOT_PROXY
    assert client.base_url == COPILOT_PROXY_BASE_URL
    assert client.require_auth is False


def test_explicit_base_url_overrides_provider_default(tmp_path, cfg):
    client = LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=True,
                       provider=PROVIDER_COPILOT_PROXY,
                       base_url="http://127.0.0.1:8787/v1")
    assert client.base_url == "http://127.0.0.1:8787/v1"


def test_unknown_provider_raises(tmp_path, cfg):
    with pytest.raises(ValueError):
        LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=True,
                  provider="not_a_provider")


def test_config_providers_block_is_read(tmp_path, cfg):
    """The config providers block supplies base_url/require_auth defaults."""
    assert cfg["providers"]["copilot_proxy"]["require_auth"] is False
    client = LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=True,
                       provider=PROVIDER_COPILOT_PROXY)
    # base_url comes from the config providers block (matches proxy default)
    assert client.base_url == cfg["providers"]["copilot_proxy"]["base_url"].rstrip("/")


# ── Proxy request shape (offline, mocked HTTP) ─────────────────────────────────

def test_proxy_no_token_required_and_no_auth_header(tmp_path, cfg, monkeypatch):
    """Proxy must NOT require a token and must NOT send an Authorization header."""
    monkeypatch.delenv("GITHUB_MODELS_TOKEN", raising=False)
    monkeypatch.delenv("GH_MODELS_TOKEN", raising=False)
    store = {}
    monkeypatch.setattr("urllib.request.urlopen", _capture_urlopen(store))

    client = LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=False,
                       provider=PROVIDER_COPILOT_PROXY)
    res = client.complete(role="tested_agents", prompt="hello", seed=1,
                          family="openai", model="gpt-4o-mini")
    assert res.text == "OK"
    assert "Authorization" not in store["headers"], store["headers"]
    assert store["url"].startswith(COPILOT_PROXY_BASE_URL)


def test_proxy_uses_max_completion_tokens_not_max_tokens(tmp_path, cfg, monkeypatch):
    store = {}
    monkeypatch.setattr("urllib.request.urlopen", _capture_urlopen(store))
    client = LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=False,
                       provider=PROVIDER_COPILOT_PROXY)
    client.complete(role="tested_agents", prompt="p", seed=1,
                    family="anthropic", model="claude-opus-4.8")
    assert "max_completion_tokens" in store["body"]
    assert "max_tokens" not in store["body"]


def test_proxy_always_requests_logprobs(tmp_path, cfg, monkeypatch):
    store = {}
    monkeypatch.setattr("urllib.request.urlopen", _capture_urlopen(store))
    client = LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=False,
                       provider=PROVIDER_COPILOT_PROXY)
    # Even a non-openai family gets logprobs requested (harmless on the proxy)
    client.complete(role="tested_agents", prompt="p", seed=1,
                    family="google", model="gemini-3.5-flash")
    assert store["body"].get("logprobs") is True
    assert store["body"].get("top_logprobs") == 1


def test_proxy_temperature_included_for_supported_slug(tmp_path, cfg, monkeypatch):
    store = {}
    monkeypatch.setattr("urllib.request.urlopen", _capture_urlopen(store))
    client = LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=False,
                       provider=PROVIDER_COPILOT_PROXY)
    client.complete(role="tested_agents", prompt="p", seed=1, temperature=0.7,
                    family="openai", model="gpt-5.4")
    assert store["body"].get("temperature") == 0.7


def test_proxy_temperature_omitted_for_unsupported_slug(tmp_path, cfg, monkeypatch):
    store = {}
    monkeypatch.setattr("urllib.request.urlopen", _capture_urlopen(store))
    client = LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=False,
                       provider=PROVIDER_COPILOT_PROXY)
    # gpt-5.6-sol and mai-code-* reject temperature on the live proxy → omit it.
    client.complete(role="tested_agents", prompt="p", seed=1, temperature=0.7,
                    family="openai", model="gpt-5.6-sol")
    assert "temperature" not in store["body"]
    store.clear()
    client.complete(role="tested_agents", prompt="p2", seed=1, temperature=0.7,
                    family="mai", model="mai-code-1-flash-picker")
    assert "temperature" not in store["body"]


def test_proxy_omits_temperature_helper():
    assert proxy_omits_temperature("gpt-5.6-sol") is True
    assert proxy_omits_temperature("gpt-5.6-terra") is True
    assert proxy_omits_temperature("mai-code-1-flash-picker") is True
    assert proxy_omits_temperature("gpt-5.4") is False
    assert proxy_omits_temperature("gpt-4o-mini") is False
    assert proxy_omits_temperature("claude-opus-4.8") is False
    assert proxy_omits_temperature("gemini-3.5-flash") is False
    # Custom pattern list is honored
    assert proxy_omits_temperature("gpt-4o-mini", patterns=("gpt-4o",)) is True


def test_proxy_no_temperature_models_configurable(tmp_path, cfg, monkeypatch):
    store = {}
    monkeypatch.setattr("urllib.request.urlopen", _capture_urlopen(store))
    client = LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=False,
                       provider=PROVIDER_COPILOT_PROXY,
                       no_temperature_models=("claude",))
    client.complete(role="tested_agents", prompt="p", seed=1, temperature=0.3,
                    family="anthropic", model="claude-opus-4.8")
    assert "temperature" not in store["body"]


def test_proxy_cost_is_zero(tmp_path, cfg, monkeypatch):
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *a, **kw: _FakeResp(_ok_response(tokens_in=100, tokens_out=100)),
    )
    client = LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=False,
                       provider=PROVIDER_COPILOT_PROXY)
    res = client.complete(role="tested_agents", prompt="p", seed=1,
                          family="openai", model="gpt-4o-mini")
    assert res.cost_usd == 0.0
    assert client._total_cost_usd == 0.0


def test_proxy_logit_conf_populated_when_logprobs_returned(tmp_path, cfg, monkeypatch):
    import math
    lp = [{"token": " OK", "logprob": -0.25}]
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *a, **kw: _FakeResp(_ok_response(logprobs_content=lp, model="gpt-4o-mini")),
    )
    client = LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=False,
                       provider=PROVIDER_COPILOT_PROXY)
    res = client.complete(role="tested_agents", prompt="p", seed=1,
                          family="openai", model="gpt-4o-mini")
    assert res.logit_conf is not None
    assert abs(res.logit_conf - math.exp(-0.25)) < 1e-9


def test_proxy_logit_conf_none_when_no_logprobs(tmp_path, cfg, monkeypatch):
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *a, **kw: _FakeResp(_ok_response(model="claude-opus-4.8")),
    )
    client = LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=False,
                       provider=PROVIDER_COPILOT_PROXY)
    res = client.complete(role="tested_agents", prompt="p", seed=1,
                          family="anthropic", model="claude-opus-4.8")
    assert res.logit_conf is None


# ── GitHub Models path unchanged (regression) ──────────────────────────────────

def test_github_models_path_unchanged_max_tokens_and_bearer(tmp_path, cfg, monkeypatch):
    monkeypatch.setenv("GITHUB_MODELS_TOKEN", FAKE_TOKEN)
    store = {}
    monkeypatch.setattr("urllib.request.urlopen", _capture_urlopen(store))
    client = LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=False)
    client.complete(role="tested_agents", prompt="p", seed=1,
                    family="meta", model="meta/llama-3.3-70b-instruct")
    assert "max_tokens" in store["body"]
    assert "max_completion_tokens" not in store["body"]
    assert store["headers"].get("Authorization", "").startswith("Bearer ")
    assert store["url"].startswith(GITHUB_MODELS_BASE_URL)


def test_github_models_still_requires_token(tmp_path, cfg, monkeypatch):
    monkeypatch.delenv("GITHUB_MODELS_TOKEN", raising=False)
    monkeypatch.delenv("GH_MODELS_TOKEN", raising=False)
    client = LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=False)
    with pytest.raises(RuntimeError, match="requires an API token"):
        client.complete(role="tested_agents", prompt="p", seed=1,
                        family="openai", model="openai/gpt-4o-mini")


# ── Cache-key provider separation ──────────────────────────────────────────────

def test_cache_key_separates_providers(tmp_path, cfg):
    gh = LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=False)
    px = LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=False,
                   provider=PROVIDER_COPILOT_PROXY)
    k_gh = gh._cache_key("tested_agents", "p", 1, "openai", "gpt-4o-mini", None)
    k_px = px._cache_key("tested_agents", "p", 1, "openai", "gpt-4o-mini", None)
    assert k_gh != k_px, "same slug/prompt must not collide across providers"


def test_cache_key_separates_base_urls(tmp_path, cfg):
    a = LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=False,
                  provider=PROVIDER_COPILOT_PROXY, base_url="http://127.0.0.1:8313/v1")
    b = LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=False,
                  provider=PROVIDER_COPILOT_PROXY, base_url="http://127.0.0.1:8787/v1")
    ka = a._cache_key("tested_agents", "p", 1, "openai", "gpt-4o-mini", None)
    kb = b._cache_key("tested_agents", "p", 1, "openai", "gpt-4o-mini", None)
    assert ka != kb


def test_proxy_and_github_do_not_cross_serve(tmp_path, cfg, monkeypatch):
    """A proxy result must never be served to a github_models client (same cache dir)."""
    cache = str(tmp_path / "shared")
    monkeypatch.delenv("GITHUB_MODELS_TOKEN", raising=False)
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *a, **kw: _FakeResp(_ok_response(text="PROXY_RESULT")),
    )
    px = LLMClient(cfg, cache_dir=cache, offline=False, provider=PROVIDER_COPILOT_PROXY)
    px.complete(role="tested_agents", prompt="p", seed=1,
                family="openai", model="gpt-4o-mini")

    monkeypatch.setenv("GITHUB_MODELS_TOKEN", FAKE_TOKEN)
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *a, **kw: _FakeResp(_ok_response(text="GH_RESULT")),
    )
    gh = LLMClient(cfg, cache_dir=cache, offline=False)
    res = gh.complete(role="tested_agents", prompt="p", seed=1,
                      family="openai", model="openai/gpt-4o-mini")
    assert res.text == "GH_RESULT"


# ── Guarded LIVE smoke (real local proxy) ──────────────────────────────────────

_SMOKE_MODEL = os.environ.get("PROXY_SMOKE_MODEL", "gemini-3.5-flash")


@pytest.mark.skipif(
    os.environ.get("RUN_PROXY_SMOKE") != "1",
    reason="live proxy smoke disabled; set RUN_PROXY_SMOKE=1 to run",
)
def test_live_proxy_smoke(tmp_path, cfg):
    """Hit the real local proxy on a cheap model and assert a response.

    Also probes the per-family request-shape (max_tokens vs max_completion_tokens,
    temperature, logprobs) and prints the findings for the record.
    """
    client = LLMClient(
        cfg, cache_dir=str(tmp_path / "c"), offline=False,
        provider=PROVIDER_COPILOT_PROXY, max_tokens_per_call=256,
    )
    res = client.complete(role="tested_agents", prompt="Reply with the single word: OK",
                          seed=1, family="google", model=_SMOKE_MODEL, temperature=0.0)
    assert isinstance(res, Completion)
    assert res.text and len(res.text.strip()) > 0
    assert res.cost_usd == 0.0

    # ── Per-family request-shape probe (raw HTTP; printed for the record) ──────
    findings = _probe_request_shapes()
    print("\n===== LIVE proxy per-family request-shape findings =====")
    for slug, row in findings.items():
        print(f"  {slug:26s} max_tokens={row['max_tokens']:>4} "
              f"max_completion_tokens={row['mct']:>4} "
              f"temperature={row['temperature']:>4} "
              f"logprobs_returned={row['logprobs']}")


def _probe_request_shapes():
    """Return {slug: {max_tokens, mct, temperature, logprobs}} from the live proxy."""
    probes = {
        "gpt-4o-mini": "openai",
        "gpt-5.4": "openai-frontier",
        "gpt-5.6-sol": "openai-frontier",
        "claude-haiku-4.5": "anthropic",
        "gemini-3.5-flash": "google",
        "mai-code-1-flash-picker": "mai",
    }
    out = {}
    base = COPILOT_PROXY_BASE_URL
    msg = [{"role": "user", "content": "Reply with the single word: OK"}]

    def post(payload):
        req = urllib.request.Request(
            base + "/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                return 200, json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            return exc.code, None
        except urllib.error.URLError:
            return -1, None

    for slug in probes:
        row = {}
        code, _ = post({"model": slug, "messages": msg, "max_tokens": 32})
        row["max_tokens"] = "OK" if code == 200 else str(code)
        code, _ = post({"model": slug, "messages": msg, "max_completion_tokens": 32})
        row["mct"] = "OK" if code == 200 else str(code)
        code, _ = post({"model": slug, "messages": msg,
                        "max_completion_tokens": 32, "temperature": 0.7})
        row["temperature"] = "OK" if code == 200 else str(code)
        code, data = post({"model": slug, "messages": msg,
                           "max_completion_tokens": 32, "logprobs": True, "top_logprobs": 1})
        has_lp = False
        if code == 200 and data:
            try:
                has_lp = bool(data["choices"][0].get("logprobs"))
            except Exception:
                has_lp = False
        row["logprobs"] = has_lp
        out[slug] = row
    return out
