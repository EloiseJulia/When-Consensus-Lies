# constructed by: Claude (Anthropic) family
"""Offline tests for default_check_h2_additions.py.

Runs with NO network and NO token: the driver is exercised against the deterministic
OFFLINE mock LLMClient with provider="copilot_proxy". Verifies:
  A. Task selection: exactly the 8 expected ids, all role "h2"; KeyError on bogus id.
  B. run_h2_additions against the mock client returns a well-formed report with 8 item
     rows + a summary line; NO network is touched.
  C. Guard: main() with RUN_H2ADD_CHECK unset prints skip + exits 0.
"""

from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path

import pytest

# ── Import all three drivers (scripts/ is not a package) ──────────────────────
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
h2add = _load("default_check_h2_additions", "default_check_h2_additions.py")


@pytest.fixture(autouse=True)
def _clear_domain_caches():
    for mod in ("bench.data_analysis",):
        try:
            m = __import__(mod, fromlist=["_RESULT_CACHE"])
            getattr(m, "_RESULT_CACHE", {}).clear()
        except (ImportError, AttributeError):
            pass
    yield


@pytest.fixture
def artifacts_dir():
    d = _REPO_ROOT / "tests" / "_h2add_artifacts"
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    yield d
    shutil.rmtree(d, ignore_errors=True)


# ── A. Task selection ─────────────────────────────────────────────────────────

EXPECTED_IDS = [
    "data_geomean_001_k0",
    "data_geomean_001_k1_growth_averaging",
    "data_harmonic_001_k0",
    "data_harmonic_001_k1_speed_averaging",
    "data_cumulative_001_k0",
    "data_cumulative_001_k1_cumulative_interpretation",
    "data_tierank_001_k0",
    "data_tierank_001_k1_tie_ranking",
]


def test_select_h2add_tasks_returns_8_ids():
    """Exactly 8 tasks are returned, matching the spec."""
    tasks, task_role = h2add.select_h2add_tasks()
    ids = [t.id for t in tasks]
    assert ids == EXPECTED_IDS, f"Unexpected task ids: {ids}"


def test_all_tasks_are_role_h2():
    """Every selected task must have task_role == 'h2'."""
    tasks, task_role = h2add.select_h2add_tasks()
    for t in tasks:
        assert task_role[t.id] == "h2", f"task {t.id} has role {task_role[t.id]!r}, expected 'h2'"


def test_h2add_task_ids_constant_matches_expected():
    """The module-level H2ADD_TASK_IDS list matches the spec exactly."""
    assert h2add.H2ADD_TASK_IDS == EXPECTED_IDS


def test_keyerror_on_bogus_id(monkeypatch):
    """If any expected id is missing from generate_tasks(), a KeyError must be raised."""
    from bench.data_analysis import generate_tasks as gen_data

    real_tasks = gen_data()
    # Remove one of the 8 expected tasks from the mock result.
    filtered = [t for t in real_tasks if t.id != "data_geomean_001_k0"]

    import bench.data_analysis as da_mod
    monkeypatch.setattr(da_mod, "generate_tasks", lambda: filtered)

    # Also patch the import inside the function (it imports locally).
    import bench.data_analysis
    monkeypatch.setattr(bench.data_analysis, "generate_tasks", lambda: filtered)

    with pytest.raises(KeyError, match="data_geomean_001_k0"):
        h2add.select_h2add_tasks()


# ── B. Offline run: well-formed report, no network ───────────────────────────

def test_run_h2_additions_offline_returns_8_item_rows(artifacts_dir):
    """run_h2_additions against an offline mock client returns 8 unique task rows
    (one per selected task id, across all ensemble types) plus a summary line, with
    NO network call."""
    from common.config import load_config

    cfg = load_config()
    client = frontier.build_client(
        cfg,
        offline=True,
        cache_dir=str(artifacts_dir / "cache"),
        budget_usd=None,
        rpm=100_000,
    )
    ckpt = str(artifacts_dir / "h2add_ckpt.jsonl")
    report = h2add.run_h2_additions(
        client,
        checkpoint_path=ckpt,
        sc_k=2,
        budget_usd=None,
        rpm=100_000,
    )

    # Required top-level keys.
    for key in ("rows", "total_calls", "per_model_calls", "runner_status", "roster_name"):
        assert key in report, f"Missing key {key!r} in report"

    # roster_name provenance.
    assert report["roster_name"] == "copilot_proxy_frontier_h2add"

    # The 8 selected task ids must all appear in the rows.
    row_task_ids = {r["task_id"] for r in report["rows"]}
    for tid in EXPECTED_IDS:
        assert tid in row_task_ids, f"task {tid!r} missing from report rows"

    # All rows must have task_role == "h2".
    for row in report["rows"]:
        assert row.get("task_role") == "h2", (
            f"Row for {row['task_id']} has task_role={row.get('task_role')!r}, expected 'h2'"
        )

    # At least one run occurred.
    assert report["total_calls"] > 0


def test_run_h2_additions_uses_separate_cache(artifacts_dir):
    """build_client with H2ADD_CACHE_DIR never touches the frontier or github cache."""
    from common.config import load_config

    cfg = load_config()
    custom_cache = str(artifacts_dir / "h2add_cache")
    client = frontier.build_client(
        cfg, offline=True, cache_dir=custom_cache, budget_usd=None, rpm=100_000,
    )
    # Verify the client's cache dir is not the frontier or github-models cache.
    cache_str = str(client.cache_dir)
    assert cache_str != default_check.CACHE_DIR
    assert cache_str != frontier.FRONTIER_CACHE_DIR
    assert "h2add" in cache_str or custom_cache in cache_str


def test_write_h2add_report_creates_files(artifacts_dir):
    """write_h2add_report writes JSONL + table with the correct H2-additions names."""
    from common.config import load_config

    cfg = load_config()
    client = frontier.build_client(
        cfg, offline=True,
        cache_dir=str(artifacts_dir / "cache"),
        budget_usd=None, rpm=100_000,
    )
    ckpt = str(artifacts_dir / "h2add_ckpt.jsonl")
    report = h2add.run_h2_additions(
        client, checkpoint_path=ckpt, sc_k=2, budget_usd=None, rpm=100_000,
    )
    jsonl_path, table_path = h2add.write_h2add_report(report, out_dir=str(artifacts_dir))

    assert Path(jsonl_path).exists()
    assert Path(table_path).exists()
    assert "h2add_summary" in Path(jsonl_path).name
    assert "h2add_table" in Path(table_path).name

    # JSONL: each row line has "type"="row", summary line has "type"="summary".
    lines = Path(jsonl_path).read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) >= 2
    summary_lines = [l for l in lines if json.loads(l).get("type") == "summary"]
    row_lines = [l for l in lines if json.loads(l).get("type") == "row"]
    assert len(summary_lines) == 1
    assert len(row_lines) >= 8  # at least one row per selected task

    # Table has the DEFAULT-CHECK header.
    assert "DEFAULT-CHECK" in Path(table_path).read_text(encoding="utf-8")


def test_report_roster_name_provenance(artifacts_dir):
    """roster_name in the report must be FRONTIER_ROSTER.name + '_h2add'."""
    from common.config import load_config

    cfg = load_config()
    client = frontier.build_client(
        cfg, offline=True,
        cache_dir=str(artifacts_dir / "cache"),
        budget_usd=None, rpm=100_000,
    )
    ckpt = str(artifacts_dir / "h2add_ckpt.jsonl")
    report = h2add.run_h2_additions(
        client, checkpoint_path=ckpt, sc_k=2, budget_usd=None, rpm=100_000,
    )
    expected = frontier.FRONTIER_ROSTER.name + "_h2add"
    assert report["roster_name"] == expected


# ── C. Guard: offline / no flag → skipped, exit 0 (no network) ───────────────

def test_flag_unset_returns_false():
    ok, reason = h2add._should_run(env={})
    assert ok is False
    assert "RUN_H2ADD_CHECK" in reason


def test_flag_set_probe_skipped():
    ok, reason = h2add._should_run(
        env={"RUN_H2ADD_CHECK": "1", "FRONTIER_SKIP_PROXY_PROBE": "1"}
    )
    assert ok is True


def test_flag_set_proxy_unreachable(monkeypatch):
    # Patch on h2add.frontier (the module object h2add actually calls through).
    monkeypatch.setattr(h2add.frontier, "proxy_reachable", lambda *a, **k: False)
    ok, reason = h2add._should_run(env={"RUN_H2ADD_CHECK": "1"})
    assert ok is False
    assert "reachable" in reason


def test_main_skips_without_flag(monkeypatch, capsys):
    monkeypatch.delenv("RUN_H2ADD_CHECK", raising=False)
    with pytest.raises(SystemExit) as exc:
        h2add.main()
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "skip" in out.lower()


# ── import json needed in test body ──────────────────────────────────────────
import json  # noqa: E402  (used in test_write_h2add_report_creates_files)
