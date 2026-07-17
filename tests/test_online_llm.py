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
--- Regression tests for 5 auditor-found bugs ---
 B1. BLOCKER 1: token absent from str/repr AND __cause__ chain on exhausted 5xx
 B2. BLOCKER 2: budget pre-auth blocks before first HTTP call (zero HTTP calls)
 M3. MAJOR 3:  rate-limit enforced+recorded for EVERY attempt (incl. failed 429)
 M4. MAJOR 4:  cache OSError never triggers a second paid API call
 M5. MAJOR 5:  urlopen receives a finite, configurable timeout kwarg
"""

import io
import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any, Dict, Optional
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
    # The config routes tested_agents → gpt-5.4 (Amendment-06 frontier homogeneous baseline)
    client.complete(role="tested_agents", prompt="hello", seed=42)

    # Slug from config must appear in the request body
    assert captured["body"]["model"] == "gpt-5.4"

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
    """BudgetExceeded raised on the FIRST call when pre-auth detects overage.

    Updated for BLOCKER 2 fix: pre-authorization fires BEFORE any HTTP call,
    so even the first call is rejected when worst-case cost > max_budget_usd.
    The old test assumed the first large-token response would succeed; the fix
    explicitly prevents that.
    """
    monkeypatch.setenv("GITHUB_MODELS_TOKEN", FAKE_TOKEN)

    http_calls = 0

    def mock_urlopen(request, *args, **kwargs):
        nonlocal http_calls
        http_calls += 1
        return _FakeHTTPResponse(_make_ok_response(tokens_in=100_000, tokens_out=100_000))

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

    # Budget far below the worst-case for a single gpt-4o-mini call (~$0.0025)
    client = LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=False,
                       max_budget_usd=0.00001)

    # Pre-auth must fire on the FIRST call, before any HTTP attempt
    with pytest.raises(BudgetExceeded, match="Pre-authorization"):
        client.complete(role="tested_agents", prompt="first", seed=1)

    assert http_calls == 0, "No HTTP call must be made when pre-auth fails"


def test_budget_exceeded_is_not_retried_by_outer_loop(tmp_path, cfg, monkeypatch):
    """BudgetExceeded must propagate immediately; the outer retry loop must not swallow it.

    Updated for BLOCKER 2 fix: pre-auth fires before any HTTP call, so we
    verify that with max_retries=5, BudgetExceeded is raised exactly once
    and urlopen is never called (not retried even with high max_retries).
    """
    monkeypatch.setenv("GITHUB_MODELS_TOKEN", FAKE_TOKEN)

    urlopen_calls = 0

    def mock_urlopen(request, *args, **kwargs):
        nonlocal urlopen_calls
        urlopen_calls += 1
        return _FakeHTTPResponse(_make_ok_response(tokens_in=100_000, tokens_out=100_000))

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

    client = LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=False,
                       max_budget_usd=0.0)

    # With budget=0.0 and max_retries=5: BudgetExceeded must fire once, never retried
    with pytest.raises(BudgetExceeded):
        client.complete(role="tested_agents", prompt="should-not-retry", seed=99,
                        max_retries=5)

    # Zero HTTP calls — pre-auth fires before urlopen on every attempt
    assert urlopen_calls == 0, (
        f"BudgetExceeded (from pre-auth) must not cause any HTTP call. "
        f"Made {urlopen_calls} with max_retries=5."
    )


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


# ═══════════════════════════════════════════════════════════════════════════════
# Audit regression tests — five bugs identified by GPT cross-family auditor
# ═══════════════════════════════════════════════════════════════════════════════

# ── BLOCKER 1: token must not leak via __cause__ chain on exhausted 5xx ──────

def test_blocker1_token_not_in_exception_chain_on_persistent_5xx(
    tmp_path, cfg, monkeypatch
):
    """Persistent 503 with token in body: token must NOT appear anywhere in the
    raised exception OR in its __cause__ / __context__ chain.

    STRENGTHENED (re-audit): the original fix used `from None` which clears
    __cause__ but Python still sets __context__ when raising inside an `except`
    block. The current fix restructures the loop so raises happen AFTER the
    loop exits all except scopes → __context__ = None guaranteed.
    """
    secret = "SECRET_BLOCKER1_MUST_NOT_LEAK_IN_5XX_CHAIN_ABC999"
    monkeypatch.setenv("GITHUB_MODELS_TOKEN", secret)

    def raise_503_with_secret_body(request, *a, **kw):
        body = f"internal server error, bearer={secret}, retry-after=1".encode()
        raise _make_http_error(503, body=body)

    monkeypatch.setattr("urllib.request.urlopen", raise_503_with_secret_body)
    monkeypatch.setattr("time.sleep", lambda t: None)

    client = LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=False)
    raised_exc: Optional[Exception] = None
    try:
        client.complete(role="tested_agents", prompt="p", seed=1)
    except Exception as exc:
        raised_exc = exc

    assert raised_exc is not None, "Expected an exception to be raised"
    assert secret not in str(raised_exc), f"Token in str(exc): {str(raised_exc)!r}"
    assert secret not in repr(raised_exc), f"Token in repr(exc): {repr(raised_exc)!r}"

    # Core assertion: both __cause__ AND __context__ must be None.
    # __cause__=None means `from None` was used (or no explicit cause).
    # __context__=None means the raise happened outside any active except scope.
    assert raised_exc.__cause__ is None, (
        f"__cause__ must be None, got: {raised_exc.__cause__!r}"
    )
    assert raised_exc.__context__ is None, (
        f"__context__ must be None (raise was inside except scope — token leak risk). "
        f"Got: {type(raised_exc.__context__).__name__}"
    )


# ── BLOCKER 2: budget pre-auth must block BEFORE the first HTTP call ──────────

def test_blocker2_budget_preauth_blocks_before_any_http_call(
    tmp_path, cfg, monkeypatch
):
    """max_budget_usd=0.0 → worst-case cost > 0 → BudgetExceeded on the VERY
    FIRST call, with ZERO HTTP attempts made.

    This proves the pre-authorization check runs before urlopen, not after
    (the old post-call check would let the first response through).
    """
    monkeypatch.setenv("GITHUB_MODELS_TOKEN", FAKE_TOKEN)

    http_calls = 0

    def mock_urlopen(req, *a, **kw):
        nonlocal http_calls
        http_calls += 1
        return _FakeHTTPResponse(_make_ok_response())

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

    # Budget of $0.0: any worst-case estimate > 0 must be rejected
    client = LLMClient(
        cfg, cache_dir=str(tmp_path / "c"), offline=False, max_budget_usd=0.0
    )

    with pytest.raises(BudgetExceeded, match="Pre-authorization"):
        client.complete(role="tested_agents", prompt="hello world", seed=1)

    assert http_calls == 0, (
        f"No HTTP call must be made when pre-auth fails. Made {http_calls}."
    )


def test_blocker2_budget_preauth_blocks_when_accumulated_near_cap(
    tmp_path, cfg, monkeypatch
):
    """When accumulated cost is close to the cap and a new worst-case would
    push it over, BudgetExceeded must fire before the HTTP call, not after.
    """
    monkeypatch.setenv("GITHUB_MODELS_TOKEN", FAKE_TOKEN)

    http_calls = 0

    def mock_urlopen(req, *a, **kw):
        nonlocal http_calls
        http_calls += 1
        return _FakeHTTPResponse(_make_ok_response(tokens_in=1, tokens_out=1))

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

    # A cap just below the worst-case for a single call (worst-case for
    # gpt-4o-mini with 4096 output tokens ≈ $0.00246, so 0.001 < that)
    tiny_cap = 0.001
    client = LLMClient(
        cfg,
        cache_dir=str(tmp_path / "c"),
        offline=False,
        max_budget_usd=tiny_cap,
        max_tokens_per_call=4096,
    )

    with pytest.raises(BudgetExceeded, match="Pre-authorization"):
        client.complete(role="tested_agents", prompt="hello", seed=1)

    assert http_calls == 0, "Pre-auth must block before any HTTP call"


# ── MAJOR 3: rate-limit applied to EVERY HTTP attempt including 429 retries ──

def test_major3_rate_limit_called_for_every_http_attempt(
    tmp_path, cfg, monkeypatch
):
    """With a 429-then-200 sequence, the rate-limit enforcement AND recording
    must run for BOTH HTTP attempts, not just the first one.

    This verifies that _enforce_rate_limit / _record_request_time are INSIDE
    the retry loop (moved from outside in the MAJOR 3 fix).
    """
    monkeypatch.setenv("GITHUB_MODELS_TOKEN", FAKE_TOKEN)

    enforce_count = 0
    record_count = 0

    _orig_enforce = LLMClient._enforce_rate_limit
    _orig_record = LLMClient._record_request_time

    def counting_enforce(self_inner):
        nonlocal enforce_count
        enforce_count += 1
        _orig_enforce(self_inner)

    def counting_record(self_inner):
        nonlocal record_count
        record_count += 1
        _orig_record(self_inner)

    monkeypatch.setattr(LLMClient, "_enforce_rate_limit", counting_enforce)
    monkeypatch.setattr(LLMClient, "_record_request_time", counting_record)

    http_attempts = 0

    def mock_urlopen(req, *a, **kw):
        nonlocal http_attempts
        http_attempts += 1
        if http_attempts == 1:
            raise _make_http_error(429)
        return _FakeHTTPResponse(_make_ok_response())

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)
    monkeypatch.setattr("time.sleep", lambda t: None)

    client = LLMClient(
        cfg, cache_dir=str(tmp_path / "c"), offline=False, max_requests_per_min=100
    )
    client.complete(role="tested_agents", prompt="p", seed=1)

    assert http_attempts == 2, "Expected 429 + 200 = 2 HTTP attempts"
    assert enforce_count >= 2, (
        f"_enforce_rate_limit must be called for EVERY HTTP attempt, "
        f"got {enforce_count} for {http_attempts} attempts"
    )
    assert record_count >= 2, (
        f"_record_request_time must record EVERY HTTP attempt (incl. 429), "
        f"got {record_count} for {http_attempts} attempts"
    )


# ── MAJOR 4: cache OSError must not trigger a second API call ─────────────────

def test_major4_cache_write_oserror_does_not_repeat_api_call(
    tmp_path, cfg, monkeypatch
):
    """If _write_cache raises OSError, the result must still be returned and
    NO second HTTP call must be made.

    Old bug: _write_cache was INSIDE the retry loop, so OSError triggered
    another _generate call (up to max_retries paid HTTP calls).
    Fix: persistence is OUTSIDE the retry loop.
    """
    monkeypatch.setenv("GITHUB_MODELS_TOKEN", FAKE_TOKEN)

    http_calls = 0

    def mock_urlopen(req, *a, **kw):
        nonlocal http_calls
        http_calls += 1
        return _FakeHTTPResponse(_make_ok_response(text="exactly_one_call"))

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

    # Make every _write_cache raise OSError (simulates full disk)
    def failing_write_cache(self_inner, key, completion):
        raise OSError("disk full — MAJOR 4 regression test")

    monkeypatch.setattr(LLMClient, "_write_cache", failing_write_cache)

    client = LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=False)
    result = client.complete(role="tested_agents", prompt="unique_m4", seed=42,
                             max_retries=5)

    # Result from the single API call must be returned
    assert result.text == "exactly_one_call", (
        f"Expected result from single API call, got: {result.text!r}"
    )
    # Exactly one HTTP call, regardless of max_retries
    assert http_calls == 1, (
        f"Cache write failure must NOT retry the API call. "
        f"Made {http_calls} HTTP calls with max_retries=5."
    )


# ── MAJOR 5: urlopen must receive a finite configurable timeout ───────────────

def test_major5_urlopen_called_with_finite_timeout(tmp_path, cfg, monkeypatch):
    """urlopen must receive a timeout= kwarg matching the configured value.

    Without this fix, a stalled connection hangs indefinitely despite finite
    retry bounds (the retry loop gives up, but each attempt can hang forever).
    """
    monkeypatch.setenv("GITHUB_MODELS_TOKEN", FAKE_TOKEN)

    captured: dict = {}

    def mock_urlopen(req, *args, **kwargs):
        # Capture both positional (urllib allows timeout as 2nd positional) and kw
        timeout_val = kwargs.get("timeout")
        if timeout_val is None and args:
            timeout_val = args[0]
        captured["timeout"] = timeout_val
        return _FakeHTTPResponse(_make_ok_response())

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

    expected_timeout = 30.0
    client = LLMClient(
        cfg,
        cache_dir=str(tmp_path / "c"),
        offline=False,
        http_timeout=expected_timeout,
    )
    client.complete(role="tested_agents", prompt="p", seed=1)

    assert "timeout" in captured, "urlopen must be called with a timeout= argument"
    assert captured["timeout"] is not None, "timeout must not be None"
    assert isinstance(captured["timeout"], (int, float)), (
        f"timeout must be numeric, got {type(captured['timeout'])}"
    )
    assert captured["timeout"] > 0, "timeout must be positive"
    assert captured["timeout"] == expected_timeout, (
        f"timeout must equal the configured http_timeout={expected_timeout}, "
        f"got {captured['timeout']}"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Re-audit regression tests — 3 issues still open after first round
# ═══════════════════════════════════════════════════════════════════════════════

# ── BLOCKER (context leak): __context__ must be None for BOTH 5xx AND 4xx ────

def test_blocker_context_is_none_on_exhausted_5xx(tmp_path, cfg, monkeypatch):
    """After the loop-restructure fix, __context__ must be None on exhausted 5xx.

    `from None` only clears __cause__; __context__ is set by Python whenever
    you raise inside an `except` block. The fix raises AFTER the loop exits
    all except scopes, so __context__ = None is the definitive proof.
    """
    secret = "CONTEXT_LEAK_CHECK_5XX_TOKEN_XYZ789"
    monkeypatch.setenv("GITHUB_MODELS_TOKEN", secret)

    def always_503(req, *a, **kw):
        raise _make_http_error(503, body=f"bearer={secret}".encode())

    monkeypatch.setattr("urllib.request.urlopen", always_503)
    monkeypatch.setattr("time.sleep", lambda t: None)

    client = LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=False)
    raised: Optional[Exception] = None
    try:
        client.complete(role="tested_agents", prompt="p", seed=1)
    except Exception as e:
        raised = e

    assert raised is not None
    assert raised.__context__ is None, (
        f"__context__ must be None (would expose HTTPError with token). "
        f"Got: {type(raised.__context__).__name__!r}"
    )
    assert raised.__cause__ is None
    assert secret not in str(raised)
    assert secret not in repr(raised)


def test_blocker_context_is_none_on_4xx_terminal(tmp_path, cfg, monkeypatch):
    """__context__ must be None on 4xx (non-429) terminal errors.

    The 4xx path `break`s out of the except scope before raising, so no
    HTTPError (which carries token-echoing headers/body) survives in the chain.
    """
    secret = "CONTEXT_LEAK_CHECK_4XX_TOKEN_ABC123"
    monkeypatch.setenv("GITHUB_MODELS_TOKEN", secret)

    def always_403(req, *a, **kw):
        raise _make_http_error(403, body=f"access denied token={secret}".encode())

    monkeypatch.setattr("urllib.request.urlopen", always_403)

    client = LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=False)
    raised: Optional[Exception] = None
    try:
        client.complete(role="tested_agents", prompt="p", seed=1)
    except Exception as e:
        raised = e

    assert raised is not None
    assert raised.__context__ is None, (
        f"__context__ must be None on 4xx terminal error. "
        f"Got: {type(raised.__context__).__name__!r}"
    )
    assert raised.__cause__ is None
    # Token may appear in the scrubbed body field of the message as "[REDACTED]"
    # but must NOT appear as the raw secret
    assert secret not in str(raised), f"Token leaked in 4xx error: {str(raised)!r}"


# ── MAJOR (budget): request must include max_tokens ──────────────────────────

def test_major_budget_request_includes_max_tokens(tmp_path, cfg, monkeypatch):
    """The outgoing request payload must include max_tokens = _max_tokens_per_call.

    Without this, the server is free to return more output tokens than the
    pre-authorization estimate assumed, breaking the budget upper bound.
    """
    monkeypatch.setenv("GITHUB_MODELS_TOKEN", FAKE_TOKEN)

    captured_payload: dict = {}

    def mock_urlopen(req, *a, **kw):
        captured_payload.update(json.loads(req.data.decode("utf-8")))
        return _FakeHTTPResponse(_make_ok_response())

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

    custom_max_tokens = 512
    client = LLMClient(
        cfg, cache_dir=str(tmp_path / "c"), offline=False,
        max_tokens_per_call=custom_max_tokens,
    )
    client.complete(role="tested_agents", prompt="hello", seed=1)

    assert "max_tokens" in captured_payload, (
        "Request payload must include 'max_tokens' to enforce output cap"
    )
    assert captured_payload["max_tokens"] == custom_max_tokens, (
        f"max_tokens in payload ({captured_payload['max_tokens']}) must equal "
        f"max_tokens_per_call ({custom_max_tokens})"
    )


def test_major_budget_call_proceeds_when_within_cap(tmp_path, cfg, monkeypatch):
    """When budget cap > worst-case, call proceeds and actual cost ≤ worst-case."""
    monkeypatch.setenv("GITHUB_MODELS_TOKEN", FAKE_TOKEN)

    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *a, **kw: _FakeHTTPResponse(_make_ok_response(tokens_in=5, tokens_out=5)),
    )

    prompt = "hi"
    max_tokens = 256
    # Compute the exact worst-case used by pre-auth: UTF-8 bytes + 64 overhead.
    # For ASCII "hi", byte count == char count so this is the same as before.
    tokens_in_upper = len(prompt.encode("utf-8")) + 64  # = 66
    cfg_tmp = load_config()
    tmp_client = LLMClient(cfg_tmp, cache_dir=str(tmp_path / "tmp"), offline=True,
                           max_tokens_per_call=max_tokens)
    slug = "openai/gpt-4o-mini"
    worst_case = tmp_client._estimate_cost(slug, tokens_in_upper, max_tokens)

    # Set budget = worst_case + epsilon: call must proceed (not raise BudgetExceeded)
    cap = worst_case + 0.001
    client = LLMClient(cfg_tmp, cache_dir=str(tmp_path / "c"), offline=False,
                       max_budget_usd=cap, max_tokens_per_call=max_tokens)
    # Must NOT raise
    result = client.complete(role="tested_agents", prompt=prompt, seed=1)
    assert result.text is not None, "Expected a completion when within budget"
    # Actual cost (5+5 tiny tokens) must be ≤ worst_case
    assert result.cost_usd <= worst_case + 1e-9, (
        f"Actual cost {result.cost_usd:.8f} must not exceed worst_case {worst_case:.8f}"
    )


# ── MAJOR 3 (RPM): URLError/transport attempts must be recorded ──────────────

def test_major3_rpm_records_urlerror_transport_attempts(tmp_path, cfg, monkeypatch):
    """URLError (connection refused, DNS failure) attempts must be recorded in
    the rate-limit window via _record_request_time in `finally`.

    Old bug: only HTTPError and success paths called _record_request_time;
    URLErrors escaped unrecorded. Fix: `finally` block in the retry loop.
    """
    monkeypatch.setenv("GITHUB_MODELS_TOKEN", FAKE_TOKEN)

    recorded: list = []
    _orig_record = LLMClient._record_request_time

    def counting_record(self_inner):
        recorded.append(1)
        _orig_record(self_inner)

    monkeypatch.setattr(LLMClient, "_record_request_time", counting_record)

    url_error_attempts = 0

    def always_url_error(req, *a, **kw):
        nonlocal url_error_attempts
        url_error_attempts += 1
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr("urllib.request.urlopen", always_url_error)
    monkeypatch.setattr("time.sleep", lambda t: None)

    client = LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=False)
    try:
        client.complete(role="tested_agents", prompt="p", seed=1)
    except Exception:
        pass  # expected to exhaust retries and fail

    assert url_error_attempts == 6, (
        f"Expected 6 URLError attempts (bounded retries), got {url_error_attempts}"
    )
    assert len(recorded) == 6, (
        f"_record_request_time must be called for EVERY URLError attempt "
        f"(got {len(recorded)} for {url_error_attempts} attempts). "
        f"The `finally` block fix is required."
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Re-audit round-2 regression tests — Unicode budget upper bound
# ═══════════════════════════════════════════════════════════════════════════════

# ── MAJOR: UTF-8 byte length is a true token upper bound for Unicode ──────────

def test_unicode_budget_preauth_blocks_below_byte_based_worst_case(
    tmp_path, cfg, monkeypatch
):
    """A prompt of multi-byte emoji/ZWJ sequences: set cap just BELOW the
    byte-based worst_case → BudgetExceeded must fire BEFORE any HTTP call.

    Auditor's case: 200 emoji ZWJ sequences → 800 chars but many more bytes
    and even more actual tokens. The char-based bound (len(prompt)+64)
    undershot, letting the call through and exceeding budget. The UTF-8 byte
    bound (len(prompt.encode('utf-8'))+64) is a genuine upper bound because
    every BPE token covers ≥ 1 byte.
    """
    monkeypatch.setenv("GITHUB_MODELS_TOKEN", FAKE_TOKEN)

    http_calls = 0

    def mock_urlopen(req, *a, **kw):
        nonlocal http_calls
        http_calls += 1
        return _FakeHTTPResponse(_make_ok_response())

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

    # A prompt with multi-byte Unicode: emoji family ZWJ sequences.
    # Each "👨‍👩‍👧‍👦" is 1 Python char sequence but encodes to 25 bytes in UTF-8.
    # 100 such sequences → 100 chars (approx) vs 2500 bytes.
    emoji_prompt = "👨‍👩‍👧‍👦" * 100
    char_count = len(emoji_prompt)
    byte_count = len(emoji_prompt.encode("utf-8"))
    # Byte count must exceed char count — verify the bound actually grew
    assert byte_count > char_count, (
        f"Test invariant: byte count ({byte_count}) must exceed char count "
        f"({char_count}) for multi-byte emoji prompt"
    )

    max_tokens = 256
    cfg_tmp = load_config()
    # Compute byte-based worst_case (what the code now uses)
    tokens_in_byte_upper = byte_count + 64
    helper = LLMClient(cfg_tmp, cache_dir=str(tmp_path / "h"), offline=True,
                       max_tokens_per_call=max_tokens)
    slug = "openai/gpt-4o-mini"
    worst_case_byte = helper._estimate_cost(slug, tokens_in_byte_upper, max_tokens)

    # Set cap just below the byte-based worst_case → BudgetExceeded expected
    cap = worst_case_byte - 1e-9
    client = LLMClient(cfg_tmp, cache_dir=str(tmp_path / "c"), offline=False,
                       max_budget_usd=cap, max_tokens_per_call=max_tokens)

    with pytest.raises(BudgetExceeded, match="Pre-authorization"):
        client.complete(role="tested_agents", prompt=emoji_prompt, seed=1)

    assert http_calls == 0, (
        f"BudgetExceeded must fire BEFORE any HTTP call; made {http_calls} calls"
    )


def test_unicode_byte_count_exceeds_char_count_for_emoji():
    """Invariant: for multi-byte Unicode prompts, UTF-8 byte count > char count.

    This proves the bound widened: the old char-based estimate would have used
    a smaller token_upper than the new byte-based estimate.
    """
    # ZWJ family emoji: 1 grapheme cluster, but 25 UTF-8 bytes each
    emoji_prompt = "👨‍👩‍👧‍👦" * 200
    char_count = len(emoji_prompt)
    byte_count = len(emoji_prompt.encode("utf-8"))
    assert byte_count > char_count, (
        f"UTF-8 bytes ({byte_count}) must exceed char count ({char_count}) "
        f"for multi-byte emoji sequences"
    )
    # Demonstrate the magnitude: ZWJ family sequences are ~3.5× bytes per char
    # (each emoji = 4 bytes, each ZWJ = 3 bytes, 7 code-points total)
    assert byte_count >= 3 * char_count, (
        f"Expected byte_count >= 3 × char_count for emoji; got {byte_count} vs {char_count}"
    )


def test_unicode_budget_ascii_unchanged(tmp_path, cfg, monkeypatch):
    """For pure ASCII prompts, byte count == char count → existing behavior
    is unchanged and no regression in the normal English/code case.
    """
    monkeypatch.setenv("GITHUB_MODELS_TOKEN", FAKE_TOKEN)

    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *a, **kw: _FakeHTTPResponse(_make_ok_response(tokens_in=5, tokens_out=5)),
    )

    ascii_prompt = "What is the time complexity of binary search?"
    assert len(ascii_prompt.encode("utf-8")) == len(ascii_prompt), (
        "Test invariant: ASCII prompt must have byte count == char count"
    )

    max_tokens = 256
    cfg_tmp = load_config()
    tokens_in_upper = len(ascii_prompt.encode("utf-8")) + 64
    helper = LLMClient(cfg_tmp, cache_dir=str(tmp_path / "h"), offline=True,
                       max_tokens_per_call=max_tokens)
    worst_case = helper._estimate_cost("openai/gpt-4o-mini", tokens_in_upper, max_tokens)

    # Set cap = worst_case + epsilon → call must proceed
    client = LLMClient(cfg_tmp, cache_dir=str(tmp_path / "c"), offline=False,
                       max_budget_usd=worst_case + 0.001,
                       max_tokens_per_call=max_tokens)
    result = client.complete(role="tested_agents", prompt=ascii_prompt, seed=1)
    assert result.text is not None, "ASCII prompt within budget must complete"


# ═══════════════════════════════════════════════════════════════════════════════
# Fix 1 — Temperature control tests (offline-safe, no network)
# ═══════════════════════════════════════════════════════════════════════════════

def test_temperature_sent_for_non_reasoning_non_openai_model(tmp_path, cfg, monkeypatch):
    """temperature is included in the payload for non-reasoning non-OpenAI models."""
    monkeypatch.setenv("GITHUB_MODELS_TOKEN", FAKE_TOKEN)

    captured: dict = {}

    def mock_urlopen(req, *a, **kw):
        captured.update(json.loads(req.data.decode("utf-8")))
        return _FakeHTTPResponse(_make_ok_response(model="meta/llama-3.3-70b-instruct"))

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

    client = LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=False)
    client.complete(
        role="tested_agents", prompt="p", seed=1,
        family="meta", model="meta/llama-3.3-70b-instruct",
        temperature=0.7,
    )

    assert "temperature" in captured, "temperature must be in payload for non-reasoning model"
    assert captured["temperature"] == 0.7
    assert "max_tokens" in captured, "non-reasoning model must use max_tokens"
    assert "max_completion_tokens" not in captured


def test_temperature_sent_for_non_reasoning_openai_model(tmp_path, cfg, monkeypatch):
    """temperature is included in the payload for non-reasoning OpenAI models."""
    monkeypatch.setenv("GITHUB_MODELS_TOKEN", FAKE_TOKEN)

    captured: dict = {}

    def mock_urlopen(req, *a, **kw):
        captured.update(json.loads(req.data.decode("utf-8")))
        return _FakeHTTPResponse(_make_ok_response(model="openai/gpt-4o-mini"))

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

    client = LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=False)
    client.complete(
        role="tested_agents", prompt="p_temp_openai", seed=1,
        family="openai", model="openai/gpt-4o-mini",
        temperature=0.3,
    )

    assert "temperature" in captured, "temperature must be in payload for non-reasoning openai model"
    assert captured["temperature"] == 0.3
    assert "logprobs" in captured, "non-reasoning openai must still include logprobs"
    assert "max_tokens" in captured


def test_temperature_none_omits_field_from_payload(tmp_path, cfg, monkeypatch):
    """When temperature=None (default), the field must NOT appear in the payload."""
    monkeypatch.setenv("GITHUB_MODELS_TOKEN", FAKE_TOKEN)

    captured: dict = {}

    def mock_urlopen(req, *a, **kw):
        captured.update(json.loads(req.data.decode("utf-8")))
        return _FakeHTTPResponse(_make_ok_response(model="openai/gpt-4o-mini"))

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

    client = LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=False)
    client.complete(role="tested_agents", prompt="p_no_temp", seed=1)

    assert "temperature" not in captured, (
        "temperature must not appear in payload when not provided (let API use its default)"
    )


def test_temperature_in_cache_key_different_temps_separate_entries(tmp_path, cfg, monkeypatch):
    """Different temperatures must produce separate cache entries and separate HTTP calls."""
    monkeypatch.setenv("GITHUB_MODELS_TOKEN", FAKE_TOKEN)

    http_calls = 0

    def mock_urlopen(req, *a, **kw):
        nonlocal http_calls
        http_calls += 1
        return _FakeHTTPResponse(_make_ok_response(text=f"response_{http_calls}"))

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

    client = LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=False)

    # Same prompt+seed but different temperatures → different cache keys → 2 HTTP calls
    r_low = client.complete(role="tested_agents", prompt="same_prompt", seed=42, temperature=0.0)
    r_high = client.complete(role="tested_agents", prompt="same_prompt", seed=42, temperature=1.0)

    assert http_calls == 2, (
        f"Different temperatures must each hit the network (separate cache keys). "
        f"Expected 2 HTTP calls, got {http_calls}."
    )
    assert r_low.text != r_high.text, "Different temperatures must produce different cached texts"

    # Third call with temperature=0.0 must serve from cache (no new HTTP call)
    r_low_again = client.complete(role="tested_agents", prompt="same_prompt", seed=42, temperature=0.0)
    assert http_calls == 2, "Repeated call with same temperature must use cache, not re-fetch"
    assert r_low_again.text == r_low.text


def test_temperature_cache_key_helper(tmp_path, cfg):
    """_cache_key must embed temperature so different temps produce different keys."""
    client = LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=True)

    key_none = client._cache_key("tested_agents", "p", 1, None, None, None)
    key_zero = client._cache_key("tested_agents", "p", 1, None, None, 0.0)
    key_high = client._cache_key("tested_agents", "p", 1, None, None, 1.0)

    assert key_none != key_zero, "temperature=None vs 0.0 must differ"
    assert key_zero != key_high, "temperature=0.0 vs 1.0 must differ"
    assert key_none != key_high, "temperature=None vs 1.0 must differ"


# ═══════════════════════════════════════════════════════════════════════════════
# Fix 2 — o-series / reasoning-model tests (offline-safe, no network)
# ═══════════════════════════════════════════════════════════════════════════════

from common.llm import is_reasoning_model


def test_is_reasoning_model_classifier():
    """is_reasoning_model must classify known reasoning and non-reasoning slugs."""
    # Reasoning slugs — must return True
    for slug in [
        "openai/o1",
        "openai/o1-mini",
        "openai/o1-preview",
        "openai/o3",
        "openai/o3-mini",
        "openai/o4-mini",
        "openai/o4",
        "openai/gpt-5",
        "openai/gpt-5-mini",
    ]:
        assert is_reasoning_model(slug), f"Expected {slug!r} to be a reasoning model"

    # Non-reasoning slugs — must return False
    for slug in [
        "openai/gpt-4o-mini",
        "openai/gpt-4o",
        "openai/gpt-4.1",
        "openai/gpt-4.1-mini",
        "meta/llama-3.3-70b-instruct",
        "mistral-ai/mistral-small-2503",
        "deepseek/deepseek-v3-0324",
        "microsoft/phi-4",
        "cohere/cohere-command-a",
    ]:
        assert not is_reasoning_model(slug), f"Expected {slug!r} NOT to be a reasoning model"


def test_reasoning_model_payload_o4_mini(tmp_path, cfg, monkeypatch):
    """openai/o4-mini (reasoning): must use max_completion_tokens, omit logprobs and temperature."""
    monkeypatch.setenv("GITHUB_MODELS_TOKEN", FAKE_TOKEN)

    captured: dict = {}

    def mock_urlopen(req, *a, **kw):
        captured.update(json.loads(req.data.decode("utf-8")))
        return _FakeHTTPResponse(_make_ok_response(model="openai/o4-mini"))

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

    client = LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=False)
    result = client.complete(
        role="tested_agents", prompt="p_reasoning", seed=1,
        family="openai", model="openai/o4-mini",
        temperature=0.7,  # must be ignored / omitted for reasoning models
    )

    # max_completion_tokens must be present (NOT max_tokens)
    assert "max_completion_tokens" in captured, (
        "Reasoning model must use max_completion_tokens, not max_tokens"
    )
    assert "max_tokens" not in captured, (
        "Reasoning model must NOT use max_tokens (causes 400)"
    )
    # logprobs must be absent
    assert "logprobs" not in captured, (
        "Reasoning model must NOT include logprobs (causes HTTP 400)"
    )
    assert "top_logprobs" not in captured, (
        "Reasoning model must NOT include top_logprobs"
    )
    # temperature must be absent (even when caller passes one)
    assert "temperature" not in captured, (
        "Reasoning model must NOT include temperature (not accepted by API)"
    )
    # logit_conf must be None
    assert result.logit_conf is None, "Reasoning model must have logit_conf=None"


def test_non_reasoning_openai_payload_has_logprobs_max_tokens_temperature(tmp_path, cfg, monkeypatch):
    """Non-reasoning openai slug: must have logprobs + max_tokens + temperature."""
    monkeypatch.setenv("GITHUB_MODELS_TOKEN", FAKE_TOKEN)

    captured: dict = {}
    logprobs_data = [{"token": " ok", "logprob": -0.1}]

    def mock_urlopen(req, *a, **kw):
        captured.update(json.loads(req.data.decode("utf-8")))
        return _FakeHTTPResponse(
            _make_ok_response(model="openai/gpt-4o-mini", logprobs_content=logprobs_data)
        )

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

    client = LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=False)
    result = client.complete(
        role="tested_agents", prompt="p_nr_openai", seed=1,
        family="openai", model="openai/gpt-4o-mini",
        temperature=0.5,
    )

    assert "logprobs" in captured and captured["logprobs"] is True
    assert "top_logprobs" in captured
    assert "max_tokens" in captured
    assert "max_completion_tokens" not in captured
    assert "temperature" in captured and captured["temperature"] == 0.5
    assert result.logit_conf is not None, "Non-reasoning openai must populate logit_conf"


def test_reasoning_model_logit_conf_is_none(tmp_path, cfg, monkeypatch):
    """Reasoning model responses must always have logit_conf=None."""
    monkeypatch.setenv("GITHUB_MODELS_TOKEN", FAKE_TOKEN)

    # Even if (hypothetically) logprobs appeared in the response, logit_conf must be None
    logprobs_data = [{"token": " x", "logprob": -0.2}]

    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *a, **kw: _FakeHTTPResponse(
            _make_ok_response(model="openai/o4-mini", logprobs_content=logprobs_data)
        ),
    )

    client = LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=False)
    result = client.complete(
        role="tested_agents", prompt="p", seed=1,
        family="openai", model="openai/o4-mini",
    )
    assert result.logit_conf is None, (
        "logit_conf must be None for reasoning models regardless of response content"
    )


def test_reasoning_model_budget_preauth_uses_max_completion_tokens(tmp_path, cfg, monkeypatch):
    """Budget pre-auth must still block for reasoning models (using _max_tokens_per_call
    as the output bound even though the field is named max_completion_tokens)."""
    monkeypatch.setenv("GITHUB_MODELS_TOKEN", FAKE_TOKEN)

    http_calls = 0

    def mock_urlopen(req, *a, **kw):
        nonlocal http_calls
        http_calls += 1
        return _FakeHTTPResponse(_make_ok_response(model="openai/o4-mini"))

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

    # Budget of $0.0 → any worst-case estimate > 0 must be rejected before HTTP
    client = LLMClient(cfg, cache_dir=str(tmp_path / "c"), offline=False,
                       max_budget_usd=0.0)

    with pytest.raises(BudgetExceeded, match="Pre-authorization"):
        client.complete(
            role="tested_agents", prompt="hello", seed=1,
            family="openai", model="openai/o4-mini",
        )

    assert http_calls == 0, "Budget pre-auth must block reasoning model calls too"
