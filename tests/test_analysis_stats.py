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


def test_two_way_cluster_ci_materially_wider_than_one_way():
    """BLOCKER 1 (audit): the correct two-way cluster bootstrap resamples the
    task AND model dimensions INDEPENDENTLY, so when the metric variance is
    driven mostly by the MODEL dimension, a one-way (task-only) bootstrap
    badly UNDERSTATES the CI. The buggy joint-cell resample (treating every
    (task, model) cell as an independent unit) gives a CI far too narrow and
    NOT materially wider than the one-way one — this test fails on it.
    """
    rng = np.random.default_rng(0)
    n_tasks, n_models = 15, 15
    task_eff = rng.normal(0, 0.3, n_tasks)     # small task variance
    model_eff = rng.normal(0, 1.5, n_models)   # large model variance (crossed)
    rows = []
    for i in range(n_tasks):
        for j in range(n_models):
            rows.append(dict(task=f"t{i}", model=f"m{j}",
                             y=task_eff[i] + model_eff[j] + rng.normal(0, 0.05)))
    data = pd.DataFrame(rows)
    mean_y = lambda f: float(f["y"].mean())  # noqa: E731

    _, lo1, hi1 = bootstrap_confidence_intervals(
        mean_y, data, n_bootstrap=400, cluster="task", seed=1)
    _, lo2, hi2 = bootstrap_confidence_intervals(
        mean_y, data, n_bootstrap=400, cluster=["task", "model"], seed=1)
    w_one, w_two = hi1 - lo1, hi2 - lo2
    assert w_two > 2.0 * w_one, (
        f"two-way CI ({w_two:.3f}) must be materially wider than one-way "
        f"({w_one:.3f}); the joint-cell resample bug makes it too narrow")


def test_two_way_bootstrap_preserves_task_multiplicity():
    """BLOCKER B (audit): the cluster bootstrap must relabel each sampled cluster
    OCCURRENCE with a UNIQUE id, so a task drawn twice becomes two distinct
    groups downstream. Otherwise a metric that RE-AGGREGATES by ``task`` (here
    ``compute_cell_cd``, which groups by task) merges the duplicated draws back
    into a single cell — discarding the resample multiplicity and producing a CI
    that is too NARROW.

    The metric is the mean cell CD (``compute_cell_cd`` regroups by task). With
    12 single-cell tasks split 6 CD=1 / 6 CD=0, the correct multiplicity-
    preserving bootstrap (each occurrence a distinct cell) gives a materially
    WIDER CI than the buggy regrouping (each distinct drawn task counted once).
    We compare the function's CI width to BOTH reference behaviours computed by
    hand — not to a row mean — so a regrouping implementation fails."""
    rows = []
    for t in range(12):
        lab = "I1" if t % 2 == 0 else "I0"      # I1 wrong -> CD 1 ; I0 -> CD 0
        rows.append(dict(task=f"t{t}", model="m0", regime="H1_external",
                         ambiguity_k=1, method="single", model_class="reasoning",
                         seed=0, label=lab, target="I0"))
    df = pd.DataFrame(rows)

    def metric(frame):
        cells = compute_cell_cd(frame)
        return float(cells["cd_primary"].mean()) if len(cells) else float("nan")

    _, lo, hi = bootstrap_confidence_intervals(
        metric, df, n_bootstrap=4000, cluster="task", seed=3)
    func_w = hi - lo

    # Reference behaviours over the same 6/6 split.
    cd = [1.0 if t % 2 == 0 else 0.0 for t in range(12)]
    rng = np.random.default_rng(11)
    relabel, regroup = [], []
    for _ in range(6000):
        draws = rng.integers(0, 12, size=12)
        relabel.append(np.mean([cd[i] for i in draws]))          # multiplicity kept
        regroup.append(np.mean([cd[i] for i in set(draws.tolist())]))  # merged draws

    def width(a):
        a = np.asarray(a)
        return float(np.percentile(a, 97.5) - np.percentile(a, 2.5))

    relabel_w, regroup_w = width(relabel), width(regroup)
    # The two behaviours genuinely differ (documents the bug magnitude).
    assert relabel_w - regroup_w > 0.03, (relabel_w, regroup_w)
    # The function must match the multiplicity-preserving (relabel) width ...
    assert abs(func_w - relabel_w) < 0.03, (func_w, relabel_w)
    # ... and be materially wider than the buggy regrouping width.
    assert func_w > regroup_w + 0.03, (func_w, regroup_w)


def test_crossed_gaussian_status_labeled_honestly():
    """BLOCKER 2 (audit): a TRUE crossed random-intercepts Gaussian fit must be
    labeled ``ok:crossed`` (constant top-level group + variance components for
    BOTH task and model), NOT the ambiguous ``ok`` the old nested
    ``groups=task, vc_formula={model}`` (model nested within task) returned.
    """
    rng = np.random.default_rng(0)
    models = [f"m{j}" for j in range(6)]
    task_re = {f"t{i}": rng.normal(0, 1.0) for i in range(24)}
    model_re = {m: rng.normal(0, 1.0) for m in models}
    rows = []
    for i in range(24):
        k = (i % 3) + 1
        for m in models:
            for _ in range(2):
                y = 0.2 * k + task_re[f"t{i}"] + model_re[m] + rng.normal(0, 0.5)
                rows.append(dict(task=f"t{i}", model=m, ambiguity_k=k, cd=y))
    data = pd.DataFrame(rows)
    res = fit_mixed_effects_model(data, "cd ~ ambiguity_k + (1|task) + (1|model)")
    assert res["status"] == "ok:crossed", res["status"]
    # The plain "ok" label (old nested model reported as crossed) is forbidden.
    assert res["status"] != "ok"


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
