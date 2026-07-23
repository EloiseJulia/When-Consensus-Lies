# constructed by: Claude (Anthropic) family
"""Study 2 LPS INTERVENTION analysis + report (Phase 2b) — H-B1' + H-B2'.

# Implementer model family: Claude / Anthropic
# Auditor model family: MUST be non-Anthropic (Law 6 — cross-family requirement)

Reads the intervention checkpoint (``.run_partitions/cp_lps_intervention.jsonl``,
produced by ``lps_intervention.py``), joins the executable, detector-independent
gold-ambiguity stratum (``lps_gold``), and renders the two pre-registered
intervention reads (``paper/preregistration/2026-07-23-study2-prereg-FROZEN.md``):

  * **H-B1' (selective clarification):** per policy —
    ``appropriate_clarification`` = clarify-rate on AMB+ (want HIGH),
    ``over_clarification`` = clarify-rate on AMB− (want LOW), and the headline
    net = appropriate − over. The LPP gate should win the net score and, in the
    low-``H_seed`` danger subset, have HIGHER AMB+ coverage than the
    semantic-entropy gate.
  * **H-B2' (oracle resolution):** per AMB+ item, the never-clarify baseline
    ``cd_primary`` vs the gold-convention-oracle ``cd_primary`` (executable gold,
    target ``I0``), the paired drop, and the oracle I0-hit rate.

AGGREGATION (mirrors ``lps_confirm_report``): the unit of analysis is the ITEM.
Each item's per-policy clarify-rate = MEAN of its (seed) rows' decisions; each
item's baseline/oracle ``cd_primary`` is computed over that item's seed labels.
All CIs cluster-bootstrap by ``task_id`` (resample items with replacement) via
``registered_run._bootstrap_ci`` / ``_bootstrap_ci_diff``.

Gold is used for EVALUATION ONLY (never in a prompt); the H-B2' oracle convention
is an evaluation-time controlled injection carried ONLY by the oracle re-ask.

Usage:
    python scripts/lps_intervention_report.py \\
        --checkpoint .run_partitions/cp_lps_intervention.jsonl \\
        --out files/study2_intervention_results.md
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_SCRIPTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPTS_DIR.parent
for _p in (str(_REPO_ROOT), str(_SCRIPTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import lps_gold as gold  # noqa: E402
import lps_intervention as intv  # noqa: E402
from analysis.cd import cd_primary  # noqa: E402  (executable resolution metric)

AMB_POS = gold.STRATUM_AMB_POS
NON_DISC = gold.STRATUM_NON_DISC
AMB_NEG = gold.STRATUM_AMB_NEG

TAU_S = intv.TAU_S
CD_TARGET = "I0"

#: Human labels for the H-B1' policies (order = intv.CLARIFY_POLICIES).
POLICY_LABELS = {
    "lpp_gated": "LPP-gated (ours)",
    "always": "always-clarify",
    "semantic_entropy_gated": "semantic-entropy-gated",
    "self_consistency_gated": "self-consistency-gated",
    "requirements_probing_gated": "requirements-probing-gated",
}


# ── Loading ──────────────────────────────────────────────────────────────────

def load_records(checkpoint_path: str) -> List[Dict[str, Any]]:
    """Load intervention records (skipping the header line)."""
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


def _mean(xs: List[float]) -> Optional[float]:
    return (sum(xs) / len(xs)) if xs else None


# ── Per-item aggregation ─────────────────────────────────────────────────────

def aggregate_by_item(rows: List[Dict[str, Any]],
                      gold_by_id: Dict[str, Dict[str, Any]]
                      ) -> List[Dict[str, Any]]:
    """Collapse (item × seed) rows to ONE aggregate per task_id.

    Per item:
      * ``clarify_rate[policy]`` = MEAN of the policy's boolean decision across
        the item's rows.
      * ``mean_H_seed`` = mean H_seed across rows (for the danger subset).
      * ``cd_baseline`` / ``cd_oracle`` = ``cd_primary`` over the item's per-seed
        baseline / oracle labels (AMB+ only; None otherwise).
      * ``i0_hit`` = fraction of the item's oracle labels equal to ``I0``.
    """
    by_task: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by_task[r.get("task_id")].append(r)

    items: List[Dict[str, Any]] = []
    for tid, rs in by_task.items():
        stratum = (gold_by_id.get(tid) or {}).get("stratum") or rs[0].get("stratum")
        clarify_rate: Dict[str, Optional[float]] = {}
        for pol in intv.CLARIFY_POLICIES:
            vals = [1.0 if (r.get("clarify") or {}).get(pol) else 0.0 for r in rs]
            clarify_rate[pol] = _mean(vals)
        mean_hseed = _mean([r["H_seed"] for r in rs
                            if isinstance(r.get("H_seed"), (int, float))])

        baseline_labels = [r["b2"]["baseline_label"] for r in rs
                           if r.get("b2") and r["b2"].get("baseline_label")
                           is not None]
        oracle_labels = [r["b2"]["oracle_label"] for r in rs
                         if r.get("b2") and r["b2"].get("oracle_label") is not None]
        cd_baseline = (cd_primary(baseline_labels, CD_TARGET)
                       if baseline_labels else None)
        cd_oracle = (cd_primary(oracle_labels, CD_TARGET)
                     if oracle_labels else None)
        i0_hit = (_mean([1.0 if lab == CD_TARGET else 0.0 for lab in oracle_labels])
                  if oracle_labels else None)

        items.append({
            "task_id": tid,
            "stratum": stratum,
            "clarify_rate": clarify_rate,
            "mean_H_seed": mean_hseed,
            "cd_baseline": cd_baseline,
            "cd_oracle": cd_oracle,
            "i0_hit": i0_hit,
            "n_rows": len(rs),
        })
    return items


# ── H-B1' analysis ───────────────────────────────────────────────────────────

def _ci(samples: List[float]) -> Tuple[Optional[float], Optional[float]]:
    if not samples:
        return (None, None)
    from registered_run import _bootstrap_ci
    lo, hi = _bootstrap_ci([float(x) for x in samples])
    return lo, hi


def _ci_diff(a: List[float], b: List[float]
             ) -> Tuple[Optional[float], Optional[float]]:
    if not a or not b:
        return (None, None)
    from registered_run import _bootstrap_ci_diff
    lo, hi = _bootstrap_ci_diff([float(x) for x in a], [float(x) for x in b])
    return lo, hi


def analyze_hb1(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Per-policy appropriate/over clarification + net + danger-subset coverage."""
    amb_pos = [it for it in items if it["stratum"] == AMB_POS]
    amb_neg = [it for it in items if it["stratum"] == AMB_NEG]
    # Danger subset: AMB+ items whose mean H_seed is in the low-confidence zone —
    # exactly where the semantic-entropy gate is blind.
    danger_pos = [it for it in amb_pos
                  if it["mean_H_seed"] is not None and it["mean_H_seed"] <= TAU_S]

    per_policy: Dict[str, Any] = {}
    for pol in intv.CLARIFY_POLICIES:
        pos_rates = [it["clarify_rate"][pol] for it in amb_pos
                     if it["clarify_rate"][pol] is not None]
        neg_rates = [it["clarify_rate"][pol] for it in amb_neg
                     if it["clarify_rate"][pol] is not None]
        danger_rates = [it["clarify_rate"][pol] for it in danger_pos
                        if it["clarify_rate"][pol] is not None]
        appropriate = _mean(pos_rates)
        over = _mean(neg_rates)
        net = (appropriate - over) if (appropriate is not None
                                       and over is not None) else None
        app_lo, app_hi = _ci(pos_rates)
        over_lo, over_hi = _ci(neg_rates)
        net_lo, net_hi = _ci_diff(pos_rates, neg_rates)
        per_policy[pol] = {
            "appropriate": appropriate,
            "appropriate_ci": (app_lo, app_hi),
            "over": over,
            "over_ci": (over_lo, over_hi),
            "net": net,
            "net_ci": (net_lo, net_hi),
            "danger_coverage": _mean(danger_rates),
            "n_pos": len(pos_rates),
            "n_neg": len(neg_rates),
            "n_danger": len(danger_rates),
        }
    return {
        "per_policy": per_policy,
        "n_AMB_pos": len(amb_pos),
        "n_AMB_neg": len(amb_neg),
        "n_danger_pos": len(danger_pos),
    }


# ── H-B2' analysis ───────────────────────────────────────────────────────────

def analyze_hb2(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Baseline vs oracle cd_primary over AMB+ items + paired drop + I0-hit."""
    amb_pos = [it for it in items if it["stratum"] == AMB_POS
               and it["cd_baseline"] is not None and it["cd_oracle"] is not None]
    baseline = [it["cd_baseline"] for it in amb_pos]
    oracle = [it["cd_oracle"] for it in amb_pos]
    deltas = [b - o for b, o in zip(baseline, oracle)]  # paired drop (baseline−oracle)
    i0_hits = [it["i0_hit"] for it in amb_pos if it["i0_hit"] is not None]

    base_lo, base_hi = _ci(baseline)
    orc_lo, orc_hi = _ci(oracle)
    d_lo, d_hi = _ci(deltas)
    hit_lo, hit_hi = _ci(i0_hits)

    # Honesty: AMB+ items the oracle does NOT resolve to I0 (cd_oracle > 0 OR
    # i0_hit < 1) — bounds how much of the failure is surfacable + resolvable.
    unresolved = [it["task_id"] for it in amb_pos if it["cd_oracle"] > 0.0]
    partial_hit = [it["task_id"] for it in amb_pos
                   if it["i0_hit"] is not None and it["i0_hit"] < 1.0]

    return {
        "n_AMB_pos": len(amb_pos),
        "baseline_cd": _mean(baseline),
        "baseline_cd_ci": (base_lo, base_hi),
        "oracle_cd": _mean(oracle),
        "oracle_cd_ci": (orc_lo, orc_hi),
        "delta_cd": _mean(deltas),
        "delta_cd_ci": (d_lo, d_hi),
        "i0_hit_rate": _mean(i0_hits),
        "i0_hit_rate_ci": (hit_lo, hit_hi),
        "n_unresolved": len(unresolved),
        "unresolved_ids": unresolved,
        "n_partial_hit": len(partial_hit),
        "partial_hit_ids": partial_hit,
    }


def analyze(records: List[Dict[str, Any]],
            gold_by_id: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Per-model + pooled H-B1'/H-B2' analysis over per-item aggregates."""
    by_model: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in records:
        by_model[r.get("model", "?")].append(r)

    def _group(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        items = aggregate_by_item(rows, gold_by_id)
        strata = {AMB_POS: 0, NON_DISC: 0, AMB_NEG: 0}
        for it in items:
            if it["stratum"] in strata:
                strata[it["stratum"]] += 1
        return {
            "n_items": len(items),
            "n_records": sum(it["n_rows"] for it in items),
            "strata_counts": strata,
            "hb1": analyze_hb1(items),
            "hb2": analyze_hb2(items),
        }

    per_model = {m: _group(rows) for m, rows in sorted(by_model.items())}
    pooled = _group(records)
    return {"per_model": per_model, "pooled": pooled, "n_records": len(records)}


# ── Markdown rendering ───────────────────────────────────────────────────────

def _fmt(v: Optional[float], nd: int = 3) -> str:
    return "—" if v is None else f"{v:.{nd}f}"


def _fmt_ci(ci: Tuple[Optional[float], Optional[float]]) -> str:
    lo, hi = ci
    if lo is None or hi is None:
        return ""
    return f" [{_fmt(lo)}, {_fmt(hi)}]"


def _hb1_table(hb1: Dict[str, Any]) -> List[str]:
    header = ("| Policy | Appropriate (AMB+↑) | Over-clarification (AMB−↓) | "
              "Net (↑) | Danger-subset AMB+ coverage |")
    sep = "|" + "---|" * 5
    lines = [header, sep]
    for pol in intv.CLARIFY_POLICIES:
        p = hb1["per_policy"][pol]
        app = f"{_fmt(p['appropriate'])}{_fmt_ci(p['appropriate_ci'])}"
        over = f"{_fmt(p['over'])}{_fmt_ci(p['over_ci'])}"
        net = f"{_fmt(p['net'])}{_fmt_ci(p['net_ci'])}"
        dang = (f"{_fmt(p['danger_coverage'])} (n={p['n_danger']})"
                if p['danger_coverage'] is not None else "—")
        lines.append(f"| **{POLICY_LABELS[pol]}** | {app} | {over} | {net} | "
                     f"{dang} |")
    return lines


def _hb2_table(hb2: Dict[str, Any]) -> List[str]:
    header = ("| Baseline cd_primary (never-clarify) | Oracle cd_primary "
              "(gold-convention) | Δ drop (paired) | Oracle I0-hit | n(AMB+) |")
    sep = "|" + "---|" * 5
    base = f"{_fmt(hb2['baseline_cd'])}{_fmt_ci(hb2['baseline_cd_ci'])}"
    orc = f"{_fmt(hb2['oracle_cd'])}{_fmt_ci(hb2['oracle_cd_ci'])}"
    delta = f"{_fmt(hb2['delta_cd'])}{_fmt_ci(hb2['delta_cd_ci'])}"
    hit = f"{_fmt(hb2['i0_hit_rate'])}{_fmt_ci(hb2['i0_hit_rate_ci'])}"
    return [header, sep,
            f"| {base} | {orc} | {delta} | {hit} | {hb2['n_AMB_pos']} |"]


def render_markdown(result: Dict[str, Any], *, checkpoint: str,
                    n_models: int) -> str:
    pooled = result["pooled"]
    hb1 = pooled["hb1"]
    hb2 = pooled["hb2"]

    lpp = hb1["per_policy"]["lpp_gated"]
    always = hb1["per_policy"]["always"]
    se = hb1["per_policy"]["semantic_entropy_gated"]

    lines: List[str] = []
    lines.append("# Study 2 — Intervention closed-loop results (Phase 2b)")
    lines.append("")
    lines.append("> Generated by `scripts/lps_intervention_report.py`. Impl "
                 "family: Claude (Anthropic). Cross-family audit REQUIRED before "
                 "any merge (Law 6). Metric defs FROZEN (prereg; Law 7).")
    lines.append("")
    lines.append(f"- Checkpoint: `{checkpoint}`")
    lines.append(f"- Records analysed: {result['n_records']} run cells "
                 f"aggregated to {pooled['n_items']} pre-registered items "
                 f"across {n_models} model(s)")
    sc = pooled["strata_counts"]
    lines.append(f"- Strata (executable gold-ambiguity): AMB+ {sc[AMB_POS]} / "
                 f"NON-DISC {sc[NON_DISC]} / AMB− {sc[AMB_NEG]}")
    lines.append(f"- FROZEN operating point: τ = {intv.TAU}, τ_s = {TAU_S} bits "
                 "(prereg §2). Resolution scored by EXECUTABLE `cd_primary` "
                 "(target `I0`) — never an LLM judge.")
    lines.append("- **Per-item aggregation:** each item's clarify-rate = mean of "
                 "its seed decisions; its baseline/oracle `cd_primary` is over the "
                 "item's per-seed labels. CIs cluster-bootstrap by `task_id`.")
    lines.append("- **Anti-leakage:** clarify decisions reuse the detector's "
                 "gold-free signals; the ONLY gold-bearing prompt is the H-B2' "
                 "oracle re-ask (a controlled, evaluation-time simulated-user "
                 "clarification — NOT detector leakage).")
    lines.append("")

    # ── H-B1' ────────────────────────────────────────────────────────────────
    lines.append("## 1. H-B1' — selective clarification (detection → action)")
    lines.append("")
    lines.append("`Appropriate` = clarify-rate on AMB+ (want HIGH). "
                 "`Over-clarification` = clarify-rate on AMB− / k0 (want LOW). "
                 "`Net` = appropriate − over (pre-committed > 0, LPP ≥ each "
                 "baseline). `Danger-subset coverage` = AMB+ clarify-rate on the "
                 "low-`H_seed` (≤ τ_s) subset — the zone where semantic entropy "
                 "is blind.")
    lines.append("")
    lines.extend(_hb1_table(hb1))
    lines.append("")
    net_ok = (lpp["net"] is not None and always["net"] is not None
              and se["net"] is not None
              and lpp["net"] >= always["net"] and lpp["net"] >= se["net"]
              and lpp["net"] > 0)
    lines.append(f"- LPP-gated net = {_fmt(lpp['net'])} vs always-clarify "
                 f"{_fmt(always['net'])} vs semantic-entropy {_fmt(se['net'])}.")
    lines.append(f"- Semantic-entropy danger-subset AMB+ coverage = "
                 f"{_fmt(se['danger_coverage'])} vs LPP-gated "
                 f"{_fmt(lpp['danger_coverage'])} "
                 "(pre-committed: LPP higher in the danger zone).")
    lines.append(f"- Pre-committed H-B1' direction met (pooled)? "
                 f"**{'YES' if net_ok else 'NO / WEAK'}** (confirmatory read).")
    lines.append("")

    # ── H-B2' ────────────────────────────────────────────────────────────────
    lines.append("## 2. H-B2' — oracle resolution (does the right axis FIX it?)")
    lines.append("")
    lines.append("Per AMB+ item: never-clarify baseline `cd_primary` vs the "
                 "gold-convention-oracle `cd_primary` (executable gold, target "
                 "`I0`). Pre-committed direction: oracle `cd_primary → 0` (a "
                 "CI-separated drop). The oracle is a CONTROLLED simulated-user "
                 "clarification (real-user study = future work).")
    lines.append("")
    lines.extend(_hb2_table(hb2))
    lines.append("")
    drop_ok = (hb2["delta_cd"] is not None
               and hb2["delta_cd_ci"][0] is not None
               and hb2["delta_cd_ci"][0] > 0.0)
    lines.append(f"- Baseline cd_primary = {_fmt(hb2['baseline_cd'])} → oracle "
                 f"cd_primary = {_fmt(hb2['oracle_cd'])} "
                 f"(paired drop {_fmt(hb2['delta_cd'])}"
                 f"{_fmt_ci(hb2['delta_cd_ci'])}).")
    lines.append(f"- Oracle I0-hit rate = {_fmt(hb2['i0_hit_rate'])}"
                 f"{_fmt_ci(hb2['i0_hit_rate_ci'])}.")
    lines.append(f"- Pre-committed H-B2' direction met (pooled, CI-separated "
                 f"drop)? **{'YES' if drop_ok else 'NO / WEAK'}** (confirmatory "
                 "read).")
    lines.append("")

    # ── Per-model ────────────────────────────────────────────────────────────
    if n_models > 1:
        lines.append("## 3. Per-model breakdown")
        lines.append("")
        for m, g in result["per_model"].items():
            lines.append(f"### {m}")
            lines.append("")
            lines.extend(_hb1_table(g["hb1"]))
            lines.append("")
            lines.extend(_hb2_table(g["hb2"]))
            lines.append("")

    # ── Honesty notes ────────────────────────────────────────────────────────
    lines.append("## Honesty notes")
    lines.append("")
    lines.append(f"- NON-DISC items ({sc[NON_DISC]}) are reported SEPARATELY "
                 "(a deleted axis exists but interpretations coincide on the given "
                 "inputs — informative, not a detector error).")
    lines.append(f"- H-B2' UNRESOLVED AMB+ items (oracle cd_primary > 0): "
                 f"{hb2['n_unresolved']} — {hb2['unresolved_ids'] or 'none'}. "
                 "Reported as-is; NOTHING was tuned to force cd → 0 (the oracle "
                 "supplies the gold convention but the model may still ignore it "
                 "or the convention may be under-determined).")
    lines.append(f"- H-B2' PARTIAL-hit AMB+ items (oracle I0-hit < 1 across "
                 f"seeds): {hb2['n_partial_hit']} — bounds how much of the failure "
                 "is surfacable + resolvable.")
    lines.append("- Reuses the FROZEN apparatus read-only: `cd_primary` "
                 "(resolution metric), the executable labeler (`_label_answer`), "
                 "`lpp_detect` (clarify signals), and `gold_ambiguity` (strata). "
                 "No frozen file / confirmatory checkpoint / metric definition was "
                 "touched.")
    lines.append("")
    return "\n".join(lines)


# ── CLI ──────────────────────────────────────────────────────────────────────

def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description="Study 2 LPS INTERVENTION analysis + markdown report "
                    "(H-B1' + H-B2')."
    )
    parser.add_argument("--checkpoint",
                        default=".run_partitions/cp_lps_intervention.jsonl",
                        help="Single checkpoint to analyse (ignored when --shards "
                             "is given).")
    parser.add_argument("--shards", default=None,
                        help="Glob for per-model shard checkpoints "
                             "(e.g. '.run_partitions/cp_lps_intervention__*.jsonl').")
    parser.add_argument("--out", default="files/study2_intervention_results.md")
    args = parser.parse_args(argv)

    import registered_run as _rr

    if args.shards:
        from glob import glob
        records: List[Dict[str, Any]] = []
        for p in sorted(glob(args.shards)):
            records.extend(load_records(p))
        source = f"{args.shards} ({len(sorted(glob(args.shards)))} shards)"
    else:
        records = load_records(args.checkpoint)
        source = args.checkpoint

    if not records:
        print(f"[Report] No records in {source}.")
        return

    tasks = _rr.load_tasks()
    gold_by_id = gold.stratify(tasks)
    result = analyze(records, gold_by_id)

    n_models = len(result["per_model"])
    md = render_markdown(result, checkpoint=source, n_models=n_models)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")

    pooled = result["pooled"]
    hb1 = pooled["hb1"]["per_policy"]
    hb2 = pooled["hb2"]
    print(f"[Report] Analysed {result['n_records']} records across {n_models} "
          f"model(s).")
    print(f"[Report] H-B1' LPP-gated net = {_fmt(hb1['lpp_gated']['net'])}  |  "
          f"always = {_fmt(hb1['always']['net'])}  |  "
          f"semantic-entropy = {_fmt(hb1['semantic_entropy_gated']['net'])}")
    print(f"[Report] H-B2' baseline cd = {_fmt(hb2['baseline_cd'])} → oracle cd = "
          f"{_fmt(hb2['oracle_cd'])}  (I0-hit {_fmt(hb2['i0_hit_rate'])})")
    print(f"[Report] Wrote {out_path}")


if __name__ == "__main__":
    main()
