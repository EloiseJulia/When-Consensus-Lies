"""Offline tests for the blinded abstention human-validation kit.

Covers the sampler (scripts/abstention_sample.py) and the scorer
(scripts/abstention_score.py) with tiny synthetic fixtures. No network, no real
partition files, no LLM.
"""
from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.abstention_sample import (  # noqa: E402
    CODING_COLUMNS,
    KEY_COLUMNS,
    LEAKAGE_SCAN_RE,
    STRATUM_IPERP,
    STRATUM_PARSEABLE,
    STRATUM_POSITIVE,
    build_row_id,
    mask_interpretation_ids,
    stratified_sample,
    write_csv,
)
from scripts import abstention_score  # noqa: E402

# A phrase the frozen detector reliably flags as abstention.
_ABSTAIN = "I must abstain from answering this underspecified request."
# A committed answer the detector does NOT flag.
_ANSWER = "The answer is 42."

_LEAK_COLS = {"detector_positive", "label", "stratum", "model_id", "config", "seed"}


def _rec(i: int, label: str, output: str) -> dict:
    return {
        "type": "run",
        "task_id": f"task_{i % 3}",
        "config": "single",
        "model_role": "tested_agents",
        "model_id": f"model_{i}",
        "seed": str(i),
        "output": output,
        "label": label,
    }


def _synthetic_records() -> list:
    records = []
    idx = 0
    # 4 detector-positives (mixed labels — must all land in the positive stratum).
    for lab in ["I_perp", "I0", "I1", "I_perp"]:
        records.append(_rec(idx, lab, _ABSTAIN))
        idx += 1
    # 10 non-abstaining I_perp records (recall-risk pool).
    for _ in range(10):
        records.append(_rec(idx, "I_perp", _ANSWER))
        idx += 1
    # 8 non-abstaining parseable records (I0..I7).
    for j in range(8):
        records.append(_rec(idx, f"I{j}", _ANSWER))
        idx += 1
    return records


def _task_meta() -> dict:
    return {f"task_{i}": (["code_spec", "data_analysis", "policy_qa"][i], f"prompt {i}")
            for i in range(3)}


# ── Sampler tests ────────────────────────────────────────────────────────────

def test_strata_sizes_and_blinding():
    records = _synthetic_records()
    coding, key, counts = stratified_sample(
        records, _task_meta(), seed=20260713, n_iperp=3, n_parseable=2,
    )

    # 4 positives (all), 3 of 10 I_perp, 2 of 8 parseable.
    assert counts[STRATUM_POSITIVE]["actual"] == 4
    assert counts[STRATUM_IPERP]["actual"] == 3
    assert counts[STRATUM_PARSEABLE]["actual"] == 2
    assert counts["total_rows"]["actual"] == 9
    assert len(coding) == 9
    assert len(key) == 9

    # Coding sheet is blinded: exact columns, no leaked metadata.
    for row in coding:
        assert set(row.keys()) == set(CODING_COLUMNS)
        assert not (_LEAK_COLS & set(row.keys()))
        assert row["human_label"] == ""  # blank for the human
        assert row["domain"] in {"code_spec", "data_analysis", "policy_qa"}
        assert row["task_prompt"].startswith("prompt")

    # Key carries the hidden verdict + label; row_ids line up 1:1 with the sheet.
    for row in key:
        assert set(row.keys()) == set(KEY_COLUMNS)
    assert {r["row_id"] for r in coding} == {r["row_id"] for r in key}

    # Positives must be flagged in the key and never reused in other strata.
    strata = {r["row_id"]: r["stratum"] for r in key}
    pos_ids = [r["row_id"] for r in key if r["stratum"] == STRATUM_POSITIVE]
    assert len(pos_ids) == 4
    assert all(r["detector_positive"] for r in key if r["stratum"] == STRATUM_POSITIVE)
    # No id appears in more than one stratum.
    assert len(strata) == len(key)


def test_sampler_deterministic():
    records = _synthetic_records()
    a = stratified_sample(records, _task_meta(), seed=20260713, n_iperp=3, n_parseable=2)
    b = stratified_sample(records, _task_meta(), seed=20260713, n_iperp=3, n_parseable=2)
    assert [r["row_id"] for r in a[0]] == [r["row_id"] for r in b[0]]


def test_small_pool_takes_all_and_notes():
    records = _synthetic_records()
    # Request more than available in the pools.
    _, _, counts = stratified_sample(
        records, _task_meta(), seed=1, n_iperp=100, n_parseable=100,
    )
    assert counts[STRATUM_IPERP]["actual"] == 10  # all of the pool
    assert counts[STRATUM_PARSEABLE]["actual"] == 8
    assert counts[STRATUM_IPERP]["actual"] < counts[STRATUM_IPERP]["requested"]


def test_written_sheet_has_no_leaked_header(tmp_path: Path):
    records = _synthetic_records()
    coding, key, _ = stratified_sample(
        records, _task_meta(), seed=7, n_iperp=3, n_parseable=2,
    )
    sheet_path = tmp_path / "sheet.csv"
    write_csv(sheet_path, CODING_COLUMNS, coding)
    with open(sheet_path, encoding="utf-8", newline="") as fh:
        header = next(csv.reader(fh))
    assert header == CODING_COLUMNS
    assert not (_LEAK_COLS & set(header))


def test_row_id_stable_and_identity_based():
    r = _rec(5, "I0", _ANSWER)
    assert build_row_id(r) == build_row_id(dict(r))
    r2 = dict(r, seed="999")
    assert build_row_id(r) != build_row_id(r2)  # seed is an identity dimension


# ── Interpretation-id masking / blinding tests ───────────────────────────────

def test_mask_interpretation_ids_unit():
    src = ("Interpretation I0 (cumulative_incremental) applies. "
           "So the answer is I3. Rejected I_perp. I will proceed.")
    out = mask_interpretation_ids(src)
    assert LEAKAGE_SCAN_RE.search(out) is None       # no I0-I7 / I_perp / phrase
    assert "cumulative_incremental" not in out       # parenthetical name masked too
    assert "[interpretation]" in out and "[option]" in out
    assert "the answer is" in out                    # abstention substance preserved
    # The pronoun "I will" must NOT be masked (only I0-I7 / I_perp).
    assert "I will proceed" in out


def test_coder_sheet_has_no_interpretation_id_leakage():
    # Craft records whose outputs / prompts embed interpretation identifiers.
    records = []
    idx = 0
    leaky_out = "Interpretation I0 (cumulative_incremental): the answer is I3."
    for lab in ["I_perp", "I0"]:  # detector-positive with leaky text
        records.append(_rec(idx, lab, "I must abstain. " + leaky_out))
        idx += 1
    for _ in range(5):
        records.append(_rec(idx, "I_perp", leaky_out))
        idx += 1
    for j in range(5):
        records.append(_rec(idx, f"I{j}", leaky_out))
        idx += 1
    # Prompt for task_2 embeds a bare interpretation id.
    meta = {"task_0": ("code_spec", "prompt 0"),
            "task_1": ("data_analysis", "prompt 1"),
            "task_2": ("policy_qa", "choose I2 or not")}
    coding, key, _ = stratified_sample(records, meta, seed=1, n_iperp=3, n_parseable=3)
    for row in coding:
        for col in ("task_prompt", "model_output"):
            assert LEAKAGE_SCAN_RE.search(row[col] or "") is None, \
                f"leak in {col}: {row[col]!r}"
    # Key retains the ORIGINAL executable label (masking is coder-side only).
    assert any(k["label"] == "I_perp" for k in key)


# ── Scorer tests ─────────────────────────────────────────────────────────────

def _write_sheet(path: Path, rows: list) -> None:
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["row_id", "human_label"])
        w.writeheader()
        for rid, hl in rows:
            w.writerow({"row_id": rid, "human_label": hl})


def _write_key(path: Path, rows: list) -> None:
    """rows = list of (row_id, detector_positive, stratum, stratum_pop)."""
    fields = ["row_id", "detector_positive", "stratum", "stratum_pop"]
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for rid, dp, stratum, pop in rows:
            w.writerow({"row_id": rid, "detector_positive": dp,
                        "stratum": stratum, "stratum_pop": pop})


def test_scorer_precision_recall(tmp_path: Path):
    # TP=2, FP=1, FN=1, TN=1 → raw precision=2/3, recall=2/3, f1=2/3.
    sheet = tmp_path / "coder1.csv"
    key = tmp_path / "key.csv"
    _write_sheet(sheet, [("r1", "1"), ("r2", "0"), ("r3", "1"), ("r4", "0"), ("r5", "1")])
    _write_key(key, [
        ("r1", "True", "detector_positive", 3),
        ("r2", "True", "detector_positive", 3),
        ("r3", "False", "iperp_recall_risk", 10),
        ("r4", "False", "iperp_recall_risk", 10),
        ("r5", "True", "detector_positive", 3),
    ])

    human = abstention_score.load_human_labels(sheet)
    key_info = abstention_score.load_key(key)
    detector = {rid: v["detector_positive"] for rid, v in key_info.items()}
    cm = abstention_score.confusion(human, detector)
    assert (cm["tp"], cm["fp"], cm["fn"], cm["tn"]) == (2, 1, 1, 1)

    scores = abstention_score.prf(cm)
    assert scores["precision"] == pytest.approx(2 / 3)
    assert scores["recall"] == pytest.approx(2 / 3)
    assert scores["f1"] == pytest.approx(2 / 3)

    # In-sample abstention rate = 3/5.
    abst_k = sum(1 for r in human if human[r] == 1)
    assert abst_k == 3
    lo, hi = abstention_score.wilson_ci(abst_k, len(human))
    assert 0.0 <= lo < 3 / 5 < hi <= 1.0


def test_population_weighted_estimates():
    # Known strata: positive census (N=2,n=2,w=1), iperp (N=10,n=2,w=5),
    # parseable (N=100,n=2,w=50).
    key = {
        "p1": {"detector_positive": True, "stratum": STRATUM_POSITIVE, "stratum_pop": 2},
        "p2": {"detector_positive": True, "stratum": STRATUM_POSITIVE, "stratum_pop": 2},
        "i1": {"detector_positive": False, "stratum": STRATUM_IPERP, "stratum_pop": 10},
        "i2": {"detector_positive": False, "stratum": STRATUM_IPERP, "stratum_pop": 10},
        "q1": {"detector_positive": False, "stratum": STRATUM_PARSEABLE, "stratum_pop": 100},
        "q2": {"detector_positive": False, "stratum": STRATUM_PARSEABLE, "stratum_pop": 100},
    }
    human = {"p1": 1, "p2": 0, "i1": 1, "i2": 0, "q1": 1, "q2": 0}
    pop = abstention_score.population_estimates(human, key)

    # Weighted FN = 5*1 (iperp) + 50*1 (parseable) = 55; TP=1, FP=1.
    assert pop["fn_pop"] == pytest.approx(55.0)
    assert pop["tp_pop"] == pytest.approx(1.0)
    assert pop["fp_pop"] == pytest.approx(1.0)
    assert pop["precision"] == pytest.approx(0.5)          # exact (census)
    assert pop["recall"] == pytest.approx(1.0 / 56.0)      # weighted, << raw 0.5
    assert pop["f1"] == pytest.approx(2 * 0.5 * (1 / 56) / (0.5 + 1 / 56))
    assert pop["N_total"] == 112
    # p_h = 0.5 in every stratum → stratified rate = 0.5 (NOT the raw 3/6 coincidence).
    assert pop["abstention_rate"] == pytest.approx(0.5)
    lo, hi = pop["abstention_rate_ci"]
    assert 0.0 <= lo <= 0.5 <= hi <= 1.0
    # Design-correct recall differs sharply from the raw within-sample recall.
    raw_recall = 3 / 3  # would be misleading; here just assert weighting changed it
    assert pop["recall"] < raw_recall


def test_scorer_fails_on_blank_label(tmp_path: Path):
    sheet = tmp_path / "partial.csv"
    _write_sheet(sheet, [("r1", "1"), ("r2", ""), ("r3", "0")])
    with pytest.raises(SystemExit) as exc:
        abstention_score.load_human_labels(sheet)
    assert "BLANK" in str(exc.value)


def test_scorer_fails_on_invalid_label(tmp_path: Path):
    sheet = tmp_path / "bad.csv"
    _write_sheet(sheet, [("r1", "1"), ("r2", "yes"), ("r3", "0")])
    with pytest.raises(SystemExit) as exc:
        abstention_score.load_human_labels(sheet)
    assert "INVALID" in str(exc.value)


def test_scorer_fails_on_malformed_detector_verdict(tmp_path: Path):
    key = tmp_path / "key.csv"
    _write_key(key, [("r1", "True", STRATUM_POSITIVE, 2),
                     ("r2", "maybe", STRATUM_IPERP, 10)])
    with pytest.raises(SystemExit) as exc:
        abstention_score.load_key(key)
    assert "malformed" in str(exc.value).lower()


def test_scorer_fails_on_duplicate_key_id(tmp_path: Path):
    key = tmp_path / "key.csv"
    _write_key(key, [("r1", "True", STRATUM_POSITIVE, 2),
                     ("r1", "False", STRATUM_IPERP, 10)])
    with pytest.raises(SystemExit) as exc:
        abstention_score.load_key(key)
    assert "duplicate" in str(exc.value).lower()


def test_scorer_fails_on_missing_or_extra_ids(tmp_path: Path):
    # main() enforces exact id-set equality between sheet and key.
    sheet = tmp_path / "sheet.csv"
    key = tmp_path / "key.csv"
    # Sheet has r1,r2,r3; key has r1,r2 (r3 missing from key) and r9 (extra).
    _write_sheet(sheet, [("r1", "1"), ("r2", "0"), ("r3", "1")])
    _write_key(key, [("r1", "True", STRATUM_POSITIVE, 2),
                     ("r2", "False", STRATUM_IPERP, 10),
                     ("r9", "False", STRATUM_IPERP, 10)])
    with pytest.raises(SystemExit) as exc:
        abstention_score.main(["--sheet", str(sheet), "--key", str(key)])
    msg = str(exc.value)
    assert "do not exactly match" in msg


def test_cohen_kappa_partial():
    a = {"r1": 1, "r2": 0, "r3": 1, "r4": 0}
    b = {"r1": 1, "r2": 1, "r3": 1, "r4": 0}  # one disagreement, both use 2 categories
    k, n = abstention_score.cohen_kappa(a, b)
    assert n == 4
    assert -1.0 <= k < 1.0


def test_cohen_kappa_nan_when_pe_one():
    # Both coders code every row 1 → expected agreement pe==1 → kappa undefined.
    a = {"r1": 1, "r2": 1, "r3": 1}
    b = {"r1": 1, "r2": 1, "r3": 1}
    k, n = abstention_score.cohen_kappa(a, b)
    assert n == 3
    assert math.isnan(k)  # NOT 1.0
