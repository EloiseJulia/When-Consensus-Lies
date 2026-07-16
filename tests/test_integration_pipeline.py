"""Integration pipeline tests — Phase 2-S2d.

Implementer family: Claude/Anthropic  (auditor MUST use a different model family).

Three parts, as specified in paper/plans/phase2-S2d-integration-plan.md:

  Part 1 — Controlled end-to-end golden cases (per domain, hand-computed assertions).
            Uses get_checkers_and_candidates canonical candidates to construct
            deterministic AgentRun outputs that map to KNOWN interpretations,
            then asserts frozen convergent_delusion / a_maj values.

  Part 2 — Real run wiring pass (offline mock; shape + validity checks only;
            no specific metric value asserted since mock outputs → mostly I_perp).

  Part 3 — tests/test_metrics_golden.py and tests/test_marginal_rho.py remain
            INTACT and run automatically as part of pytest.  No duplication here;
            see those files for the frozen unit-level golden metric assertions.

Relationship to test_smoke_pipeline.py:
  test_smoke_pipeline.py exercises the Phase-0 MOCK hash path (useful as a
  no-network sanity check).  This file carries the MEANINGFUL executable-signal
  assertions.  Both coexist; do not remove test_smoke_pipeline.py.
"""

import pytest
from common.schema import AgentRun
from common.config import load_config
from common.llm import LLMClient
from harness.run import run_task
from harness.label import label_run
from harness.metrics import (
    false_consensus_rate,
    convergent_delusion,
    a_maj,
    marginal_rho,
    ece,
    confidence_accuracy_slope,
    error_indicators,
)
from bench.build import load_tasks


# ── Fixture: clear subprocess-result caches before each test ─────────────────

@pytest.fixture(autouse=True)
def clear_domain_caches():
    """Prevent cross-test cache pollution in the subprocess gold-checker domains."""
    try:
        from bench.data_analysis import _RESULT_CACHE as _da
        _da.clear()
    except ImportError:
        pass
    try:
        from bench.code_spec import _RESULT_CACHE as _cs
        _cs.clear()
    except ImportError:
        pass
    yield


# ── Shared builder ────────────────────────────────────────────────────────────

def _make_run(task_id: str, output: str, seed: int, conf: float = 0.8) -> AgentRun:
    """Construct a minimal AgentRun for controlled-output labeling tests."""
    return AgentRun(
        task_id=task_id,
        config="single",
        model_role="tested_agents",
        model_id="test-model",
        output=output,
        label="",
        verbalized_conf=conf,
        logit_conf=None,
        seed=seed,
    )


# ============================================================================
# PART 1 — CONTROLLED END-TO-END GOLDEN CASES
# ============================================================================

def test_golden_code_spec():
    """Part 1 golden — code_spec, 5 controlled agents, frozen hand-computed values.

    Task: code_quarterdate_001_k2_all  (ambiguity_level=2, combinatorial, reversed-property)
      I0 = fiscal-April quarter + US date format (target, all-target, NON-default)
      I1 = fiscal-April quarter + ISO date (C_D defaulted, partial)
      I2 = calendar quarter + US date (C_Q defaulted, partial)
      I3 = calendar quarter + ISO date ([combined-default])

    Controlled distribution (5 agents):
      agents 0–2 : I1 candidate in ```python fence  → label I1
      agent  3   : I0 candidate in ```python fence  → label I0  (target)
      agent  4   : I2 candidate in ```python fence  → label I2

    HAND CALCULATIONS
    -----------------
    Expected labels: [I1, I1, I1, I0, I2]

    convergent_delusion  (primary metric):
      wrong_counts = {I1: 3, I2: 1}   (I0 is the target -> excluded)
      max_wrong_count = 3
      total = 5
      => 3 / 5 = 0.6

    a_maj:
      counts = {I1: 3, I0: 1, I2: 1}
      unique_winner = I1  (strict plurality, count 3 > every other label)
      I1 != target I0
      => 0.0
    """
    from bench.code_spec import get_checkers_and_candidates

    tasks = load_tasks("bench/data/code_spec.jsonl")
    task = next(t for t in tasks if t.id == "code_quarterdate_001_k2_all")

    _, candidates, _ = get_checkers_and_candidates(task.domain, task)
    i0_code = candidates["I0"]
    i1_code = candidates["I1"]
    i2_code = candidates["I2"]

    controlled_runs = [
        _make_run(task.id, f"```python\n{i1_code}\n```", seed=100, conf=0.80),  # → I1
        _make_run(task.id, f"```python\n{i1_code}\n```", seed=101, conf=0.80),  # → I1
        _make_run(task.id, f"```python\n{i1_code}\n```", seed=102, conf=0.80),  # → I1
        _make_run(task.id, f"```python\n{i0_code}\n```", seed=103, conf=0.90),  # → I0
        _make_run(task.id, f"```python\n{i2_code}\n```", seed=104, conf=0.70),  # → I2
    ]

    # Step 1: prove each controlled output maps to the intended interpretation (NOT I_perp)
    labels = [label_run(run, task) for run in controlled_runs]
    assert labels[0] == "I1", f"agent 0: expected I1, got {labels[0]}"
    assert labels[1] == "I1", f"agent 1: expected I1, got {labels[1]}"
    assert labels[2] == "I1", f"agent 2: expected I1, got {labels[2]}"
    assert labels[3] == "I0", f"agent 3: expected I0 (target), got {labels[3]}"
    assert labels[4] == "I2", f"agent 4: expected I2, got {labels[4]}"

    # Step 2: frozen golden metric assertions
    # convergent_delusion = max_wrong_count / total = 3 / 5 = 0.6
    cd = convergent_delusion(labels, target="I0")
    assert cd == 0.6, f"convergent_delusion: expected 3/5=0.6, got {cd}"

    # a_maj: unique plurality is I1 (3 votes); I1 ≠ target I0 → 0.0
    am = a_maj(labels, target="I0")
    assert am == 0.0, f"a_maj: expected 0.0 (wrong plurality), got {am}"

    # Step 3: secondary metrics must run without error and return floats
    confs = [r.verbalized_conf for r in controlled_runs]
    correct_bools = [lbl == "I0" for lbl in labels]  # [F, F, F, T, F]

    # marginal_rho: single task → 5×1 error matrix; pairwise variance undefined → 0.0
    err_mat = [[e] for e in error_indicators(labels, "I0")]
    rho = marginal_rho(err_mat)
    assert isinstance(rho, float), f"marginal_rho: expected float, got {type(rho)}"

    ece_val = ece(confs, correct_bools)
    assert isinstance(ece_val, float), f"ece: expected float, got {type(ece_val)}"

    slope = confidence_accuracy_slope(confs, correct_bools)
    assert isinstance(slope, float), f"confidence_accuracy_slope: expected float, got {type(slope)}"


def test_golden_data_analysis():
    """Part 1 golden — data_analysis, 5 controlled agents, frozen hand-computed values.

    Task: data_report_001_k2_all  (ambiguity_level=2, combinatorial, reversed-property)
      I0 = KPI threshold >=3 + half-up rounding (target, all-target, NON-default)
      I1 = threshold >=3 + half-even rounding (avg_rounding defaulted, partial)
      I2 = threshold >=1 + half-up rounding (active_user_threshold defaulted, partial)
      I3 = threshold >=1 + half-even rounding ([combined-default])

    Controlled distribution (5 agents):
      agents 0–2 : I1 candidate in ```python fence  → label I1
      agent  3   : I0 candidate in ```python fence  → label I0  (target)
      agent  4   : I2 candidate in ```python fence  → label I2

    HAND CALCULATIONS
    ─────────────────
    Expected labels: [I1, I1, I1, I0, I2]

    convergent_delusion  (primary metric):
      wrong_counts = {I1: 3, I2: 1}   (I0 is the target -> excluded)
      max_wrong_count = 3  (three agents on I1)
      total = 5
      => 3 / 5 = 0.6

    a_maj:
      counts = {I1: 3, I0: 1, I2: 1}
      unique_winner = I1  (strict plurality)
      I1 ≠ target I0
      => 0.0
    """
    from bench.data_analysis import get_checkers_and_candidates

    tasks = load_tasks("bench/data/data_analysis.jsonl")
    task = next(t for t in tasks if t.id == "data_report_001_k2_all")

    _, candidates, _ = get_checkers_and_candidates(task.domain, task)
    i0_code = candidates["I0"]
    i1_code = candidates["I1"]
    i2_code = candidates["I2"]

    controlled_runs = [
        _make_run(task.id, f"```python\n{i1_code}\n```", seed=200, conf=0.80),  # → I1
        _make_run(task.id, f"```python\n{i1_code}\n```", seed=201, conf=0.80),  # → I1
        _make_run(task.id, f"```python\n{i1_code}\n```", seed=202, conf=0.80),  # → I1
        _make_run(task.id, f"```python\n{i0_code}\n```", seed=203, conf=0.90),  # → I0
        _make_run(task.id, f"```python\n{i2_code}\n```", seed=204, conf=0.70),  # → I2
    ]

    labels = [label_run(run, task) for run in controlled_runs]
    assert labels[0] == "I1", f"agent 0: expected I1, got {labels[0]}"
    assert labels[1] == "I1", f"agent 1: expected I1, got {labels[1]}"
    assert labels[2] == "I1", f"agent 2: expected I1, got {labels[2]}"
    assert labels[3] == "I0", f"agent 3: expected I0 (target), got {labels[3]}"
    assert labels[4] == "I2", f"agent 4: expected I2, got {labels[4]}"

    # convergent_delusion = max_wrong_count / total = 3 / 5 = 0.6
    cd = convergent_delusion(labels, target="I0")
    assert cd == 0.6, f"convergent_delusion: expected 3/5=0.6, got {cd}"

    # a_maj: unique plurality is I1 (3 votes); I1 ≠ target I0 → 0.0
    am = a_maj(labels, target="I0")
    assert am == 0.0, f"a_maj: expected 0.0 (wrong plurality), got {am}"

    confs = [r.verbalized_conf for r in controlled_runs]
    correct_bools = [lbl == "I0" for lbl in labels]

    err_mat = [[e] for e in error_indicators(labels, "I0")]
    rho = marginal_rho(err_mat)
    assert isinstance(rho, float)

    ece_val = ece(confs, correct_bools)
    assert isinstance(ece_val, float)

    slope = confidence_accuracy_slope(confs, correct_bools)
    assert isinstance(slope, float)


def test_golden_policy_qa():
    """Part 1 golden — policy_qa, 5 controlled agents, frozen hand-computed values.

    Task: policy_paymileage_001_k2_all  (ambiguity_level=2, reversed k=2 family)
      I0 = OT after 35 h + mileage rounded UP to whole $ → $1063.00  (target, all-target)
           Arithmetic: (35*$20 + 10*$30) + ceil($0.60*104=$62.40)=$63.00 = $1000 + $63.00 = $1063.00
      I1 = OT after 35 h + exact-cent mileage → $1062.40  (mileage_rounding defaulted)
           Arithmetic: (35*$20 + 10*$30) + 104*$0.60 = $1000 + $62.40 = $1062.40
      I2 = OT after 40 h + mileage rounded up → $1013.00  (overtime defaulted)
           Arithmetic: (40*$20 + 5*$30) + $63.00 = $950 + $63.00 = $1013.00

    Format: "FINAL ANSWER: $<amount>" (the STRUCTURED format accepted by
    harness/label.py's _extract_numeric_from_output path).

    Controlled distribution (5 agents):
      agents 0–2 : FINAL ANSWER: $1062.40 → label I1
      agent  3   : FINAL ANSWER: $1063.00 → label I0  (target)
      agent  4   : FINAL ANSWER: $1013.00 → label I2

    HAND CALCULATIONS
    ─────────────────
    Expected labels: [I1, I1, I1, I0, I2]

    convergent_delusion  (primary metric):
      wrong_counts = {I1: 3, I2: 1}
      max_wrong_count = 3
      total = 5
      => 3 / 5 = 0.6

    a_maj:
      counts = {I1: 3, I0: 1, I2: 1}
      unique_winner = I1  (strict plurality)
      I1 ≠ target I0
      => 0.0
    """
    from bench.policy_qa import get_checkers_and_candidates

    tasks = load_tasks("bench/data/policy_qa.jsonl")
    task = next(t for t in tasks if t.id == "policy_paymileage_001_k2_all")

    _, candidates, _ = get_checkers_and_candidates(task.domain, task)
    i0_amount = candidates["I0"]["amount"]   # 1063.00
    i1_amount = candidates["I1"]["amount"]   # 1062.40
    i2_amount = candidates["I2"]["amount"]   # 1013.00

    controlled_runs = [
        _make_run(task.id, f"FINAL ANSWER: ${i1_amount:.2f}", seed=300, conf=0.80),  # → I1
        _make_run(task.id, f"FINAL ANSWER: ${i1_amount:.2f}", seed=301, conf=0.80),  # → I1
        _make_run(task.id, f"FINAL ANSWER: ${i1_amount:.2f}", seed=302, conf=0.80),  # → I1
        _make_run(task.id, f"FINAL ANSWER: ${i0_amount:.2f}", seed=303, conf=0.90),  # → I0
        _make_run(task.id, f"FINAL ANSWER: ${i2_amount:.2f}", seed=304, conf=0.70),  # → I2
    ]

    labels = [label_run(run, task) for run in controlled_runs]
    assert labels[0] == "I1", f"agent 0: expected I1 (${i1_amount:.2f}), got {labels[0]}"
    assert labels[1] == "I1", f"agent 1: expected I1 (${i1_amount:.2f}), got {labels[1]}"
    assert labels[2] == "I1", f"agent 2: expected I1 (${i1_amount:.2f}), got {labels[2]}"
    assert labels[3] == "I0", f"agent 3: expected I0 (${i0_amount:.2f}, target), got {labels[3]}"
    assert labels[4] == "I2", f"agent 4: expected I2 (${i2_amount:.2f}), got {labels[4]}"

    # convergent_delusion = max_wrong_count / total = 3 / 5 = 0.6
    cd = convergent_delusion(labels, target="I0")
    assert cd == 0.6, f"convergent_delusion: expected 3/5=0.6, got {cd}"

    # a_maj: unique plurality is I1 (3 votes); I1 ≠ target I0 → 0.0
    am = a_maj(labels, target="I0")
    assert am == 0.0, f"a_maj: expected 0.0 (wrong plurality), got {am}"

    confs = [r.verbalized_conf for r in controlled_runs]
    correct_bools = [lbl == "I0" for lbl in labels]

    err_mat = [[e] for e in error_indicators(labels, "I0")]
    rho = marginal_rho(err_mat)
    assert isinstance(rho, float)

    ece_val = ece(confs, correct_bools)
    assert isinstance(ece_val, float)

    slope = confidence_accuracy_slope(confs, correct_bools)
    assert isinstance(slope, float)


# ============================================================================
# PART 2 — REAL RUN WIRING PASS (offline mock; shape + validity, no fixed values)
# ============================================================================
#
# These tests call the TRUE code path (run_task → label_run → metrics) with an
# offline LLMClient.  Offline mock outputs are "MOCK_OUTPUT_…" strings which
# match no interpreter → all labels are I_perp.  That is expected and fine.
# We assert only: correct run count, correct identity fields, label == "" out of
# run_task, labels ∈ valid set, convergent_delusion ∈ [0.0, 1.0].
# ============================================================================

def _wiring_check(
    domain: str,
    task_ids: list,
    configs: list,  # list of (config_name, expected_run_count, extra_kwargs)
) -> None:
    """Common wiring-pass logic shared across domains."""
    cfg_obj = load_config()
    client = LLMClient(cfg_obj, offline=True)
    tasks = load_tasks(f"bench/data/{domain}.jsonl")

    for task_id in task_ids:
        task = next(t for t in tasks if t.id == task_id)
        valid_labels = {i.id for i in task.interpretations} | {"I_perp"}
        target = next(i.id for i in task.interpretations if i.is_target)

        for cfg_name, expected_count, extra_kwargs in configs:
            runs = run_task(task, config=cfg_name, client=client, **extra_kwargs)

            # Shape / identity checks
            assert len(runs) == expected_count, (
                f"{task_id}/{cfg_name}: expected {expected_count} runs, got {len(runs)}"
            )
            for run in runs:
                assert run.task_id == task.id, (
                    f"{task_id}/{cfg_name}: run.task_id={run.task_id!r}"
                )
                assert run.config == cfg_name, (
                    f"{task_id}/{cfg_name}: run.config={run.config!r}"
                )
                # run_task MUST NOT pre-assign labels
                assert run.label == "", (
                    f"{task_id}/{cfg_name}: run.label must be '' out of run_task, "
                    f"got {run.label!r}"
                )

            # Label each run via the real code path
            labels = [label_run(r, task) for r in runs]
            assert all(lbl in valid_labels for lbl in labels), (
                f"{task_id}/{cfg_name}: label not in valid set: {labels}"
            )

            # Metric must be a float in [0, 1]
            cd = false_consensus_rate(labels, target=target)
            assert isinstance(cd, float), (
                f"{task_id}/{cfg_name}: convergent_delusion type {type(cd)}"
            )
            assert 0.0 <= cd <= 1.0, (
                f"{task_id}/{cfg_name}: convergent_delusion out of range: {cd}"
            )


def test_wiring_code_spec():
    """Part 2 wiring: code_spec — single, sc (k=5), verifier; no-crash + shape check."""
    _wiring_check(
        domain="code_spec",
        task_ids=[
            "code_quarter_001_k1_fiscal_year_start",
            "code_roundcurr_001_k1_rounding_standard",
        ],
        configs=[
            ("single",   1, {}),
            ("sc",       5, {"k": 5}),
            ("verifier", 1, {}),
        ],
    )


def test_wiring_data_analysis():
    """Part 2 wiring: data_analysis — single, sc (k=5), verifier."""
    _wiring_check(
        domain="data_analysis",
        task_ids=[
            "data_activeusers_001_k1_active_user_threshold",
            "data_typical_001_k1_central_tendency",
        ],
        configs=[
            ("single",   1, {}),
            ("sc",       5, {"k": 5}),
            ("verifier", 1, {}),
        ],
    )


def test_wiring_policy_qa():
    """Part 2 wiring: policy_qa — single, sc (k=5), verifier."""
    _wiring_check(
        domain="policy_qa",
        task_ids=[
            "policy_overtime_001_k1_overtime_threshold",
            "policy_interest_001_k1_compounding",
        ],
        configs=[
            ("single",   1, {}),
            ("sc",       5, {"k": 5}),
            ("verifier", 1, {}),
        ],
    )
