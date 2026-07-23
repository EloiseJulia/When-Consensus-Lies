# constructed by: Claude (Anthropic) family
"""Study 2 LPS CONFIRMATORY analysis + report (Phase 2a).

# Implementer model family: Claude / Anthropic
# Auditor model family: MUST be non-Anthropic (Law 6 — cross-family requirement)

Reads the confirmatory checkpoint (``.run_partitions/cp_lps_confirm.jsonl``,
produced by ``lps_confirm.py``), joins the executable, detector-independent
gold-ambiguity label (``lps_gold``), and computes — PER MODEL and POOLED — the
pre-registered detection read (``paper/preregistration/2026-07-23-study2-prereg-
FROZEN.md``):

  * PRIMARY: AUROC of ``H_ctx-self`` vs gold-ambiguity (AMB+ vs AMB−) with
    item-level bootstrap CIs, AND the AUROC of EACH baseline on the SAME test
    (``H_seed``, token-logprob/answer-token-confidence, self-consistency,
    requirements-probing) — the baselines must be shown to lose in the danger
    quadrant.
  * The item-flag confusion + precision/recall + k0 (AMB−) false-positive rate at
    the FROZEN operating point (τ = 0.0, τ_s = 0.5 bits).
  * Danger-quadrant mass: AMB+ ∧ H_seed ≤ 0.5 ∧ H_ctx-self > 0 (the SOTA-blind
    zone the study targets).
  * Localization (SECONDARY): argmax-H_ctx dimension matches the true deleted axis.

Bootstrap CIs resample ITEMS with replacement (item-level, deterministic via
``random.Random``). Mean-based CIs (danger mass, precision/recall) reuse
``registered_run._bootstrap_ci``; the threshold-free AUROC CI uses an
AUROC-specific item bootstrap (a mean-of-samples CI is not valid for AUROC).

Gold-ambiguity is used for EVALUATION ONLY (never in any prompt) — non-circular
(benchmark-enumerated interpretations vs the detector's model-self pins).

Usage:
    python scripts/lps_confirm_report.py \\
        --checkpoint .run_partitions/cp_lps_confirm.jsonl \\
        --out files/study2_confirm_results.md
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_SCRIPTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPTS_DIR.parent
for _p in (str(_REPO_ROOT), str(_SCRIPTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import lps_gold as gold  # noqa: E402
import lps_baselines as baselines  # noqa: E402
from lps_pilot2 import _auroc  # noqa: E402  (tie-aware Mann-Whitney AUROC — reuse)

AMB_POS = gold.STRATUM_AMB_POS
NON_DISC = gold.STRATUM_NON_DISC
AMB_NEG = gold.STRATUM_AMB_NEG

#: FROZEN operating point (prereg §2).
TAU = 0.0
TAU_S = 0.5

#: Every signal scored for AUROC-vs-gold-ambiguity (higher ⇒ more ambiguous).
#: ``H_ctx_self`` is the PRIMARY detector; the rest are the baseline panel.
SIGNAL_ORDER = [
    ("H_ctx_self", "H_ctx-self (DETECTOR)"),
    ("H_seed", "H_seed (semantic entropy)"),
    ("token_logprob", "answer-token confidence (1 − logit_conf)"),
    ("self_consistency", "self-consistency disagreement"),
    ("requirements_probing", "requirements probing (# dims)"),
]


# ── Loading ──────────────────────────────────────────────────────────────────

def load_records(checkpoint_path: str) -> List[Dict[str, Any]]:
    """Load detector records (skipping the header line) from a confirm checkpoint."""
    p = Path(checkpoint_path)
    if not p.exists():
        raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")
    out: List[Dict[str, Any]] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("_header"):
            continue
        out.append(rec)
    return out


def _signal_scores(record: Dict[str, Any]) -> Dict[str, Optional[float]]:
    """All AUROC signals for one record (higher ⇒ ambiguous). None ⇒ N/A/excluded."""
    scores: Dict[str, Optional[float]] = {}
    hctx = record.get("H_ctx_max")
    scores["H_ctx_self"] = float(hctx) if isinstance(hctx, (int, float)) else None
    scores.update(baselines.record_baseline_scores(record))
    return scores


def _is_flagged_frozen(record: Dict[str, Any], *, tau: float = TAU,
                       tau_s: float = TAU_S) -> bool:
    """Recompute the item flag at the FROZEN operating point (not the stored τ)."""
    hctx = record.get("H_ctx_max")
    hseed = record.get("H_seed")
    if not isinstance(hctx, (int, float)) or not isinstance(hseed, (int, float)):
        return False
    return bool(hctx > tau and hseed <= tau_s)


# ── Metrics ──────────────────────────────────────────────────────────────────

def _auroc_ci(pairs: List[Tuple[float, int]], *, n_boot: int = 2000,
              seed: int = 42) -> Tuple[Optional[float], Optional[float]]:
    """Item-level bootstrap 95% CI for AUROC (resample the (score,label) pairs).

    A mean-of-samples CI (``registered_run._bootstrap_ci``) is NOT valid for AUROC,
    so we resample the paired items with replacement and recompute the tie-aware
    AUROC each time (deterministic ``random.Random``). Returns (None, None) if
    either class is empty in the base sample.
    """
    if _auroc(pairs) is None:
        return (None, None)
    rng = random.Random(seed)
    n = len(pairs)
    boots: List[float] = []
    for _ in range(n_boot):
        sample = [pairs[rng.randrange(n)] for _ in range(n)]
        a = _auroc(sample)
        if a is not None:
            boots.append(a)
    if not boots:
        return (None, None)
    boots.sort()
    lo_idx = max(0, int(len(boots) * 0.025) - 1)
    hi_idx = min(len(boots) - 1, int(len(boots) * 0.975))
    return boots[lo_idx], boots[hi_idx]


def _mean_ci(binary: List[float]) -> Tuple[Optional[float], Optional[float]]:
    """Mean 95% CI reusing ``registered_run._bootstrap_ci`` (item-level)."""
    if not binary:
        return (None, None)
    from registered_run import _bootstrap_ci
    lo, hi = _bootstrap_ci([float(x) for x in binary])
    return lo, hi


def _auroc_for_signal(rows: List[Dict[str, Any]], signal: str
                      ) -> Dict[str, Any]:
    """AUROC of one signal for AMB+ (1) vs AMB− (0), with item-level bootstrap CI.

    Items whose signal is None (e.g. token-logprob on a model without logprobs) are
    EXCLUDED from that signal's AUROC and counted in ``n_na``.
    """
    pairs: List[Tuple[float, int]] = []
    n_na = 0
    for r in rows:
        stratum = r.get("stratum")
        if stratum not in (AMB_POS, AMB_NEG):
            continue
        score = _signal_scores(r).get(signal)
        if score is None:
            n_na += 1
            continue
        pairs.append((score, 1 if stratum == AMB_POS else 0))
    auroc = _auroc(pairs)
    ci_lo, ci_hi = _auroc_ci(pairs) if auroc is not None else (None, None)
    return {
        "auroc": auroc,
        "ci_lo": ci_lo,
        "ci_hi": ci_hi,
        "n_pos": sum(1 for _, y in pairs if y == 1),
        "n_neg": sum(1 for _, y in pairs if y == 0),
        "n_na": n_na,
    }


def analyze_group(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Full detection read for one group of records (a single model, or pooled)."""
    joined = [r for r in rows if r.get("stratum") is not None]
    amb_pos = [r for r in joined if r["stratum"] == AMB_POS]
    amb_neg = [r for r in joined if r["stratum"] == AMB_NEG]
    non_disc = [r for r in joined if r["stratum"] == NON_DISC]

    # ── AUROC per signal (detector + baselines) ──────────────────────────────
    aurocs = {sig: _auroc_for_signal(joined, sig) for sig, _label in SIGNAL_ORDER}

    # ── Item-flag confusion at the FROZEN operating point ────────────────────
    tp = sum(1 for r in amb_pos if _is_flagged_frozen(r))
    fn = len(amb_pos) - tp
    fp = sum(1 for r in amb_neg if _is_flagged_frozen(r))
    tn = len(amb_neg) - fp
    precision = (tp / (tp + fp)) if (tp + fp) else None
    recall = (tp / (tp + fn)) if (tp + fn) else None
    k0_fp_rate = (fp / len(amb_neg)) if amb_neg else None

    # ── Danger-quadrant mass: AMB+ ∧ H_seed ≤ τ_s ∧ H_ctx-self > 0 ───────────
    def _danger(r: Dict[str, Any]) -> bool:
        hs = r.get("H_seed")
        hc = r.get("H_ctx_max")
        return (isinstance(hs, (int, float)) and isinstance(hc, (int, float))
                and hs <= TAU_S and hc > 0.0)

    danger_flags = [1.0 if _danger(r) else 0.0 for r in amb_pos]
    n_danger = int(sum(danger_flags))
    danger_lo, danger_hi = _mean_ci(danger_flags)

    # ── Localization (SECONDARY): argmax dim == true deleted axis, on AMB+ ────
    loc_flags = [1.0 if r.get("axis_match") else 0.0 for r in amb_pos]
    loc_rate = (sum(loc_flags) / len(loc_flags)) if loc_flags else None

    return {
        "n_records": len(joined),
        "strata_counts": {
            AMB_POS: len(amb_pos), NON_DISC: len(non_disc), AMB_NEG: len(amb_neg),
        },
        "aurocs": aurocs,
        "flag_confusion": {"TP": tp, "FP": fp, "FN": fn, "TN": tn},
        "flag_precision": precision,
        "flag_recall": recall,
        "k0_false_positive_rate": k0_fp_rate,
        "danger_quadrant": {
            "n_AMB_pos": len(amb_pos),
            "n_danger": n_danger,
            "mass": (n_danger / len(amb_pos)) if amb_pos else None,
            "ci_lo": danger_lo,
            "ci_hi": danger_hi,
        },
        "localization_AMB_pos_hit_rate": loc_rate,
    }


def analyze(records: List[Dict[str, Any]], gold_by_id: Dict[str, Dict[str, Any]]
            ) -> Dict[str, Any]:
    """Join gold + analyse per-model and pooled."""
    joined: List[Dict[str, Any]] = []
    for r in records:
        g = gold_by_id.get(r.get("task_id"), {})
        rr = dict(r)
        rr["stratum"] = g.get("stratum")
        rr["H_ctx_gold"] = g.get("H_ctx_gold")
        joined.append(rr)

    by_model: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in joined:
        by_model[r.get("model", "?")].append(r)

    per_model = {m: analyze_group(rows) for m, rows in sorted(by_model.items())}
    pooled = analyze_group(joined)
    return {"per_model": per_model, "pooled": pooled, "n_records": len(joined)}


# ── Markdown rendering ───────────────────────────────────────────────────────

def _fmt(v: Optional[float], nd: int = 3) -> str:
    return "—" if v is None else f"{v:.{nd}f}"


def _fmt_auroc(a: Dict[str, Any]) -> str:
    if a["auroc"] is None:
        return "N/A"
    ci = ""
    if a["ci_lo"] is not None:
        ci = f" [{_fmt(a['ci_lo'])}, {_fmt(a['ci_hi'])}]"
    na = f" (N/A×{a['n_na']})" if a.get("n_na") else ""
    return f"{a['auroc']:.3f}{ci}{na}"


def _auroc_table(groups: List[Tuple[str, Dict[str, Any]]]) -> List[str]:
    """AUROC table: one row per group (models + pooled), one column per signal."""
    header = "| Group | " + " | ".join(lbl for _sig, lbl in SIGNAL_ORDER) + " |"
    sep = "|" + "---|" * (len(SIGNAL_ORDER) + 1)
    lines = [header, sep]
    for name, a in groups:
        cells = [_fmt_auroc(a["aurocs"][sig]) for sig, _lbl in SIGNAL_ORDER]
        lines.append(f"| **{name}** | " + " | ".join(cells) + " |")
    return lines


def _operating_table(groups: List[Tuple[str, Dict[str, Any]]]) -> List[str]:
    header = ("| Group | AMB+ | AMB− | TP | FP | FN | TN | Precision | Recall | "
              "k0 FP-rate | Danger mass | Localization |")
    sep = "|" + "---|" * 13
    lines = [header, sep]
    for name, a in groups:
        sc = a["strata_counts"]
        c = a["flag_confusion"]
        dq = a["danger_quadrant"]
        dmass = (f"{_fmt(dq['mass'])} ({dq['n_danger']}/{dq['n_AMB_pos']})"
                 if dq["mass"] is not None else "—")
        lines.append(
            f"| **{name}** | {sc[AMB_POS]} | {sc[AMB_NEG]} | {c['TP']} | {c['FP']} | "
            f"{c['FN']} | {c['TN']} | {_fmt(a['flag_precision'])} | "
            f"{_fmt(a['flag_recall'])} | {_fmt(a['k0_false_positive_rate'])} | "
            f"{dmass} | {_fmt(a['localization_AMB_pos_hit_rate'])} |"
        )
    return lines


def render_markdown(result: Dict[str, Any], *, checkpoint: str,
                    n_models: int) -> str:
    pooled = result["pooled"]
    groups = [(m, a) for m, a in result["per_model"].items()]
    groups_with_pooled = groups + [("POOLED", pooled)]

    p_hctx = pooled["aurocs"]["H_ctx_self"]["auroc"]
    p_hseed = pooled["aurocs"]["H_seed"]["auroc"]
    delta = (p_hctx - p_hseed) if (p_hctx is not None and p_hseed is not None) else None
    dq = pooled["danger_quadrant"]

    lines: List[str] = []
    lines.append("# Study 2 — Confirmatory detection results (Phase 2a)")
    lines.append("")
    lines.append("> Generated by `scripts/lps_confirm_report.py`. Impl family: "
                 "Claude (Anthropic). Cross-family audit REQUIRED before any merge "
                 "(Law 6).")
    lines.append("")
    lines.append(f"- Checkpoint: `{checkpoint}`")
    lines.append(f"- Records analysed: {result['n_records']} "
                 f"across {n_models} model(s)")
    lines.append(f"- FROZEN operating point: τ = {TAU}, τ_s = {TAU_S} bits (prereg §2)")
    lines.append("- Gold-ambiguity is executable + detector-independent "
                 "(`lps_gold`); used for EVALUATION only (never in a prompt).")
    lines.append("")

    lines.append("## 1. Pre-registered PRIMARY read (pooled)")
    lines.append("")
    lines.append(f"- **AUROC(H_ctx-self)** = {_fmt(p_hctx)} "
                 f"(pre-committed ≥ 0.75)")
    lines.append(f"- **AUROC(H_seed)** = {_fmt(p_hseed)} "
                 f"— semantic-entropy baseline")
    lines.append(f"- **ΔAUROC (H_ctx-self − H_seed)** = {_fmt(delta)} "
                 f"(pre-committed ≥ 0.15)")
    lines.append(f"- **Danger-quadrant mass** = {_fmt(dq['mass'])} "
                 f"({dq['n_danger']}/{dq['n_AMB_pos']}) "
                 f"(pre-committed ≥ 0.40; the SOTA-blind zone)")
    h1a1 = (p_hctx is not None and p_hseed is not None
            and p_hctx >= 0.75 and delta is not None and delta >= 0.15)
    lines.append(f"- Pre-committed H-A1′ direction met (pooled)? "
                 f"**{'YES' if h1a1 else 'NO / WEAK'}** "
                 f"(confirmatory read — reported per the frozen prereg).")
    lines.append("")

    lines.append("## 2. AUROC vs gold-ambiguity — detector + baseline panel")
    lines.append("")
    lines.append("Higher ⇒ more ambiguous. `[lo, hi]` = item-level bootstrap 95% CI. "
                 "`N/A×n` = items excluded because the signal is unavailable "
                 "(e.g. token-logprob on a non-OpenAI slug).")
    lines.append("")
    lines.extend(_auroc_table(groups_with_pooled))
    lines.append("")

    lines.append("## 3. Operating point (τ=0, τ_s=0.5) — confusion, danger, "
                 "localization")
    lines.append("")
    lines.append("`Danger mass` = AMB+ ∧ H_seed ≤ 0.5 ∧ H_ctx-self > 0. "
                 "`Localization` (SECONDARY) = argmax-H_ctx dim matches the true "
                 "deleted axis on AMB+.")
    lines.append("")
    lines.extend(_operating_table(groups_with_pooled))
    lines.append("")

    lines.append("## 4. Notes / honesty")
    lines.append("")
    lines.append("- Token-logprob baseline is N/A for models that do not expose "
                 "logprobs (Anthropic / Google slugs); shown as `N/A` where so.")
    lines.append("- Localization is a SECONDARY metric (known-weak; a recall lever, "
                 "not a headline) — reported honestly.")
    lines.append("- AUROC CIs resample items with replacement; danger-mass / "
                 "precision-recall CIs reuse `registered_run._bootstrap_ci`.")
    lines.append("- Metric definitions are FROZEN (prereg); never changed "
                 "post-freeze (Law 7).")
    lines.append("")
    return "\n".join(lines)


# ── CLI ──────────────────────────────────────────────────────────────────────

def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description="Study 2 LPS CONFIRMATORY analysis + markdown report."
    )
    parser.add_argument("--checkpoint",
                        default=".run_partitions/cp_lps_confirm.jsonl")
    parser.add_argument("--out", default="files/study2_confirm_results.md")
    args = parser.parse_args(argv)

    import registered_run as _rr
    records = load_records(args.checkpoint)
    if not records:
        print(f"[Report] No records in {args.checkpoint}.")
        return

    tasks = _rr.load_tasks()
    gold_by_id = gold.stratify(tasks)
    result = analyze(records, gold_by_id)

    n_models = len(result["per_model"])
    md = render_markdown(result, checkpoint=args.checkpoint, n_models=n_models)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")

    pooled = result["pooled"]
    print(f"[Report] Analysed {result['n_records']} records across {n_models} "
          f"model(s).")
    print(f"[Report] Pooled AUROC H_ctx-self = "
          f"{_fmt(pooled['aurocs']['H_ctx_self']['auroc'])}  |  "
          f"H_seed = {_fmt(pooled['aurocs']['H_seed']['auroc'])}")
    print(f"[Report] Pooled danger-quadrant mass = "
          f"{_fmt(pooled['danger_quadrant']['mass'])}")
    print(f"[Report] Wrote {out_path}")


if __name__ == "__main__":
    main()
