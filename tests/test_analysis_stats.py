"""Tests for analysis.stats (Deliverable 3) — mixed effects + bootstrap.

Model family of implementer: Claude (Anthropic). Auditor: NON-Claude (GPT).

Synthetic data with a KNOWN injected effect: item-level convergent delusion
rises with ambiguity k. The mixed-effects fit must recover a POSITIVE k
coefficient whose CI excludes 0; the cluster bootstrap must cover a known metric
and respect clustering. All OFFLINE.
"""

import numpy as np
import pandas as pd

from analysis.contrasts import compute_cell_cd
from analysis.stats import bootstrap_confidence_intervals, fit_mixed_effects_model


def _synthetic_labels(df_seed: int = 0) -> pd.DataFrame:
    """Agent-level table where P(converge on wrong I1) grows with k."""
    rng = np.random.default_rng(df_seed)
    rows = []
    methods = {"single": 1, "heterogeneous-MAD": 5, "homogeneous-MAD": 5}
    for task in range(20):
        regime = "H1_external" if task % 2 == 0 else "H2_derivable"
        for k in (1, 2, 3):
            for method, n in methods.items():
                for mc in ("homogeneous", "reasoning"):
                    for seed in (0, 1):
                        base = 0.12 * k + (0.15 if method == "heterogeneous-MAD" else 0.0)
                        labels = []
                        for _ in range(n):
                            r = rng.random()
                            labels.append("I1" if r < base else
                                          ("I_perp" if r < base + 0.05 else "I0"))
                        for lab in labels:
                            rows.append(dict(
                                task=f"t{task}_k{k}", model=f"m_{mc}", regime=regime,
                                ambiguity_k=k, method=method, model_class=mc,
                                seed=seed, label=lab, target="I0"))
    return pd.DataFrame(rows)


def _cells_with_model(df: pd.DataFrame) -> pd.DataFrame:
    cells = compute_cell_cd(df)
    cells["model"] = "m_" + cells["model_class"].astype(str)
    return cells


def test_mixed_effects_recovers_positive_k_effect():
    """Item-level CD ~ ambiguity_k must recover a POSITIVE slope, CI excludes 0.

    Uses a random intercept by ``model`` (within which k varies), so the
    task-level covariate k stays identifiable. (A random intercept by ``task``
    is confounded with k here because each task has a single fixed k — that
    crossed form is exercised in :func:`test_mixed_effects_two_random_effects_runs`
    on the agent-level model where it is identifiable.)
    """
    cells = _cells_with_model(_synthetic_labels(0))
    res = fit_mixed_effects_model(cells, "cd_primary ~ ambiguity_k + (1|model)")
    assert res["status"].startswith("ok"), res["status"]
    assert "ambiguity_k" in res["coefficients"]
    coef = res["coefficients"]["ambiguity_k"]
    lo, hi = res["confidence_intervals"]["ambiguity_k"]
    assert coef > 0, f"expected positive k effect, got {coef}"
    assert lo > 0, f"CI should exclude 0 (positive), got ({lo}, {hi})"


def test_mixed_effects_two_random_effects_runs():
    """Frozen §8 crossed logistic form on the AGENT level:
    P(wrong) rises with k, fit with (1|task)+(1|model) -> positive coefficient,
    CI excludes 0 (this is the identifiable, faithful §8 primary model)."""
    df = _synthetic_labels(0)
    df["wrong"] = (df["label"] != df["target"]).astype(int)
    res = fit_mixed_effects_model(
        df, "wrong ~ ambiguity_k + (1|task) + (1|model)")
    assert res["status"].startswith("ok"), res["status"]
    assert res["family"].startswith("binomial")
    coef = res["coefficients"]["ambiguity_k"]
    lo, hi = res["confidence_intervals"]["ambiguity_k"]
    assert coef > 0 and lo > 0, f"expected positive k effect with CI>0, got {(coef, lo, hi)}"


def test_mixed_effects_binary_logistic_runs():
    """Binary `correct ~ k` fits (logistic) and returns coefficients + CIs."""
    rng = np.random.default_rng(3)
    rows = []
    for i in range(160):
        k = int(rng.integers(1, 4))
        p = 0.7 - 0.15 * k  # accuracy DROPS with k
        rows.append(dict(task=f"t{i % 20}", model=f"m{i % 4}",
                         ambiguity_k=k, correct=int(rng.random() < p)))
    data = pd.DataFrame(rows)
    res = fit_mixed_effects_model(
        data, "correct ~ ambiguity_k + (1|task) + (1|model)")
    assert res["status"].startswith("ok"), res["status"]
    assert "ambiguity_k" in res["coefficients"]
    # correctness falls with k -> negative coefficient.
    assert res["coefficients"]["ambiguity_k"] < 0
    assert "ambiguity_k" in res["confidence_intervals"]


def test_mixed_effects_degenerate_no_crash():
    cells = _cells_with_model(_synthetic_labels(0))
    res = fit_mixed_effects_model(cells.head(3), "cd_primary ~ ambiguity_k")
    assert res["status"].startswith("degenerate")
    assert res["coefficients"] == {}


def test_mixed_effects_missing_outcome_no_crash():
    cells = _cells_with_model(_synthetic_labels(0))
    res = fit_mixed_effects_model(cells, "not_a_column ~ ambiguity_k")
    assert res["status"].startswith("error")


def test_bootstrap_covers_known_metric():
    """Bootstrap point == metric on the full data; CI brackets the point."""
    df = _synthetic_labels(1)

    def mean_primary(frame: pd.DataFrame) -> float:
        cells = compute_cell_cd(frame)
        return float(cells["cd_primary"].mean()) if len(cells) else float("nan")

    truth = mean_primary(df)
    point, lo, hi = bootstrap_confidence_intervals(
        mean_primary, df, n_bootstrap=300, cluster="task", seed=5)
    assert point == truth
    assert lo <= point <= hi
    assert lo < hi  # non-degenerate interval


def test_bootstrap_respects_clustering():
    """A metric constant WITHIN each cluster but variable BETWEEN clusters has a
    wider CI under cluster resampling than under naive i.i.d. row resampling
    (i.i.d. row resampling underestimates the variance)."""
    rng = np.random.default_rng(9)
    rows = []
    # 12 clusters, each cluster's rows all share the cluster's value.
    cluster_values = rng.normal(0, 1, size=12)
    for c, val in enumerate(cluster_values):
        for _ in range(25):
            rows.append(dict(cluster=f"c{c}", y=val))
    data = pd.DataFrame(rows)

    def mean_y(frame: pd.DataFrame) -> float:
        return float(frame["y"].mean())

    _, lo_c, hi_c = bootstrap_confidence_intervals(
        mean_y, data, n_bootstrap=500, cluster="cluster", seed=1)
    _, lo_i, hi_i = bootstrap_confidence_intervals(
        mean_y, data, n_bootstrap=500, cluster=None, seed=1)
    assert (hi_c - lo_c) > (hi_i - lo_i) * 2, \
        "cluster-bootstrap CI should be much wider than i.i.d. row bootstrap"


def test_bootstrap_two_way_cluster_runs():
    """Joint (item AND model) clustering resamples and returns a finite CI."""
    df = _synthetic_labels(2)

    def mean_frozen(frame: pd.DataFrame) -> float:
        cells = compute_cell_cd(frame)
        return float(cells["cd_sensitivity_frozen"].mean()) if len(cells) else float("nan")

    point, lo, hi = bootstrap_confidence_intervals(
        mean_frozen, df, n_bootstrap=200, cluster=["task", "model_class"], seed=2)
    assert not np.isnan(point)
    assert lo <= point <= hi


def test_bootstrap_single_cluster_degrades_gracefully():
    data = pd.DataFrame({"cluster": ["only"] * 10, "y": range(10)})
    point, lo, hi = bootstrap_confidence_intervals(
        lambda f: float(f["y"].mean()), data, n_bootstrap=50, cluster="cluster")
    assert lo == point == hi  # single cluster -> no variability estimate


def test_bootstrap_reproducible():
    df = _synthetic_labels(4)

    def m(frame):
        return float(compute_cell_cd(frame)["cd_primary"].mean())

    a = bootstrap_confidence_intervals(m, df, n_bootstrap=100, cluster="task", seed=42)
    b = bootstrap_confidence_intervals(m, df, n_bootstrap=100, cluster="task", seed=42)
    assert a == b
