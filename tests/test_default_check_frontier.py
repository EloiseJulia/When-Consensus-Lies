# constructed by: Claude (Anthropic) family
"""Offline test for the FRONTIER-ROSTER default-check driver (Amendment 06).

Runs with NO network and NO token: the driver drives the deterministic OFFLINE mock LLM
client constructed with provider="copilot_proxy". Verifies the roster WIRING:
  A. FRONTIER_ROSTER carries the exact A06 §2 frontier model slugs, split reasoner/weak/
     ρ-baseline/heterogeneous, with code_invoice EXCLUDED from the homogeneous-sc pass.
  B. build_client yields a client whose provider is copilot_proxy (no token) and the
     driver uses a SEPARATE checkpoint file (never the GitHub-Models one).
  C. A full offline run: sc (pass A) checkpoint excludes code_invoice; the heterogeneous
     pool (pass B) contains the 3 frontier families; model_class tags are as specified.
  D. Base-URL host/port override + the double-guard (flag + proxy-reachability), all
     without any real network call.
"""

from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path

import pytest

# ── Import both drivers (scripts/ is not a package) ───────────────────────────
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _load(mod_name: str, filename: str):
    path = _REPO_ROOT / "scripts" / filename
    spec = importlib.util.spec_from_file_location(mod_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(mod_name, mod)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


default_check = _load("default_check", "default_check.py")
frontier = _load("default_check_frontier", "default_check_frontier.py")


@pytest.fixture(autouse=True)
def _clear_domain_caches():
    for mod in ("bench.data_analysis", "bench.code_spec", "bench.diagnostic"):
        try:
            m = __import__(mod, fromlist=["_RESULT_CACHE"])
            getattr(m, "_RESULT_CACHE", {}).clear()
        except (ImportError, AttributeError):
            pass
    yield


@pytest.fixture
def artifacts_dir():
    d = _REPO_ROOT / "tests" / "_frontier_artifacts"
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    yield d
    shutil.rmtree(d, ignore_errors=True)


# ── A. Roster wiring: exact A06 §2 slugs + classification + exclusions ─────────

def test_frontier_roster_slugs_match_amendment_06():
    r = frontier.FRONTIER_ROSTER
    assert r.reasoner_slugs == {"gpt-5.6-sol", "claude-opus-4.8", "gemini-3.1-pro-preview"}
    assert r.weak_slugs == {"gpt-4o-mini", "gemini-3.5-flash", "claude-haiku-4.5"}
    assert r.rho_baseline_slugs == {"gpt-5.4"}

    homo = [m for _role, m in r.homogeneous_models]
    # ρ-baseline + reasoners + weak all run their own homogeneous sc ensemble (pass A).
    assert homo[0] == "gpt-5.4"  # ρ-baseline first
    for slug in ("gpt-5.6-sol", "claude-opus-4.8", "gemini-3.1-pro-preview",
                 "gpt-4o-mini", "gemini-3.5-flash", "claude-haiku-4.5"):
        assert slug in homo, f"{slug} missing from homogeneous-sc pass"

    pool = [m for _role, m in r.pool_models]
    # Heterogeneous cross-family pool (pass B): the 3-family row-35 headline.
    assert pool == ["gpt-5.4", "claude-sonnet-4.6", "gemini-3.1-pro-preview"]

    # Every roster model uses the tested_agents role (Runner only invokes that role).
    for _role, _slug in list(r.homogeneous_models) + list(r.pool_models):
        assert _role == "tested_agents"


def test_frontier_model_class_tags():
    r = frontier.FRONTIER_ROSTER
    assert r.model_class("gpt-5.6-sol") == "reasoner"
    assert r.model_class("claude-opus-4.8") == "reasoner"
    assert r.model_class("gemini-3.1-pro-preview") == "reasoner"
    assert r.model_class("gpt-4o-mini") == "weak"
    assert r.model_class("gemini-3.5-flash") == "weak"
    assert r.model_class("claude-haiku-4.5") == "weak"
    assert r.model_class("gpt-5.4") == "rho_baseline"


def test_code_invoice_excluded_from_reasoner_pass():
    """code_invoice k-gradient must be excluded from the homogeneous-sc (reasoner) pass."""
    excluded = frontier.FRONTIER_ROSTER.reasoner_sc_excluded_ids
    assert set(default_check.K_GRADIENT_IDS)
    for task_id in default_check.K_GRADIENT_IDS:
        assert "code_invoice" in task_id
        assert task_id in excluded, f"{task_id} not excluded from the reasoner pass"


def test_separate_checkpoint_and_provider_constants():
    assert frontier.PROVIDER == "copilot_proxy"
    assert frontier.FRONTIER_CHECKPOINT == "default_check_frontier_checkpoint.jsonl"
    # Never collide with the GitHub-Models run's checkpoint / cache / outputs.
    assert frontier.FRONTIER_CHECKPOINT != default_check.CHECKPOINT
    assert frontier.FRONTIER_CACHE_DIR != default_check.CACHE_DIR
    # Sensible caps: unlimited local proxy → higher RPM; raised reasoner token budget.
    assert frontier.FRONTIER_RPM >= 20
    assert frontier.FRONTIER_MAX_TOKENS_PER_CALL >= 8192


# ── B. build_client uses provider=copilot_proxy and needs NO token ────────────

def test_build_client_is_copilot_proxy_no_token(artifacts_dir):
    from common.config import load_config

    cfg = load_config()
    client = frontier.build_client(
        cfg, offline=True, cache_dir=str(artifacts_dir / "cache"),
        budget_usd=None, rpm=100000,
    )
    assert client.provider == "copilot_proxy"
    assert client.require_auth is False       # proxy needs no Authorization token
    assert client.base_url                     # resolved from config/provider default


def test_resolve_base_url_host_port_override():
    assert frontier.resolve_base_url(env={}) is None  # → LLMClient config/default
    assert frontier.resolve_base_url(
        env={"FRONTIER_PROXY_BASE_URL": "http://10.0.0.5:9000/v1"}
    ) == "http://10.0.0.5:9000/v1"
    assert frontier.resolve_base_url(
        env={"FRONTIER_PROXY_HOST": "myhost", "FRONTIER_PROXY_PORT": "9999"}
    ) == "http://myhost:9999/v1"
    assert frontier.resolve_base_url(
        env={"FRONTIER_PROXY_PORT": "9999"}
    ) == "http://127.0.0.1:9999/v1"


def test_resolve_base_url_reads_config_provider():
    """With no env override, the configured providers.copilot_proxy.base_url wins —
    the SAME source LLMClient resolves from (guard must not diverge from the client)."""
    cfg = {"providers": {"copilot_proxy": {"base_url": "http://cfg-host:7000/v1"}}}
    assert frontier.resolve_base_url(env={}, config=cfg) == "http://cfg-host:7000/v1"
    # Env override still beats config.
    assert frontier.resolve_base_url(
        env={"FRONTIER_PROXY_BASE_URL": "http://env-host:1/v1"}, config=cfg
    ) == "http://env-host:1/v1"
    # No env, no config → None (LLMClient owns default resolution).
    assert frontier.resolve_base_url(env={}, config={}) is None


def test_guard_probes_the_resolved_url(monkeypatch):
    """The reachability guard must probe EXACTLY the resolved base_url (config or env),
    never a hard-coded default, so a configured alternate endpoint is not mis-probed."""
    probed = []
    monkeypatch.setattr(frontier, "proxy_reachable",
                        lambda url, *a, **k: (probed.append(url), True)[1])

    cfg = {"providers": {"copilot_proxy": {"base_url": "http://cfg-host:7000/v1"}}}
    ok, _ = frontier._should_run(env={"RUN_FRONTIER_CHECK": "1"}, config=cfg)
    assert ok is True
    assert probed == ["http://cfg-host:7000/v1"], "guard must probe the config base_url"

    probed.clear()
    frontier._should_run(
        env={"RUN_FRONTIER_CHECK": "1", "FRONTIER_PROXY_HOST": "envhost"}, config=cfg
    )
    assert probed == ["http://envhost:8313/v1"], "env override must win in the probe"


# ── C. Full offline run: pass A excludes code_invoice; pool = 3 families ───────

def test_offline_frontier_run_wiring(artifacts_dir):
    from common.config import load_config
    from harness.runner import CheckpointStore, endpoint_identity

    cfg = load_config()
    client = frontier.build_client(
        cfg, offline=True, cache_dir=str(artifacts_dir / "cache"),
        budget_usd=None, rpm=100000,
    )
    ckpt = str(artifacts_dir / frontier.FRONTIER_CHECKPOINT)
    report = frontier.run_frontier(
        client, checkpoint_path=ckpt, sc_k=2, budget_usd=None, rpm=100000,
    )

    # Report shape + roster provenance.
    for key in ("rows", "total_calls", "per_model_calls", "runner_status",
                "reasoner_resolution_h2", "saturation_disambiguation", "roster_name"):
        assert key in report
    assert report["roster_name"] == "copilot_proxy_frontier"
    assert report["total_calls"] > 0

    # Pass A (sc) checkpoint must NOT contain any code_invoice task.
    store = CheckpointStore(
        Path(ckpt), endpoint=endpoint_identity(client.provider, client.base_url)
    )
    sc_task_ids = {r["task_id"] for r in store.all_runs() if r["config"] == "sc"}
    for invoice_id in default_check.K_GRADIENT_IDS:
        assert invoice_id not in sc_task_ids, f"{invoice_id} leaked into the sc pass"

    # The 3 frontier families each produced pool (single-pass) runs.
    single_models = {r["model_id"] for r in store.all_runs() if r["config"] == "single"}
    for slug in ("gpt-5.4", "claude-sonnet-4.6", "gemini-3.1-pro-preview"):
        assert slug in single_models, f"{slug} missing from the heterogeneous pool pass"

    # model_class tags present across the report as specified.
    classes = {r["model_class"] for r in report["rows"]}
    assert {"reasoner", "weak", "heterogeneous", "rho_baseline"} <= classes

    # Homogeneous reasoner + weak slugs each ran their own sc ensemble.
    sc_models = {r["model_id"] for r in store.all_runs() if r["config"] == "sc"}
    for slug in ("gpt-5.6-sol", "claude-opus-4.8", "gpt-4o-mini",
                 "gemini-3.5-flash", "claude-haiku-4.5", "gpt-5.4"):
        assert slug in sc_models, f"{slug} missing from the homogeneous-sc pass"

    # Table renders without error.
    assert "DEFAULT-CHECK" in default_check.render_table(report)


# ── D. Double-guard: offline / no flag → skipped, exit 0 (no network) ─────────

def test_should_run_requires_flag():
    ok, reason = frontier._should_run(env={})
    assert ok is False and "RUN_FRONTIER_CHECK" in reason


def test_should_run_flag_but_probe_skipped():
    ok, reason = frontier._should_run(
        env={"RUN_FRONTIER_CHECK": "1", "FRONTIER_SKIP_PROXY_PROBE": "1"}
    )
    assert ok is True


def test_should_run_flag_but_proxy_unreachable(monkeypatch):
    monkeypatch.setattr(frontier, "proxy_reachable", lambda *a, **k: False)
    ok, reason = frontier._should_run(env={"RUN_FRONTIER_CHECK": "1"})
    assert ok is False and "reachable" in reason


def test_main_skips_without_flag(monkeypatch, capsys):
    monkeypatch.delenv("RUN_FRONTIER_CHECK", raising=False)
    with pytest.raises(SystemExit) as exc:
        frontier.main()
    assert exc.value.code == 0
    assert "skip" in capsys.readouterr().out.lower()
