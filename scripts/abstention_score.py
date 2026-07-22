#!/usr/bin/env python
"""Score the FILLED abstention coding sheet against the rule-based detector.

Reads the human-coded ``abstention_coding_sheet.csv`` (with ``human_label``
filled by a coder) and the hidden ``abstention_key.csv`` (carrying the detector
verdict), joins on ``row_id``, and reports the detector's precision / recall /
F1 vs the human ground truth, plus the in-sample human abstention rate with a
Wilson 95% CI. With a second coder file (``--coder2``) it also reports Cohen's
kappa (inter-rater agreement).

This script FAILS LOUDLY if any ``human_label`` is blank or invalid — it never
fabricates or defaults a label.

Usage
-----
    python scripts/abstention_score.py
    python scripts/abstention_score.py --coder2 files/coder2_sheet.csv \\
        --out files/abstention_validation_results.md
"""
from __future__ import annotations

import argparse
import csv
import math
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[1]

_VALID = {"0", "1"}


# ── IO ───────────────────────────────────────────────────────────────────────

def _read_csv(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def load_human_labels(path: Path, *, label_col: str = "human_label") -> Dict[str, int]:
    """Load {row_id → int(0/1)} from a filled coding sheet. Fail loudly on gaps.

    Raises SystemExit if any row has a missing/blank/invalid human_label, or a
    duplicate/missing row_id.
    """
    rows = _read_csv(path)
    if not rows:
        raise SystemExit(f"ERROR: {path} has no data rows.")
    if label_col not in rows[0]:
        raise SystemExit(f"ERROR: {path} has no '{label_col}' column "
                         f"(columns: {list(rows[0].keys())}).")

    labels: Dict[str, int] = {}
    blanks: List[str] = []
    invalid: List[Tuple[str, str]] = []
    for i, row in enumerate(rows):
        rid = (row.get("row_id") or "").strip()
        if not rid:
            raise SystemExit(f"ERROR: {path} row {i + 2} has a blank row_id.")
        raw = (row.get(label_col) or "").strip()
        if raw == "":
            blanks.append(rid)
            continue
        if raw not in _VALID:
            invalid.append((rid, raw))
            continue
        if rid in labels:
            raise SystemExit(f"ERROR: duplicate row_id {rid!r} in {path}.")
        labels[rid] = int(raw)

    if blanks or invalid:
        msg = [f"ERROR: {path} has un-coded / invalid '{label_col}' values "
               f"— refusing to score a partial sheet."]
        if blanks:
            msg.append(f"  {len(blanks)} BLANK row(s): {blanks[:10]}"
                       + (" …" if len(blanks) > 10 else ""))
        if invalid:
            msg.append(f"  {len(invalid)} INVALID (not 0/1): {invalid[:10]}"
                       + (" …" if len(invalid) > 10 else ""))
        raise SystemExit("\n".join(msg))

    return labels


def load_key(path: Path) -> Dict[str, Dict[str, object]]:
    """Load the hidden key: {row_id → {detector_positive, stratum, stratum_pop}}.

    Strict: fails loudly on a blank/duplicate row_id or a malformed
    ``detector_positive`` verdict (never coerces silently).
    """
    rows = _read_csv(path)
    if not rows:
        raise SystemExit(f"ERROR: {path} has no data rows.")
    for req in ("row_id", "detector_positive", "stratum", "stratum_pop"):
        if req not in rows[0]:
            raise SystemExit(f"ERROR: {path} missing required column {req!r} "
                             f"(columns: {list(rows[0].keys())}).")

    out: Dict[str, Dict[str, object]] = {}
    for i, row in enumerate(rows):
        rid = (row.get("row_id") or "").strip()
        if not rid:
            raise SystemExit(f"ERROR: {path} row {i + 2} has a blank row_id.")
        if rid in out:
            raise SystemExit(f"ERROR: duplicate row_id {rid!r} in {path}.")
        raw = (row.get("detector_positive") or "").strip().lower()
        if raw in {"true", "1"}:
            dp = True
        elif raw in {"false", "0"}:
            dp = False
        else:
            raise SystemExit(
                f"ERROR: {path} row {i + 2} (row_id {rid}) has a malformed "
                f"detector_positive verdict {row.get('detector_positive')!r}; "
                f"expected true/false.")
        try:
            pop = int(str(row.get("stratum_pop")).strip())
        except (TypeError, ValueError):
            raise SystemExit(
                f"ERROR: {path} row {i + 2} (row_id {rid}) has a malformed "
                f"stratum_pop {row.get('stratum_pop')!r}; expected an integer.")
        out[rid] = {
            "detector_positive": dp,
            "stratum": (row.get("stratum") or "").strip(),
            "stratum_pop": pop,
        }
    return out


# ── Statistics ───────────────────────────────────────────────────────────────

def wilson_ci(k: int, n: int, z: float = 1.959963984540054) -> Tuple[float, float]:
    """Wilson score 95% CI for a binomial proportion."""
    if n == 0:
        return (float("nan"), float("nan"))
    phat = k / n
    denom = 1.0 + z * z / n
    center = (phat + z * z / (2 * n)) / denom
    half = (z * math.sqrt(phat * (1 - phat) / n + z * z / (4 * n * n))) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def cohen_kappa(labels_a: Dict[str, int], labels_b: Dict[str, int]) -> Tuple[float, int]:
    """Cohen's kappa for two coders over their common row_ids (binary labels)."""
    common = sorted(set(labels_a) & set(labels_b))
    n = len(common)
    if n == 0:
        return (float("nan"), 0)
    a = [labels_a[r] for r in common]
    b = [labels_b[r] for r in common]
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    pa1 = sum(a) / n
    pb1 = sum(b) / n
    pe = pa1 * pb1 + (1 - pa1) * (1 - pb1)
    if pe >= 1.0:
        # Degenerate: both coders used a single category → kappa undefined.
        return (float("nan"), n)
    return ((po - pe) / (1 - pe), n)


def confusion(human: Dict[str, int], detector: Dict[str, bool]) -> Dict[str, int]:
    """Confusion of detector (prediction) vs human (ground truth) on shared ids.

    Positive class = abstention (human_label==1 / detector_positive==True).
    """
    common = set(human) & set(detector)
    tp = fp = fn = tn = 0
    for rid in common:
        h = human[rid] == 1
        d = detector[rid]
        if d and h:
            tp += 1
        elif d and not h:
            fp += 1
        elif not d and h:
            fn += 1
        else:
            tn += 1
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "n": len(common)}


def prf(cm: Dict[str, int]) -> Dict[str, float]:
    tp, fp, fn = cm["tp"], cm["fp"], cm["fn"]
    precision = tp / (tp + fp) if (tp + fp) else float("nan")
    recall = tp / (tp + fn) if (tp + fn) else float("nan")
    if precision != precision or recall != recall or (precision + recall) == 0:
        f1 = float("nan") if (precision != precision or recall != recall) else 0.0
    else:
        f1 = 2 * precision * recall / (precision + recall)
    return {"precision": precision, "recall": recall, "f1": f1}


def population_estimates(
    human: Dict[str, int],
    key: Dict[str, Dict[str, object]],
    z: float = 1.959963984540054,
) -> Dict[str, object]:
    """Design-correct (inverse-inclusion weighted) population estimates.

    The sample is STRATIFIED: detector-positives are a census; I_perp and
    parseable detector-negatives are sub-sampled from much larger pools. Raw
    TP/(TP+FN) therefore understates population recall (I_perp over-sampled) and
    the pooled Wilson CI is not a population rate. Here each sampled row is
    weighted by its stratum inverse inclusion probability ``w_h = N_h / n_h``
    (N_h = ``stratum_pop`` from the key, n_h = sampled rows in that stratum).

    Population precision is exact (all detector-positives are a census, w=1).
    Recall / F1 use the weighted (Horvitz–Thompson) false-negative estimate.
    The abstention rate is a stratified estimator with a stratified
    survey-variance 95% CI (finite-population corrected).
    """
    # Aggregate sampled rows by stratum.
    strata: Dict[str, Dict[str, float]] = {}
    for rid, h in human.items():
        info = key[rid]
        s = str(info["stratum"])
        d = bool(info["detector_positive"])
        g = strata.setdefault(s, {
            "N": float(info["stratum_pop"]), "n": 0.0,
            "h1": 0.0, "tp": 0.0, "fp": 0.0, "fn": 0.0, "tn": 0.0,
        })
        # N_h must be consistent within a stratum.
        g["N"] = max(g["N"], float(info["stratum_pop"]))
        g["n"] += 1
        if h == 1:
            g["h1"] += 1
        if d and h == 1:
            g["tp"] += 1
        elif d and h == 0:
            g["fp"] += 1
        elif (not d) and h == 1:
            g["fn"] += 1
        else:
            g["tn"] += 1

    tp_pop = fp_pop = fn_pop = tn_pop = 0.0
    per_stratum = []
    N_total = 0.0
    rate_num = 0.0  # sum_h N_h * p_h
    var = 0.0
    for s, g in sorted(strata.items()):
        N_h, n_h = g["N"], g["n"]
        w_h = N_h / n_h if n_h else float("nan")
        tp_pop += g["tp"] * w_h
        fp_pop += g["fp"] * w_h
        fn_pop += g["fn"] * w_h
        tn_pop += g["tn"] * w_h
        p_h = g["h1"] / n_h if n_h else float("nan")
        N_total += N_h
        rate_num += N_h * p_h
        fpc = (1 - n_h / N_h) if N_h else 0.0
        if n_h > 1:
            var += (N_h ** 2) * fpc * (p_h * (1 - p_h) / (n_h - 1))
        per_stratum.append({
            "stratum": s, "N_h": int(N_h), "n_h": int(n_h),
            "weight": w_h, "human_abstain": int(g["h1"]), "p_h": p_h,
        })

    var = var / (N_total ** 2) if N_total else float("nan")
    se = math.sqrt(var) if var == var and var >= 0 else float("nan")
    rate = rate_num / N_total if N_total else float("nan")
    rate_ci = (max(0.0, rate - z * se), min(1.0, rate + z * se)) \
        if se == se else (float("nan"), float("nan"))

    precision = tp_pop / (tp_pop + fp_pop) if (tp_pop + fp_pop) else float("nan")
    recall = tp_pop / (tp_pop + fn_pop) if (tp_pop + fn_pop) else float("nan")
    if precision == precision and recall == recall and (precision + recall) > 0:
        f1 = 2 * precision * recall / (precision + recall)
    else:
        f1 = float("nan")

    return {
        "tp_pop": tp_pop, "fp_pop": fp_pop, "fn_pop": fn_pop, "tn_pop": tn_pop,
        "precision": precision, "recall": recall, "f1": f1,
        "abstention_rate": rate, "abstention_rate_ci": rate_ci,
        "N_total": int(N_total), "per_stratum": per_stratum,
    }


# ── Report ───────────────────────────────────────────────────────────────────

def _fmt(x: float) -> str:
    return "n/a" if x != x else f"{x:.4f}"


def build_report(
    cm: Dict[str, int],
    scores: Dict[str, float],
    abst_k: int,
    abst_n: int,
    abst_ci: Tuple[float, float],
    pop: Dict[str, object],
    kappa: Optional[Tuple[float, int]] = None,
) -> str:
    lines: List[str] = []
    lines.append("# Abstention detector — human validation results\n")
    lines.append(f"Rows scored (coder1 == key, exact id match): **{cm['n']}**\n")
    lines.append("## Confusion matrix (detector = prediction, human = truth)\n")
    lines.append("Positive class = abstention / clarification.\n")
    lines.append("| | human=1 (abstain) | human=0 (answer) |")
    lines.append("|---|---|---|")
    lines.append(f"| **detector=1** | TP = {cm['tp']} | FP = {cm['fp']} |")
    lines.append(f"| **detector=0** | FN = {cm['fn']} | TN = {cm['tn']} |\n")

    lines.append("## A. Raw within-sample numbers (UNWEIGHTED)\n")
    lines.append("> These treat the stratified sample as if it were a simple "
                 "random sample. They are NOT population estimates — I_perp is "
                 "over-sampled and parseable under-sampled.\n")
    lines.append(f"- Precision: **{_fmt(scores['precision'])}**")
    lines.append(f"- Recall:    **{_fmt(scores['recall'])}**")
    lines.append(f"- F1:        **{_fmt(scores['f1'])}**")
    rate = abst_k / abst_n if abst_n else float("nan")
    lines.append(f"- In-sample abstention rate: {abst_k}/{abst_n} = "
                 f"**{_fmt(rate)}**  (Wilson 95% CI "
                 f"[{_fmt(abst_ci[0])}, {_fmt(abst_ci[1])}])\n")

    lines.append("## B. Population-weighted estimates (DESIGN-CORRECT)\n")
    lines.append("> Each sampled row is weighted by its stratum inverse "
                 "inclusion probability w_h = N_h / n_h. Detector-positives are "
                 "a census (w=1) so precision is EXACT; recall / F1 / abstention "
                 "rate use the weighted (Horvitz–Thompson) estimates.\n")
    lines.append(f"- Population size N = {pop['N_total']}")
    lines.append(f"- Est. population counts: "
                 f"TP={pop['tp_pop']:.1f}, FP={pop['fp_pop']:.1f}, "
                 f"FN={pop['fn_pop']:.1f}, TN={pop['tn_pop']:.1f}")
    lines.append(f"- Precision (exact): **{_fmt(pop['precision'])}**")
    lines.append(f"- Recall (weighted): **{_fmt(pop['recall'])}**")
    lines.append(f"- F1 (weighted):     **{_fmt(pop['f1'])}**")
    rci = pop["abstention_rate_ci"]
    lines.append(f"- Population abstention rate (stratified/Horvitz–Thompson): "
                 f"**{_fmt(pop['abstention_rate'])}** "
                 f"(stratified survey 95% CI [{_fmt(rci[0])}, {_fmt(rci[1])}])\n")

    lines.append("### Stratum design\n")
    lines.append("| stratum | N_h (pop) | n_h (sampled) | weight | human=1 | p_h |")
    lines.append("|---|---|---|---|---|---|")
    for s in pop["per_stratum"]:
        lines.append(f"| {s['stratum']} | {s['N_h']} | {s['n_h']} | "
                     f"{_fmt(s['weight'])} | {s['human_abstain']} | {_fmt(s['p_h'])} |")
    lines.append("")

    if kappa is not None:
        lines.append("## Inter-rater agreement (coder1 vs coder2)\n")
        kv = "n/a (undefined — both coders single-category)" if kappa[0] != kappa[0] \
            else f"**{_fmt(kappa[0])}**"
        lines.append(f"- Cohen's kappa: {kv} over {kappa[1]} shared rows\n")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sheet", default=str(_REPO_ROOT / "files" / "abstention_coding_sheet.csv"),
                        help="Filled coding sheet (coder 1).")
    parser.add_argument("--key", default=str(_REPO_ROOT / "files" / "abstention_key.csv"),
                        help="Hidden key file with detector verdicts.")
    parser.add_argument("--coder2", default=None,
                        help="Optional second filled sheet for Cohen's kappa.")
    parser.add_argument("--out", default=None,
                        help="Optional path to write the markdown report.")
    args = parser.parse_args(argv)

    human = load_human_labels(Path(args.sheet))
    key = load_key(Path(args.key))

    # Fix 3: require EXACT row-id set equality between the filled sheet and key.
    missing = set(key) - set(human)   # coded rows deleted from the sheet
    extra = set(human) - set(key)     # rows in the sheet not present in the key
    if missing or extra:
        parts = ["ERROR: coding sheet row_ids do not exactly match the key."]
        if missing:
            parts.append(f"  {len(missing)} key row(s) MISSING from the sheet: "
                         f"{sorted(missing)[:10]}")
        if extra:
            parts.append(f"  {len(extra)} sheet row(s) NOT in the key: "
                         f"{sorted(extra)[:10]}")
        raise SystemExit("\n".join(parts))

    detector = {rid: bool(info["detector_positive"]) for rid, info in key.items()}
    cm = confusion(human, detector)
    scores = prf(cm)
    abst_k = sum(1 for r in human if human[r] == 1)
    abst_n = len(human)
    abst_ci = wilson_ci(abst_k, abst_n)
    pop = population_estimates(human, key)

    kappa = None
    if args.coder2:
        human2 = load_human_labels(Path(args.coder2))
        kappa = cohen_kappa(human, human2)

    report = build_report(cm, scores, abst_k, abst_n, abst_ci, pop, kappa)
    print(report)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report + "\n", encoding="utf-8")
        print(f"\nWrote report → {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
