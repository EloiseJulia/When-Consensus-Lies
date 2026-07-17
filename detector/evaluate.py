"""Offline evaluation harness for the Hypothesis-Surfacing detector (Phase 3).

Implemented by: Claude / Anthropic family (implement sub-agent).

Computes, over a set of (Task, agent-label-distribution) pairs:
  * HEADLINE — false-surfacing rate on k=0 controls (pre-registered target < 10%).
  * Paired surfacing discrimination on k>=1 items: AUROC + F1 over the detector
    `score`.
  * Breakdown by regime (H1_external vs H2_derivable) and by ambiguity level k.
  * A threshold-selection routine that picks the operating point meeting the
    k=0 false-surfacing < target constraint while maximizing recall.

EVAL-TIME GROUND TRUTH: the positive/negative class for discrimination is
`task.ambiguity_level` (k=0 = negative/unambiguous control, k>=1 = positive/
underspecified). This is used ONLY to SCORE the detector — the detector itself
never sees k or the gold target (spec §5 blindness guard).

OFFLINE ONLY: pure computation over provided labels. No network / no live models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from detector.surfacing import SurfacingDetector, SurfacingResult


@dataclass
class EvalItem:
    """One evaluation unit: a Task + the agent-label distribution for a config."""

    task: object  # common.schema.Task
    labels: Sequence[str]
    per_model_samples: Optional[Mapping[str, Sequence[str]]] = None
    model_families: Optional[Sequence[str]] = None

    @property
    def k(self) -> int:
        return int(getattr(self.task, "ambiguity_level"))

    @property
    def regime(self) -> Optional[str]:
        return getattr(self.task, "regime", None)

    @property
    def is_positive(self) -> bool:
        """Eval ground truth: k>=1 items are underspecified (should surface)."""
        return self.k >= 1


def auroc(scores: Sequence[float], positives: Sequence[bool]) -> float:
    """Area under ROC via the Mann-Whitney U statistic (ties → 0.5 credit).

    Returns float('nan') when either class is empty.
    """
    pos = [s for s, p in zip(scores, positives) if p]
    neg = [s for s, p in zip(scores, positives) if not p]
    if not pos or not neg:
        return float("nan")
    wins = 0.0
    for sp in pos:
        for sn in neg:
            if sp > sn:
                wins += 1.0
            elif sp == sn:
                wins += 0.5
    return wins / (len(pos) * len(neg))


def _prf1(fired: Sequence[bool], positives: Sequence[bool]) -> Tuple[float, float, float]:
    tp = sum(1 for f, p in zip(fired, positives) if f and p)
    fp = sum(1 for f, p in zip(fired, positives) if f and not p)
    fn = sum(1 for f, p in zip(fired, positives) if not f and p)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)
          if (precision + recall) else 0.0)
    return precision, recall, f1


@dataclass
class EvalReport:
    """Result of evaluating a detector over an eval set at its threshold."""

    threshold: float
    n_items: int
    n_controls: int              # k == 0
    n_positive: int              # k >= 1
    false_surfacing_rate: float  # HEADLINE: fraction of k=0 controls that fired
    auroc: float
    precision: float
    recall: float
    f1: float
    by_regime: Dict[str, Dict[str, float]] = field(default_factory=dict)
    by_k: Dict[int, Dict[str, float]] = field(default_factory=dict)

    def meets_headline(self, target: float = 0.10) -> bool:
        return self.false_surfacing_rate < target


def _run(detector: SurfacingDetector,
         items: Sequence[EvalItem]) -> List[SurfacingResult]:
    return [
        detector.detect(
            it.task,
            labels=list(it.labels),
            per_model_samples=it.per_model_samples,
            model_families=it.model_families,
        )
        for it in items
    ]


def evaluate(detector: SurfacingDetector,
             items: Sequence[EvalItem]) -> EvalReport:
    """Evaluate `detector` over `items` at the detector's current threshold."""
    results = _run(detector, items)
    scores = [r.score for r in results]
    fired = [r.fired for r in results]
    positives = [it.is_positive for it in items]

    controls = [i for i, it in enumerate(items) if it.k == 0]
    n_controls = len(controls)
    false_surfacing_rate = (
        sum(1 for i in controls if fired[i]) / n_controls if n_controls else 0.0
    )

    precision, recall, f1 = _prf1(fired, positives)
    au = auroc(scores, positives)

    # Breakdown by regime.
    by_regime: Dict[str, Dict[str, float]] = {}
    regimes = sorted({str(it.regime) for it in items})
    for reg in regimes:
        idx = [i for i, it in enumerate(items) if str(it.regime) == reg]
        r_scores = [scores[i] for i in idx]
        r_fired = [fired[i] for i in idx]
        r_pos = [positives[i] for i in idx]
        r_ctrl = [i for i in idx if items[i].k == 0]
        p, r, f = _prf1(r_fired, r_pos)
        by_regime[reg] = {
            "n": len(idx),
            "n_controls": len(r_ctrl),
            "false_surfacing_rate": (
                sum(1 for i in r_ctrl if fired[i]) / len(r_ctrl) if r_ctrl else 0.0
            ),
            "auroc": auroc(r_scores, r_pos),
            "recall": r,
            "f1": f,
        }

    # Breakdown by k.
    by_k: Dict[int, Dict[str, float]] = {}
    ks = sorted({it.k for it in items})
    for kk in ks:
        idx = [i for i, it in enumerate(items) if it.k == kk]
        k_fired = [fired[i] for i in idx]
        fire_rate = sum(1 for f in k_fired if f) / len(idx) if idx else 0.0
        by_k[kk] = {
            "n": len(idx),
            "fire_rate": fire_rate,
            "mean_score": sum(scores[i] for i in idx) / len(idx) if idx else 0.0,
        }

    return EvalReport(
        threshold=detector.threshold,
        n_items=len(items),
        n_controls=n_controls,
        n_positive=sum(1 for p in positives if p),
        false_surfacing_rate=false_surfacing_rate,
        auroc=au,
        precision=precision,
        recall=recall,
        f1=f1,
        by_regime=by_regime,
        by_k=by_k,
    )


def select_threshold(detector: SurfacingDetector,
                     items: Sequence[EvalItem],
                     target_fpr: float = 0.10) -> float:
    """Pick the operating threshold meeting the k=0 constraint (spec §2).

    Scans candidate thresholds (the observed scores, plus a small epsilon above
    each so a score exactly equal to a control's score does not fire) and returns
    the LOWEST threshold whose k=0 control false-surfacing rate is < target_fpr,
    which maximizes recall subject to the constraint. When NO in-range threshold
    qualifies (e.g. a control scores exactly 1.0), it returns a "never fire"
    threshold slightly above 1.0 (valid because firing is `score >= threshold`
    and scores are <= 1.0). The returned threshold is thus GUARANTEED to actually
    yield the reported false-surfacing rate — it is never clamped back into a
    range that would re-fire a control (audit MAJOR 2).

    The returned threshold is NOT written back to the detector — the caller
    decides whether to adopt it.
    """
    results = _run(detector, items)
    scores = [r.score for r in results]
    control_scores = [scores[i] for i, it in enumerate(items) if it.k == 0]
    positives = [it.is_positive for it in items]

    def fpr_at(thr: float) -> float:
        if not control_scores:
            return 0.0
        return sum(1 for s in control_scores if s >= thr) / len(control_scores)

    def recall_at(thr: float) -> float:
        tp = sum(1 for s, p in zip(scores, positives) if p and s >= thr)
        n_pos = sum(1 for p in positives if p)
        return tp / n_pos if n_pos else 0.0

    eps = 1e-9
    never_fire = 1.0 + eps  # no score (<= 1.0) can reach this → fires nothing
    candidates = sorted({0.0, never_fire}
                        | {s for s in scores}
                        | {s + eps for s in scores})
    best_thr = never_fire  # guaranteed to satisfy the constraint (fires nothing)
    best_recall = -1.0
    for thr in candidates:
        if thr > never_fire:
            continue
        if fpr_at(thr) < target_fpr:
            r = recall_at(thr)
            # Prefer higher recall; tie-break to the LOWER threshold.
            if r > best_recall + 1e-12:
                best_recall = r
                best_thr = thr
    # NO clamp: returning a value > 1.0 is a legitimate never-fire operating
    # point. Clamping to 1.0 would let a control scoring exactly 1.0 re-fire.
    return best_thr
