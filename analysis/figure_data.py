"""Figure DATA (no rendering) for the frozen §8 figure intents.

Model family of implementer: Claude (Anthropic). Auditor: NON-Claude (GPT).

matplotlib is intentionally NOT a dependency (rendering is a later slice). This
module emits the structured tables behind the frozen figure intents (prereg §8)
as pandas DataFrames / JSON-serializable dicts:

- ``phase_diagram_table``      — the rho-ambiguity phase diagram: CD by
  method x k x regime.
- ``method_ambiguity_heatmap`` — the method x ambiguity silent-failure heatmap
  (a pivot of CD by method x k).
- ``per_regime_cd``            — CD by regime (H1_external vs H2_derivable).
- ``cd_vs_k_table``            — CD as a function of ambiguity level k.

Each is reported for a chosen A04 CD variant (default ``cd_primary``); the
I_perp rate is carried alongside so the degeneracy diagnostic travels with the
figure data.
"""

from typing import Dict, List

import pandas as pd

from analysis.cd import CD_VARIANTS
from analysis.contrasts import CD_COLS, COLS, _gb, cd_vs_k, compute_cell_cd

_DEFAULT_CD = "cd_primary"


def _mean_by(cells: pd.DataFrame, group_cols: List[str]) -> pd.DataFrame:
    group_cols = [c for c in group_cols if c in cells.columns]
    if cells.empty or not group_cols:
        return pd.DataFrame(columns=group_cols + ["n_cells"] + CD_COLS)
    rows: List[Dict] = []
    for key, group in cells.groupby(_gb(group_cols), dropna=False, sort=True):
        if not isinstance(key, tuple):
            key = (key,)
        row: Dict = dict(zip(group_cols, key))
        row["n_cells"] = len(group)
        for c in CD_COLS:
            row[c] = float(group[c].mean())
        rows.append(row)
    return pd.DataFrame(rows)


def phase_diagram_table(df: pd.DataFrame) -> pd.DataFrame:
    """rho-ambiguity phase diagram data: CD by method x k x regime.

    Returns a long-form DataFrame with columns [method, ambiguity_k, regime,
    n_cells, <all CD variant columns + iperp_rate>].
    """
    cells = compute_cell_cd(df)
    return _mean_by(cells, [COLS["method"], COLS["ambiguity_k"], COLS["regime"]])


def method_ambiguity_heatmap(df: pd.DataFrame, cd_col: str = _DEFAULT_CD) -> pd.DataFrame:
    """Method x ambiguity silent-failure heatmap: pivot of CD (method x k).

    Args:
        df: Agent-level tidy table.
        cd_col: Which A04 CD variant to place in the heatmap cells.

    Returns:
        DataFrame pivot with methods as the index and ambiguity_k as columns.
    """
    if cd_col not in CD_VARIANTS and cd_col != "iperp_rate":
        raise ValueError(f"unknown cd_col {cd_col!r}; expected one of {CD_COLS}")
    cells = compute_cell_cd(df)
    method_col, k_col = COLS["method"], COLS["ambiguity_k"]
    if cells.empty or method_col not in cells.columns or k_col not in cells.columns:
        return pd.DataFrame()
    return cells.pivot_table(index=method_col, columns=k_col, values=cd_col, aggfunc="mean")


def per_regime_cd(df: pd.DataFrame) -> pd.DataFrame:
    """CD by regime (H1_external vs H2_derivable).

    Returns a DataFrame with columns [regime, n_cells, <CD columns>].
    """
    cells = compute_cell_cd(df)
    return _mean_by(cells, [COLS["regime"]])


def cd_vs_k_table(df: pd.DataFrame, h1_only: bool = False) -> pd.DataFrame:
    """CD as a function of ambiguity level k (delegates to contrasts.cd_vs_k).

    Args:
        df: Agent-level tidy table.
        h1_only: Restrict to H1_external items (default False for figure data,
            which shows both regimes).
    """
    return cd_vs_k(df, h1_only=h1_only)


def all_figure_data(df: pd.DataFrame, cd_col: str = _DEFAULT_CD) -> Dict[str, object]:
    """Bundle every figure table as JSON-serializable structures.

    Returns:
        Dict with keys ``phase_diagram``, ``method_ambiguity_heatmap``,
        ``per_regime_cd``, ``cd_vs_k`` — each a list-of-records / nested dict
        suitable for ``json.dumps``.
    """
    heatmap = method_ambiguity_heatmap(df, cd_col=cd_col)
    return {
        "phase_diagram": phase_diagram_table(df).to_dict(orient="records"),
        "method_ambiguity_heatmap": {
            "cd_variant": cd_col,
            "table": {str(k): v for k, v in heatmap.to_dict(orient="index").items()},
        },
        "per_regime_cd": per_regime_cd(df).to_dict(orient="records"),
        "cd_vs_k": cd_vs_k_table(df).to_dict(orient="records"),
    }
