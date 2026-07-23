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

#: Fingerprint keys that MUST agree across shards for the merge to be valid. The
#: ``models`` key is intentionally EXCLUDED — each per-model shard legitimately
#: carries its own single-model list; every OTHER knob (method version, k, τ, τ_s,
#: seed roster) must be identical or the shards measured incompatible quantities.
_SHARED_FP_KEYS = ("method_version", "k", "tau", "tau_s", "seed_bases")


class MergeError(RuntimeError):
    """Raised when shards are incompatible or genuinely conflict (fail loudly)."""


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


def _read_header_fingerprint(path: Path) -> Optional[Dict[str, Any]]:
    """Return the ``_fingerprint`` from a shard's header line, if present."""
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                return None
            if rec.get("_header"):
                return rec.get("_fingerprint")
            # First non-header line: fall back to its per-record fingerprint.
            return rec.get("_fingerprint")
    except OSError:
        return None
    return None


def _shared_fp(fp: Optional[Dict[str, Any]]) -> Optional[Tuple[Any, ...]]:
    """The cross-shard-compatible projection of a fingerprint (drops ``models``)."""
    if not fp:
        return None
    return tuple(_hashable(fp.get(k)) for k in _SHARED_FP_KEYS)


def _hashable(v: Any) -> Any:
    return tuple(v) if isinstance(v, list) else v


def _validate_shard_fingerprints(paths: List[str]) -> Optional[Dict[str, Any]]:
    """ABORT (MergeError) if shards carry incompatible run-fingerprints.

    Compares every shard's fingerprint MINUS the per-shard ``models`` field. A
    differing method version / k / τ / τ_s / seed roster means the shards measured
    incompatible quantities and MUST NOT be pooled.
    """
    ref_shared: Optional[Tuple[Any, ...]] = None
    ref_fp: Optional[Dict[str, Any]] = None
    ref_path: Optional[str] = None
    for path in paths:
        fp = _read_header_fingerprint(Path(path))
        shared = _shared_fp(fp)
        if shared is None:
            continue
        if ref_shared is None:
            ref_shared, ref_fp, ref_path = shared, fp, path
        elif shared != ref_shared:
            raise MergeError(
                "Incompatible shard fingerprints — refusing to merge.\n"
                f"  {ref_path}: "
                f"{ {k: ref_fp.get(k) for k in _SHARED_FP_KEYS} }\n"
                f"  {path}: "
                f"{ {k: (fp or {}).get(k) for k in _SHARED_FP_KEYS} }\n"
                "Shards must share method_version/k/tau/tau_s/seed_bases."
            )
    return ref_fp


def merge_records(paths: List[str], *, strict: bool = True) -> Dict[str, Any]:
    """Load + dedup records across shard files (validated, fail-loud).

    (a) ABORTS if shards carry incompatible run-fingerprints (different
        method_version/k/τ/τ_s/seed roster).
    (b) DEDUPS by ``(task_id, model, seed_base, method_version)``.
    (c) ABORTS on a genuine value CONFLICT (same key, different payload) rather
        than silently keeping the first — a fixed method must be reproducible.

    Returns ``{records, n_read, n_dup, n_conflict, per_shard, per_model,
    shared_fingerprint}``. ``strict=False`` downgrades (a)/(c) to counts (for
    diagnostics/tests only).
    """
    shared_fp = None
    if strict:
        shared_fp = _validate_shard_fingerprints(paths)
    else:
        shared_fp = _read_header_fingerprint(Path(paths[0])) if paths else None

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
                    if strict:
                        raise MergeError(
                            "Conflicting duplicate records for the same cell — "
                            "refusing to merge.\n"
                            f"  key (task_id, model, seed_base, method_version) = "
                            f"{key}\n"
                            f"  in shard: {path}\n"
                            "Two shards recorded DIFFERENT results for the same "
                            "cell; a fixed method must be reproducible. Investigate "
                            "before pooling."
                        )
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
        "shared_fingerprint": shared_fp,
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
    try:
        merged = merge_records(paths)
    except MergeError as exc:
        print(f"[Merge] ABORT — {exc}", file=sys.stderr)
        raise SystemExit(2)
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
