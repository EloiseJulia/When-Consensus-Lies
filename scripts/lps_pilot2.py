# constructed by: Claude (Anthropic) family
"""Study 2 LPS VALIDATION PILOT (v2) — full item set under executable gold.

# Implementer model family: Claude / Anthropic
# Auditor model family: MUST be non-Anthropic (Law 6)

Implements the validation pilot of ``paper/plans/2026-07-23-study2-eval-redesign.md``
(owner-ratified redesign). Unlike ``lps_pilot.py`` (9 hand-picked items, H1/H2
regime buckets), this pilot:

  * STRATIFIES every item by the EXECUTABLE gold-ambiguity label (``lps_gold``):
    AMB+ / NON-DISC / AMB- — detector-INDEPENDENT ground truth.
  * runs the black-box detector (H_seed + H_ctx-self) on the FULL frozen item set
    (all 54: code_spec + data_analysis + policy_qa, incl. k0 controls) with ONE
    model (default openai gpt-5.6-sol) and 1 seed (a $0 pilot read).
  * reports the DECISIVE detection metrics against gold: AUROC of H_ctx-self vs
    H_seed for AMB+ vs AMB-; danger-quadrant mass; localization on AMB+; k0
    false-positive rate; and the H_ctx-self ~ H_ctx-gold correlation (does the
    black-box detector recover the oracle ambiguity magnitude?).

ANTI-CIRCULARITY: gold-ambiguity clusters the BENCHMARK's enumerated
interpretations (``lps_gold``); the detector clusters the MODEL's self-generated
pins (``lps_method``). Gold is used for EVALUATION ONLY — never in any prompt.

Isolated artifacts (path-guarded, resumable): checkpoint
``.run_partitions/cp_lps_pilot2.jsonl`` + cache ``.llm_cache_lps_pilot2``.

Usage:
    python scripts/lps_pilot2.py --dry-run              # enumerate 54 jobs
    python scripts/lps_pilot2.py --rescore-existing     # STEP 2: re-stratify old pilot (offline)
    RUNNER_LIVE=1 python scripts/lps_pilot2.py          # STEP 3: full live pilot ($0)
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_SCRIPTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPTS_DIR.parent
for _p in (str(_REPO_ROOT), str(_SCRIPTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import lps_method as lps  # noqa: E402
import lps_gold as gold  # noqa: E402
import lps_pilot as pilot1  # noqa: E402  (reuse run(), guards, path validation)

# ── Isolated artifacts (NEVER a confirmatory/other-pass path) ────────────────
CHECKPOINT = ".run_partitions/cp_lps_pilot2.jsonl"
CACHE_DIR = ".llm_cache_lps_pilot2"
MODEL = "gpt-5.6-sol"
BASE_SEED = 20260713

AMB_POS = gold.STRATUM_AMB_POS
NON_DISC = gold.STRATUM_NON_DISC
AMB_NEG = gold.STRATUM_AMB_NEG


# ── Metrics ──────────────────────────────────────────────────────────────────

def _auroc(scored: List[Tuple[float, int]]) -> Optional[float]:
    """AUROC via the Mann-Whitney U statistic with tie-aware mid-ranks.

    ``scored`` = list of (score, label) with label 1 = positive (AMB+), 0 = negative.
    Returns None if either class is empty.
    """
    pos = [s for s, y in scored if y == 1]
    neg = [s for s, y in scored if y == 0]
    if not pos or not neg:
        return None
    # Mid-rank the pooled scores.
    pooled = sorted(s for s, _ in scored)
    ranks: Dict[float, float] = {}
    i = 0
    n = len(pooled)
    while i < n:
        j = i
        while j < n and pooled[j] == pooled[i]:
            j += 1
        midrank = (i + 1 + j) / 2.0  # average of 1-based ranks in the tie block
        ranks[pooled[i]] = midrank
        i = j
    sum_ranks_pos = sum(ranks[s] for s in pos)
    n_pos, n_neg = len(pos), len(neg)
    u = sum_ranks_pos - n_pos * (n_pos + 1) / 2.0
    return u / (n_pos * n_neg)


def _pearson(xs: List[float], ys: List[float]) -> Optional[float]:
    n = len(xs)
    if n < 2:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx == 0 or syy == 0:
        return None
    return sxy / math.sqrt(sxx * syy)


def _join_gold(results: List[Dict[str, Any]], gold_by_id: Dict[str, Dict[str, Any]]
               ) -> List[Dict[str, Any]]:
    """Attach the gold-ambiguity stratum + H_ctx_gold to each detector result."""
    joined = []
    for r in results:
        g = gold_by_id.get(r["task_id"], {})
        rr = dict(r)
        rr["stratum"] = g.get("stratum")
        rr["H_ctx_gold"] = g.get("H_ctx_gold")
        rr["n_distinct_gold"] = g.get("n_distinct")
        joined.append(rr)
    return joined


def analyze(results: List[Dict[str, Any]], gold_by_id: Dict[str, Dict[str, Any]],
            *, tau: float = 0.0, tau_s: float = lps.DEFAULT_TAU_S) -> Dict[str, Any]:
    """Compute the decisive detection read against the executable gold."""
    rows = _join_gold(results, gold_by_id)
    amb_pos = [r for r in rows if r["stratum"] == AMB_POS]
    amb_neg = [r for r in rows if r["stratum"] == AMB_NEG]
    non_disc = [r for r in rows if r["stratum"] == NON_DISC]

    # ── AUROC: H_ctx-self and H_seed for AMB+ (1) vs AMB- (0) ────────────────
    pool = ([(r["H_ctx_max"], 1) for r in amb_pos]
            + [(r["H_ctx_max"], 0) for r in amb_neg])
    auroc_hctx = _auroc(pool)
    pool_seed = ([(r["H_seed"], 1) for r in amb_pos]
                 + [(r["H_seed"], 0) for r in amb_neg])
    auroc_hseed = _auroc(pool_seed)

    # ── Item-level flag confusion (operating point: is_flagged) ──────────────
    tp = sum(1 for r in amb_pos if r["is_flagged"])
    fn = len(amb_pos) - tp
    fp = sum(1 for r in amb_neg if r["is_flagged"])
    tn = len(amb_neg) - fp

    # ── Danger-quadrant mass: AMB+ with low H_seed AND high H_ctx-self (> tau) ─
    danger = [r for r in amb_pos if r["H_seed"] <= tau_s and r["H_ctx_max"] > tau]
    low_hseed_pos = [r for r in amb_pos if r["H_seed"] <= tau_s]

    # ── Localization on AMB+ (argmax dim == true deleted axis) ───────────────
    flagged_pos = [r for r in amb_pos if r["is_flagged"]]
    loc_hits_flagged = sum(1 for r in flagged_pos if r.get("axis_match"))
    loc_hits_all = sum(1 for r in amb_pos if r.get("axis_match"))

    # ── k0 (AMB-) false-positive rate ────────────────────────────────────────
    k0_fp_rate = (fp / len(amb_neg)) if amb_neg else None

    # ── H_ctx-self ~ H_ctx-gold correlation on AMB+ ──────────────────────────
    xs = [r["H_ctx_max"] for r in amb_pos if r["H_ctx_gold"] is not None]
    ys = [r["H_ctx_gold"] for r in amb_pos if r["H_ctx_gold"] is not None]
    corr = _pearson(xs, ys)

    return {
        "n_total": len(rows),
        "strata_counts": {
            AMB_POS: len(amb_pos), NON_DISC: len(non_disc), AMB_NEG: len(amb_neg),
        },
        "AUROC_H_ctx_self": auroc_hctx,
        "AUROC_H_seed_baseline": auroc_hseed,
        "flag_confusion": {"TP": tp, "FP": fp, "FN": fn, "TN": tn},
        "flag_precision": (tp / (tp + fp)) if (tp + fp) else None,
        "flag_recall": (tp / (tp + fn)) if (tp + fn) else None,
        "danger_quadrant": {
            "n_AMB_pos": len(amb_pos),
            "n_low_Hseed_AMB_pos": len(low_hseed_pos),
            "n_danger": len(danger),
            "mass_over_AMB_pos": (len(danger) / len(amb_pos)) if amb_pos else None,
            "mass_over_low_Hseed": (len(danger) / len(low_hseed_pos))
                                   if low_hseed_pos else None,
        },
        "localization_AMB_pos": {
            "hit_rate_all": (loc_hits_all / len(amb_pos)) if amb_pos else None,
            "precision_among_flagged": (loc_hits_flagged / len(flagged_pos))
                                       if flagged_pos else None,
            "recall_over_AMB_pos": (loc_hits_all / len(amb_pos)) if amb_pos else None,
        },
        "k0_false_positive_rate": k0_fp_rate,
        "H_ctx_self_vs_gold_pearson_AMB_pos": corr,
        "non_disc_count": len(non_disc),
        "non_disc_ids": [r["task_id"] for r in non_disc],
    }


# ── Reporting ────────────────────────────────────────────────────────────────

def _print_item_table(rows: List[Dict[str, Any]], gold_by_id: Dict[str, Dict[str, Any]],
                      *, title: str, only_ids: Optional[List[str]] = None) -> None:
    joined = _join_gold(rows, gold_by_id)
    if only_ids is not None:
        keep = set(only_ids)
        joined = [r for r in joined if r["task_id"] in keep]
    print(f"\n{title}")
    print("=" * 118)
    print(f"{'item':<44}{'stratum':<9}{'H_seed':>8}{'Hctx-self':>10}"
          f"{'Hctx-gold':>10}{'flag':>6}{'match':>7}{'cover':>8}")
    print("-" * 118)
    order = {AMB_POS: 0, NON_DISC: 1, AMB_NEG: 2}
    for r in sorted(joined, key=lambda x: (order.get(x["stratum"], 9), x["task_id"])):
        hg = r["H_ctx_gold"]
        cov = f"{r.get('n_parseable_total', 0)}/{r.get('n_pins_total', 0)}"
        print(
            f"{r['task_id'][:43]:<44}{str(r['stratum']):<9}{r['H_seed']:>8.3f}"
            f"{r['H_ctx_max']:>10.3f}{(hg if hg is not None else float('nan')):>10.3f}"
            f"{('Y' if r['is_flagged'] else '.'): >6}"
            f"{('Y' if r.get('axis_match') else '.'): >7}{cov:>8}"
        )
    print("=" * 118)


def _load_checkpoint(path: str) -> List[Dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def _print_analysis(a: Dict[str, Any]) -> None:
    print("\n[Pilot2] DECISIVE ANALYSIS (executable gold-ambiguity):")
    print(json.dumps(a, indent=2))
    ah, as_ = a["AUROC_H_ctx_self"], a["AUROC_H_seed_baseline"]
    print(f"\n[Pilot2] AUROC  H_ctx-self = {ah}   vs   H_seed baseline = {as_}")
    dq = a["danger_quadrant"]
    print(f"[Pilot2] Danger-quadrant mass (AMB+ in low-H_seed & high-H_ctx-self): "
          f"{dq['n_danger']}/{dq['n_AMB_pos']} "
          f"(= {dq['mass_over_AMB_pos']})")
    print(f"[Pilot2] k0 (AMB-) false-positive rate: {a['k0_false_positive_rate']}")
    print(f"[Pilot2] Localization hit-rate on AMB+: "
          f"{a['localization_AMB_pos']['hit_rate_all']}")
    print(f"[Pilot2] H_ctx-self ~ H_ctx-gold (Pearson, AMB+): "
          f"{a['H_ctx_self_vs_gold_pearson_AMB_pos']}")
    sep = (ah is not None and as_ is not None and ah > as_ and ah >= 0.7)
    print(f"[Pilot2] KEY CHECK — does H_ctx-self SEPARATE AMB+ from AMB- and BEAT "
          f"the H_seed baseline? {'YES' if sep else 'NO / WEAK'}")


# ── CLI ──────────────────────────────────────────────────────────────────────

def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description="Study 2 LPS VALIDATION pilot (v2) — full set, executable gold."
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--rescore-existing", action="store_true",
                        help="STEP 2: re-stratify the existing 9-item pilot (offline).")
    parser.add_argument("--checkpoint", default=CHECKPOINT)
    parser.add_argument("--cache-dir", default=CACHE_DIR)
    parser.add_argument("--model", default=MODEL)
    parser.add_argument("--k", type=int, default=lps.DEFAULT_K)
    parser.add_argument("--budget-usd", type=float, default=None)
    args = parser.parse_args(argv)

    import registered_run as _rr
    tasks = _rr.load_tasks()
    gold_by_id = gold.stratify(tasks)

    # ── STEP 2: re-score the EXISTING 9-item pilot offline (instant) ─────────
    if args.rescore_existing:
        old = _load_checkpoint(pilot1.CHECKPOINT)
        if not old:
            print(f"[Pilot2] No existing pilot checkpoint at {pilot1.CHECKPOINT}.")
            return
        from collections import Counter
        strata = Counter(gold_by_id[r["task_id"]]["stratum"] for r in old
                         if r["task_id"] in gold_by_id)
        print(f"[Pilot2] Re-scored existing pilot ({len(old)} records) strata: "
              f"{dict(strata)}")
        _print_item_table(old, gold_by_id,
                          title="[Pilot2] STEP 2 — existing 9-item pilot under NEW strata")
        return

    # ── Strata overview (offline, always) ────────────────────────────────────
    from collections import Counter
    strata_all = Counter(v["stratum"] for v in gold_by_id.values())
    print("=" * 72)
    print("STUDY 2 — LPS VALIDATION PILOT v2 (executable gold-ambiguity)")
    print(f"  items={len(tasks)}  model={args.model}  k={args.k}")
    print(f"  gold strata (of {len(tasks)}): {dict(strata_all)}")
    print(f"  checkpoint={args.checkpoint}  cache={args.cache_dir}")
    print("=" * 72)

    from common.config import load_config
    cfg = load_config()

    if not args.dry_run:
        if not pilot1._live_ok():
            print("lps_pilot2: skipped (RUNNER_LIVE != 1).")
            sys.exit(0)
        if not pilot1._proxy_reachable():
            print("lps_pilot2: skipped (copilot_proxy not reachable).")
            sys.exit(0)

    result = pilot1.run(
        tasks, cfg,
        models=[args.model],
        checkpoint_path=args.checkpoint,
        cache_dir=args.cache_dir,
        base_seed=BASE_SEED,
        k=args.k,
        dry_run=args.dry_run,
        budget_usd=args.budget_usd,
        select_pilot=False,
    )

    if args.dry_run:
        print(f"\n[Pilot2] Dry-run: {result['total']} jobs "
              f"({len(tasks)} items x 1 model).")
        return

    results = result["results"]
    _print_item_table(results, gold_by_id,
                      title="[Pilot2] Full-set per-item (all 54)")
    a = analyze(results, gold_by_id)
    _print_analysis(a)
    print(f"\n[Pilot2] Result: completed={result['completed']} "
          f"skipped={result['skipped']} checkpoint={result['checkpoint']}")


if __name__ == "__main__":
    main()
