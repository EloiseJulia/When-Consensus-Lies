# constructed by: Claude (Anthropic) family
"""Merge per-model CONFIRMATORY shards for Study-2 analysis (Phase 2a).

# Implementer model family: Claude / Anthropic
# Auditor model family: MUST be non-Anthropic (Law 6 — cross-family requirement)

The confirmatory grid is run in parallel — ONE runner per model, each writing an
independent namespaced shard (``lps_confirm.py --shard-by-model``):
``.run_partitions/cp_lps_confirm__<slug>.jsonl``. This tool GATHERS every shard
into a single deduplicated record stream for the report.

DEDUP KEY = ``(task_id, model, seed_base, method_version)`` — the cell identity
plus the method version (from each record's ``_fingerprint``). Duplicate cells
(e.g. a shard replayed, or overlapping globs) collapse to ONE record; header lines
are skipped. Records that disagree on the SAME key keep the FIRST seen and count a
conflict (reported) — they should be identical under a fixed method.

Usage:
    python scripts/lps_confirm_merge.py                       # merge default glob
    python scripts/lps_confirm_merge.py --out .run_partitions/cp_lps_confirm_merged.jsonl
    python scripts/lps_confirm_merge.py --shards '.run_partitions/cp_lps_confirm__*.jsonl'
"""

from __future__ import annotations

import argparse
import glob as _glob
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_SCRIPTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPTS_DIR.parent
for _p in (str(_REPO_ROOT), str(_SCRIPTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import lps_confirm as confirm  # noqa: E402

DEFAULT_SHARDS_GLOB = confirm.SHARD_CHECKPOINT_GLOB
DEFAULT_MERGED_OUT = ".run_partitions/cp_lps_confirm_merged.jsonl"


def _record_method_version(rec: Dict[str, Any]) -> Optional[str]:
    fp = rec.get("_fingerprint") or {}
    return fp.get("method_version")


def _dedup_key(rec: Dict[str, Any]) -> Tuple[Any, Any, Any, Any]:
    """Cell identity for dedup: (task_id, model, seed_base, method_version)."""
    return (rec.get("task_id"), rec.get("model"), rec.get("seed_base"),
            _record_method_version(rec))


def iter_shard_paths(shards_glob: str) -> List[str]:
    """Sorted list of shard checkpoint paths matching the glob."""
    return sorted(_glob.glob(shards_glob))


def merge_records(paths: List[str]) -> Dict[str, Any]:
    """Load + dedup records across shard files.

    Returns ``{records, n_read, n_dup, n_conflict, per_shard, per_model}``:
      * ``records``  — deduped record list (header lines dropped).
      * ``n_read``   — total non-header records read.
      * ``n_dup``    — duplicate cells collapsed (same key, first kept).
      * ``n_conflict`` — duplicates whose payload differed from the kept one.
    """
    seen: Dict[Tuple[Any, Any, Any, Any], Dict[str, Any]] = {}
    n_read = 0
    n_dup = 0
    n_conflict = 0
    per_shard: Dict[str, int] = {}
    for path in paths:
        p = Path(path)
        if not p.exists():
            continue
        count = 0
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
            n_read += 1
            count += 1
            key = _dedup_key(rec)
            if key in seen:
                n_dup += 1
                if seen[key] != rec:
                    n_conflict += 1
                continue
            seen[key] = rec
        per_shard[path] = count

    records = list(seen.values())
    per_model: Dict[str, int] = {}
    for r in records:
        per_model[r.get("model", "?")] = per_model.get(r.get("model", "?"), 0) + 1
    return {
        "records": records,
        "n_read": n_read,
        "n_dup": n_dup,
        "n_conflict": n_conflict,
        "per_shard": per_shard,
        "per_model": per_model,
    }


def merge_shards(shards_glob: str = DEFAULT_SHARDS_GLOB) -> List[Dict[str, Any]]:
    """Convenience: deduped record list for the report (see ``merge_records``)."""
    return merge_records(iter_shard_paths(shards_glob))["records"]


def write_merged(records: List[Dict[str, Any]], out_path: str) -> None:
    """Write the merged records to a single checkpoint (header + one line each)."""
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        fh.write(json.dumps({"_header": True, "_merged": True,
                             "n_records": len(records)}) + "\n")
        for rec in records:
            fh.write(json.dumps(rec) + "\n")


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description="Merge per-model LPS confirmatory shards (dedup by "
                    "task_id×model×seed×method_version)."
    )
    parser.add_argument("--shards", default=DEFAULT_SHARDS_GLOB,
                        help=f"Glob for shard checkpoints (default: "
                             f"{DEFAULT_SHARDS_GLOB}).")
    parser.add_argument("--out", default=DEFAULT_MERGED_OUT,
                        help=f"Merged checkpoint output (default: {DEFAULT_MERGED_OUT}).")
    args = parser.parse_args(argv)

    paths = iter_shard_paths(args.shards)
    if not paths:
        print(f"[Merge] No shards match {args.shards!r}.")
        return
    merged = merge_records(paths)
    write_merged(merged["records"], args.out)
    print(f"[Merge] Shards: {len(paths)}")
    for path, n in merged["per_shard"].items():
        print(f"    {path}  ({n} records)")
    print(f"[Merge] Read {merged['n_read']} records; kept "
          f"{len(merged['records'])}; deduped {merged['n_dup']} "
          f"(conflicts: {merged['n_conflict']}).")
    print(f"[Merge] Per-model: {merged['per_model']}")
    print(f"[Merge] Wrote {args.out}")
    print(f"[Merge] Report with: python scripts/lps_confirm_report.py "
          f"--checkpoint {args.out} --out files/study2_confirm_results.md")


if __name__ == "__main__":
    main()
