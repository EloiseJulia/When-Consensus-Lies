"""Pre-registered confirmatory analysis — human-reliance study (Phase 8).

FROZEN WITH THE PRE-REGISTRATION (Law 7). Written and validated against *simulated* data
BEFORE any real data collection. Only the input data file changes at run time; the model
specifications, contrasts, directional tests, and multiplicity correction below are fixed.

Design: within-subjects, 3 display conditions (single / fake / dep), Latin square over 12 items.
Primary DVs:
  - accept  (1 = accept-as-is, 0 = flag-missing-info)      [behavioral]
  - confidence (0-100)                                       [subjective]
Primary directional hypotheses (Holm-corrected across the family of 4):
  H-U1a: P(accept | fake) > P(accept | single)
  H-U1b: confidence(fake)  > confidence(single)
  H-U2a: P(accept | dep)   < P(accept | fake)
  H-U2b: confidence(dep)   < confidence(fake)

Confirmatory models (frozen):
  - accept:     GEE logistic, exchangeable working correlation, clustered on participant,
                item as fixed-effect covariates. (Same engine as the pre-registered power
                simulation, so power <-> inference are consistent.) GLMM with crossed random
                intercepts is reported only as a SENSITIVITY check.
  - confidence: linear mixed model (MixedLM) with crossed random intercepts for participant
                and item.

Usage:
  python preregistered_analysis.py                 # runs on simulated data (effect + null demos)
  python preregistered_analysis.py --data real.csv # runs the frozen analysis on real data

Real-data CSV schema (one row per completed trial, AFTER exclusions):
  participant_id, item_id, condition{single|fake|dep}, accept{0,1}, confidence{0..100},
  gap_correct{0,1, or blank if accepted}, rt_sec, order_index
Plus participant-level columns used ONLY by apply_exclusions(): passed_comprehension{0,1},
  passed_attention{0,1}, total_time_sec, straightline_confidence{0,1}, duplicate_id{0,1}.
"""
from __future__ import annotations
import argparse
import numpy as np
import pandas as pd
from scipy.stats import norm

CONDITIONS = ["single", "fake", "dep"]
ALPHA = 0.05           # family-wise, Holm
N_ITEMS = 12

# ----------------------------------------------------------------------------- exclusions
def apply_exclusions(df: pd.DataFrame) -> pd.DataFrame:
    """Pre-specified participant-level exclusions (applied before analysis).

    Robust to missing/blank cells: blanks are coerced to NaN and treated as 'unknown'
    (kept), so only known rule-violations are dropped.
    """
    keep = df.copy()
    def num(col):
        return pd.to_numeric(keep[col], errors="coerce")
    if "passed_comprehension" in keep:
        keep = keep[num("passed_comprehension") != 0]
    if "passed_attention" in keep:
        keep = keep[num("passed_attention") != 0]
    if "straightline_confidence" in keep:
        keep = keep[num("straightline_confidence") != 1]
    if "duplicate_id" in keep:
        keep = keep[num("duplicate_id") != 1]
    if "total_time_sec" in keep:
        keep = keep[~(num("total_time_sec") < 120)]   # <CONFIRM> min time; NaN (unknown) kept
    return keep

# ----------------------------------------------------------------------------- helpers
def _design(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["fake"] = (d["condition"] == "fake").astype(float)
    d["dep"]  = (d["condition"] == "dep").astype(float)
    return d

def _holm(pvals: dict) -> dict:
    """Holm step-down on {name: one-sided p}. Returns {name: (p_raw, p_adj, reject)}."""
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(items); out = {}; running = 0.0
    for i, (name, p) in enumerate(items):
        adj = min(1.0, (m - i) * p)
        running = max(running, adj)            # enforce monotonicity
        out[name] = (p, running, running < ALPHA)
    return out

# ----------------------------------------------------------------------------- accept (GEE)
def analyze_accept(df: pd.DataFrame) -> dict:
    from statsmodels.genmod.generalized_estimating_equations import GEE
    from statsmodels.genmod.cov_struct import Exchangeable
    from statsmodels.genmod.families import Binomial
    d = _design(df)
    item_dum = pd.get_dummies(d["item_id"].astype(str), prefix="it", drop_first=True).astype(float)
    X = pd.concat([pd.Series(1.0, index=d.index, name="const"),
                   d[["fake", "dep"]], item_dum], axis=1)
    m = GEE(d["accept"].astype(float), X, groups=d["participant_id"],
            family=Binomial(), cov_struct=Exchangeable()).fit()
    b, V = m.params, m.cov_params()
    se_fake = np.sqrt(V.loc["fake", "fake"])
    z1 = b["fake"] / se_fake
    p_u1a = 1 - norm.cdf(z1)                                    # H-U1a: fake > single
    ci_u1a = (np.exp(b["fake"] - 1.96*se_fake), np.exp(b["fake"] + 1.96*se_fake))
    L = b["dep"] - b["fake"]
    seL = np.sqrt(V.loc["dep", "dep"] + V.loc["fake", "fake"] - 2*V.loc["dep", "fake"])
    p_u2a = norm.cdf(L / seL)                                   # H-U2a: dep < fake
    ci_u2a = (np.exp(L - 1.96*seL), np.exp(L + 1.96*seL))
    return {
        "H-U1a": dict(p=p_u1a, est=np.exp(b["fake"]), ci=ci_u1a, label="OR accept fake/single"),
        "H-U2a": dict(p=p_u2a, est=np.exp(L),         ci=ci_u2a, label="OR accept dep/fake"),
    }

# ----------------------------------------------------------------------------- confidence (MixedLM)
def analyze_confidence(df: pd.DataFrame) -> dict:
    import statsmodels.formula.api as smf
    d = df.copy()
    d["condition"] = pd.Categorical(d["condition"], categories=CONDITIONS)  # single = reference
    d["grp"] = 1
    m = smf.mixedlm("confidence ~ C(condition)", data=d, groups=d["grp"],
                    vc_formula={"pid": "0 + C(participant_id)", "item": "0 + C(item_id)"}).fit()
    b = m.fe_params
    V = m.cov_params().loc[b.index, b.index]
    c_fake, c_dep = "C(condition)[T.fake]", "C(condition)[T.dep]"
    se_fake = np.sqrt(V.loc[c_fake, c_fake]); z1 = b[c_fake] / se_fake
    p_u1b = 1 - norm.cdf(z1)                                    # H-U1b: fake > single
    ci_fake = (b[c_fake] - 1.96*se_fake, b[c_fake] + 1.96*se_fake)
    L = b[c_dep] - b[c_fake]
    seL = np.sqrt(V.loc[c_dep, c_dep] + V.loc[c_fake, c_fake] - 2*V.loc[c_dep, c_fake])
    p_u2b = norm.cdf(L / seL)                                   # H-U2b: dep < fake
    ci_L = (L - 1.96*seL, L + 1.96*seL)
    return {
        "H-U1b": dict(p=p_u1b, est=b[c_fake], ci=ci_fake, label="mean-diff confidence fake-single"),
        "H-U2b": dict(p=p_u2b, est=L,         ci=ci_L,    label="mean-diff confidence dep-fake"),
    }

# ----------------------------------------------------------------------------- secondary
def describe_gap(df: pd.DataFrame):
    flagged = df[(df["accept"] == 0) & (df["gap_correct"] != "")] if "gap_correct" in df else None
    if flagged is None or flagged.empty:
        return None
    g = flagged.copy(); g["gap_correct"] = g["gap_correct"].astype(float)
    return g.groupby("condition", observed=True)["gap_correct"].mean().to_dict()

# ----------------------------------------------------------------------------- pipeline
def run_confirmatory(df: pd.DataFrame) -> pd.DataFrame:
    df = apply_exclusions(df)
    res = {}
    res.update(analyze_accept(df))
    res.update(analyze_confidence(df))
    holm = _holm({k: v["p"] for k, v in res.items()})
    rows = []
    for k in ["H-U1a", "H-U1b", "H-U2a", "H-U2b"]:
        p_raw, p_adj, rej = holm[k]
        rows.append(dict(hypothesis=k, contrast=res[k]["label"],
                         estimate=round(float(res[k]["est"]), 4),
                         ci_lo=round(float(res[k]["ci"][0]), 4),
                         ci_hi=round(float(res[k]["ci"][1]), 4),
                         p_one_sided=round(float(p_raw), 5),
                         p_holm=round(float(p_adj), 5),
                         reject_at_05=bool(rej)))
    out = pd.DataFrame(rows)
    gap = describe_gap(df)
    if gap:
        print("[secondary] gap-identification rate by condition:",
              {k: round(v, 3) for k, v in gap.items()})
    return out

# ----------------------------------------------------------------------------- simulator (demo / frozen reference)
def simulate(N=55, seed=0, p_single=0.55, p_fake=0.72, p_dep=0.56,
             conf_single=55.0, conf_fake=66.0, conf_dep=56.0,
             sd_u=0.6, sd_i=0.5, conf_sd_u=10.0, conf_sd_i=6.0, conf_resid=14.0) -> pd.DataFrame:
    """Synthetic dataset with the real-data schema under specified true effects."""
    rng = np.random.default_rng(seed)
    def logit(p): return np.log(p / (1 - p))
    b0, bf, bd = logit(p_single), logit(p_fake) - logit(p_single), logit(p_dep) - logit(p_single)
    u  = rng.normal(0, sd_u, N);       it = rng.normal(0, sd_i, N_ITEMS)
    cu = rng.normal(0, conf_sd_u, N);  ci = rng.normal(0, conf_sd_i, N_ITEMS)
    rows = []
    for pid in range(N):
        order = np.tile(np.arange(3), int(np.ceil(N_ITEMS / 3)))[:N_ITEMS]
        rng.shuffle(order)
        for j, c in zip(range(N_ITEMS), order):
            cond = CONDITIONS[c]
            eta = b0 + (bf if c == 1 else 0) + (bd if c == 2 else 0) + u[pid] + it[j]
            accept = int(rng.random() < 1 / (1 + np.exp(-eta)))
            cbase = {"single": conf_single, "fake": conf_fake, "dep": conf_dep}[cond]
            conf = float(np.clip(rng.normal(cbase + cu[pid] + ci[j], conf_resid), 0, 100))
            gap = "" if accept == 1 else int(rng.random() < 0.6)
            rows.append(dict(participant_id=f"P{pid:03d}", item_id=f"{j+1:02d}", condition=cond,
                             accept=accept, confidence=round(conf, 1), gap_correct=gap,
                             rt_sec=round(rng.uniform(8, 40), 1), order_index=j,
                             passed_comprehension=1, passed_attention=1,
                             straightline_confidence=0, duplicate_id=0,
                             total_time_sec=rng.uniform(300, 600)))
    return pd.DataFrame(rows)

def _print(title, res):
    print(f"\n=== {title} ===")
    with pd.option_context("display.width", 160, "display.max_columns", 20):
        print(res.to_string(index=False))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", help="real-data CSV (frozen schema). If omitted, runs simulated demos.")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    if args.data:
        df = pd.read_csv(args.data, dtype={"item_id": str}, keep_default_na=False)
        _print(f"CONFIRMATORY ANALYSIS on {args.data}", run_confirmatory(df))
        return
    print("No --data given: running the FROZEN pipeline on SIMULATED data as a self-test.")
    _print("DEMO A - simulated under the pre-registered effect (expect: reject all 4)",
           run_confirmatory(simulate(N=55, seed=args.seed)))
    _print("DEMO B - simulated under the NULL (expect: reject ~none)",
           run_confirmatory(simulate(N=55, seed=args.seed, p_fake=0.55, p_dep=0.55,
                                     conf_fake=55.0, conf_dep=55.0)))

if __name__ == "__main__":
    main()
