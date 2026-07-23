# constructed by: Claude (Anthropic) family
"""Export the per-item danger-quadrant scatter data for figure F-DQ.

Impl family: Claude (Anthropic). Cross-family audit REQUIRED before merge (Law 6).

This is a *read-only* data export: it reuses the FROZEN per-item aggregation of
``scripts/lps_confirm_report.py`` (``aggregate_by_item`` on the POOLED confirm
records, joined with the executable gold stratum from ``lps_gold``) and writes one
JSON record per PRE-REGISTERED item with its pooled ``(mean_H_seed, mean_H_ctx)``
means, gold stratum (AMB+/AMB−), and frozen danger-quadrant decision. NO number is
recomputed with a different rule; NO point position is invented.

The emitted JSON is the authoritative data asset behind ``fig_danger_quadrant.pdf``
so the figure renders reproducibly without the live checkpoints, and an auditor can
diff every plotted point against the confirmatory checkpoint.

Usage:
  python scripts/lps_danger_quadrant_export.py \
      --shards ".run_partitions/cp_lps_confirm__*.jsonl" \
      --out paper/tex/figures/fig_danger_quadrant_data.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_SCRIPTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPTS_DIR.parent
for _p in (str(_REPO_ROOT), str(_SCRIPTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import lps_gold as gold  # noqa: E402
import lps_confirm_merge as merge  # noqa: E402
import lps_confirm_report as rep  # noqa: E402
import registered_run as rr  # noqa: E402


def extract_items(shards_glob: str) -> Dict[str, Any]:
    """Reuse the frozen aggregation to produce the pooled per-item scatter data."""
    shard_paths = merge.iter_shard_paths(shards_glob)
    if not shard_paths:
        raise FileNotFoundError(f"No confirm shards match {shards_glob!r}.")
    merged = merge.merge_records(shard_paths)
    if merged["n_conflict"] > 0:
        raise RuntimeError(f"{merged['n_conflict']} shard conflict(s); refusing.")
    records = merged["records"]

    gold_by_id = gold.stratify(rr.load_tasks())
    joined: List[Dict[str, Any]] = []
    for r in records:
        g = gold_by_id.get(r.get("task_id"), {})
        rr2 = dict(r)
        rr2["stratum"] = g.get("stratum")
        joined.append(rr2)

    # POOLED per-item aggregation — identical rule to lps_confirm_report.
    items = rep.aggregate_by_item(joined)

    points: List[Dict[str, Any]] = []
    for it in items:
        points.append({
            "task_id": it["task_id"],
            "stratum": it["stratum"],
            "H_seed": it["mean_H_seed"],
            "H_ctx_self": it["mean_H_ctx"],
            "is_danger": bool(it["is_danger"]),
            "n_rows": it["n_rows"],
        })
    points.sort(key=lambda p: (p["stratum"], p["task_id"]))

    amb_pos = [p for p in points if p["stratum"] == gold.STRATUM_AMB_POS]
    amb_neg = [p for p in points if p["stratum"] == gold.STRATUM_AMB_NEG]
    n_danger = sum(1 for p in amb_pos if p["is_danger"])
    return {
        "provenance": {
            "source": "confirmatory checkpoint cp_lps_confirm__*.jsonl (6 shards)",
            "aggregation": "pooled per-item mean across model x seed cells "
                           "(scripts/lps_confirm_report.aggregate_by_item)",
            "frozen_operating_point": {"tau": rep.TAU, "tau_s": rep.TAU_S},
            "n_records": merged and len(records),
        },
        "counts": {
            "n_items": len(points),
            "n_AMB_pos": len(amb_pos),
            "n_AMB_neg": len(amb_neg),
            "n_danger_AMB_pos": n_danger,
            "danger_mass": (n_danger / len(amb_pos)) if amb_pos else None,
        },
        "points": points,
    }


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shards",
                        default=".run_partitions/cp_lps_confirm__*.jsonl")
    parser.add_argument("--out",
                        default="paper/tex/figures/fig_danger_quadrant_data.json")
    args = parser.parse_args(argv)

    data = extract_items(args.shards)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    c = data["counts"]
    print(f"[F-DQ export] items={c['n_items']} AMB+={c['n_AMB_pos']} "
          f"AMB-={c['n_AMB_neg']} danger={c['n_danger_AMB_pos']}/{c['n_AMB_pos']} "
          f"(mass={c['danger_mass']:.3f})")
    print(f"[F-DQ export] Wrote {out_path}")


if __name__ == "__main__":
    main()
