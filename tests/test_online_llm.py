"""Offline-safe tests for the online LLM path (common/llm.py).

ALL tests here mock the HTTP layer (urllib.request.urlopen) — no network calls.
The token env var is always a fake string; the real token is never required.

Test coverage:
  1. Request carries the correct model slug and Authorization: Bearer header
  2. logprobs requested only for openai/* slugs; not for other families
  3. BudgetExceeded raised when spend cap is hit; not retried by outer loop
  4. HTTP 429 triggers bounded exponential backoff + succeeds on retry
  5. Persistent 429 gives up after bounded retries (no infinite loop)
  6. HTTP 5xx triggers bounded retry
  7. HTTP 4xx (non-429) fails loud immediately (single attempt)
  8. Cache hit skips the HTTP call entirely (one network call, then cached)
  9. Token string never appears in any log or exception message
 10. Offline default unchanged (all offline tests still pass)
 11. Non-openai slugs produce logit_conf=None
"""

import io
import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any, Dict
from unittest.mock import MagicMock, call, patch

import pytest

from common.config import load_config
from common.llm import BudgetExceeded, Completion, LLMClient


# ── Shared helpers ─────────────────────────────────────────────────────────────

FAKE_TOKEN = "FAKE_TEST_TOKEN_NEVER_USE_IN_PRODUCTION_XYZ123"


def _make_ok_response(
    text: str = "test response",
    model: str = "openai/gpt-4o-mini",
    tokens_in: int = 10,
    tokens_out: int = 5,
    logprobs_content: Any = None,
) -> bytes:
    """Build a minimal OpenAI-compatible JSON response body."""
    return json.dumps({
        "choices": [{
            "message": {"content": text},
            "logprobs": (
                {"content": logprobs_content} if logprobs_content is not None else None
            ),
            "finish_reason": "stop",
        }],
        "usage": {"prompt_tokens": tokens_in, "completion_tokens": tokens_out},
        "model": model,
    }).encode("utf-8")


class _FakeHTTPResponse:
    """Context-manager mock for a successful urllib response."""
    def __init__(self, body: bytes):
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass


def _make_http_error(status: int, body: bytes = b"error") -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        url="http://test",
        code=status,
        msg=f"HTTP {status}",
        hdrs={},  # type: ignore[arg-type]
        fp=io.BytesIO(body),
    )


@pytest.fixture
def cfg():
    return load_config()


@pytest.fixture
def online_client(tmp_path, cfg, monkeypatch):
    """Online LLMClient with fake token injected."""
    monkeypatch.setenv("GITHUB_MODELS_TOKEN", FAKE_TOKEN)
    return LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=False)


# ── Test 1: request shape (slug + Bearer header) ──────────────────────────────

def test_request_carries_correct_slug_and_bearer_header(
    tmp_path, cfg, monkeypatch
):
    """The HTTP POST must carry the model slug and a Bearer Authorization header."""
    monkeypatch.setenv("GITHUB_MODELS_TOKEN", FAKE_TOKEN)

    captured: Dict[str, Any] = {}

    def mock_urlopen(request, *args, **kwargs):
        captured["headers"] = dict(request.headers)
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return _FakeHTTPResponse(_make_ok_response())

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

    client = LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=False)
    # The config routes tested_agents → openai/gpt-4o-mini in the new config
    client.complete(role="tested_agents", prompt="hello", seed=42)

    # Slug from config must appear in the request body
    assert captured["body"]["model"] == "openai/gpt-4o-mini"

    # Authorization header must be Bearer (token value not checked here to
    # avoid hardcoding; see test_token_never_logged_or_in_exceptions)
    auth = captured["headers"].get("Authorization", "")
    assert auth.startswith("Bearer "), f"Expected 'Bearer ...', got: {auth!r}"
    # Token must be present (non-empty) but we only check it starts with Bearer
    assert len(auth) > len("Bearer ")


# ── Test 2: logprobs only for openai slugs ────────────────────────────────────

def test_logprobs_requested_only_for_openai_slugs(tmp_path, cfg, monkeypatch):
    """logprobs=True must be included for openai/* slugs only."""
    monkeypatch.setenv("GITHUB_MODELS_TOKEN", FAKE_TOKEN)

    payloads = []

    def mock_urlopen(request, *args, **kwargs):
        payloads.append(json.loads(request.data.decode("utf-8")))
        return _FakeHTTPResponse(_make_ok_response(model=request.data and
            json.loads(request.data).get("model", "")))

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

    client = LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=False)

    # openai slug: logprobs should be requested
    client.complete(role="tested_agents", prompt="p_openai", seed=1,
                    family="openai", model="openai/gpt-4o-mini")
    assert payloads[-1].get("logprobs") is True, "logprobs must be True for openai slug"
    assert "top_logprobs" in payloads[-1]

    # Non-openai slug: logprobs must NOT be requested
    client.complete(role="tested_agents", prompt="p_meta", seed=2,
                    family="meta", model="meta/llama-3.3-70b-instruct")
    assert "logprobs" not in payloads[-1], "logprobs must not be sent for non-openai slug"


# ── Test 3: non-openai logit_conf is None ─────────────────────────────────────

def test_non_openai_logit_conf_is_none(tmp_path, cfg, monkeypatch):
    """Non-openai completions must have logit_conf=None."""
    monkeypatch.setenv("GITHUB_MODELS_TOKEN", FAKE_TOKEN)
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *a, **kw: _FakeHTTPResponse(_make_ok_response(model="meta/llama-3.3-70b-instruct")),
    )
    client = LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=False)
    result = client.complete(role="tested_agents", prompt="p", seed=1,
                             family="meta", model="meta/llama-3.3-70b-instruct")
    assert result.logit_conf is None


def test_openai_logit_conf_populated_from_logprobs(tmp_path, cfg, monkeypatch):
    """openai completions with logprobs data must have logit_conf != None."""
    import math
    monkeypatch.setenv("GITHUB_MODELS_TOKEN", FAKE_TOKEN)
    logprobs_content = [{"token": " hello", "logprob": -0.5}]
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *a, **kw: _FakeHTTPResponse(
            _make_ok_response(model="openai/gpt-4o-mini", logprobs_content=logprobs_content)
        ),
    )
    client = LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=False)
    result = client.complete(role="tested_agents", prompt="p", seed=1,
                             family="openai", model="openai/gpt-4o-mini")
    assert result.logit_conf is not None
    # exp(-0.5) ≈ 0.607
    assert abs(result.logit_conf - math.exp(-0.5)) < 1e-9


# ── Test 4: BudgetExceeded raised and not retried ─────────────────────────────

def test_budget_cap_raises_budget_exceeded(tmp_path, cfg, monkeypatch):
    """BudgetExceeded raised when accumulated cost >= cap."""
    monkeypatch.setenv("GITHUB_MODELS_TOKEN", FAKE_TOKEN)

    call_count = 0

    def mock_urlopen(request, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        # Return a response with many tokens to drive up cost
        return _FakeHTTPResponse(_make_ok_response(tokens_in=100_000, tokens_out=100_000))

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

    # Set a very low budget so the first call exceeds it
    client = LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=False,
                       max_budget_usd=0.00001)

    # First call should succeed (cost > budget only AFTER the call accumulates)
    # Pre-check: 0 < 0.00001, so first call goes through; post-call total > cap
    client.complete(role="tested_agents", prompt="first", seed=1)

    # Second call: pre-check sees total >= cap → BudgetExceeded before HTTP
    calls_before = call_count
    with pytest.raises(BudgetExceeded, match="Budget cap"):
        client.complete(role="tested_agents", prompt="second", seed=2)

    # No additional HTTP call should have been made
    assert call_count == calls_before, "BudgetExceeded should stop before any HTTP call"


def test_budget_exceeded_is_not_retried_by_outer_loop(tmp_path, cfg, monkeypatch):
    """BudgetExceeded must propagate immediately; the outer retry loop must not swallow it."""
    monkeypatch.setenv("GITHUB_MODELS_TOKEN", FAKE_TOKEN)

    urlopen_calls = 0

    def mock_urlopen(request, *args, **kwargs):
        nonlocal urlopen_calls
        urlopen_calls += 1
        return _FakeHTTPResponse(_make_ok_response(tokens_in=100_000, tokens_out=100_000))

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

    client = LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=False,
                       max_budget_usd=0.00001)
    client.complete(role="tested_agents", prompt="warmup", seed=0)

    calls_at_exceeded = urlopen_calls
    with pytest.raises(BudgetExceeded):
        # max_retries=5 — if BudgetExceeded were retried it would loop 5 times;
        # it must raise on the first attempt
        client.complete(role="tested_agents", prompt="should-not-retry", seed=99,
                        max_retries=5)

    # Zero additional HTTP calls (BudgetExceeded raised before urlopen)
    assert urlopen_calls == calls_at_exceeded


# ── Test 5: 429 backoff + success ─────────────────────────────────────────────

def test_429_triggers_backoff_then_succeeds(tmp_path, cfg, monkeypatch):
    """A 429 then 200 sequence: client must retry and return the success response."""
    monkeypatch.setenv("GITHUB_MODELS_TOKEN", FAKE_TOKEN)

    responses = [
        _make_http_error(429),
        _FakeHTTPResponse(_make_ok_response(text="after_retry")),
    ]
    call_index = 0

    def mock_urlopen(request, *args, **kwargs):
        nonlocal call_index
        r = responses[call_index]
        call_index += 1
        if isinstance(r, urllib.error.HTTPError):
            raise r
        return r

    slept: list = []
    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)
    monkeypatch.setattr("time.sleep", lambda t: slept.append(t))

    client = LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=False)
    result = client.complete(role="tested_agents", prompt="p", seed=1)

    assert result.text == "after_retry"
    assert call_index == 2, "Should have made exactly 2 HTTP attempts"
    assert len(slept) >= 1, "At least one sleep (backoff) must have occurred"
    assert all(t > 0 for t in slept), "Backoff durations must be positive"


# ── Test 6: persistent 429 gives up after bounded retries ─────────────────────

def test_persistent_429_bounded_giveup(tmp_path, cfg, monkeypatch):
    """Persistent 429 must raise RuntimeError after a bounded number of retries."""
    monkeypatch.setenv("GITHUB_MODELS_TOKEN", FAKE_TOKEN)

    call_count = 0

    def mock_urlopen(request, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        raise _make_http_error(429)

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)
    monkeypatch.setattr("time.sleep", lambda t: None)  # skip actual sleeping

    client = LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=False)
    with pytest.raises(RuntimeError, match="gave up"):
        client.complete(role="tested_agents", prompt="p", seed=1)

    # Must have made exactly _MAX_HTTP_RETRIES=6 attempts, not infinite
    assert call_count == 6, f"Expected 6 bounded retries, got {call_count}"


# ── Test 7: 5xx bounded retry ─────────────────────────────────────────────────

def test_5xx_triggers_bounded_retry(tmp_path, cfg, monkeypatch):
    """Persistent 5xx must raise RuntimeError after bounded retries."""
    monkeypatch.setenv("GITHUB_MODELS_TOKEN", FAKE_TOKEN)

    call_count = 0

    def mock_urlopen(request, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        raise _make_http_error(503)

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)
    monkeypatch.setattr("time.sleep", lambda t: None)

    client = LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=False)
    with pytest.raises(RuntimeError, match="gave up"):
        client.complete(role="tested_agents", prompt="p", seed=1)

    assert call_count == 6


# ── Test 8: non-429 4xx fails loud (single attempt) ──────────────────────────

def test_4xx_non_429_fails_loud_single_attempt(tmp_path, cfg, monkeypatch):
    """A 401/403 must raise RuntimeError immediately (no retry)."""
    monkeypatch.setenv("GITHUB_MODELS_TOKEN", FAKE_TOKEN)

    call_count = 0

    def mock_urlopen(request, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        raise _make_http_error(401, b"Unauthorized")

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

    client = LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=False)
    with pytest.raises(RuntimeError, match="401"):
        client.complete(role="tested_agents", prompt="p", seed=1)

    assert call_count == 1, "4xx (non-429) must not be retried"


# ── Test 9: cache hit skips HTTP call ─────────────────────────────────────────

def test_cache_hit_skips_http_call(tmp_path, cfg, monkeypatch):
    """A cache hit must return the stored result without any HTTP call."""
    monkeypatch.setenv("GITHUB_MODELS_TOKEN", FAKE_TOKEN)

    urlopen_calls = 0

    def mock_urlopen(request, *args, **kwargs):
        nonlocal urlopen_calls
        urlopen_calls += 1
        return _FakeHTTPResponse(_make_ok_response(text="cached_response"))

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

    client = LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=False)

    # First call: hits the network
    r1 = client.complete(role="tested_agents", prompt="cache_test", seed=7)
    assert urlopen_calls == 1

    # Second call (same args): must serve from cache, zero additional HTTP calls
    r2 = client.complete(role="tested_agents", prompt="cache_test", seed=7)
    assert urlopen_calls == 1, "Cache hit must not make a second HTTP call"
    assert r1.text == r2.text == "cached_response"


# ── Test 10: token never in logs or exception messages ────────────────────────

def test_token_never_appears_in_logs_or_exceptions(tmp_path, cfg, monkeypatch, caplog):
    """The API token must never appear in any log record or exception message."""
    secret_token = "super_secret_api_token_that_must_never_leak_abc123"
    monkeypatch.setenv("GITHUB_MODELS_TOKEN", secret_token)

    def mock_urlopen_401(request, *args, **kwargs):
        # The error body happens to contain the token (worst-case: server echo)
        raise _make_http_error(401, body=f"Token {secret_token} is invalid".encode())

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen_401)

    client = LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=False)

    exc_message = ""
    with caplog.at_level(logging.DEBUG):
        try:
            client.complete(role="tested_agents", prompt="p", seed=1)
        except Exception as exc:
            exc_message = str(exc)

    # Token must not appear in exception message
    assert secret_token not in exc_message, (
        f"Token appeared in exception message: {exc_message!r}"
    )

    # Token must not appear in any log record
    for record in caplog.records:
        assert secret_token not in record.getMessage(), (
            f"Token appeared in log record: {record.getMessage()!r}"
        )

    # Token must not appear in the cost log file
    cost_log = client.cost_log_path
    if cost_log.exists():
        contents = cost_log.read_text(encoding="utf-8")
        assert secret_token not in contents, "Token must not appear in cost_log.jsonl"


def test_token_not_in_exception_when_present_in_error_body(tmp_path, cfg, monkeypatch):
    """Even if the API echoes the token in its error body, we must scrub it."""
    secret = "scrub_me_from_error_body_secret_xyz"
    monkeypatch.setenv("GITHUB_MODELS_TOKEN", secret)

    def raise_error_with_token_body(request, *args, **kwargs):
        raise _make_http_error(403, body=f"access denied for token {secret}".encode())

    monkeypatch.setattr("urllib.request.urlopen", raise_error_with_token_body)

    client = LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=False)
    try:
        client.complete(role="tested_agents", prompt="p", seed=1)
        assert False, "Should have raised"
    except RuntimeError as exc:
        assert secret not in str(exc), f"Token leaked in error: {exc}"


# ── Test 11: missing token raises clear error ─────────────────────────────────

def test_missing_token_raises_clear_error(tmp_path, cfg, monkeypatch):
    """Online mode without a token must raise a clear RuntimeError."""
    monkeypatch.delenv("GITHUB_MODELS_TOKEN", raising=False)
    monkeypatch.delenv("GH_MODELS_TOKEN", raising=False)

    client = LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=False)
    with pytest.raises(RuntimeError, match="token"):
        client.complete(role="tested_agents", prompt="p", seed=1)


# ── Test 12: offline default unchanged ────────────────────────────────────────

def test_offline_default_still_works(tmp_path, cfg):
    """offline=True (default) must still return deterministic mock outputs."""
    client = LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=True)
    r1 = client.complete(role="tested_agents", prompt="hello", seed=42)
    r2 = client.complete(role="tested_agents", prompt="hello", seed=42)
    assert r1.text == r2.text
    assert r1.cost_usd == 0.0
    assert r1.logit_conf is None  # offline mock never sets logit_conf


def test_offline_and_online_use_different_cache_keys(tmp_path, cfg, monkeypatch):
    """Offline and online clients must have distinct cache key spaces."""
    monkeypatch.setenv("GITHUB_MODELS_TOKEN", FAKE_TOKEN)
    offline = LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=True)
    online = LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=False)

    offline_key = offline._cache_key("tested_agents", "p", 1, None, None)
    online_key = online._cache_key("tested_agents", "p", 1, None, None)
    assert offline_key != online_key, "offline and online must use different cache keys"


# ── Test 13: rate-limit sleep is called when cap is hit ───────────────────────

def test_rate_limit_enforced(tmp_path, cfg, monkeypatch):
    """When max_requests_per_min=1, the second call must trigger rate-limit sleep."""
    monkeypatch.setenv("GITHUB_MODELS_TOKEN", FAKE_TOKEN)
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *a, **kw: _FakeHTTPResponse(_make_ok_response()),
    )

    slept: list = []
    monkeypatch.setattr("time.sleep", lambda t: slept.append(t))

    client = LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=False,
                       max_requests_per_min=1)
    # First call: goes through, records timestamp
    client.complete(role="tested_agents", prompt="p1", seed=1)

    # Simulate that only 1 second has passed (within the 60-second window)
    import time as _time_module
    original_time = _time_module.time

    # Patch time so it looks like only 1s has elapsed (within window)
    fake_now = [original_time() + 1]

    def fake_time():
        return fake_now[0]

    monkeypatch.setattr("time.time", fake_time)

    # Second call: should detect 1 request in window, sleep until window clears
    client.complete(role="tested_agents", prompt="p2", seed=2)

    assert any(t > 0 for t in slept), "Rate limit must have triggered a sleep"
