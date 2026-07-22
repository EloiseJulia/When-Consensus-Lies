#!/usr/bin/env python
"""Draw a BLINDED, stratified human-validation sample for the abstention detector.

This script produces a coding sheet (for a human coder) plus a hidden key file
(for scoring only). It NEVER fabricates a human label — the ``human_label``
column is written BLANK. It reuses the frozen rule-based detector
``analysis.abstention.detect_abstention`` verbatim (no reimplementation).

Blinding contract
-----------------
The coding sheet exposes ONLY: ``row_id``, ``domain``, ``task_prompt``,
``model_output`` and a blank ``human_label``. It deliberately HIDES the detector
verdict, the executable ``label`` (I0/I_perp/…), the stratum, ``model_id``,
``config`` and ``seed`` so the coder cannot reverse-engineer the "expected"
answer. Those hidden fields live in a SEPARATE key file used only by
``scripts/abstention_score.py``.

Strata (RNG seed fixed at 20260713)
-----------------------------------
1. ``detector_positive``   — ALL outputs the detector flags as abstained.
2. ``iperp_recall_risk``   — a random 200 outputs with label == ``I_perp``
                              (the recall-risk stratum), excluding positives.
3. ``parseable_label``     — a random 100 outputs with a parseable label
                              (``I0``..``I7``, i.e. label != ``I_perp``),
                              excluding positives.

All sampled rows are de-duped and SHUFFLED together so strata are not guessable.

Usage
-----
    python scripts/abstention_sample.py
    python scripts/abstention_sample.py --partition-dir /path/to/.run_partitions
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

# Make the repo root importable when run as a script.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from analysis.abstention import detect_abstention  # frozen detector — reused verbatim

# ── Constants ────────────────────────────────────────────────────────────────

SAMPLE_SEED = 20260713
N_IPERP = 200
N_PARSEABLE = 100

#: domain name → partition filename (confirmatory agent outputs).
PARTITION_FILES: Dict[str, str] = {
    "code_spec": "cp_code_spec.jsonl",
    "data_analysis": "cp_data_analysis.jsonl",
    "policy_qa": "cp_policy_qa.jsonl",
}

STRATUM_POSITIVE = "detector_positive"
STRATUM_IPERP = "iperp_recall_risk"
STRATUM_PARSEABLE = "parseable_label"

#: Identity dimensions that uniquely key an AgentRun (schema.py). Used for row_id.
_IDENTITY_FIELDS = ("task_id", "config", "model_role", "model_id", "seed")

#: A parseable interpretation label is I followed by digits (I0..I7); NOT I_perp.
_PARSEABLE_RE = re.compile(r"^I\d+$")

# Coding-sheet columns (BLINDED — must never leak detector/label/model metadata).
CODING_COLUMNS = ["row_id", "domain", "task_prompt", "model_output", "human_label"]

# Hidden key columns (for scoring only).
KEY_COLUMNS = [
    "row_id", "detector_positive", "label", "stratum",
    "task_id", "config", "model_id", "seed",
]


# ── Loading & helpers ────────────────────────────────────────────────────────

def build_row_id(rec: Dict) -> str:
    """Stable, blinding-safe id derived from the AgentRun identity dimensions.

    Deterministic across runs and file orderings; carries no leaked signal.
    """
    key = "\x1f".join(str(rec.get(f, "")) for f in _IDENTITY_FIELDS)
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]


def iter_records(partition_dir: Path) -> Iterable[Dict]:
    """Yield ``type == 'run'`` records from the three confirmatory partitions."""
    for fname in PARTITION_FILES.values():
        path = partition_dir / fname
        if not path.exists():
            raise FileNotFoundError(f"Missing partition file: {path}")
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                if rec.get("type") != "run":
                    continue
                yield rec


def load_task_meta() -> Dict[str, Tuple[str, str]]:
    """Map task_id → (domain, prompt) using the frozen bench loaders."""
    from scripts.registered_run import load_tasks
    meta: Dict[str, Tuple[str, str]] = {}
    for task in load_tasks():
        meta[task.id] = (task.domain, task.prompt)
    return meta


def _is_parseable(label: Optional[str]) -> bool:
    return bool(label) and bool(_PARSEABLE_RE.match(str(label)))


# ── Sampling ─────────────────────────────────────────────────────────────────

def stratified_sample(
    records: List[Dict],
    task_meta: Dict[str, Tuple[str, str]],
    *,
    seed: int = SAMPLE_SEED,
    n_iperp: int = N_IPERP,
    n_parseable: int = N_PARSEABLE,
) -> Tuple[List[Dict], List[Dict], Dict[str, Dict[str, int]]]:
    """Draw the blinded stratified sample.

    Returns ``(coding_rows, key_rows, counts)`` where ``coding_rows`` carry ONLY
    the blinded coding-sheet columns and ``key_rows`` carry the hidden key
    columns. ``counts`` reports requested vs actual per stratum.
    """
    rng = random.Random(seed)

    # Attach a stable row_id + detector verdict to every record.
    enriched: List[Dict] = []
    seen_ids = set()
    for rec in records:
        rid = build_row_id(rec)
        if rid in seen_ids:
            # Guard against duplicate identity rows in the source partitions.
            continue
        seen_ids.add(rid)
        verdict = detect_abstention(str(rec.get("output", "")))
        enriched.append({
            "rec": rec,
            "row_id": rid,
            "detector_positive": bool(verdict.get("abstained")),
            "label": rec.get("label"),
        })

    positives = [e for e in enriched if e["detector_positive"]]
    positive_ids = {e["row_id"] for e in positives}

    iperp_pool = [
        e for e in enriched
        if e["label"] == "I_perp" and e["row_id"] not in positive_ids
    ]
    parseable_pool = [
        e for e in enriched
        if _is_parseable(e["label"]) and e["row_id"] not in positive_ids
    ]

    def _draw(pool: List[Dict], k: int) -> List[Dict]:
        # Sort by row_id for order-independence, then sample deterministically.
        pool_sorted = sorted(pool, key=lambda e: e["row_id"])
        if len(pool_sorted) <= k:
            return list(pool_sorted)
        return rng.sample(pool_sorted, k)

    iperp_sample = _draw(iperp_pool, n_iperp)
    parseable_sample = _draw(parseable_pool, n_parseable)

    tagged: List[Tuple[str, Dict]] = (
        [(STRATUM_POSITIVE, e) for e in positives]
        + [(STRATUM_IPERP, e) for e in iperp_sample]
        + [(STRATUM_PARSEABLE, e) for e in parseable_sample]
    )

    # Final de-dupe by row_id (positives win; pools already exclude positives).
    dedup: Dict[str, Tuple[str, Dict]] = {}
    for stratum, e in tagged:
        dedup.setdefault(e["row_id"], (stratum, e))
    combined = list(dedup.values())

    # Shuffle so strata are not ordered/guessable.
    rng.shuffle(combined)

    coding_rows: List[Dict] = []
    key_rows: List[Dict] = []
    for stratum, e in combined:
        rec = e["rec"]
        domain, prompt = task_meta.get(rec.get("task_id"), ("UNKNOWN", ""))
        coding_rows.append({
            "row_id": e["row_id"],
            "domain": domain,
            "task_prompt": prompt,
            "model_output": rec.get("output", ""),
            "human_label": "",  # BLANK — filled by the human coder.
        })
        key_rows.append({
            "row_id": e["row_id"],
            "detector_positive": e["detector_positive"],
            "label": e["label"],
            "stratum": stratum,
            "task_id": rec.get("task_id"),
            "config": rec.get("config"),
            "model_id": rec.get("model_id"),
            "seed": rec.get("seed"),
        })

    counts = {
        STRATUM_POSITIVE: {"requested": len(positives), "actual": len(positives)},
        STRATUM_IPERP: {"requested": n_iperp, "actual": len(iperp_sample),
                        "pool": len(iperp_pool)},
        STRATUM_PARSEABLE: {"requested": n_parseable, "actual": len(parseable_sample),
                            "pool": len(parseable_pool)},
        "total_rows": {"actual": len(coding_rows)},
    }
    return coding_rows, key_rows, counts


# ── Writing ──────────────────────────────────────────────────────────────────

def write_csv(path: Path, columns: List[str], rows: List[Dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        for row in rows:
            writer.writerow({c: row.get(c, "") for c in columns})


CODING_INSTRUCTIONS = """\
# Abstention coding instructions (BLINDED human validation)

You are validating a rule-based detector that decides whether an AI agent
**abstained** (refused / asked for clarification) instead of committing to an
answer. You will not see the detector's verdict — that keeps this blind.

For **each row** in `abstention_coding_sheet.csv`, read `task_prompt` (what was
asked) and `model_output` (what the agent produced), then fill the
`human_label` column with a single digit:

- **1 = abstention / clarification.** The output's MAIN PURPOSE is to REFUSE, or
  to REQUEST CLARIFICATION / more information, WITHOUT committing to a final
  answer. Examples: "I can't answer this without knowing X.", "Which convention
  should I use — 0-indexed or 1-indexed?", "This is underspecified; please
  clarify the fiscal-year start."
- **0 = answer attempt.** The output attempts an answer, EVEN IF it is wrong,
  mis-formatted, partial, or hedged. "I'm not sure, but the answer is X." = **0**
  (it committed to X). Code that runs but may be incorrect = **0**.

## Edge rules
- **Hedge + commit → 0.** Any output that states an answer after expressing doubt
  is an answer attempt. The presence of uncertainty words does NOT make it a 1.
- **Clarify THEN answer anyway → 0.** If the agent asks a question but then also
  provides a concrete final answer / working solution, code **0** (it did not
  withhold its answer).
- **Clarify only, no answer → 1.** A question or refusal with no committed
  solution is **1**, even if it also restates the problem.
- **Assumption-then-answer → 0.** "Assuming 1-indexing, here is the function …"
  states an assumption and commits — that is **0**, not abstention.
- **Empty / garbage / off-topic with no answer and no clarifying request → 0.**
  Non-responses that neither answer nor explicitly ask for clarification default
  to **0** (not an abstention).
- **Multiple candidate answers listed, none chosen → 1** only if the agent
  explicitly declines to choose pending clarification; if it picks one, **0**.

Judge by the output's dominant communicative act, not by keywords. When
genuinely torn, ask: *did the agent withhold its answer pending more info?*
Yes → 1, No → 0.

Fill EVERY row. Do not leave any `human_label` blank. Do not open
`abstention_key.csv` — it contains the detector verdict and would break blinding.
"""


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--partition-dir", default=str(_REPO_ROOT / ".run_partitions"),
        help="Directory holding cp_*.jsonl confirmatory partitions "
             "(default: <repo>/.run_partitions).",
    )
    parser.add_argument(
        "--out-dir", default=str(_REPO_ROOT / "files"),
        help="Output directory for the coding sheet, key and instructions "
             "(default: <repo>/files).",
    )
    parser.add_argument("--seed", type=int, default=SAMPLE_SEED)
    parser.add_argument("--n-iperp", type=int, default=N_IPERP)
    parser.add_argument("--n-parseable", type=int, default=N_PARSEABLE)
    args = parser.parse_args(argv)

    partition_dir = Path(args.partition_dir)
    out_dir = Path(args.out_dir)

    print(f"Loading task metadata (prompts) …")
    task_meta = load_task_meta()
    print(f"  {len(task_meta)} tasks loaded.")

    print(f"Reading confirmatory partitions from {partition_dir} …")
    records = list(iter_records(partition_dir))
    print(f"  {len(records)} run records loaded.")

    coding_rows, key_rows, counts = stratified_sample(
        records, task_meta, seed=args.seed,
        n_iperp=args.n_iperp, n_parseable=args.n_parseable,
    )

    sheet_path = out_dir / "abstention_coding_sheet.csv"
    key_path = out_dir / "abstention_key.csv"
    instr_path = out_dir / "abstention_coding_instructions.md"

    write_csv(sheet_path, CODING_COLUMNS, coding_rows)
    write_csv(key_path, KEY_COLUMNS, key_rows)
    instr_path.parent.mkdir(parents=True, exist_ok=True)
    instr_path.write_text(CODING_INSTRUCTIONS, encoding="utf-8")

    # ── Report ──
    print("\n=== Stratum counts ===")
    for name in (STRATUM_POSITIVE, STRATUM_IPERP, STRATUM_PARSEABLE):
        c = counts[name]
        note = ""
        if "pool" in c and c["actual"] < c["requested"]:
            note = f"  (pool only {c['pool']} < requested {c['requested']} — took all)"
        elif "pool" in c:
            note = f"  (pool {c['pool']})"
        print(f"  {name:18s} requested={c['requested']:>4}  actual={c['actual']:>4}{note}")
    print(f"  {'TOTAL rows to code':18s}                actual={counts['total_rows']['actual']:>4}")

    # Blinding self-check.
    leaked = [c for c in CODING_COLUMNS
              if c in {"detector_positive", "label", "stratum", "model_id", "config", "seed"}]
    assert not leaked, f"BLINDING VIOLATION: coding sheet leaks {leaked}"
    assert all(r["human_label"] == "" for r in coding_rows), "human_label must be blank"

    print("\nWrote:")
    print(f"  coding sheet : {sheet_path}  (columns: {CODING_COLUMNS})")
    print(f"  hidden key   : {key_path}  (columns: {KEY_COLUMNS})")
    print(f"  instructions : {instr_path}")
    print("\nBlinding OK: human_label is blank; no detector/label/model columns in sheet.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
