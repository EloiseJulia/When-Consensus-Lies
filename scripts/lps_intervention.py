# constructed by: Claude (Anthropic) family
"""Study 2 LPS INTERVENTION closed-loop driver (Phase 2b) — H-B1' + H-B2'.

# Implementer model family: Claude / Anthropic
# Auditor model family: MUST be non-Anthropic (Law 6 — cross-family requirement)

ADDITIVE driver for the FROZEN prereg intervention hypotheses
(``paper/preregistration/2026-07-23-study2-prereg-FROZEN.md`` §1):

  * **H-B1' (selective clarification):** for every (item, seed) it computes the
    clarify DECISION under each policy, reusing the signals the black-box detector
    already produces (``lps_method.lpp_detect``):
      - ``lpp_gated`` (ours)      — clarify iff ``is_flagged`` (H_ctx-self > τ ∧
        H_seed ≤ τ_s, FROZEN τ=0, τ_s=0.5) — fires in the danger quadrant.
      - ``always``                — clarify = True for every item (the always-ask
        baseline; loses on specificity).
      - ``semantic_entropy_gated``— clarify iff ``H_seed > τ_s`` (the SOTA policy;
        MISSES the low-H_seed danger quadrant).
      - ``self_consistency_gated``— clarify iff the k seed resamples disagree
        (self-consistency < 1).
      - ``requirements_probing_gated`` — clarify iff ≥1 dimension was surfaced
        (surfacing WITHOUT the pinning test; the strong detection baseline).
    The gold NEED (``lps_gold.gold_ambiguity``) is evaluation-only (never a prompt).

  * **H-B2' (oracle resolution):** for each AMB+ item it commits a
    never-clarify baseline answer AND an oracle-resolved answer where the deleted-
    axis GOLD convention (the benchmark's ``latent_spec`` = the intended I0 spec)
    is supplied "by the simulated user" as a clarification. Both answers are
    labeled by the FROZEN executable labeler and scored downstream with the
    executable ``analysis.cd.cd_primary`` (target ``I0``) — NEVER an LLM judge.

ANTI-LEAKAGE (inviolable): every DETECTOR / surfacing / clarify-decision prompt is
GENERIC (it reuses ``lpp_detect``, whose prompts are already gold-free). The ONLY
prompt that carries any gold text is the H-B2' oracle re-ask, which appends the
intended convention as an EVALUATION-time controlled oracle ("Clarification from
the user: ..."). Gold / target / foil / key_questions / interpretation text never
enters any detector or surfacing prompt.

ISOLATED, RESUMABLE, GUARDED (mirrors ``lps_confirm``):
  * OWN checkpoint ``.run_partitions/cp_lps_intervention.jsonl`` + OWN cache
    ``.llm_cache_lps_intv`` — path-guarded so it can NEVER read/write ANY
    confirmatory (or other pass's) checkpoint/cache.
  * FULL run-fingerprint (intervention version + method version + k + τ/τ_s + the
    MODEL list + the SEED list) stamped on every record; a resume refuses to reuse
    any record whose fingerprint differs.
  * ``main()`` requires ``RUNNER_LIVE=1`` AND a reachable copilot_proxy, else it
    prints "skipped" and exits 0 (offline/CI safe). ``--dry-run`` enumerates the
    job count with NO network.

Usage:
    python scripts/lps_intervention.py --dry-run                        # enumerate
    python scripts/lps_intervention.py --models gpt-5.6-sol \\
        --seeds 30260713 30270713 30280713 --dry-run
    RUNNER_LIVE=1 python scripts/lps_intervention.py                    # live (gated)

Do NOT run the live grid here — the Manager launches it after the cross-family
audit + merge. This script BUILDS + DRY-RUNS the apparatus only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

_SCRIPTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPTS_DIR.parent
for _p in (str(_REPO_ROOT), str(_SCRIPTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import lps_method as lps  # noqa: E402
import lps_baselines as baselines  # noqa: E402
import lps_gold as gold  # noqa: E402
import lps_pilot as pilot1  # noqa: E402  (reuse live/proxy guards read-only)


# ── Intervention version (NEW tag; does NOT mutate lps.METHOD_VERSION) ────────
#: Bumped whenever the intervention wiring (policies / oracle construction /
#: answer prompts) changes so a resume cannot silently mix incompatible records.
INTERVENTION_VERSION = "lps-intv-2026-07-23-v1"

# ── Isolated artifacts (NEVER a confirmatory / pilot / other-pass path) ───────
CHECKPOINT = ".run_partitions/cp_lps_intervention.jsonl"
CACHE_DIR = ".llm_cache_lps_intv"
CHECKPOINT_BASE = ".run_partitions/cp_lps_intervention"
CACHE_BASE = ".llm_cache_lps_intv"
SHARD_CHECKPOINT_GLOB = ".run_partitions/cp_lps_intervention__*.jsonl"

#: Pilot roster (owner-scoped, DECISION-LOG row 89): gpt-5.6-sol FIRST. The driver
#: ACCEPTS ``--models`` but the pilot targets a single model.
DEFAULT_MODELS = ["gpt-5.6-sol"]

#: 3 collision-free seed bases, spaced 10_000 apart — far wider than any seed
#: offset lps_method uses internally (H_seed: base+j for j<k; H_ctx pinning:
#: base + dim*100 + val ≤ ~500; the intervention answers use base + 700_000 /
#: 700_001, all disjoint) so no two (item, model, seed) cells collide. Distinct
#: from the confirmatory bases (2026/2027/2028-0713) AND written to a SEPARATE
#: checkpoint+cache, so the confirmatory artifacts are never touched.
DEFAULT_SEED_BASES = [30260713, 30270713, 30280713]

RPM = 30

#: FROZEN operating point (prereg §2). Item flag = (H_ctx-self > τ) ∧ (H_seed ≤ τ_s).
TAU = 0.0
TAU_S = 0.5

#: Distinct seed offsets for the H-B2' committed answers (disjoint from lpp_detect's
#: internal H_seed / H_ctx seed ranges so their cache cells never collide).
_BASELINE_SEED_OFFSET = 700_000
_ORACLE_SEED_OFFSET = 700_001

#: The oracle clarification marker. The ONLY prompt allowed to carry gold text is
#: the H-B2' oracle re-ask, which begins with this marker.
ORACLE_PREFIX = "Clarification from the user:"

#: H-B1' clarify policies (order fixed for reporting).
CLARIFY_POLICIES = [
    "lpp_gated",
    "always",
    "semantic_entropy_gated",
    "self_consistency_gated",
    "requirements_probing_gated",
]

#: Protected substrings that must NEVER appear ANYWHERE in the FULL resolved path
#: of an intervention checkpoint/cache — not just the basename. This blocks writing
#: INSIDE a confirmatory/pilot/other-pass namespace (e.g. a nested directory named
#: ``cp_lps_confirm_archive`` or ``.llm_cache_registered_run``), which a
#: basename-only check would wrongly accept. Matched case-insensitively against the
#: path RELATIVE to the repo root (so the check is insensitive to where the repo is
#: checked out), falling back to the full path for out-of-repo (e.g. temp) paths.
_PROTECTED_PATH_SUBSTR = (
    "cp_lps_confirm", "lps_confirm", "llm_cache_lps_confirm",
    "registered_run", "cp_sck10", "sck10", "phaseb",
    "pilot", "pilot_gate", "default_check",
)


def _rel_lower(p: Path) -> str:
    """Path relative to the repo root (else the full path), lowercased/posix.

    Used for the protected-substring scan so it is insensitive to the repo's
    checkout location while still catching a protected token anywhere INSIDE the
    (possibly nested) intervention path.
    """
    try:
        rel = p.relative_to(_REPO_ROOT.resolve())
        return rel.as_posix().lower()
    except ValueError:
        return p.as_posix().lower()


def _is_under(child: Path, root: Path) -> bool:
    try:
        return child.is_relative_to(root)
    except AttributeError:  # pragma: no cover (py<3.9)
        return str(child).startswith(str(root))


def _validate_output_paths(checkpoint_path: str, cache_dir: str) -> None:
    """Reject any path that could read/write a confirmatory/other-pass artifact.

    Defence in depth (MAJOR-1 hardening — a basename-only check is bypassable):
      1. The checkpoint BASENAME must start with ``cp_lps_intervention`` and the
         cache basename with ``.llm_cache_lps_intv``.
      2. NO protected substring (``cp_lps_confirm``, ``registered_run``, ``sck10``,
         ``phaseb``, ``pilot``, …) may appear ANYWHERE in the FULL resolved path —
         so a nested confirmatory/other-pass DIRECTORY cannot smuggle a write in.
      3. The checkpoint's PARENT must be EXACTLY the repo's ``.run_partitions`` root
         (or under a temp dir for tests) — never a nested subdirectory; the cache's
         parent must be EXACTLY the repo root (or under a temp dir). This blocks
         ``.run_partitions/cp_lps_confirm_archive/cp_lps_intervention.jsonl`` and
         ``.llm_cache_registered_run/.llm_cache_lps_intv``.
    """
    cp = Path(checkpoint_path).resolve()
    cache = Path(cache_dir).resolve()
    repo_root = _REPO_ROOT.resolve()
    runparts_root = (repo_root / ".run_partitions").resolve()
    tmp_root = Path(tempfile.gettempdir()).resolve()

    # (1) basename namespace.
    if not cp.name.startswith("cp_lps_intervention"):
        raise ValueError(
            f"Refusing checkpoint {checkpoint_path!r}: intervention must write its "
            "OWN checkpoint (cp_lps_intervention*.jsonl), never a confirmatory or "
            "other-pass file."
        )
    if not cache.name.startswith(".llm_cache_lps_intv"):
        raise ValueError(
            f"Refusing cache dir {cache_dir!r}: intervention must use its OWN cache "
            "(.llm_cache_lps_intv*), never a confirmatory/other-pass cache."
        )

    # (2) protected substring ANYWHERE in the full (relative) resolved path.
    for label, p in (("checkpoint", cp), ("cache dir", cache)):
        rel = _rel_lower(p)
        hit = next((tok for tok in _PROTECTED_PATH_SUBSTR if tok in rel), None)
        if hit is not None:
            raise ValueError(
                f"Refusing {label} {p!s}: protected token {hit!r} appears in the "
                "resolved path — it lives inside a confirmatory/pilot/other-pass "
                "namespace. Intervention artifacts must be fully isolated."
            )

    # (3) exact approved parent root (no nesting inside a foreign directory).
    if not (cp.parent == runparts_root or _is_under(cp, tmp_root)):
        raise ValueError(
            f"Refusing checkpoint {checkpoint_path!r}: parent must be exactly "
            f"'{runparts_root}' (or a temp dir for tests), got '{cp.parent}'."
        )
    if not (cache.parent == repo_root or _is_under(cache, tmp_root)):
        raise ValueError(
            f"Refusing cache dir {cache_dir!r}: parent must be exactly the repo "
            f"root '{repo_root}' (or a temp dir for tests), got '{cache.parent}'."
        )


# ── Per-model sharding (PARALLEL-safe namespaced paths) ──────────────────────

def sanitize_slug(model: str) -> str:
    """Filesystem-safe token for a model slug (any non ``[A-Za-z0-9_-]`` → ``_``)."""
    return re.sub(r"[^A-Za-z0-9_-]", "_", model.strip())


def shard_checkpoint(model: str) -> str:
    """Per-model checkpoint: ``.run_partitions/cp_lps_intervention__<slug>.jsonl``."""
    return f"{CHECKPOINT_BASE}__{sanitize_slug(model)}.jsonl"


def shard_cache(model: str) -> str:
    """Per-model cache dir: ``.llm_cache_lps_intv__<slug>``."""
    return f"{CACHE_BASE}__{sanitize_slug(model)}"


# ── H-B1' clarify decisions (derived from detector signals; no new prompt) ────

def clarify_decisions(detect: Dict[str, Any], *, tau_s: float = TAU_S
                      ) -> Dict[str, bool]:
    """Per-policy clarify decision from a ``lpp_detect`` result dict.

    Reuses ONLY signals the detector already produced (``is_flagged``, ``H_seed``,
    ``seed_labels``, ``surfaced_dims``) — no additional model-facing prompt, so
    anti-leakage is inherited from the detector.
    """
    h_seed = detect.get("H_seed")
    seed_labels = detect.get("seed_labels") or []
    surfaced = detect.get("surfaced_dims") or []
    sc_dis = baselines.self_consistency_disagreement(seed_labels)
    return {
        "lpp_gated": bool(detect.get("is_flagged")),
        "always": True,
        "semantic_entropy_gated": bool(
            isinstance(h_seed, (int, float)) and h_seed > tau_s
        ),
        "self_consistency_gated": bool(sc_dis is not None and sc_dis > 0.0),
        "requirements_probing_gated": baselines.requirements_probing_flag(surfaced),
    }


# ── H-B2' oracle construction (gold enters ONLY here — evaluation-time) ───────

def i0_gold_signature(task: Any) -> Optional[Any]:
    """The executable I0 (target) gold RESULT signature from the benchmark.

    Derived from the benchmark's ENUMERATED interpretation gold (via
    ``lps_gold._interpretation_signatures`` → ``bench.<domain>.get_checkers_and_
    candidates``), NOT from the model. Diagnostic/provenance only — recorded on the
    checkpoint so the report can confirm the oracle corresponds to I0. Returns None
    if the item exposes no evaluable I0 gold.
    """
    try:
        sigs = gold._interpretation_signatures(task)
    except (ValueError, KeyError, RuntimeError):
        return None
    return sigs.get("I0")


def oracle_clarification_text(task: Any) -> str:
    """The deleted-axis GOLD convention, framed as a simulated-user clarification.

    Source (benchmark gold, NOT the model): ``task.latent_spec`` is the frozen
    benchmark's FULL intended specification — i.e. the I0 convention on the deleted
    axis — and ``task.key_questions`` name that axis. Both are supplied ONLY here,
    in the oracle re-ask (an evaluation-time controlled oracle), NEVER in any
    detector / surfacing / clarify-decision prompt (anti-leakage).
    """
    convention = (task.latent_spec or "").strip()
    if task.key_questions:
        axis = "; ".join(q.strip() for q in task.key_questions if q.strip())
        return (
            f"{ORACLE_PREFIX} regarding {axis} — the intended specification is as "
            f"follows. {convention}"
        )
    return f"{ORACLE_PREFIX} the intended specification is as follows. {convention}"


def baseline_answer_prompt(task: Any) -> str:
    """Never-clarify committed-answer prompt: the SAME generic answer prompt the
    detector/confirmatory path uses (``task.prompt`` + frozen answer contract). No
    gold — comparable to the silent-convergence baseline."""
    return lps._with_contract(task.prompt, task.domain)


def oracle_answer_prompt(task: Any) -> str:
    """Oracle re-ask prompt: the generic answer prompt with the gold convention
    appended as a simulated-user clarification (the ONLY gold-bearing prompt)."""
    body = f"{task.prompt}\n\n{oracle_clarification_text(task)}"
    return lps._with_contract(body, task.domain)


# ── Job enumeration ──────────────────────────────────────────────────────────

def enumerate_jobs(
    tasks: List[Any], models: List[str], seed_bases: List[int]
) -> List[Dict[str, Any]]:
    """Every (item × model × seed) cell (no network). Order: item→model→seed."""
    jobs: List[Dict[str, Any]] = []
    for task in tasks:
        for model in models:
            for seed_base in seed_bases:
                jobs.append({
                    "task_id": task.id,
                    "model": model,
                    "seed_base": int(seed_base),
                    "regime": task.regime,
                    "ambiguity_level": task.ambiguity_level,
                })
    return jobs


def run_fingerprint(
    *,
    models: List[str],
    seed_bases: List[int],
    k: int,
    tau: float,
    tau_s: float,
) -> Dict[str, Any]:
    """Canonical run fingerprint (resume guard) incl. models + seeds.

    Captures every knob whose change makes previously-recorded H_seed/H_ctx/answer
    labels incompatible: intervention version, method version, k, τ, τ_s, the full
    MODEL list AND the full SEED list. On resume, records whose fingerprint differs
    are refused.
    """
    return {
        "intervention_version": INTERVENTION_VERSION,
        "method_version": lps.METHOD_VERSION,
        "k": int(k),
        "tau": float(tau),
        "tau_s": float(tau_s),
        "models": sorted(models),
        "seed_bases": sorted(int(s) for s in seed_bases),
    }


# ── Core per-cell computation ────────────────────────────────────────────────

def compute_cell(
    task: Any,
    client: Any,
    model: str,
    seed_base: int,
    *,
    k: int,
    tau: float,
    tau_s: float,
    stratum: str,
) -> Dict[str, Any]:
    """Compute one (item, model, seed) intervention record (LIVE — issues calls).

    1. ``lpp_detect`` → H-B1' clarify decisions (all policies).
    2. H-B2' (AMB+ only): never-clarify baseline answer + oracle-resolved answer,
       each labeled by the frozen executable labeler.
    """
    detect = lps.lpp_detect(
        task, client, model, tau=tau, tau_s=tau_s, k=k, base_seed=seed_base
    )
    clarify = clarify_decisions(detect, tau_s=tau_s)

    b2: Optional[Dict[str, Any]] = None
    if stratum == gold.STRATUM_AMB_POS:
        b_seed = seed_base + _BASELINE_SEED_OFFSET
        o_seed = seed_base + _ORACLE_SEED_OFFSET
        baseline_text = lps._complete_text(
            client, prompt=baseline_answer_prompt(task), model=model,
            seed=b_seed, temperature=0.0,
        )
        oracle_text = lps._complete_text(
            client, prompt=oracle_answer_prompt(task), model=model,
            seed=o_seed, temperature=0.0,
        )
        baseline_label = lps._label_answer(
            baseline_text, task, model_id=model, seed=b_seed
        )
        oracle_label = lps._label_answer(
            oracle_text, task, model_id=model, seed=o_seed
        )
        b2 = {
            "baseline_label": baseline_label,
            "oracle_label": oracle_label,
            "i0_gold_signature": i0_gold_signature(task),
        }

    return {
        "task_id": task.id,
        "model": model,
        "seed_base": seed_base,
        "domain": task.domain,
        "regime": task.regime,
        "ambiguity_level": task.ambiguity_level,
        "stratum": stratum,
        "H_seed": detect.get("H_seed"),
        "H_ctx_max": detect.get("H_ctx_max"),
        "is_flagged": detect.get("is_flagged"),
        "flagged_dimension": detect.get("flagged_dimension"),
        "n_surfaced_dims": len(detect.get("surfaced_dims") or []),
        "seed_labels": detect.get("seed_labels"),
        "clarify": clarify,
        "b2": b2,
    }


# ── Core run ─────────────────────────────────────────────────────────────────

def run(
    tasks: List[Any],
    cfg: Dict[str, Any],
    *,
    models: Optional[List[str]] = None,
    seed_bases: Optional[List[int]] = None,
    checkpoint_path: str = CHECKPOINT,
    cache_dir: str = CACHE_DIR,
    rpm: int = RPM,
    k: int = lps.DEFAULT_K,
    tau: float = TAU,
    tau_s: float = TAU_S,
    dry_run: bool = False,
    offline: bool = False,
    budget_usd: Optional[float] = None,
    _client_override: Optional[Any] = None,
) -> Dict[str, Any]:
    """Run (or dry-run) the intervention grid. Offline-test-friendly.

    On dry_run: returns ``{status, total, jobs}`` with no network. Otherwise
    computes, per (item, model, seed), the H-B1' clarify decisions + the H-B2'
    baseline/oracle answers, appending each as a JSON line to ``checkpoint_path``
    (resumable, fingerprint-guarded).
    """
    if models is None:
        models = list(DEFAULT_MODELS)
    if seed_bases is None:
        seed_bases = list(DEFAULT_SEED_BASES)

    jobs = enumerate_jobs(tasks, models, seed_bases)

    if dry_run:
        return {"status": "dry_run", "total": len(jobs), "jobs": jobs}

    _validate_output_paths(checkpoint_path, cache_dir)

    cp = Path(checkpoint_path)
    cp.parent.mkdir(parents=True, exist_ok=True)

    fingerprint = run_fingerprint(
        models=models, seed_bases=seed_bases, k=k, tau=tau, tau_s=tau_s
    )

    done: set = set()
    results: List[Dict[str, Any]] = []
    if cp.exists():
        with cp.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if rec.get("_header"):
                    continue
                rec_fp = rec.get("_fingerprint")
                if rec_fp != fingerprint:
                    raise RuntimeError(
                        "LPS-intervention checkpoint fingerprint mismatch — "
                        "refusing to reuse incompatible results.\n"
                        f"  checkpoint: {checkpoint_path}\n"
                        f"  record (task={rec.get('task_id')}, "
                        f"model={rec.get('model')}, seed={rec.get('seed_base')}) "
                        f"fingerprint: {rec_fp}\n"
                        f"  current run fingerprint: {fingerprint}\n"
                        "Delete/namespace the checkpoint before re-running with a "
                        "different roster/seeds/k/τ/τ_s/version."
                    )
                done.add((rec.get("task_id"), rec.get("model"),
                          rec.get("seed_base")))
                results.append(rec)
    else:
        with cp.open("w", encoding="utf-8") as fh:
            fh.write(json.dumps({"_header": True,
                                 "_fingerprint": fingerprint}) + "\n")

    if _client_override is not None:
        client = _client_override
    else:
        import copy
        import registered_run as _rr
        client = _rr.build_client(
            copy.deepcopy(cfg),
            offline=offline,
            cache_dir=cache_dir,
            budget_usd=budget_usd,
            rpm=rpm,
        )

    # Gold-ambiguity stratum is EXECUTABLE + detector-independent; computed here
    # for EVALUATION routing only (which items get the H-B2' oracle path) — never
    # placed in a prompt.
    stratum_by_id = {t.id: gold.gold_ambiguity(t)["stratum"] for t in tasks}
    task_by_id = {t.id: t for t in tasks}

    completed = 0
    skipped = 0
    for job in jobs:
        key = (job["task_id"], job["model"], job["seed_base"])
        if key in done:
            skipped += 1
            continue
        task = task_by_id[job["task_id"]]
        rec = compute_cell(
            task, client, job["model"], job["seed_base"],
            k=k, tau=tau, tau_s=tau_s, stratum=stratum_by_id[job["task_id"]],
        )
        rec["_fingerprint"] = fingerprint
        with cp.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")
        results.append(rec)
        done.add(key)
        completed += 1

    return {
        "status": "ok",
        "total": len(jobs),
        "completed": completed,
        "skipped": skipped,
        "checkpoint": str(cp),
        "results": results,
    }


# ── CLI ──────────────────────────────────────────────────────────────────────

def _select_items(tasks: List[Any], item_ids: Optional[List[str]],
                  max_items: Optional[int]) -> List[Any]:
    """Optionally restrict the item set (smoke runs). Fail loud on unknown IDs."""
    if item_ids:
        by_id = {t.id: t for t in tasks}
        missing = [i for i in item_ids if i not in by_id]
        if missing:
            raise ValueError(f"Unknown --items IDs: {missing}")
        return [by_id[i] for i in item_ids]
    if max_items is not None:
        return list(tasks)[:max_items]
    return list(tasks)


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description="Study 2 LPS INTERVENTION grid (H-B1' selective clarification "
                    "+ H-B2' oracle resolution)."
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Enumerate the job count with NO network.")
    parser.add_argument("--checkpoint", default=CHECKPOINT)
    parser.add_argument("--cache-dir", default=CACHE_DIR)
    parser.add_argument("--rpm", type=int, default=RPM)
    parser.add_argument("--models", nargs="+", default=None,
                        help=f"Override model slugs (default: {DEFAULT_MODELS}). "
                             "Pilot targets gpt-5.6-sol.")
    parser.add_argument("--seeds", "--seed-bases", dest="seed_bases", nargs="+",
                        type=int, default=None,
                        help=f"Override seed bases (default: {DEFAULT_SEED_BASES}).")
    parser.add_argument("--shard-by-model", action="store_true",
                        help="Write PER-MODEL namespaced checkpoint+cache "
                             "(cp_lps_intervention__<slug>.jsonl / "
                             ".llm_cache_lps_intv__<slug>). Ignores "
                             "--checkpoint/--cache-dir.")
    parser.add_argument("--items", nargs="+", default=None,
                        help="Restrict to specific item IDs (smoke).")
    parser.add_argument("--max-items", type=int, default=None,
                        help="Restrict to the first N items (smoke).")
    parser.add_argument("--k", type=int, default=lps.DEFAULT_K)
    parser.add_argument("--budget-usd", type=float, default=None)
    args = parser.parse_args(argv)

    import registered_run as _rr
    from common.config import load_config

    tasks_all = _rr.load_tasks()
    tasks = _select_items(tasks_all, args.items, args.max_items)
    models = args.models or list(DEFAULT_MODELS)
    seed_bases = args.seed_bases or list(DEFAULT_SEED_BASES)

    n_jobs = len(tasks) * len(models) * len(seed_bases)
    print("=" * 76)
    print("STUDY 2 — LPS INTERVENTION grid (Phase 2b: H-B1' + H-B2')")
    print(f"  items={len(tasks)} (of {len(tasks_all)})  models={len(models)}  "
          f"seeds={len(seed_bases)}  k={args.k}")
    print(f"  models: {models}")
    print(f"  seed_bases: {seed_bases}")
    print(f"  operating point (FROZEN): tau={TAU}  tau_s={TAU_S}")
    print(f"  intervention_version: {INTERVENTION_VERSION}")
    print(f"  jobs = {len(tasks)} × {len(models)} × {len(seed_bases)} = {n_jobs}")
    if args.shard_by_model:
        print("  shard-by-model: ON — per-model namespaced checkpoint+cache")
        for m in models:
            print(f"    {m:<20} → {shard_checkpoint(m)}  |  {shard_cache(m)}")
    else:
        print(f"  checkpoint={args.checkpoint}  cache={args.cache_dir}")
    print("=" * 76)

    if args.dry_run:
        res = run(tasks, load_config(), models=models, seed_bases=seed_bases,
                  k=args.k, dry_run=True)
        print(f"\n[Intervention] Dry-run: {res['total']} jobs "
              f"({len(tasks)} items × {len(models)} models × "
              f"{len(seed_bases)} seeds).")
        return

    if not pilot1._live_ok():
        print("lps_intervention: skipped (RUNNER_LIVE != 1). Set RUNNER_LIVE=1 to "
              "run live (copilot_proxy, no token required).")
        sys.exit(0)
    if not pilot1._proxy_reachable():
        print("lps_intervention: skipped (copilot_proxy not reachable at "
              "http://127.0.0.1:8313). Start the proxy before running live.")
        sys.exit(0)

    cfg = load_config()

    if args.shard_by_model:
        totals = {"completed": 0, "skipped": 0, "total": 0}
        for m in models:
            r = run(
                tasks, cfg,
                models=[m], seed_bases=seed_bases,
                checkpoint_path=shard_checkpoint(m), cache_dir=shard_cache(m),
                rpm=args.rpm, k=args.k, budget_usd=args.budget_usd,
            )
            print(f"[Intervention] shard {m}: completed={r['completed']} "
                  f"skipped={r['skipped']} → {r['checkpoint']}")
            for key in totals:
                totals[key] += r[key]
        print(f"\n[Intervention] All shards: completed={totals['completed']} "
              f"skipped={totals['skipped']} total={totals['total']}")
        print("[Intervention] Analyse with: python scripts/"
              "lps_intervention_report.py --shards "
              f"'{SHARD_CHECKPOINT_GLOB}' --out files/study2_intervention_results.md")
        return

    result = run(
        tasks, cfg,
        models=models, seed_bases=seed_bases,
        checkpoint_path=args.checkpoint, cache_dir=args.cache_dir,
        rpm=args.rpm, k=args.k, budget_usd=args.budget_usd,
    )
    print(f"\n[Intervention] Result: completed={result['completed']} "
          f"skipped={result['skipped']} total={result['total']}")
    print(f"[Intervention] Checkpoint: {result['checkpoint']}")
    print("[Intervention] Analyse with: python scripts/lps_intervention_report.py "
          f"--checkpoint {args.checkpoint} "
          "--out files/study2_intervention_results.md")


if __name__ == "__main__":
    main()
