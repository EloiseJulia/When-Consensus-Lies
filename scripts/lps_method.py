# constructed by: Claude (Anthropic) family
"""Latent-Premise Sensitivity (LPS) method — black-box, inference-only (Study 2).

# Implementer model family: Claude / Anthropic
# Auditor model family: MUST be non-Anthropic (Law 6 — cross-family requirement)

Implements the seed/context uncertainty decomposition and the Latent-Premise
Probing (LPP) detector defined in
``paper/plans/2026-07-23-study2-latent-premise-sensitivity-design.md`` (§1–§2).

Two uncertainty axes, per (item, model):
  * ``H_seed`` — semantic entropy of the answer distribution under RESAMPLING the
    SAME underspecified prompt (temperature>0, k samples). The SOTA signal.
  * ``H_ctx``  — answer dispersion under COUNTERFACTUAL PINNING of a candidate
    unstated dimension the model itself surfaced. High ``H_ctx`` ⇒ the answer
    depends on a dimension the prompt did not fix.

DANGER quadrant = high ``H_ctx`` AND low ``H_seed`` (confident latent-premise
ambiguity — the SOTA blind spot this study targets).

ANTI-LEAKAGE (inviolable, design §2/§6): every prompt the model sees is
GENERIC — it uses ONLY ``task.prompt`` (+ the coarse domain name) and, for
pinning, the model's OWN self-generated dimension/value strings. NONE of
``task.interpretations`` (id / gold_check), ``task.key_questions``,
``task.latent_spec``, or any target/foil text ever enters a prompt. The gold
axis (``key_questions``) is used ONLY for EVALUATION/reporting downstream.

"Semantic clustering" is EXACT (not embedding-approximate): each distinct
enumerated interpretation label from the FROZEN labeler
(``harness.label.label_run``) is its own semantic cluster, and ``I_perp`` is its
own cluster. Entropy is reported in BITS (log base 2).
"""

from __future__ import annotations

import json
import math
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── Repo root on sys.path (scripts/ is not a package) ────────────────────────
_SCRIPTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPTS_DIR.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from common.schema import AgentRun, Task  # noqa: E402
from harness.label import label_run  # noqa: E402  (FROZEN executable-gold labeler)


# ── Defaults (pilot-tunable; FROZEN before the confirmatory run) ─────────────
DEFAULT_K = 5              # seed-resamples for H_seed
DEFAULT_TEMPERATURE = 0.7  # resampling temperature (omitted for reasoning slugs)
DEFAULT_MAX_DIMS = 4       # cap on surfaced assumption dimensions
DEFAULT_TAU = 0.5          # H_ctx flag threshold (bits) — pilot-calibrated
DEFAULT_TAU_S = 0.5        # H_seed low-confidence ceiling (bits) — pilot-calibrated
_ROLE = "tested_agents"    # generic answering role


# ── Generic prompts (NO gold; auditor-visible verbatim) ──────────────────────

#: Assumption-surfacing prompt. Uses ONLY task.prompt + coarse domain. Asks the
#: model to name decision-relevant unstated assumptions with alternative values.
ASSUMPTION_SURFACING_TEMPLATE = (
    "You are about to answer the following {domain} task:\n"
    "----- TASK -----\n"
    "{prompt}\n"
    "----- END TASK -----\n\n"
    "Before answering, list the decision-relevant assumptions your answer would "
    "depend on that are NOT fixed by the task text above. For each assumption, "
    "give a short dimension name and 2 or 3 concrete alternative values it could "
    "plausibly take. List at most {max_dims} dimensions, most decision-relevant "
    "first.\n\n"
    "Respond with ONLY a JSON array, no prose, in exactly this shape:\n"
    "[{{\"dimension\": \"<short name>\", \"values\": [\"<v1>\", \"<v2>\"]}}]"
)

#: Counterfactual-pinning template. Appends a NEUTRAL clause built from the
#: model's OWN surfaced dimension/value strings. No gold text.
PINNING_TEMPLATE = (
    "{prompt}\n\n"
    "For this answer, assume the following resolution of an otherwise "
    "unspecified detail: {dimension} = {value}.\n"
    "Give your final answer now."
)


# ── Entropy (BITS) over exact label clusters ─────────────────────────────────

def semantic_entropy(labels: List[str]) -> float:
    """Shannon entropy (BITS) of the empirical distribution over EXACT labels.

    Each distinct label string is its own semantic cluster (``I_perp`` included).
    Returns 0.0 for an empty list or a degenerate (single-cluster) distribution.
    """
    n = len(labels)
    if n == 0:
        return 0.0
    counts = Counter(labels)
    h = 0.0
    for c in counts.values():
        p = c / n
        h -= p * math.log2(p)
    return h


# ── Labeling adapter (FROZEN labeler; gold used for LABELING only, not prompts) ─

def _label_answer(output: str, task: Task, *, model_id: str, seed: int) -> str:
    """Wrap a raw model answer in an AgentRun and label it via the frozen labeler."""
    run = AgentRun(
        task_id=task.id,
        config="lps",
        model_role=_ROLE,
        model_id=model_id,
        output=output,
        label="",
        verbalized_conf=0.0,
        logit_conf=None,
        seed=seed,
    )
    return label_run(run, task)


def _complete_text(
    client: Any,
    *,
    prompt: str,
    model: str,
    seed: int,
    temperature: Optional[float],
) -> str:
    """Call ``client.complete`` and return the completion text.

    Uses the generic answering role; the explicit ``model`` overrides role-based
    routing so a single client can sweep multiple models.
    """
    completion = client.complete(
        role=_ROLE,
        prompt=prompt,
        seed=seed,
        model=model,
        temperature=temperature,
    )
    return completion.text


# ── Stage A: H_seed (SOTA seed-resampling semantic entropy) ──────────────────

def H_seed(
    task: Task,
    client: Any,
    model: str,
    *,
    k: int = DEFAULT_K,
    temperature: float = DEFAULT_TEMPERATURE,
    base_seed: int = 0,
) -> Dict[str, Any]:
    """Semantic entropy (bits) over k resamples of the SAME underspecified prompt.

    The prompt is ``task.prompt`` verbatim — NO added text (anti-leakage trivially
    holds). k distinct samples are obtained by advancing the seed
    (``base_seed + j``); temperature>0 drives the sampling variation.

    Returns ``{"H_seed", "labels", "k"}``.
    """
    labels: List[str] = []
    for j in range(k):
        seed = base_seed + j
        text = _complete_text(
            client, prompt=task.prompt, model=model, seed=seed, temperature=temperature
        )
        labels.append(_label_answer(text, task, model_id=model, seed=seed))
    return {"H_seed": semantic_entropy(labels), "labels": labels, "k": k}


# ── Stage B: assumption surfacing (self-generated, generic) ──────────────────

def _extract_json_array(text: str) -> Optional[list]:
    """Best-effort extraction of the first top-level JSON array from model text.

    Handles ```json fences and surrounding prose. Returns a Python list or None.
    """
    if not text:
        return None
    # Strip common code fences.
    fenced = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.DOTALL)
    candidate = fenced.group(1) if fenced else None
    if candidate is None:
        # Fall back to the first balanced [...] span.
        start = text.find("[")
        if start == -1:
            return None
        depth = 0
        end = -1
        for i in range(start, len(text)):
            ch = text[i]
            if ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        if end == -1:
            return None
        candidate = text[start : end + 1]
    try:
        parsed = json.loads(candidate)
    except (json.JSONDecodeError, ValueError):
        return None
    return parsed if isinstance(parsed, list) else None


def _normalise_dims(parsed: Optional[list], *, max_dims: int) -> List[Dict[str, Any]]:
    """Coerce parsed JSON into a clean list of {dimension, values} dicts.

    Drops malformed entries, dedupes values, keeps dimensions with >= 2 values,
    and truncates to ``max_dims``.
    """
    dims: List[Dict[str, Any]] = []
    if not isinstance(parsed, list):
        return dims
    for entry in parsed:
        if not isinstance(entry, dict):
            continue
        name = entry.get("dimension")
        vals = entry.get("values")
        if not isinstance(name, str) or not name.strip():
            continue
        if not isinstance(vals, list):
            continue
        clean_vals: List[str] = []
        for v in vals:
            s = str(v).strip()
            if s and s not in clean_vals:
                clean_vals.append(s)
        if len(clean_vals) < 2:
            continue
        dims.append({"dimension": name.strip(), "values": clean_vals})
        if len(dims) >= max_dims:
            break
    return dims


def surface_assumptions(
    task: Task,
    client: Any,
    model: str,
    *,
    max_dims: int = DEFAULT_MAX_DIMS,
    seed: int = 0,
) -> List[Dict[str, Any]]:
    """Ask the model to self-generate decision-relevant unstated dimensions.

    GENERIC prompt (design §2 stage 1): uses ONLY ``task.prompt`` + ``task.domain``.
    Returns a list of ``{"dimension": str, "values": [str, ...]}`` (>= 2 values each).
    Never includes any gold/interpretation/key-question text.
    """
    prompt = ASSUMPTION_SURFACING_TEMPLATE.format(
        domain=task.domain, prompt=task.prompt, max_dims=max_dims
    )
    # Deterministic surfacing (temperature=0 style) for reproducibility.
    text = _complete_text(client, prompt=prompt, model=model, seed=seed, temperature=0.0)
    return _normalise_dims(_extract_json_array(text), max_dims=max_dims)


# ── Stage C: H_ctx (counterfactual pinning) ──────────────────────────────────

def H_ctx(
    task: Task,
    client: Any,
    model: str,
    dims: List[Dict[str, Any]],
    *,
    base_seed: int = 0,
) -> Dict[str, Any]:
    """Per-dimension semantic entropy under counterfactual pinning.

    For each surfaced dimension d_i with values {v_ij}, build a pinned prompt
    ``task.prompt ⊕ "assume d_i = v_ij"`` (model's OWN strings — no gold), answer,
    and label. ``H_ctx(d_i)`` = semantic entropy (bits) over {labels_j}.

    Returns ``{"per_dim", "H_ctx_max", "flagged_dimension"}`` where ``per_dim`` is a
    list of ``{dimension, values, labels, H_ctx}`` and ``flagged_dimension`` is the
    argmax-entropy dimension name (None if no dimensions).
    """
    per_dim: List[Dict[str, Any]] = []
    for di, dim in enumerate(dims):
        name = dim["dimension"]
        values = dim["values"]
        labels: List[str] = []
        for vj, value in enumerate(values):
            prompt = PINNING_TEMPLATE.format(
                prompt=task.prompt, dimension=name, value=value
            )
            # Distinct seed per (dim, value) so the cache never collapses cells.
            seed = base_seed + di * 100 + vj
            text = _complete_text(
                client, prompt=prompt, model=model, seed=seed, temperature=0.0
            )
            labels.append(_label_answer(text, task, model_id=model, seed=seed))
        per_dim.append(
            {
                "dimension": name,
                "values": values,
                "labels": labels,
                "H_ctx": semantic_entropy(labels),
            }
        )

    if not per_dim:
        return {"per_dim": [], "H_ctx_max": 0.0, "flagged_dimension": None}

    best = max(per_dim, key=lambda d: d["H_ctx"])
    return {
        "per_dim": per_dim,
        "H_ctx_max": best["H_ctx"],
        "flagged_dimension": best["dimension"],
    }


# ── Detector: Latent-Premise Probing (LPP) ───────────────────────────────────

def lpp_detect(
    task: Task,
    client: Any,
    model: str,
    *,
    tau: float = DEFAULT_TAU,
    tau_s: float = DEFAULT_TAU_S,
    k: int = DEFAULT_K,
    temperature: float = DEFAULT_TEMPERATURE,
    max_dims: int = DEFAULT_MAX_DIMS,
    base_seed: int = 0,
) -> Dict[str, Any]:
    """Full black-box detector: surface → pin → decompose → flag danger quadrant.

    Item is flagged AMBIGUOUS iff ``H_ctx_max >= tau`` AND ``H_seed <= tau_s``
    (the danger quadrant: answer depends on an unstated dimension yet resampling
    looks confident).

    Returns a dict with H_seed, H_ctx_max, flagged_dimension, is_flagged, plus the
    per-dimension breakdown, surfaced dims, and seed labels (for reporting/audit).
    """
    seed_res = H_seed(
        task, client, model, k=k, temperature=temperature, base_seed=base_seed
    )
    dims = surface_assumptions(
        task, client, model, max_dims=max_dims, seed=base_seed
    )
    ctx_res = H_ctx(task, client, model, dims, base_seed=base_seed)

    h_seed = seed_res["H_seed"]
    h_ctx_max = ctx_res["H_ctx_max"]
    is_flagged = bool(h_ctx_max >= tau and h_seed <= tau_s)

    return {
        "task_id": task.id,
        "model": model,
        "regime": task.regime,
        "ambiguity_level": task.ambiguity_level,
        "H_seed": h_seed,
        "H_ctx_max": h_ctx_max,
        "flagged_dimension": ctx_res["flagged_dimension"],
        "is_flagged": is_flagged,
        "tau": tau,
        "tau_s": tau_s,
        "surfaced_dims": dims,
        "per_dim": ctx_res["per_dim"],
        "seed_labels": seed_res["labels"],
    }


# ── Localization evaluation (gold axis used for REPORTING ONLY) ───────────────

_STOPWORDS = frozenset(
    """a an the of to for in on at by is are be do does which what when where how
    that this these those or and it its with as your you answer value single
    should would could may might rounded decimal places returns return function
    given between from into per each""".split()
)


def _keywords(text: str) -> set:
    """Lowercased alphanumeric tokens of length>=3, minus generic stopwords."""
    toks = re.findall(r"[a-z0-9]+", text.lower())
    return {t for t in toks if len(t) >= 3 and t not in _STOPWORDS}


def axis_match(dimension_text: str, key_questions: List[str]) -> bool:
    """Heuristic: does the surfaced dimension name overlap the true deleted axis?

    EVALUATION-ONLY (never influences any prompt). Returns True iff the surfaced
    dimension shares >= 2 salient keywords with some gold key_question, OR shares
    >= 1 keyword when that question has only one salient keyword. This is a coarse
    localization sanity check, reported honestly as such.
    """
    if not dimension_text or not key_questions:
        return False
    dim_kw = _keywords(dimension_text)
    if not dim_kw:
        return False
    for q in key_questions:
        q_kw = _keywords(q)
        if not q_kw:
            continue
        overlap = dim_kw & q_kw
        need = 1 if len(q_kw) <= 1 else 2
        if len(overlap) >= need:
            return True
    return False
