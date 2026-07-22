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


def load_key(path: Path) -> Dict[str, bool]:
    """Load {row_id → detector_positive(bool)} from the hidden key file."""
    rows = _read_csv(path)
    out: Dict[str, bool] = {}
    for row in rows:
        rid = (row.get("row_id") or "").strip()
        val = (row.get("detector_positive") or "").strip().lower()
        out[rid] = val in {"true", "1", "yes"}
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
    if pe == 1.0:
        return (1.0 if po == 1.0 else 0.0, n)
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


# ── Report ───────────────────────────────────────────────────────────────────

def _fmt(x: float) -> str:
    return "n/a" if x != x else f"{x:.4f}"


def build_report(
    cm: Dict[str, int],
    scores: Dict[str, float],
    abst_k: int,
    abst_n: int,
    abst_ci: Tuple[float, float],
    kappa: Optional[Tuple[float, int]] = None,
) -> str:
    lines: List[str] = []
    lines.append("# Abstention detector — human validation results\n")
    lines.append(f"Rows scored (coder1 ∩ key): **{cm['n']}**\n")
    lines.append("## Confusion matrix (detector = prediction, human = truth)\n")
    lines.append("Positive class = abstention / clarification.\n")
    lines.append("| | human=1 (abstain) | human=0 (answer) |")
    lines.append("|---|---|---|")
    lines.append(f"| **detector=1** | TP = {cm['tp']} | FP = {cm['fp']} |")
    lines.append(f"| **detector=0** | FN = {cm['fn']} | TN = {cm['tn']} |\n")
    lines.append("## Detector performance vs human\n")
    lines.append(f"- Precision: **{_fmt(scores['precision'])}**")
    lines.append(f"- Recall:    **{_fmt(scores['recall'])}**")
    lines.append(f"- F1:        **{_fmt(scores['f1'])}**\n")
    lines.append("## Human abstention rate (in-sample)\n")
    rate = abst_k / abst_n if abst_n else float("nan")
    lines.append(f"- {abst_k} / {abst_n} rows coded as abstention "
                 f"= **{_fmt(rate)}**")
    lines.append(f"- Wilson 95% CI: **[{_fmt(abst_ci[0])}, {_fmt(abst_ci[1])}]**")
    lines.append("\n> NOTE: the sample is STRATIFIED (positives + I_perp + parseable),")
    lines.append("> so this in-sample rate is NOT a population abstention rate.")
    lines.append("> It summarises the coded validation set only.\n")
    if kappa is not None:
        lines.append("## Inter-rater agreement (coder1 vs coder2)\n")
        lines.append(f"- Cohen's kappa: **{_fmt(kappa[0])}** over {kappa[1]} shared rows\n")
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
    detector = load_key(Path(args.key))

    missing = set(human) - set(detector)
    if missing:
        raise SystemExit(f"ERROR: {len(missing)} coded row_id(s) not in key: "
                         f"{sorted(missing)[:10]}")

    cm = confusion(human, detector)
    scores = prf(cm)
    abst_k = sum(1 for r in human if human[r] == 1)
    abst_n = len(human)
    abst_ci = wilson_ci(abst_k, abst_n)

    kappa = None
    if args.coder2:
        human2 = load_human_labels(Path(args.coder2))
        kappa = cohen_kappa(human, human2)

    report = build_report(cm, scores, abst_k, abst_n, abst_ci, kappa)
    print(report)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report + "\n", encoding="utf-8")
        print(f"\nWrote report → {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
