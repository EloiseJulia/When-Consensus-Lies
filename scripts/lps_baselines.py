# constructed by: Claude (Anthropic) family
"""Baseline detection signals for the Study-2 CONFIRMATORY comparison (Phase 2a).

# Implementer model family: Claude / Anthropic
# Auditor model family: MUST be non-Anthropic (Law 6 — cross-family requirement)

The frozen pre-registration (``paper/preregistration/2026-07-23-study2-prereg-
FROZEN.md`` §3) requires that the black-box detector signal ``H_ctx-self`` is
compared, on the SAME AUROC-vs-gold-ambiguity test, against a fixed panel of
baselines that must be shown to LOSE in the danger quadrant:

  * ``H_seed`` (semantic entropy) — already implemented in ``lps_method`` and IS
    the semantic-entropy baseline; here we only READ it off a detector record.
  * ``token_logprob`` / max-token-entropy — the model's OWN answer-token
    confidence. Uses the copilot-proxy ``logit_conf`` (= exp(mean first-token
    logprobs)); only OpenAI-family slugs expose logprobs (per ``common/llm.py``),
    so Anthropic / Google models return N/A (marked, never faked).
  * ``self_consistency_agreement`` — fraction of the k seed-resamples that agree
    with the MODAL answer label (1 − normalised disagreement).
  * ``requirements_probing`` — the assumption-surfacing step WITHOUT the
    counterfactual pinning test (Yang-style): an item is flagged iff the model
    lists ≥1 decision-relevant unspecified dimension. Isolates the VALUE of the
    pinning test by removing it.

ORIENTATION (for AUROC vs gold-ambiguity, where AMB+ = positive class): every
signal here is returned ALSO as an ambiguity score where HIGHER ⇒ MORE ambiguous,
so it can be pooled with ``H_ctx-self`` in the same AUROC direction:
  * ``H_seed``                         higher ⇒ ambiguous (entropy)            ✓
  * ``token_uncertainty = 1 − conf``   higher ⇒ ambiguous (low confidence)     ✓
  * ``self_consistency_disagreement``  higher ⇒ ambiguous (answers disagree)   ✓
  * ``requirements_probing_count``     higher ⇒ ambiguous (more surfaced dims) ✓

ANTI-LEAKAGE (inviolable): every prompt a baseline issues is GENERIC. The
token-confidence baseline replays the EXACT generic base-prompt used by
``lps_method.H_seed`` (``task.prompt`` + the domain answer contract — no gold);
the requirements-probing baseline reuses the SAME generic assumption-surfacing
prompt as the detector (``lps_method.ASSUMPTION_SURFACING_TEMPLATE``). NONE of
``task.interpretations`` / ``key_questions`` / ``latent_spec`` / target / foil
text ever enters a baseline prompt. Gold is used for EVALUATION ONLY (downstream).
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

_SCRIPTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPTS_DIR.parent
for _p in (str(_REPO_ROOT), str(_SCRIPTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import lps_method as lps  # noqa: E402  (read-only reuse of the frozen detector API)


# ── 1. Semantic-entropy baseline (reuse H_seed) ──────────────────────────────

def semantic_entropy_baseline(record: Dict[str, Any]) -> Optional[float]:
    """Read the semantic-entropy signal ``H_seed`` off a detector record.

    ``H_seed`` IS the semantic-entropy baseline (already computed by
    ``lps_method.H_seed`` during ``lpp_detect``). Higher ⇒ more ambiguous.
    """
    val = record.get("H_seed")
    return float(val) if isinstance(val, (int, float)) else None


# ── 2. Token-logprob / answer-token confidence baseline ──────────────────────

def token_confidence(
    task: Any,
    client: Any,
    model: str,
    *,
    k: int = lps.DEFAULT_K,
    temperature: float = lps.DEFAULT_TEMPERATURE,
    base_seed: int = 0,
) -> Dict[str, Any]:
    """Answer-token confidence over the k generic base-prompt resamples.

    Replays the EXACT calls ``lps_method.H_seed`` makes (same generic anti-leakage
    prompt = ``task.prompt`` + domain answer contract, same seeds ``base_seed+j``,
    same temperature, same model) so that — when invoked AFTER ``lpp_detect`` on the
    SAME client — every call is a CACHE HIT (no extra token cost) and reads the
    cached ``logit_conf``.

    ``logit_conf`` (= exp(mean of the first-token logprobs) ∈ (0, 1]) is only
    populated for OpenAI-family slugs; Anthropic / Google return None. When NO
    resample yields a logprob the baseline is N/A (``available=False``).

    Returns ``{available, logit_confs, mean_confidence, uncertainty}`` where
    ``uncertainty = 1 − mean_confidence`` is the ambiguity-oriented score (higher ⇒
    more ambiguous, i.e. the model is LESS token-confident).
    """
    prompt = lps._with_contract(task.prompt, task.domain)
    confs: List[float] = []
    for j in range(k):
        seed = base_seed + j
        completion = client.complete(
            role=lps._ROLE,
            prompt=prompt,
            seed=seed,
            model=model,
            temperature=temperature,
        )
        lc = getattr(completion, "logit_conf", None)
        if isinstance(lc, (int, float)):
            confs.append(float(lc))
    if not confs:
        return {
            "available": False,
            "logit_confs": [],
            "mean_confidence": None,
            "uncertainty": None,
        }
    mean_c = sum(confs) / len(confs)
    return {
        "available": True,
        "logit_confs": confs,
        "mean_confidence": mean_c,
        "uncertainty": 1.0 - mean_c,
    }


# ── 3. Self-consistency agreement baseline ───────────────────────────────────

def self_consistency_agreement(labels: List[str]) -> Optional[float]:
    """Fraction of the k resamples agreeing with the MODAL answer label.

    ``labels`` are the FROZEN-labeler labels across the k seed resamples (the
    ``seed_labels`` field of a detector record). Returns the modal fraction in
    [1/k, 1]; None for an empty list. Higher ⇒ MORE self-consistent (LESS
    ambiguous) — this is the confidence-oriented reading.
    """
    if not labels:
        return None
    counts = Counter(labels)
    modal = max(counts.values())
    return modal / len(labels)


def self_consistency_disagreement(labels: List[str]) -> Optional[float]:
    """Ambiguity-oriented self-consistency score: ``1 − agreement``.

    Higher ⇒ MORE disagreement across resamples ⇒ MORE ambiguous. This is the
    signal pooled into the AUROC-vs-gold-ambiguity comparison (same direction as
    ``H_ctx-self`` / ``H_seed``). None for an empty label list.
    """
    agree = self_consistency_agreement(labels)
    return None if agree is None else 1.0 - agree


# ── 4. Requirements-probing baseline (surfacing WITHOUT pinning) ─────────────

def requirements_probing_count(surfaced_dims: Optional[List[Dict[str, Any]]]) -> int:
    """Number of decision-relevant unspecified dimensions the model surfaced.

    This is the assumption-surfacing step WITHOUT the counterfactual pinning test
    (Yang-style requirements probing). Reuses the dimensions already surfaced by
    the detector (``surfaced_dims`` on a record) so no extra call is needed.
    Higher ⇒ the model itself flags more missing detail ⇒ ambiguity-oriented.
    """
    return len(surfaced_dims) if surfaced_dims else 0


def requirements_probing_flag(surfaced_dims: Optional[List[Dict[str, Any]]]) -> bool:
    """Item flagged iff the model surfaced ≥1 decision-relevant dimension."""
    return requirements_probing_count(surfaced_dims) >= 1


def requirements_probing(
    task: Any,
    client: Any,
    model: str,
    *,
    max_dims: int = lps.DEFAULT_MAX_DIMS,
    seed: int = 0,
) -> Dict[str, Any]:
    """Standalone requirements-probing baseline: surface dimensions, no pinning.

    Issues ONLY the generic assumption-surfacing prompt (no gold; anti-leakage
    identical to the detector's surfacing stage) and returns
    ``{n_dims, flag, dims}``. Provided for standalone use/tests; the confirmatory
    driver instead reuses the detector's already-surfaced dims for free.
    """
    dims = lps.surface_assumptions(task, client, model, max_dims=max_dims, seed=seed)
    return {
        "n_dims": len(dims),
        "flag": len(dims) >= 1,
        "dims": dims,
    }


# ── Baseline scalars for one detector record (offline, no network) ───────────

def record_baseline_scores(record: Dict[str, Any]) -> Dict[str, Any]:
    """Extract every baseline's ambiguity-oriented scalar from a detector record.

    Uses ONLY fields already present on the record (``H_seed``, ``seed_labels``,
    ``surfaced_dims`` and, when the driver captured it, ``baselines.token_*``).
    Returns a dict of ``{signal_name: score_or_None}`` where higher ⇒ more
    ambiguous for every signal (token uncertainty, disagreement, dim count).
    """
    labels = record.get("seed_labels") or []
    surfaced = record.get("surfaced_dims") or []
    captured = record.get("baselines") or {}
    token_unc = captured.get("token_uncertainty")
    return {
        "H_seed": semantic_entropy_baseline(record),
        "token_logprob": (float(token_unc)
                          if isinstance(token_unc, (int, float)) else None),
        "self_consistency": self_consistency_disagreement(labels),
        "requirements_probing": float(requirements_probing_count(surfaced)),
    }


#: Human-readable baseline roster (order = report column order). Each entry is the
#: signal name used in ``record_baseline_scores`` + a short label.
BASELINE_ORDER = [
    ("H_seed", "semantic entropy (H_seed)"),
    ("token_logprob", "answer-token confidence (1 − logit_conf)"),
    ("self_consistency", "self-consistency disagreement"),
    ("requirements_probing", "requirements probing (# surfaced dims)"),
]
