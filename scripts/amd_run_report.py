# constructed by: Claude (Anthropic) family
"""Amendment 13 / 14 sidecar analysis + report.

# Implementer model family: Claude/Anthropic

Reads an ``amd_run`` sidecar checkpoint (written by ``scripts/amd_run.py``) and
produces the pre-registered SECONDARY-robustness analysis:

  * **Amendment 13 (regime×domain crossing, H-A13):** per-domain
    ``cd_primary(H1) − cd_primary(H2)`` on the k1 (underspecified) items, with an
    item-level bootstrap CI, plus a ``regime × domain`` read — the regime effect
    (H1→high / H2→low convergent delusion) must hold WITHIN code_spec AND
    policy_qa, i.e. it is not a domain artifact. Provenance: the contrast is
    computed on tested-family ≠ constructor-family cells (mai-code is out-of-pool,
    so all tested cells qualify — documented).

  * **Amendment 14 (unfiltered replication, H-A14):** the UNCONDITIONED pooled
    ``cd_primary`` on the unfiltered k1 items + the DELTA vs the screened
    confirmatory rate (≈0.53), item-level bootstrap CI, reported HONESTLY
    regardless of outcome (integrity clause §0).

Executable gold ONLY — the frozen ``cd_primary`` (target I0) via the frozen
labeler; NO LLM judge. Writes ``files/amd13_results.md`` / ``files/amd14_results.md``.

Usage::

    python scripts/amd_run_report.py --which amd13
    python scripts/amd_run_report.py --which amd14 --checkpoint .run_partitions/cp_amd_run__amd14.jsonl
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_SCRIPTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPTS_DIR.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# The screened confirmatory pooled cd_primary rate (Amendment 14 §2 / §3 baseline).
SCREENED_CONFIRMATORY_RATE = 0.53
# Constructor family (out-of-pool). Provenance holdout drops any tested cell whose
# model family equals this (none exist, since mai-code is not in the tested roster).
CONSTRUCTOR_FAMILY = "mai-code"


def _load(mod_name: str, filename: str):
    if mod_name in sys.modules:
        return sys.modules[mod_name]
    spec = importlib.util.spec_from_file_location(mod_name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    sys.modules[mod_name] = mod
    return mod


# ── Provenance holdout (tested-family ≠ constructor-family) ──────────────────

def _model_family(model_id: str) -> str:
    """Extract a coarse model family from a slug / pool identity."""
    if not isinstance(model_id, str):
        return ""
    low = model_id.lower()
    if "mai-code" in low or "mai_code" in low:
        return "mai-code"
    if "/" in model_id:
        return model_id.split("/", 1)[0]
    return model_id.split("-", 1)[0]


def apply_provenance_holdout(tidy):
    """Drop tested cells whose model family == the constructor family (mai-code).

    Returns (filtered_df, n_dropped). With mai-code out-of-pool this drops 0 rows
    — the holdout is documented and enforced defensively.
    """
    if len(tidy) == 0 or "model" not in tidy.columns:
        return tidy, 0
    fam = tidy["model"].map(_model_family)
    mask = fam != CONSTRUCTOR_FAMILY
    n_dropped = int((~mask).sum())
    return tidy[mask], n_dropped


# ── Per-item cd_primary means (restricted to k1 items of a regime/domain) ────

def _per_item_cd(tidy, *, regime: Optional[str] = None, domain: Optional[str] = None,
                 k_min: int = 1):
    """Return {item_id: mean cd_primary over its cells} for the filtered subset.

    Filters to ambiguity_k >= ``k_min`` (default 1 = underspecified) and, when
    given, the requested ``regime`` and ``domain``. cd_primary is computed per
    (item, method, model_class, seed) cell via the frozen ``compute_cell_cd`` then
    averaged per item.
    """
    from analysis.contrasts import compute_cell_cd, COLS

    if len(tidy) == 0:
        return {}
    df = tidy
    df = df[df[COLS["ambiguity_k"]] >= k_min]
    if regime is not None:
        df = df[df[COLS["regime"]] == regime]
    if domain is not None and "domain" in df.columns:
        df = df[df["domain"] == domain]
    elif domain is not None:
        # tidy has no explicit domain column → derive from task id prefix mapping
        df = df[df[COLS["item"]].map(_domain_of_item) == domain]
    if len(df) == 0:
        return {}
    cells = compute_cell_cd(df)
    if len(cells) == 0:
        return {}
    item_col = COLS["item"]
    return cells.groupby(item_col)["cd_primary"].mean().to_dict()


def _domain_of_item(item_id: str) -> str:
    """Best-effort domain from a task-id prefix (code_*, policy_*, data_*)."""
    if not isinstance(item_id, str):
        return ""
    if item_id.startswith("code_"):
        return "code_spec"
    if item_id.startswith("policy_"):
        return "policy_qa"
    if item_id.startswith("data_"):
        return "data_analysis"
    return ""


# ── Amendment 13: per-domain contrast + regime×domain read ───────────────────

def a13_analysis(tidy, *, domains: List[str] = None) -> Dict[str, Any]:
    """Per-domain cd_primary(H1) − cd_primary(H2) with item-level bootstrap CI.

    Returns a dict with per-domain contrasts + a regime×domain read (whether the
    H1>H2 direction holds within EACH domain with the CI excluding 0).
    """
    rr = _load("registered_run", "registered_run.py")
    if domains is None:
        domains = ["code_spec", "policy_qa"]

    held, n_dropped = apply_provenance_holdout(tidy)

    per_domain: Dict[str, Any] = {}
    for dom in domains:
        h1 = _per_item_cd(held, regime="H1_external", domain=dom, k_min=1)
        h2 = _per_item_cd(held, regime="H2_derivable", domain=dom, k_min=1)
        h1_vals = list(h1.values())
        h2_vals = list(h2.values())
        mean_h1 = sum(h1_vals) / len(h1_vals) if h1_vals else float("nan")
        mean_h2 = sum(h2_vals) / len(h2_vals) if h2_vals else float("nan")
        contrast = (mean_h1 - mean_h2) if (h1_vals and h2_vals) else float("nan")
        ci_lo, ci_hi = rr._bootstrap_ci_diff(h1_vals, h2_vals) if (
            len(h1_vals) >= 2 and len(h2_vals) >= 2
        ) else (float("-inf"), float("inf"))
        holds = (
            len(h1_vals) >= 2 and len(h2_vals) >= 2 and contrast > 0 and ci_lo > 0
        )
        per_domain[dom] = {
            "n_h1_items": len(h1_vals),
            "n_h2_items": len(h2_vals),
            "cd_h1": mean_h1,
            "cd_h2": mean_h2,
            "contrast": contrast,
            "ci_lo": ci_lo,
            "ci_hi": ci_hi,
            "direction_holds": holds,
            "h1_items": h1,
            "h2_items": h2,
        }

    # regime×domain read: the regime effect is NOT domain-confounded iff the
    # contrast is positive (CI>0) within EACH domain that has both regimes.
    testable = [d for d, r in per_domain.items() if r["n_h1_items"] >= 2 and r["n_h2_items"] >= 2]
    all_hold = bool(testable) and all(per_domain[d]["direction_holds"] for d in testable)
    return {
        "per_domain": per_domain,
        "testable_domains": testable,
        "regime_effect_holds_within_domain": all_hold,
        "provenance_dropped_cells": n_dropped,
        "constructor_family": CONSTRUCTOR_FAMILY,
    }


# ── Amendment 14: unconditioned pooled rate + delta vs screened ──────────────

def a14_analysis(tidy) -> Dict[str, Any]:
    """Pooled UNCONDITIONED cd_primary on the unfiltered k1 items + delta vs 0.53."""
    rr = _load("registered_run", "registered_run.py")
    held, n_dropped = apply_provenance_holdout(tidy)

    per_item = _per_item_cd(held, regime="H1_external", k_min=1)
    vals = list(per_item.values())
    pooled = sum(vals) / len(vals) if vals else float("nan")
    ci_lo, ci_hi = rr._bootstrap_ci(vals) if len(vals) >= 2 else (float("-inf"), float("inf"))
    delta = pooled - SCREENED_CONFIRMATORY_RATE if vals else float("nan")
    frac_convergent = (sum(1 for v in vals if v > 0) / len(vals)) if vals else float("nan")
    return {
        "n_items": len(vals),
        "pooled_cd_primary": pooled,
        "ci_lo": ci_lo,
        "ci_hi": ci_hi,
        "screened_rate": SCREENED_CONFIRMATORY_RATE,
        "delta_vs_screened": delta,
        "fraction_convergent": frac_convergent,
        "per_item": per_item,
        "provenance_dropped_cells": n_dropped,
    }


# ── Markdown rendering ────────────────────────────────────────────────────────

def render_amd13(result: Dict[str, Any]) -> str:
    L: List[str] = []
    L.append("# Amendment 13 — regime × domain crossing (pre-registered SECONDARY robustness)")
    L.append("")
    L.append("Metric: FROZEN `cd_primary` (target I0), executable gold only (Law 7). "
             "Reported as pre-registered secondary robustness — the frozen confirmatory "
             "finding is NOT changed.")
    L.append("")
    L.append("Hypothesis **H-A13**: within EACH of code_spec and policy_qa, matched "
             "`H1_external` items show HIGH convergent delusion while `H2_derivable` "
             "items show LOW (attenuated) — i.e. the regime effect is NOT domain-confounded. "
             "Pre-committed direction: per-domain `cd_primary(H1) − cd_primary(H2) > 0` with "
             "item-level bootstrap CI excluding 0.")
    L.append("")
    L.append(f"Provenance holdout: contrast computed on tested-family ≠ constructor-family "
             f"(`{result['constructor_family']}`, out-of-pool) cells — "
             f"{result['provenance_dropped_cells']} cell(s) dropped (0 expected, mai-code not in the tested roster).")
    L.append("")
    L.append("| domain | n(H1) | n(H2) | cd_primary(H1) | cd_primary(H2) | contrast (H1−H2) | 95% CI | direction holds |")
    L.append("|---|---|---|---|---|---|---|---|")
    for dom, r in result["per_domain"].items():
        L.append(
            f"| {dom} | {r['n_h1_items']} | {r['n_h2_items']} | "
            f"{_f(r['cd_h1'])} | {_f(r['cd_h2'])} | {_f(r['contrast'])} | "
            f"[{_f(r['ci_lo'])}, {_f(r['ci_hi'])}] | {r['direction_holds']} |"
        )
    L.append("")
    L.append("### regime × domain read")
    L.append(f"- Testable domains (both regimes ≥2 items): {result['testable_domains']}")
    L.append(f"- **Regime effect holds WITHIN each testable domain (not domain-confounded): "
             f"{result['regime_effect_holds_within_domain']}**")
    L.append("")
    L.append("Honesty: any null / manipulation-check failure is reported as-is; items are "
             "never tuned. This crossing is only claimed if (a) the manipulation check "
             "(`scripts/amd13_manipulation_check.py`) PASSED and (b) the within-domain "
             "contrast direction holds above.")
    L.append("")
    return "\n".join(L)


def render_amd14(result: Dict[str, Any]) -> str:
    L: List[str] = []
    L.append("# Amendment 14 — unfiltered-sample replication (pre-registered SECONDARY robustness)")
    L.append("")
    L.append("Metric: FROZEN `cd_primary` (target I0), executable gold only (Law 7).")
    L.append("")
    L.append("Hypothesis **H-A14**: on the UNFILTERED sample (NO default-screen inclusion "
             "filter), report the cross-family convergent-delusion rate UNCONDITIONALLY. "
             "Integrity clause (§0): reported HONESTLY regardless of outcome (high, "
             "attenuated, or null) — prominence, not suppression.")
    L.append("")
    L.append(f"- Unfiltered items (k1): **{result['n_items']}**")
    L.append(f"- **Pooled UNCONDITIONED cd_primary = {_f(result['pooled_cd_primary'])}** "
             f"(95% CI [{_f(result['ci_lo'])}, {_f(result['ci_hi'])}])")
    L.append(f"- Screened confirmatory rate (baseline) = {result['screened_rate']:.2f}")
    L.append(f"- **Delta vs screened = {_f(result['delta_vs_screened'])}**")
    L.append(f"- Fraction of unfiltered items still exhibiting convergent delusion "
             f"(cd_primary > 0) = {_f(result['fraction_convergent'])}")
    L.append("")
    L.append("Reading (pre-committed, NOT a pass/fail gate): if the unfiltered rate stays "
             "HIGH → prominent rebuttal to the selection-bias attack; if it ATTENUATES → an "
             "honest bound (effect partly enrichment-driven) and the claim is sharpened to "
             "its conditional form. NO tuning; the result stands as-is.")
    L.append("")
    return "\n".join(L)


def _f(x: Any) -> str:
    try:
        xf = float(x)
    except (TypeError, ValueError):
        return str(x)
    if xf != xf:  # NaN
        return "n/a"
    if xf in (float("inf"), float("-inf")):
        return "±inf" if xf > 0 else "-inf"
    return f"{xf:.4f}"


# ── Checkpoint → tidy → report ───────────────────────────────────────────────

def load_tidy_for(which: str, checkpoint_path: str):
    """Load the amd_run checkpoint into a tidy table (with a domain column)."""
    amd_run = _load("amd_run", "amd_run.py")
    from analysis.io import load_runs_tidy, FRONTIER_MODEL_CLASS_MAP

    include_anchors = which == "amd13"
    tasks = amd_run.load_amd_tasks(which, include_h1_anchors=include_anchors)
    # endpoint None is fine when the checkpoint has a single namespace; if it has
    # several, load_runs_tidy raises and the caller must pass expected_endpoint.
    tidy = load_runs_tidy(
        checkpoint_path, tasks, model_class_map=FRONTIER_MODEL_CLASS_MAP,
    )
    tidy = attach_domain_column(tidy, tasks)
    return tidy


def attach_domain_column(tidy, tasks: List[Any]):
    """Add a ``domain`` column derived from each task's domain (fallback: id prefix)."""
    if len(tidy) == 0:
        return tidy
    from analysis.contrasts import COLS
    dom_by_id = {t.id: t.domain for t in tasks}
    tidy = tidy.copy()
    tidy["domain"] = tidy[COLS["item"]].map(
        lambda i: dom_by_id.get(i) or _domain_of_item(i)
    )
    return tidy


def write_report(which: str, markdown: str, out_dir: str = None) -> str:
    out = Path(out_dir) if out_dir else (_REPO_ROOT / "files")
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{which}_results.md"
    path.write_text(markdown, encoding="utf-8")
    return str(path)


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Amendment 13/14 sidecar analysis + report")
    parser.add_argument("--which", choices=("amd13", "amd14"), required=True)
    parser.add_argument("--checkpoint", default=None)
    parser.add_argument("--out-dir", default=None)
    args = parser.parse_args(argv)

    amd_run = _load("amd_run", "amd_run.py")
    def_cp, _, _ = amd_run._which_defaults(args.which)
    checkpoint = args.checkpoint or def_cp

    tidy = load_tidy_for(args.which, checkpoint)
    if len(tidy) == 0:
        print(f"amd_run_report: checkpoint {checkpoint} has no labeled runs yet — "
              "writing a placeholder report (run the driver live first).", file=sys.stderr)

    if args.which == "amd13":
        result = a13_analysis(tidy)
        md = render_amd13(result)
    else:
        result = a14_analysis(tidy)
        md = render_amd14(result)

    path = write_report(args.which, md, out_dir=args.out_dir)
    print(md)
    print(f"\n[amd_run_report] wrote {path}")


if __name__ == "__main__":
    main()
