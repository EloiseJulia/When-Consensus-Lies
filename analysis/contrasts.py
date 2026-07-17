"""Pre-registered comparisons (contrasts) over convergent-delusion.

Model family of implementer: Claude (Anthropic). Auditor: NON-Claude (GPT).

Operates on a tidy AGENT-LEVEL table (one row per agent observation) with the
columns declared in :data:`COLS`. A "cell" is one item under one
(method x model_class x seed); convergent delusion is computed over that cell's
agent labels, then aggregated (mean over cells) for each contrast. Every
contrast is reported with ALL THREE A04 CD variants (primary + both
sensitivities) + the I_perp rate (Amendment 04 / prereg §8).

Contrasts implemented (prereg §1/§8/§9):
- ``aggregation_vs_single``      — H1a: each aggregation method vs single.
- ``cross_model_vs_homogeneous`` — ⭐ row-35 headline: heterogeneous (cross
  family, genuine convergent delusion) vs homogeneous/SC (rho->1 fake
  redundancy).
- ``cd_by_regime``               — H2: H1_external vs H2_derivable by
  model_class.
- ``cd_vs_k``                    — H1b: CD as a function of ambiguity level k.
"""

from typing import Dict, List, Optional, Sequence

import pandas as pd

from analysis.cd import CD_VARIANTS, iperp_rate

#: Canonical tidy AGENT-LEVEL column names consumed by the contrasts/figures.
COLS = {
    "item": "task",
    "method": "method",
    "model_class": "model_class",
    "seed": "seed",
    "label": "label",
    "target": "target",
    "regime": "regime",
    "ambiguity_k": "ambiguity_k",
}

#: The single-agent baseline method name (prereg configs).
SINGLE_METHOD = "single"
#: The heterogeneous cross-family aggregation method (row-35 headline).
HETEROGENEOUS_METHOD = "heterogeneous-MAD"
#: The homogeneous shared-prior aggregation method (rho->1 fake redundancy).
HOMOGENEOUS_METHOD = "homogeneous-MAD"

#: Names of the reported CD columns (three A04 variants + I_perp rate).
CD_COLS: List[str] = list(CD_VARIANTS.keys()) + ["iperp_rate"]


def _gb(cols: Sequence[str]):
    """Normalize a groupby key (scalar for a single column) to avoid the
    pandas>=3 Futurewarning about single-element list groupby keys."""
    cols = list(cols)
    return cols[0] if len(cols) == 1 else cols


def compute_cell_cd(
    df: pd.DataFrame,
    cell_cols: Optional[Sequence[str]] = None,
    carry_cols: Optional[Sequence[str]] = None,
) -> pd.DataFrame:
    """Collapse an agent-level table to one CD row per (item x config) cell.

    Groups the agent rows into cells and computes, per cell, all three A04 CD
    variants + the I_perp rate over the cell's agent labels. The item's
    ``regime`` / ``ambiguity_k`` (constant within a cell) are carried through.

    Args:
        df: Agent-level tidy table with the :data:`COLS` columns.
        cell_cols: Columns identifying a CD cell. Defaults to
            (item, method, model_class, seed).
        carry_cols: Item-level attribute columns to carry through (first value
            per cell). Defaults to (regime, ambiguity_k).

    Returns:
        DataFrame with one row per cell: the cell keys, the carried attribute
        columns, an ``n_agents`` count, and the columns in :data:`CD_COLS`.
    """
    item = COLS["item"]
    if cell_cols is None:
        cell_cols = [item, COLS["method"], COLS["model_class"], COLS["seed"]]
    else:
        cell_cols = list(cell_cols)
    if carry_cols is None:
        carry_cols = [COLS["regime"], COLS["ambiguity_k"]]
    carry_cols = [c for c in carry_cols if c in df.columns]

    label_col = COLS["label"]
    target_col = COLS["target"]

    rows: List[Dict] = []
    if df.empty:
        return pd.DataFrame(columns=list(cell_cols) + list(carry_cols) + ["n_agents"] + CD_COLS)

    present_cell_cols = [c for c in cell_cols if c in df.columns]
    # Carry columns are item-level attributes (regime, ambiguity_k). Include them
    # in the grouping key so a cell never merges rows with different attribute
    # values (in real data each task_id already fixes these; this also keeps
    # synthetic tables that reuse a task_id across k levels correct).
    group_cols = present_cell_cols + [c for c in carry_cols if c not in present_cell_cols]
    for key, group in df.groupby(group_cols, dropna=False, sort=False):
        labels = list(group[label_col])
        # target is constant within a cell; take the first.
        target = group[target_col].iloc[0]
        if not isinstance(key, tuple):
            key = (key,)
        row: Dict = dict(zip(group_cols, key))
        row["n_agents"] = len(labels)
        for name, fn in CD_VARIANTS.items():
            row[name] = fn(labels, target)
        row["iperp_rate"] = iperp_rate(labels)
        rows.append(row)

    return pd.DataFrame(rows)


def _mean_cd(cell_df: pd.DataFrame) -> Dict[str, float]:
    """Mean of each CD column over the given cells (empty -> NaNs)."""
    if cell_df.empty:
        return {c: float("nan") for c in CD_COLS}
    return {c: float(cell_df[c].mean()) for c in CD_COLS}


def _filter_h1_external(cell_df: pd.DataFrame) -> pd.DataFrame:
    regime = COLS["regime"]
    if regime in cell_df.columns:
        return cell_df[cell_df[regime] == "H1_external"]
    return cell_df


def aggregation_vs_single(
    df: pd.DataFrame,
    h1_only: bool = True,
) -> pd.DataFrame:
    """H1a contrast: each aggregation method vs the single-agent baseline.

    CD difference (method - single) for every aggregation method, reported per
    A04 CD variant + I_perp rate, pooled over items (executable-gold domains).
    By default restricted to ``H1_external`` items (prereg H1a).

    Args:
        df: Agent-level tidy table.
        h1_only: If True (default), restrict to ``regime == "H1_external"``.

    Returns:
        DataFrame indexed by method (excluding single) with columns
        ``<cd>``, ``<cd>_single``, ``delta_<cd>`` for each CD column.
    """
    cells = compute_cell_cd(df)
    if h1_only:
        cells = _filter_h1_external(cells)

    method_col = COLS["method"]
    single_cells = cells[cells[method_col] == SINGLE_METHOD]
    single_means = _mean_cd(single_cells)

    rows: List[Dict] = []
    for method, group in cells.groupby(method_col, sort=True):
        if method == SINGLE_METHOD:
            continue
        means = _mean_cd(group)
        row: Dict = {method_col: method}
        for c in CD_COLS:
            row[c] = means[c]
            row[f"{c}_single"] = single_means[c]
            row[f"delta_{c}"] = means[c] - single_means[c]
        rows.append(row)

    return pd.DataFrame(rows)


def cross_model_vs_homogeneous(
    df: pd.DataFrame,
    h1_only: bool = True,
    baselines: Sequence[str] = (HOMOGENEOUS_METHOD, "sc"),
) -> pd.DataFrame:
    """⭐ Row-35 headline: heterogeneous (cross-family) CD vs homogeneous/SC.

    The heterogeneous condition is genuine convergent delusion across families;
    the homogeneous / self-consistency conditions are the ``rho->1`` fake
    redundancy baselines. Reports the heterogeneous CD, each baseline CD, and
    the (heterogeneous - baseline) delta, per A04 variant.

    Args:
        df: Agent-level tidy table.
        h1_only: Restrict to ``H1_external`` items (default True).
        baselines: Method-name prefixes to compare against. A baseline matches
            if the method name equals it or starts with ``"<baseline>"`` (so
            ``"sc"`` matches ``"sc-k5"`` / ``"sc-k10"``).

    Returns:
        DataFrame with one row per matched baseline: columns ``baseline``,
        ``<cd>_hetero``, ``<cd>_baseline``, ``delta_<cd>`` per CD column.
    """
    cells = compute_cell_cd(df)
    if h1_only:
        cells = _filter_h1_external(cells)

    method_col = COLS["method"]
    hetero_cells = cells[cells[method_col] == HETEROGENEOUS_METHOD]
    hetero_means = _mean_cd(hetero_cells)

    def _match(method_name: str, base: str) -> bool:
        return method_name == base or str(method_name).startswith(base)

    rows: List[Dict] = []
    for base in baselines:
        base_cells = cells[cells[method_col].apply(lambda m: _match(m, base))]
        base_means = _mean_cd(base_cells)
        row: Dict = {"baseline": base}
        for c in CD_COLS:
            row[f"{c}_hetero"] = hetero_means[c]
            row[f"{c}_baseline"] = base_means[c]
            row[f"delta_{c}"] = hetero_means[c] - base_means[c]
        rows.append(row)

    return pd.DataFrame(rows)


def cd_by_regime(df: pd.DataFrame) -> pd.DataFrame:
    """H2 contrast: CD by ``regime`` x ``model_class`` (mean over cells).

    Supports the H2 ``regime x model_class`` interaction (prereg §1/§9): the
    effect should attenuate in ``H2_derivable`` and further for reasoning models.

    Returns:
        DataFrame with columns regime, model_class, ``n_cells`` and the CD
        columns (means).
    """
    cells = compute_cell_cd(df)
    regime = COLS["regime"]
    model_class = COLS["model_class"]

    group_cols = [c for c in (regime, model_class) if c in cells.columns]
    if not group_cols or cells.empty:
        return pd.DataFrame(columns=group_cols + ["n_cells"] + CD_COLS)

    rows: List[Dict] = []
    for key, group in cells.groupby(_gb(group_cols), dropna=False, sort=True):
        if not isinstance(key, tuple):
            key = (key,)
        row: Dict = dict(zip(group_cols, key))
        row["n_cells"] = len(group)
        row.update(_mean_cd(group))
        rows.append(row)
    return pd.DataFrame(rows)


def cd_vs_k(
    df: pd.DataFrame,
    by: Sequence[str] = ("model_class", "method"),
    h1_only: bool = True,
) -> pd.DataFrame:
    """H1b contrast: CD as a function of ambiguity level k.

    Args:
        df: Agent-level tidy table.
        by: Extra grouping columns (default model_class, method). Any missing
            column is silently skipped.
        h1_only: Restrict to ``H1_external`` items (default True).

    Returns:
        DataFrame with columns [ambiguity_k, *by, n_cells, <CD cols>] sorted by
        the grouping keys then k.
    """
    cells = compute_cell_cd(df)
    if h1_only:
        cells = _filter_h1_external(cells)

    k_col = COLS["ambiguity_k"]
    by_cols = [COLS.get(b, b) for b in by if COLS.get(b, b) in cells.columns]
    group_cols = ([k_col] if k_col in cells.columns else []) + by_cols
    if not group_cols or cells.empty:
        return pd.DataFrame(columns=group_cols + ["n_cells"] + CD_COLS)

    rows: List[Dict] = []
    for key, group in cells.groupby(_gb(group_cols), dropna=False, sort=True):
        if not isinstance(key, tuple):
            key = (key,)
        row: Dict = dict(zip(group_cols, key))
        row["n_cells"] = len(group)
        row.update(_mean_cd(group))
        rows.append(row)

    out = pd.DataFrame(rows)
    sort_cols = by_cols + ([k_col] if k_col in out.columns else [])
    if sort_cols:
        out = out.sort_values(sort_cols).reset_index(drop=True)
    return out
