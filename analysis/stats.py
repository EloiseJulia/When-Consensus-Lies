"""Mixed-effects models and bootstrap CIs (prereg §8).

Model family of implementer: Claude (Anthropic). Auditor: NON-Claude (GPT).

Implements the two FROZEN §8 analysis primitives:

- :func:`fit_mixed_effects_model` — statsmodels mixed-effects regression of the
  frozen §8 form ``correct ~ regime * ambiguity_k * method * model_class`` with
  crossed random intercepts by ``task`` and by ``model``. Binary outcomes
  (``correct``) use a mixed-effects logistic (Bayes variational) fit; a
  continuous outcome (the item-level ``convergent_delusion`` model) uses a
  Gaussian mixed model. Degenerate / tiny data returns a clear status instead
  of raising.
- :func:`bootstrap_confidence_intervals` — item- AND model-clustered cluster
  bootstrap of any metric over a tidy table, returning ``(point, lo, hi)`` at
  the requested confidence level.

Offline only (no network / tokens).
"""

import re
import warnings
from typing import Callable, List, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd

# Random-effect term like "(1|task)" or "( 1 | model )".
_RE_RANDOM = re.compile(r"\(\s*1\s*\|\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)")


def _parse_formula(formula: str) -> Tuple[str, str, List[str]]:
    """Split a formula into (outcome, fixed_rhs, random_group_vars).

    Strips ``(1|group)`` random-intercept terms from the RHS and returns the
    group variable names separately. Leftover ``+`` separators are cleaned up.
    """
    lhs, _, rhs = formula.partition("~")
    outcome = lhs.strip()
    groups = _RE_RANDOM.findall(rhs)
    rhs = _RE_RANDOM.sub("", rhs)
    # Clean dangling '+' left by removed random terms.
    rhs = re.sub(r"\+\s*\+", "+", rhs)
    rhs = rhs.strip().strip("+").strip()
    if not rhs:
        rhs = "1"
    return outcome, rhs, groups


def _is_binary(series: pd.Series) -> bool:
    vals = set(pd.unique(series.dropna()))
    return vals.issubset({0, 1, 0.0, 1.0, True, False}) and len(vals) > 1


def _degenerate(outcome_series: pd.Series, min_rows: int = 8) -> Optional[str]:
    """Return a status string if the data is too small / degenerate, else None."""
    n = int(outcome_series.dropna().shape[0])
    if n < min_rows:
        return f"degenerate: only {n} usable rows (<{min_rows})"
    if outcome_series.dropna().nunique() < 2:
        return "degenerate: outcome has no variance"
    return None


def fit_mixed_effects_model(
    data: pd.DataFrame,
    formula: str,
    group_vars: Optional[Sequence[str]] = None,
    family: Optional[str] = None,
) -> dict:
    """Fit a mixed-effects model (prereg §8) and return coefficients + CIs.

    Args:
        data: Tidy table with the outcome + predictor columns and the grouping
            columns (``task``, ``model``).
        formula: Patsy formula. ``(1|task)`` / ``(1|model)`` random-intercept
            terms are parsed out automatically; e.g.
            ``"correct ~ regime * ambiguity_k * method * model_class +
            (1|task) + (1|model)"`` or the item-level
            ``"convergent_delusion ~ ambiguity_k + (1|task) + (1|model)"``.
        group_vars: Override the random-intercept grouping columns. Defaults to
            those parsed from the formula (falling back to any of ``task`` /
            ``model`` present in ``data``).
        family: ``"binomial"`` (logistic) or ``"gaussian"``. Default: inferred
            from the outcome (binary -> binomial, else gaussian).

    Returns:
        Dict with keys ``coefficients`` (name -> float), ``p_values``
        (name -> float), ``confidence_intervals`` (name -> (lo, hi)),
        ``status`` (``"ok"`` / ``"ok:linear_fallback"`` / ``"degenerate: ..."``
        / ``"error: ..."``), and ``family`` (the family actually used).
    """
    empty = {"coefficients": {}, "p_values": {}, "confidence_intervals": {}}

    outcome, fixed_rhs, parsed_groups = _parse_formula(formula)
    if outcome not in data.columns:
        return {**empty, "status": f"error: outcome '{outcome}' not in data", "family": None}

    groups = list(group_vars) if group_vars is not None else parsed_groups
    groups = [g for g in groups if g in data.columns]
    if not groups:
        groups = [g for g in ("task", "model") if g in data.columns]

    work = data.copy()
    deg = _degenerate(work[outcome])
    if deg is not None:
        return {**empty, "status": deg, "family": None}

    if family is None:
        family = "binomial" if _is_binary(work[outcome]) else "gaussian"

    fixed_formula = f"{outcome} ~ {fixed_rhs}"

    if family == "binomial":
        result = _fit_binomial(work, fixed_formula, groups)
        if result is not None:
            return result
        # Fall back to a linear-probability Gaussian mixed model.
        gaussian = _fit_gaussian(work, fixed_formula, groups)
        if gaussian is None:
            return {**empty, "status": "error: both logistic and gaussian fits failed",
                    "family": "binomial"}
        gaussian["status"] = "ok:linear_fallback"
        gaussian["family"] = "gaussian(linear_probability)"
        return gaussian

    gaussian = _fit_gaussian(work, fixed_formula, groups)
    if gaussian is None:
        return {**empty, "status": "error: gaussian fit failed", "family": "gaussian"}
    return gaussian


def _fit_gaussian(data: pd.DataFrame, fixed_formula: str, groups: List[str]) -> Optional[dict]:
    """Gaussian mixed model with CROSSED random intercepts, with fallbacks.

    The prereg §8 item-level model has crossed (NOT nested) random intercepts
    by ``task`` and by ``model``. A ``MixedLM(groups=task, vc_formula={model})``
    is WRONG: it makes the model-variance component nested WITHIN each task. The
    statsmodels crossed-RE idiom is a single constant top-level group with a
    variance component for EACH grouping var:
    ``groups=<constant>``, ``vc_formula={"task": "0+C(task)", "model": ...}``.

    Mixed-effects covariance estimation can still hit a singular covariance /
    non-convergence on highly DISCRETE outcomes (common in this project's small
    synthetic cells). To stay robust while keeping the fixed-effect estimates
    valid, we degrade gracefully and record the path honestly in ``status``:

    1. ``ok:crossed`` — true crossed random intercepts for ALL grouping vars,
       reported ONLY if the fit converged with a valid covariance;
    2. ``ok:single_re:<var>`` — a single random intercept by the first var
       (used when the crossed fit fails / does not converge);
    3. ``ok:ols_cluster_fallback`` — OLS with cluster-robust SEs on the first
       grouping var (fixed-effect point estimates unchanged).

    ``status`` NEVER claims the full crossed model when a fallback actually ran.
    """
    import statsmodels.formula.api as smf

    df = data.copy()

    def _extract(res, fe_index):
        coefficients = {n: float(res.fe_params[n] if hasattr(res, "fe_params") else res.params[n])
                        for n in fe_index}
        pv_src = res.pvalues
        p_values = {n: float(pv_src[n]) for n in fe_index if n in pv_src.index}
        ci = res.conf_int()
        confidence_intervals = {
            n: (float(ci.loc[n, 0]), float(ci.loc[n, 1])) for n in fe_index if n in ci.index
        }
        return coefficients, p_values, confidence_intervals

    def _converged(res) -> bool:
        conv = getattr(res, "converged", None)
        if conv is False:
            return False
        # A valid covariance is required for trustworthy CIs.
        try:
            ci = res.conf_int()
            if not np.all(np.isfinite(np.asarray(ci, dtype=float))):
                return False
        except Exception:
            return False
        return True

    # --- Path 1: TRUE crossed random intercepts (constant top-level group) ---
    if groups:
        grp_col = "__crossed_grp__"
        i = 0
        while grp_col in df.columns:
            i += 1
            grp_col = f"__crossed_grp__{i}"
        df[grp_col] = "all"
        vc = {g: f"0 + C({g})" for g in groups}
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error")  # treat convergence warnings as failure
                model = smf.mixedlm(fixed_formula, df, groups=df[grp_col], vc_formula=vc)
                res = model.fit(reml=True, method="lbfgs")
            if _converged(res):
                fe_names = list(res.fe_params.index)
                coefficients, p_values, confidence_intervals = _extract(res, fe_names)
                return {
                    "coefficients": coefficients,
                    "p_values": p_values,
                    "confidence_intervals": confidence_intervals,
                    "status": "ok:crossed",
                    "family": "gaussian",
                }
        except Exception:
            pass

    # --- Path 2: single random intercept by the first grouping var ---
    if groups:
        primary = groups[0]
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                model = smf.mixedlm(fixed_formula, df, groups=df[primary])
                res = model.fit(reml=True, method="lbfgs")
            fe_names = list(res.fe_params.index)
            coefficients, p_values, confidence_intervals = _extract(res, fe_names)
            return {
                "coefficients": coefficients,
                "p_values": p_values,
                "confidence_intervals": confidence_intervals,
                "status": f"ok:single_re:{primary}",
                "family": "gaussian",
            }
        except Exception:
            pass

    # --- Path 3: OLS with cluster-robust SEs (fixed effects only) ---
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            ols = smf.ols(fixed_formula, df)
            if groups and groups[0] in df.columns:
                res = ols.fit(cov_type="cluster",
                              cov_kwds={"groups": df[groups[0]].astype("category").cat.codes})
                status = "ok:ols_cluster_fallback"
            else:
                res = ols.fit()
                status = "ok:ols_fallback"
        fe_names = list(res.params.index)
        coefficients, p_values, confidence_intervals = _extract(res, fe_names)
        return {
            "coefficients": coefficients,
            "p_values": p_values,
            "confidence_intervals": confidence_intervals,
            "status": status,
            "family": "gaussian",
        }
    except Exception:  # pragma: no cover - defensive
        return None


def _fit_binomial(data: pd.DataFrame, fixed_formula: str, groups: List[str]) -> Optional[dict]:
    """Mixed-effects logistic (Bayes variational) fit; None on failure."""
    try:
        from statsmodels.genmod.bayes_mixed_glm import BinomialBayesMixedGLM
        from scipy.stats import norm
    except Exception:  # pragma: no cover
        return None

    df = data.copy()
    vc_formulas = {g: f"0 + C({g})" for g in groups}
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model = BinomialBayesMixedGLM.from_formula(fixed_formula, vc_formulas, df)
            res = model.fit_vb()
    except Exception:
        return None

    names = list(model.exog_names)
    fe_mean = np.asarray(res.fe_mean)
    fe_sd = np.asarray(res.fe_sd)
    coefficients, p_values, confidence_intervals = {}, {}, {}
    for i, name in enumerate(names):
        mean = float(fe_mean[i])
        sd = float(fe_sd[i])
        coefficients[name] = mean
        lo, hi = mean - 1.96 * sd, mean + 1.96 * sd
        confidence_intervals[name] = (lo, hi)
        if sd > 0:
            z = abs(mean / sd)
            p_values[name] = float(2.0 * (1.0 - norm.cdf(z)))
        else:
            p_values[name] = float("nan")
    return {
        "coefficients": coefficients,
        "p_values": p_values,
        "confidence_intervals": confidence_intervals,
        "status": "ok",
        "family": "binomial(logistic, variational-bayes)",
    }


def bootstrap_confidence_intervals(
    metric_fn: Callable[[pd.DataFrame], float],
    data: pd.DataFrame,
    n_bootstrap: int = 1000,
    cluster: Optional[Union[str, Sequence[str]]] = None,
    seed: int = 0,
    ci: float = 0.95,
) -> Tuple[float, float, float]:
    """Cluster-bootstrap CI for a metric over a tidy table (prereg §8).

    Resamples clusters WITH REPLACEMENT and recomputes ``metric_fn`` on each
    resampled table. Supports item- and model-clustered bootstraps:

    - ``cluster=None`` -> i.i.d. row resample.
    - ``cluster="task"`` -> resample distinct task (item) clusters.
    - ``cluster="model"`` -> resample distinct model clusters.
    - ``cluster=["task", "model"]`` -> INDEPENDENT two-way cluster bootstrap:
      the task levels and the model levels are each resampled with replacement
      independently. Every sampled cluster OCCURRENCE is relabeled with a UNIQUE
      id, so a task/model drawn twice becomes two DISTINCT groups downstream —
      this preserves the resample multiplicity through any downstream cell
      aggregation (a metric that regroups by ``task`` would otherwise merge the
      duplicated draws and understate the CI). Correctly yields WIDER CIs than a
      naive joint-cell resample.

    Args:
        metric_fn: Callable taking a DataFrame and returning a float.
        data: The tidy observation table.
        n_bootstrap: Number of bootstrap replicates.
        cluster: Clustering column(s); see above.
        seed: RNG seed (reproducible).
        ci: Confidence level (default 0.95).

    Returns:
        ``(point, lo, hi)``. If the data cannot be resampled (empty / a single
        cluster), ``lo == hi == point`` (no variability estimate available).
    """
    point = float(metric_fn(data)) if len(data) else float("nan")
    if data is None or len(data) == 0:
        return (point, float("nan"), float("nan"))

    rng = np.random.default_rng(seed)
    alpha = 1.0 - ci
    lo_pct, hi_pct = 100.0 * (alpha / 2.0), 100.0 * (1.0 - alpha / 2.0)

    if cluster is None:
        n = len(data)
        idx = np.arange(n)
        stats: List[float] = []
        for _ in range(n_bootstrap):
            take = rng.choice(idx, size=n, replace=True)
            stats.append(_safe_metric(metric_fn, data.iloc[take]))
        return _summarize(point, stats, lo_pct, hi_pct)

    cluster_cols = [cluster] if isinstance(cluster, str) else list(cluster)
    cluster_cols = [c for c in cluster_cols if c in data.columns]
    if not cluster_cols:
        return (point, float("nan"), float("nan"))

    return _cluster_bootstrap(
        metric_fn, data, cluster_cols, n_bootstrap, rng, point, lo_pct, hi_pct)


def _cluster_bootstrap(metric_fn, data, cluster_cols, n_bootstrap, rng,
                       point, lo_pct, hi_pct):
    """Cluster bootstrap with UNIQUE occurrence relabeling (one- and multi-way).

    Each clustering dimension's levels are resampled with replacement
    INDEPENDENTLY (the standard multi-way / two-way cluster bootstrap). Crucially
    every sampled cluster OCCURRENCE is given a UNIQUE relabeled id in its
    cluster column, so that a task (or model) drawn twice becomes TWO distinct
    groups downstream. Without this, a metric that re-aggregates by the cluster
    id (e.g. ``compute_cell_cd`` grouping by ``task``) would merge the duplicated
    draws back into a single cell — silently discarding the resample multiplicity
    and yielding a CI that is far too narrow. Relabeling propagates the
    multiplicity through any downstream cell aggregation.

    For a single clustering column this reduces to the ordinary cluster
    bootstrap (with the same occurrence-relabeling fix). A joint (task, model)
    cell contributes its rows under every combination of the resampled
    task-occurrence x model-occurrence relabelings.
    """
    import itertools

    dim_levels = [list(pd.unique(data[c])) for c in cluster_cols]
    if all(len(lv) < 2 for lv in dim_levels):
        return (point, point, point)

    joint = data.groupby(_gb(cluster_cols), dropna=False, sort=False)
    joint_index = {}
    for key, idx in joint.groups.items():
        key_t = key if isinstance(key, tuple) else (key,)
        joint_index[key_t] = np.asarray(idx)

    n_dims = len(cluster_cols)
    stats: List[float] = []
    for _ in range(n_bootstrap):
        # Resample each dimension's levels; relabel each occurrence uniquely.
        occ = []  # per dim: list of (orig_level, new_label)
        for d, levels in enumerate(dim_levels):
            draws = rng.choice(len(levels), size=len(levels), replace=True)
            occ.append([(levels[i], f"{cluster_cols[d]}##b{j}") for j, i in enumerate(draws)])

        take_idx: List[np.ndarray] = []
        relabels: List[List[np.ndarray]] = [[] for _ in range(n_dims)]
        for combo in itertools.product(*occ):
            orig_key = tuple(o[0] for o in combo)
            idx = joint_index.get(orig_key)
            if idx is None or len(idx) == 0:
                continue
            take_idx.append(idx)
            n = len(idx)
            for d in range(n_dims):
                relabels[d].append(np.full(n, combo[d][1], dtype=object))

        if not take_idx:
            stats.append(float("nan"))
            continue
        all_idx = np.concatenate(take_idx)
        boot = data.loc[all_idx].copy()
        boot.reset_index(drop=True, inplace=True)
        for d, c in enumerate(cluster_cols):
            boot[c] = np.concatenate(relabels[d])
        stats.append(_safe_metric(metric_fn, boot))
    return _summarize(point, stats, lo_pct, hi_pct)


def _gb(cols: Sequence[str]):
    """Normalize a groupby key: a scalar for a single column, else the list.

    Avoids the pandas>=3 Futurewarning about single-element list groupby keys.
    """
    cols = list(cols)
    return cols[0] if len(cols) == 1 else cols


def _safe_metric(metric_fn: Callable[[pd.DataFrame], float], frame: pd.DataFrame) -> float:
    try:
        return float(metric_fn(frame))
    except Exception:
        return float("nan")


def _summarize(point: float, stats: List[float], lo_pct: float, hi_pct: float
               ) -> Tuple[float, float, float]:
    arr = np.asarray([s for s in stats if s is not None and not np.isnan(s)], dtype=float)
    if arr.size == 0:
        return (point, float("nan"), float("nan"))
    lo = float(np.percentile(arr, lo_pct))
    hi = float(np.percentile(arr, hi_pct))
    return (point, lo, hi)
