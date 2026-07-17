"""Hypothesis-Surfacing detector (Phase 3, offline v1).

Implemented by: Claude / Anthropic family (implement sub-agent).
Cross-family (GPT) audit to follow — see paper/plans/2026-07-17-phase3-detector-plan.md.

WHAT THIS IS (spec §1):
  Hypothesis Surfacing — flag that a consensus/answer DEPENDS ON an unstated
  interpretation axis (an aleatoric fork), so a downstream decision-maker can be
  warned "this result assumes X; confirm X". The discriminating signal is
  interpretation-branch DIVERGENCE across agents, NOT agreement/confidence
  magnitude.

WHAT THIS IS NOT:
  A no-ground-truth right/wrong judge. Consensus STRENGTH cannot separate a true
  consensus from a convergent-delusion consensus, so it is never a headline
  signal here. The detector NEVER inspects which interpretation is correct
  (`Interpretation.is_target` / gold target) — it only sees the agent label
  DISTRIBUTION. Surfacing == divergence, not correctness.

AMENDMENT-04 CONSISTENCY (inviolable):
  `I_perp` is DEGENERACY (garbage / no-unique-checker), NOT a genuine
  interpretation fork. Every divergence signal counts ONLY distinct ENUMERATED
  interpretations (I0/I1/...), excluding `I_perp`. An `I_perp`-heavy or fully
  degenerate distribution therefore CANNOT fire.

OFFLINE ONLY: pure functions over label strings / AgentRun labels. No network,
no token, no live models.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Optional, Sequence

# Degeneracy sentinel from the labeler (harness/label.py) — NOT a genuine fork.
PERP_LABEL = "I_perp"


@dataclass
class SurfacingResult:
    """Output of the Hypothesis-Surfacing detector for one task/config.

    Attributes:
        task_id: The task this result is for.
        fired: True iff score >= detector threshold (surface a warning).
        score: Detection score in [0, 1] (higher = more interpretation divergence).
        diverging_axes: Human-facing "this result assumes X" axes — the task's
            key_questions surfaced when divergence is present. Empty when nothing
            diverges. Derived WITHOUT reference to the gold target.
        evidence: Per-signal breakdown + enumerated-label counts (for audit).
    """

    task_id: str
    fired: bool
    score: float
    diverging_axes: List[str] = field(default_factory=list)
    evidence: Dict[str, object] = field(default_factory=dict)


def _enumerated(labels: Sequence[str]) -> List[str]:
    """Keep only ENUMERATED interpretation labels (drop I_perp / None / blanks).

    A04: I_perp is degeneracy, never a fork, so it is excluded from EVERY
    divergence computation.
    """
    return [l for l in labels if l and l != PERP_LABEL]


def _counts(labels: Sequence[str]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for l in labels:
        out[l] = out.get(l, 0) + 1
    return out


def _normalized_entropy(labels: Sequence[str]) -> float:
    """Shannon entropy of a label multiset, normalized to [0, 1].

    Normalized by log(D) where D = number of DISTINCT labels present, so a
    perfectly even split over any number of branches → 1.0, and a single branch
    (D <= 1) → 0.0. This measures HOW DIVIDED the agents are, independent of how
    many branches theoretically exist (and independent of the gold target).
    """
    counts = _counts(labels)
    distinct = len(counts)
    if distinct <= 1:
        return 0.0
    n = sum(counts.values())
    ent = 0.0
    for c in counts.values():
        p = c / n
        ent -= p * math.log(p)
    return ent / math.log(distinct)


def _branch_divergence(labels: Sequence[str]) -> float:
    """Signal 1 — interpretation-branch divergence over ENUMERATED labels.

    Entropy of the enumerated-label distribution (I_perp excluded per A04). A
    single enumerated branch (or an all-I_perp / empty distribution) → 0.0.
    """
    return _normalized_entropy(_enumerated(labels))


def _instability(per_model_samples: Optional[Mapping[str, Sequence[str]]]) -> Optional[float]:
    """Signal 2 — sampling-induced label instability (same model, temp>0).

    For each model that produced >= 2 ENUMERATED samples, measure whether the
    interpretation label FLIPS across resamples (normalized entropy of that
    model's enumerated samples). Average across such models. Returns None when
    no model has enough enumerated resamples (signal unavailable).
    """
    if not per_model_samples:
        return None
    per_model_scores: List[float] = []
    for _model, samples in per_model_samples.items():
        enum = _enumerated(samples)
        if len(enum) >= 2:
            per_model_scores.append(_normalized_entropy(enum))
    if not per_model_scores:
        return None
    return sum(per_model_scores) / len(per_model_scores)


def _cross_model(labels: Sequence[str],
                 model_families: Optional[Sequence[str]]) -> Optional[float]:
    """Signal 3 — cross-model (cross-family) label disagreement.

    Different model FAMILIES landing on DIFFERENT enumerated interpretations is
    the fake-redundancy tell: homogeneous agreement is uninformative, cross-model
    divergence reveals the fork. For each family, take its modal ENUMERATED label;
    return the normalized entropy across those family-modal labels. Returns None
    when fewer than 2 families carry an enumerated label (signal unavailable).
    """
    if not model_families:
        return None
    if len(model_families) != len(labels):
        raise ValueError(
            "model_families must be aligned 1:1 with labels "
            f"(got {len(model_families)} families for {len(labels)} labels)"
        )
    by_family: Dict[str, List[str]] = {}
    for fam, lab in zip(model_families, labels):
        by_family.setdefault(fam, []).append(lab)
    family_modals: List[str] = []
    for _fam, labs in by_family.items():
        enum = _enumerated(labs)
        if not enum:
            continue  # family produced only degeneracy → no enumerated vote
        counts = _counts(enum)
        # Deterministic modal pick: highest count, tie broken by label string.
        modal = max(sorted(counts), key=lambda k: counts[k])
        family_modals.append(modal)
    if len(family_modals) < 2:
        return None
    return _normalized_entropy(family_modals)


class SurfacingDetector:
    """Offline Hypothesis-Surfacing detector over interpretation-label distributions.

    The detector combines up to three DIVERGENCE signals — all computed on the
    interpretation-LABEL distribution (never consensus strength, never the gold
    target):
        (1) interpretation-branch divergence   (always available)
        (2) sampling-induced label instability  (if per-model resamples given)
        (3) cross-model label disagreement       (if model families given)
    into `score` ∈ [0, 1]. `fire` = score >= threshold. Signals lacking data are
    dropped and the remaining weights renormalized, so a divergence-only call
    reduces to signal (1).

    The `threshold` is a free PARAMETER calibrated (see detector/evaluate.py
    `select_threshold`) so the k=0 control false-surfacing rate < 10% (spec §2).
    """

    def __init__(self,
                 threshold: float = 0.30,
                 w_divergence: float = 0.50,
                 w_instability: float = 0.25,
                 w_cross_model: float = 0.25) -> None:
        if not (0.0 <= threshold <= 1.0):
            raise ValueError(f"threshold must be in [0, 1], got {threshold}")
        for name, w in (("w_divergence", w_divergence),
                        ("w_instability", w_instability),
                        ("w_cross_model", w_cross_model)):
            if w < 0:
                raise ValueError(f"{name} must be non-negative, got {w}")
        if w_divergence <= 0:
            raise ValueError("w_divergence must be > 0 (signal 1 is always present)")
        self.threshold = threshold
        self.w_divergence = w_divergence
        self.w_instability = w_instability
        self.w_cross_model = w_cross_model

    # ── input normalization ────────────────────────────────────────────────
    @staticmethod
    def _resolve_labels(labels: Optional[Sequence[str]],
                        agent_runs) -> List[str]:
        """Accept explicit label strings OR AgentRuns (use their .label)."""
        if labels is not None and agent_runs is not None:
            raise ValueError("Pass either labels or agent_runs, not both")
        if labels is not None:
            return list(labels)
        if agent_runs is not None:
            return [r.label for r in agent_runs]
        raise ValueError("Provide labels or agent_runs")

    # ── scoring ────────────────────────────────────────────────────────────
    def detect(self,
               task,
               labels: Optional[Sequence[str]] = None,
               agent_runs=None,
               per_model_samples: Optional[Mapping[str, Sequence[str]]] = None,
               model_families: Optional[Sequence[str]] = None) -> SurfacingResult:
        """Run the detector for one task under one config.

        Args:
            task: A `common.schema.Task` (used ONLY for id + key_questions; the
                gold target is never inspected).
            labels: Interpretation labels (one per agent), e.g. ["I0","I1",...].
            agent_runs: Alternatively, AgentRuns whose `.label` is used.
            per_model_samples: Optional {model_key: [labels across resamples]}
                for the instability signal (same model, temperature>0).
            model_families: Optional family tag per label (aligned with `labels`)
                for the cross-model signal.

        Returns:
            SurfacingResult(task_id, fired, score, diverging_axes, evidence).
        """
        label_list = self._resolve_labels(labels, agent_runs)

        s_div = _branch_divergence(label_list)
        s_inst = _instability(per_model_samples)
        s_cross = _cross_model(label_list, model_families)

        # Weighted combine over AVAILABLE signals (renormalized).
        num = self.w_divergence * s_div
        den = self.w_divergence
        if s_inst is not None:
            num += self.w_instability * s_inst
            den += self.w_instability
        if s_cross is not None:
            num += self.w_cross_model * s_cross
            den += self.w_cross_model
        score = num / den if den > 0 else 0.0
        score = max(0.0, min(1.0, score))

        fired = score >= self.threshold

        enum_labels = _enumerated(label_list)
        distinct_enum = sorted(set(enum_labels))
        # diverging_axes: surface the task's clarifying questions ONLY when there
        # is genuine enumerated divergence (>=2 distinct enumerated branches).
        diverging_axes: List[str] = []
        if len(distinct_enum) >= 2 and fired:
            diverging_axes = list(getattr(task, "key_questions", []) or [])

        evidence: Dict[str, object] = {
            "n_agents": len(label_list),
            "label_counts": _counts(label_list),
            "enumerated_label_counts": _counts(enum_labels),
            "n_distinct_enumerated": len(distinct_enum),
            "distinct_enumerated": distinct_enum,
            "n_perp": sum(1 for l in label_list if l == PERP_LABEL),
            "signal_divergence": s_div,
            "signal_instability": s_inst,
            "signal_cross_model": s_cross,
            "score": score,
            "threshold": self.threshold,
        }

        return SurfacingResult(
            task_id=getattr(task, "id", ""),
            fired=fired,
            score=score,
            diverging_axes=diverging_axes,
            evidence=evidence,
        )

    def score(self,
              task,
              labels: Optional[Sequence[str]] = None,
              agent_runs=None,
              per_model_samples: Optional[Mapping[str, Sequence[str]]] = None,
              model_families: Optional[Sequence[str]] = None) -> float:
        """Convenience: the detection score in [0, 1]."""
        return self.detect(task, labels, agent_runs,
                           per_model_samples, model_families).score

    def fire(self,
             task,
             labels: Optional[Sequence[str]] = None,
             agent_runs=None,
             per_model_samples: Optional[Mapping[str, Sequence[str]]] = None,
             model_families: Optional[Sequence[str]] = None) -> bool:
        """Convenience: score >= threshold."""
        return self.detect(task, labels, agent_runs,
                          per_model_samples, model_families).fired
