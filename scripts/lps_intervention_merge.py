# constructed by: Claude (Anthropic) family
"""Merge + integrity-validate Study-2 INTERVENTION checkpoints/shards (Phase 2b).

# Implementer model family: Claude / Anthropic
# Auditor model family: MUST be non-Anthropic (Law 6 — cross-family requirement)

Mirrors the FAIL-LOUD discipline of ``scripts/lps_confirm_merge.py`` (MAJOR-2
hardening) so the report can NEVER silently pool an interrupted / overlapping /
incompatible intervention grid:

  * ABORT (``MergeError``) if any record LINE is malformed (never silently skip).
  * ABORT if shards carry incompatible run-fingerprints — the FULL intervention
    fingerprint (``intervention_version``, ``method_version``, ``k``, ``τ``, ``τ_s``,
    ``seed_bases``) must agree; only the per-shard ``models`` list may differ.
  * DEDUP by ``(task_id, model, seed_base, intervention_version, method_version)``;
    an identical duplicate collapses, a CONFLICTING duplicate (same key, different
    payload) ABORTS.
  * COMPLETENESS: the observed cells must fill the full Cartesian grid
    (items × models × declared seed roster). A missing cell ABORTS — an
    interrupted grid must not be averaged as if complete.

Usage:
    python scripts/lps_intervention_merge.py                       # default glob
    python scripts/lps_intervention_merge.py --shards '.run_partitions/cp_lps_intervention__*.jsonl'
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

import lps_intervention as intv  # noqa: E402
import lps_method as lps  # noqa: E402  (FROZEN METHOD_VERSION source of truth)

DEFAULT_SHARDS_GLOB = intv.SHARD_CHECKPOINT_GLOB
DEFAULT_MERGED_OUT = ".run_partitions/cp_lps_intervention_merged.jsonl"

#: Record keys that MUST be present, non-null, and correctly typed on EVERY cell
#: before it may enter the (item × model × seed) universe. A null-keyed record must
#: never slip into completeness accounting (MAJOR-4 hardening).
_REQUIRED_KEYS = ("task_id", "model", "seed_base")

#: Fingerprint keys that MUST agree across shards. ``models`` is intentionally
#: EXCLUDED — a per-model shard legitimately carries its own single-model list;
#: every OTHER knob must be identical or the shards measured incompatible things.
_SHARED_FP_KEYS = ("intervention_version", "method_version", "k", "tau", "tau_s",
                   "seed_bases")


class MergeError(RuntimeError):
    """Raised when checkpoints are malformed, incompatible, conflicting, or the
    grid is incomplete (fail loudly — never silently skip/concatenate)."""


def _fp(rec: Dict[str, Any]) -> Dict[str, Any]:
    return rec.get("_fingerprint") or {}


def _dedup_key(rec: Dict[str, Any]) -> Tuple[Any, ...]:
    fp = _fp(rec)
    return (rec.get("task_id"), rec.get("model"), rec.get("seed_base"),
            fp.get("intervention_version"), fp.get("method_version"))


def iter_shard_paths(shards_glob: str) -> List[str]:
    """Sorted list of checkpoint paths matching the glob."""
    return sorted(_glob.glob(shards_glob))


def _hashable(v: Any) -> Any:
    return tuple(v) if isinstance(v, list) else v


def _shared_fp(fp: Optional[Dict[str, Any]]) -> Optional[Tuple[Any, ...]]:
    if not fp:
        return None
    return tuple(_hashable(fp.get(k)) for k in _SHARED_FP_KEYS)


def _validate_record_keys(rec: Dict[str, Any], path: str, lineno: int) -> None:
    """ABORT unless the record has non-null, correctly-typed identity keys.

    A cell with a missing / None / wrong-typed ``task_id``|``model``|``seed_base``
    would poison the (item × model × seed) universe (a null cell could silently
    satisfy completeness). Fail loud instead of skipping (MAJOR-4).
    """
    if not isinstance(rec, dict):
        raise MergeError(
            f"Record at {path}:{lineno} is not a JSON object — refusing to pool a "
            f"malformed record ({type(rec).__name__})."
        )
    for key in _REQUIRED_KEYS:
        if key not in rec or rec.get(key) is None:
            raise MergeError(
                f"Record at {path}:{lineno} is missing required key {key!r} "
                "(or it is null) — refusing to let a null-keyed cell into the grid."
            )
    tid, model, seed = rec.get("task_id"), rec.get("model"), rec.get("seed_base")
    if not isinstance(tid, str) or not tid.strip():
        raise MergeError(
            f"Record at {path}:{lineno} has a non-string/empty task_id ({tid!r})."
        )
    if not isinstance(model, str) or not model.strip():
        raise MergeError(
            f"Record at {path}:{lineno} has a non-string/empty model ({model!r})."
        )
    # bool is a subclass of int — reject it explicitly so True/False can't pass.
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise MergeError(
            f"Record at {path}:{lineno} has a non-int seed_base ({seed!r})."
        )


def load_shard(path: str) -> Dict[str, Any]:
    """Load ONE checkpoint's records + declared roster, ABORTING on any malformity.

    Returns ``{"records": [...], "roster": {...}|None}``. A non-empty line that is
    not valid JSON, a record missing its ``_fingerprint`` header, or a record with
    a missing/None/wrong-typed identity key raises ``MergeError`` — a corrupted or
    unstamped checkpoint must never be silently truncated into valid-looking
    metrics. The DECLARED grid roster (from the ``_header`` line) is returned so a
    downstream completeness check can validate against the INTENDED grid.
    """
    p = Path(path)
    if not p.exists():
        raise MergeError(f"Checkpoint not found: {path}")
    out: List[Dict[str, Any]] = []
    roster: Optional[Dict[str, Any]] = None
    for lineno, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError as exc:
            raise MergeError(
                f"Malformed JSON at {path}:{lineno} — refusing to silently skip a "
                f"corrupted record ({exc})."
            )
        if isinstance(rec, dict) and rec.get("_header"):
            if rec.get("_roster"):
                roster = rec["_roster"]
            continue
        if not isinstance(rec, dict) or not rec.get("_fingerprint"):
            raise MergeError(
                f"Record at {path}:{lineno} has no _fingerprint — refusing to pool "
                "an unstamped record (cannot verify method/version compatibility)."
            )
        _validate_record_keys(rec, path, lineno)
        out.append(rec)
    return {"records": out, "roster": roster}


def load_records_strict(path: str) -> List[Dict[str, Any]]:
    """Back-compat thin wrapper: records only (see :func:`load_shard`)."""
    return load_shard(path)["records"]


def _validate_versions(records: List[Dict[str, Any]]) -> None:
    """ABORT unless every record's versions EQUAL the CURRENT module constants.

    Cross-record agreement alone is insufficient (MAJOR-2): a self-consistent
    checkpoint stamped a WRONG (but uniform) version would otherwise pass. Enforce
    equality to the live ``INTERVENTION_VERSION`` / ``METHOD_VERSION`` so an
    incompatible-but-uniform grid is rejected.
    """
    for rec in records:
        fp = _fp(rec)
        iv = fp.get("intervention_version")
        mv = fp.get("method_version")
        if iv != intv.INTERVENTION_VERSION:
            raise MergeError(
                f"intervention_version {iv!r} != current "
                f"{intv.INTERVENTION_VERSION!r} (task={rec.get('task_id')}, "
                f"model={rec.get('model')}, seed={rec.get('seed_base')}). Refusing "
                "to merge a checkpoint built by a different intervention version."
            )
        if mv != lps.METHOD_VERSION:
            raise MergeError(
                f"method_version {mv!r} != current {lps.METHOD_VERSION!r} "
                f"(task={rec.get('task_id')}, model={rec.get('model')}, "
                f"seed={rec.get('seed_base')}). Refusing to merge a checkpoint "
                "built by a different method version."
            )


def _merge_rosters(rosters: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Union the declared rosters across shards (fail loud if none present).

    The declared grid (models × seed_bases × items) MUST come from the checkpoint
    header manifest, never the observed records (MAJOR-3). In shard mode every
    shard header carries the SAME full roster, so unioning is a no-op; if a shard
    declares a superset the union keeps it (stricter completeness). With no roster
    at all we cannot know the intended grid → abort rather than trust observations.
    """
    if not rosters:
        raise MergeError(
            "No declared roster found in any checkpoint header — cannot verify "
            "grid completeness against the INTENDED grid. A checkpoint written by "
            "the current driver always stamps a _roster; refusing to fall back to "
            "the (possibly interrupted) observed universe."
        )
    models: set = set()
    seeds: set = set()
    items: set = set()
    for r in rosters:
        models.update(r.get("models") or [])
        seeds.update(int(s) for s in (r.get("seed_bases") or []))
        items.update(r.get("items") or [])
    return {"models": sorted(models), "seed_bases": sorted(seeds),
            "items": sorted(items)}


def _validate_fingerprints(records: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """ABORT if any record's shared fingerprint differs from the first."""
    ref_shared: Optional[Tuple[Any, ...]] = None
    ref_fp: Optional[Dict[str, Any]] = None
    for rec in records:
        fp = _fp(rec)
        shared = _shared_fp(fp)
        if shared is None:
            raise MergeError(
                f"Record (task={rec.get('task_id')}, model={rec.get('model')}, "
                f"seed={rec.get('seed_base')}) has an empty fingerprint."
            )
        if ref_shared is None:
            ref_shared, ref_fp = shared, fp
        elif shared != ref_shared:
            raise MergeError(
                "Incompatible fingerprints — refusing to merge.\n"
                f"  ref: {{ {', '.join(f'{k}={ref_fp.get(k)!r}' for k in _SHARED_FP_KEYS)} }}\n"
                f"  got: {{ {', '.join(f'{k}={fp.get(k)!r}' for k in _SHARED_FP_KEYS)} }}\n"
                "All records must share intervention_version/method_version/k/tau/"
                "tau_s/seed_bases."
            )
    return ref_fp


def _check_completeness(records: List[Dict[str, Any]],
                        roster: Dict[str, Any]) -> None:
    """ABORT if the observed cells do not fill the DECLARED roster grid.

    The item, model, AND seed axes all come from the declared roster manifest
    (``run_roster`` in the header), NOT the observed records (MAJOR-3): a shard
    that is entirely absent, or a partially-interrupted grid, is caught because a
    declared cell has no observed record. An interrupted grid must never be
    averaged as if complete.
    """
    if not records:
        raise MergeError("No records to validate for completeness.")
    items = list(roster.get("items") or [])
    models = list(roster.get("models") or [])
    seeds = sorted(int(s) for s in (roster.get("seed_bases") or []))
    if not (items and models and seeds):
        raise MergeError(
            "Declared roster is missing one of models/seed_bases/items — cannot "
            f"verify completeness (roster={roster!r})."
        )
    present = {(r.get("task_id"), r.get("model"), r.get("seed_base"))
               for r in records}
    missing = [(t, m, s) for t in items for m in models for s in seeds
               if (t, m, s) not in present]
    if missing:
        preview = ", ".join(f"(item={t}, model={m}, seed={s})"
                            for t, m, s in missing[:5])
        raise MergeError(
            f"Incomplete grid — {len(missing)} declared cell(s) missing from "
            f"{len(items)} items × {len(models)} models × {len(seeds)} seeds "
            f"(= {len(items) * len(models) * len(seeds)} declared). "
            f"First missing: {preview}. Refusing to average an interrupted grid."
        )


def merge_records(paths: List[str], *, strict: bool = True,
                  check_completeness: bool = True) -> Dict[str, Any]:
    """Load + validate + dedup records across checkpoint files (fail-loud).

    Returns ``{records, n_read, n_dup, n_conflict, per_shard, per_model,
    shared_fingerprint, roster}``. With ``strict=True`` (default): malformed lines,
    missing/None identity keys, versions ≠ the current constants, incompatible
    fingerprints, conflicting duplicates, and (if ``check_completeness``) any
    declared-roster cell missing all raise ``MergeError``.
    """
    all_records: List[Dict[str, Any]] = []
    rosters: List[Dict[str, Any]] = []
    per_shard: Dict[str, int] = {}
    for path in paths:
        shard = load_shard(path)
        per_shard[path] = len(shard["records"])
        all_records.extend(shard["records"])
        if shard["roster"] is not None:
            rosters.append(shard["roster"])

    shared_fp = None
    if strict:
        _validate_versions(all_records)
        shared_fp = _validate_fingerprints(all_records)
    elif all_records:
        shared_fp = _fp(all_records[0])

    seen: Dict[Tuple[Any, ...], Dict[str, Any]] = {}
    n_read = 0
    n_dup = 0
    n_conflict = 0
    for rec in all_records:
        n_read += 1
        key = _dedup_key(rec)
        if key in seen:
            n_dup += 1
            if seen[key] != rec:
                n_conflict += 1
                if strict:
                    raise MergeError(
                        "Conflicting duplicate records for the same cell — "
                        "refusing to merge.\n"
                        f"  key (task_id, model, seed_base, intervention_version, "
                        f"method_version) = {key}\n"
                        "Two records recorded DIFFERENT payloads for the same cell; "
                        "a fixed method must be reproducible. Investigate before "
                        "pooling."
                    )
            continue
        seen[key] = rec

    records = list(seen.values())
    roster = None
    if strict and check_completeness:
        roster = _merge_rosters(rosters)
        _check_completeness(records, roster)

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
        "roster": roster,
    }


def write_merged(records: List[Dict[str, Any]], out_path: str) -> None:
    """Write merged records to a single checkpoint (header + one line each)."""
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        fh.write(json.dumps({"_header": True, "_merged": True,
                             "n_records": len(records)}) + "\n")
        for rec in records:
            fh.write(json.dumps(rec) + "\n")


def main(argv: Optional[List[str]] = None, *,
         allowed_roots: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description="Merge + validate Study-2 intervention checkpoints/shards "
                    "(fail-loud: dedup by task×model×seed×version, grid "
                    "completeness)."
    )
    parser.add_argument("--shards", default=DEFAULT_SHARDS_GLOB,
                        help=f"Glob for checkpoints (default: {DEFAULT_SHARDS_GLOB}).")
    parser.add_argument("--out", default=DEFAULT_MERGED_OUT,
                        help=f"Merged output (default: {DEFAULT_MERGED_OUT}).")
    args = parser.parse_args(argv)

    paths = iter_shard_paths(args.shards)
    if not paths:
        print(f"[Merge] No checkpoints match {args.shards!r}.")
        return

    # Artifact-isolation gate (MAJOR-5): neither the INPUT shards nor the OUTPUT
    # may resolve into a confirmatory/frozen/other-pass namespace.
    try:
        for p in paths:
            intv.validate_merge_io_path(p, label="input shard", is_checkpoint=True,
                                        allowed_roots=allowed_roots)
        intv.validate_merge_io_path(args.out, label="--out", is_checkpoint=True,
                                    allowed_roots=allowed_roots)
    except ValueError as exc:
        print(f"[Merge] ABORT — {exc}", file=sys.stderr)
        raise SystemExit(2)

    try:
        merged = merge_records(paths)
    except MergeError as exc:
        print(f"[Merge] ABORT — {exc}", file=sys.stderr)
        raise SystemExit(2)
    write_merged(merged["records"], args.out)
    print(f"[Merge] Checkpoints: {len(paths)}")
    for path, n in merged["per_shard"].items():
        print(f"    {path}  ({n} records)")
    print(f"[Merge] Read {merged['n_read']}; kept {len(merged['records'])}; "
          f"deduped {merged['n_dup']} (conflicts: {merged['n_conflict']}).")
    print(f"[Merge] Per-model: {merged['per_model']}")
    print(f"[Merge] Wrote {args.out}")


if __name__ == "__main__":
    main()
