# -*- coding: utf-8 -*-
"""Pre-registered confirmatory analysis - human-reliance study (Phase 8, within-subjects redesign).

FROZEN WITH THE PRE-REGISTRATION (Law 7). Written and validated on *simulated* data BEFORE any real
data collection. Only the input data file changes at run time.

DESIGN: within-subjects, 3 display conditions (single/fake/dep) x 14 items (9 underspecified + 5
well-specified/`complete`), balanced Latin square. Underspecified items are missing a decisive
convention (appropriate response = flag); complete items state it (appropriate response = accept).
The 5 complete items break the "always-flag" set so the accept baseline is not at floor, AND enable a
discrimination check (secondary). A pilot go/no-go confirms the baseline before launch.

PRIMARY DVs & hypotheses (on UNDERSPECIFIED items; Holm across the family of 4; one-sided; FW alpha=0.05):
  H-U1a (accept):     P(accept | fake)  > P(accept | single)      -- over-reliance from consensus
  H-U1b (confidence): confidence(fake)  > confidence(single)
  H-U2a (accept):     P(accept | dep)   < P(accept | fake)        -- dependence disclosure corrects it
  H-U2b (confidence): confidence(dep)   < confidence(fake)

Confirmatory models (both cluster-robust, same engine as the power simulation):
  accept:     GEE logistic, exchangeable, participant-clustered, item fixed effects (underspecified only).
  confidence: GEE Gaussian, exchangeable, participant-clustered, item fixed effects (underspecified only).
  (An ordinal mixed model for the 1-5 confidence rating is a pre-specified sensitivity check.)

SECONDARY / exploratory (reported separately, NOT Holm-corrected):
  - DISCRIMINATION: condition x completeness interaction on accept (GEE logistic over ALL items). Over-
    reliance predicts fake shrinks the completeness slope [accept(complete)-accept(underspecified)];
    dep restores it. Ceiling-robust but lower-powered, so secondary.
  - FIRST-EXPOSURE between-subjects read (each participant's first trial only).
  - objective gap-identification by condition (underspecified & flagged trials only; conditional -> biased).

Usage:
  python preregistered_analysis.py                 # self-test on simulated data (effect + null demos)
  python preregistered_analysis.py --data real.csv # frozen analysis on real data

Real-data CSV schema (one row per completed trial; oTree custom export):
  participant_id, label, item_id, condition{single|fake|dep}, complete{0,1}, accept{0,1},
  confidence{1..5}, gap_correct{0,1 or blank}, rt_sec, order_index, group_g, lang,
  passed_comprehension, passed_attention, total_time_sec, straightline_confidence, duplicate_id,
  age_group, ai_use
"""
from __future__ import annotations
import argparse
import numpy as np
import pandas as pd
from scipy.stats import norm

CONDITIONS = ["single", "fake", "dep"]
N_ITEMS = 14
N_UNDERSPEC = 9        # item indices 0..8 underspecified, 9..13 complete (matches stimuli.py)

# ----------------------------------------------------------------- exclusions
def apply_exclusions(df: pd.DataFrame) -> pd.DataFrame:
    """Pre-specified exclusions: **attention-check failure and duplicate id only**. There is NO
    minimum-time exclusion (fast responders are kept). The comprehension check is pre-selected and is
    NOT an exclusion; confidence-straightlining is NOT an exclusion (excluding on a DV biases effects).
    total_time_sec and straightline_confidence are recorded for description only. Blanks -> kept."""
    keep = df.copy()
    def num(c):
        return pd.to_numeric(keep[c], errors="coerce")
    if "passed_attention" in keep:
        keep = keep[num("passed_attention") != 0]
    if "duplicate_id" in keep:
        keep = keep[num("duplicate_id") != 1]
    return keep

def _design(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["complete"] = pd.to_numeric(d["complete"], errors="coerce").astype(float)
    d["fake"] = (d["condition"] == "fake").astype(float)
    d["dep"] = (d["condition"] == "dep").astype(float)
    d["c_fake"] = d["complete"] * d["fake"]
    d["c_dep"] = d["complete"] * d["dep"]
    return d

def _holm(pvals: dict) -> dict:
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(items); out = {}; running = 0.0
    for i, (name, p) in enumerate(items):
        adj = min(1.0, (m - i) * p); running = max(running, adj)
        out[name] = (p, running, running < 0.05)
    return out

def _gee(y, X, groups, family):
    from statsmodels.genmod.generalized_estimating_equations import GEE
    from statsmodels.genmod.cov_struct import Exchangeable
    m = GEE(y, X, groups=groups, family=family, cov_struct=Exchangeable())
    try:
        # bias_reduced (Mancl-DeRouen): less anti-conservative with a modest number of clusters
        return m.fit(cov_type="bias_reduced")
    except Exception:
        return m.fit()   # fall back to the standard robust covariance (e.g. tiny/degenerate pilots)

def _fake_dep_contrasts(m, tag, logscale):
    """From a model with 'fake' and 'dep' terms: H-U?a fake>single (upper), H-U?b dep<fake (lower)."""
    b, V = m.params, m.cov_params()
    se_f = np.sqrt(V.loc["fake", "fake"])
    p_fake = 1 - norm.cdf(b["fake"] / se_f)                     # fake > single
    L = b["dep"] - b["fake"]
    seL = np.sqrt(V.loc["dep", "dep"] + V.loc["fake", "fake"] - 2 * V.loc["dep", "fake"])
    p_dep = norm.cdf(L / seL)                                   # dep < fake
    est_f = np.exp(b["fake"]) if logscale else b["fake"]
    est_d = np.exp(L) if logscale else L
    return (dict(p=p_fake, est=est_f, label=f"{tag} fake vs single"),
            dict(p=p_dep, est=est_d, label=f"{tag} dep vs fake"))

# ----------------------------------------------------------------- PRIMARY (underspecified items)
def analyze_primary(df: pd.DataFrame) -> dict:
    from statsmodels.genmod.families import Binomial, Gaussian
    d = _design(df)
    und = d[d["complete"] == 0].copy()
    item_dum = pd.get_dummies(und["item_id"].astype(str), prefix="it", drop_first=True).astype(float)
    X = pd.concat([pd.Series(1.0, index=und.index, name="const"), und[["fake", "dep"]], item_dum], axis=1)
    ma = _gee(und["accept"].astype(float), X, und["participant_id"], Binomial())
    mc = _gee(und["confidence"].astype(float), X, und["participant_id"], Gaussian())
    a_fake, a_dep = _fake_dep_contrasts(ma, "accept(OR)", logscale=True)
    c_fake, c_dep = _fake_dep_contrasts(mc, "confidence(diff)", logscale=False)
    return {"H-U1a": a_fake, "H-U2a": a_dep, "H-U1b": c_fake, "H-U2b": c_dep}

# ----------------------------------------------------------------- SECONDARY: discrimination interaction
def analyze_discrimination(df: pd.DataFrame) -> dict:
    from statsmodels.genmod.families import Binomial
    d = _design(df)
    item_dum = pd.get_dummies(d["item_id"].astype(str), prefix="it", drop_first=True).astype(float)
    X = pd.concat([pd.Series(1.0, index=d.index, name="const"),
                   d[["complete", "fake", "dep", "c_fake", "c_dep"]], item_dum], axis=1)
    m = _gee(d["accept"].astype(float), X, d["participant_id"], Binomial())
    b, V = m.params, m.cov_params()
    se_cf = np.sqrt(V.loc["c_fake", "c_fake"])
    p1 = norm.cdf(b["c_fake"] / se_cf)                          # fake shrinks discrimination (<0)
    L = b["c_dep"] - b["c_fake"]
    seL = np.sqrt(V.loc["c_dep", "c_dep"] + V.loc["c_fake", "c_fake"] - 2 * V.loc["c_dep", "c_fake"])
    p2 = 1 - norm.cdf(L / seL)                                  # dep restores (>0)
    return {"disc_fake(complete:fake<0)": (round(float(b["c_fake"]), 3), round(float(p1), 4)),
            "disc_dep(complete:dep-complete:fake>0)": (round(float(L), 3), round(float(p2), 4))}

def secondary(df: pd.DataFrame):
    d = _design(df)
    acc = d[d["complete"] == 0].groupby("condition", observed=True)["accept"].mean().round(3).to_dict()
    disc = (d[d["complete"] == 1].groupby("condition", observed=True)["accept"].mean()
            - d[d["complete"] == 0].groupby("condition", observed=True)["accept"].mean()).round(3).to_dict()
    first = d[pd.to_numeric(d["order_index"], errors="coerce") == 0]
    fa = first[first["complete"] == 0].groupby("condition", observed=True)["accept"].mean().round(3).to_dict()
    return acc, disc, fa, len(first)

# ----------------------------------------------------------------- pipeline
def run_confirmatory(df: pd.DataFrame) -> pd.DataFrame:
    df = apply_exclusions(df)
    res = analyze_primary(df)
    # PRIMARY confirmatory family = the two behavioral accept contrasts (Holm over 2).
    prim = ["H-U1a", "H-U2a"]
    holm = _holm({k: res[k]["p"] for k in prim})
    rows = []
    for k in prim:
        p_raw, p_adj, rej = holm[k]
        rows.append(dict(hypothesis=k, contrast=res[k]["label"], estimate=round(float(res[k]["est"]), 4),
                         p_one_sided=round(float(p_raw), 5), p_holm=round(float(p_adj), 5),
                         reject_at_05=bool(rej)))
    out = pd.DataFrame(rows)
    # SECONDARY corroboration: confidence contrasts (reported one-sided, not in the Holm family).
    print("[secondary-confidence] H-U1b", res["H-U1b"]["label"],
          "est=%.3f p=%.4f" % (res["H-U1b"]["est"], res["H-U1b"]["p"]))
    print("[secondary-confidence] H-U2b", res["H-U2b"]["label"],
          "est=%.3f p=%.4f" % (res["H-U2b"]["est"], res["H-U2b"]["p"]))
    acc, disc, fa, nfirst = secondary(df)
    print("[secondary] accept(underspecified) by condition:", acc)
    print("[secondary] discrimination [accept(complete)-accept(underspec)] by condition:", disc)
    print("[secondary] discrimination interaction (GEE):", analyze_discrimination(df))
    print(f"[secondary] first-exposure accept | underspecified by condition (N={nfirst}):", fa)
    return out

# ----------------------------------------------------------------- simulator (demo / frozen reference)
def simulate(N=65, seed=0,
             b0=-0.41, b_complete=2.14, b_fake=0.81, b_dep=0.0, b_cfake=-0.81, b_cdep=0.0,
             sd_u=0.6, sd_i=0.5,
             c0=3.0, c_complete=1.2, c_fake=0.7, c_dep=0.0, c_cfake=-0.7, c_cdep=0.0,
             c_sd_u=0.5, c_sd_i=0.3, c_resid=0.8) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    comp_flag = np.array([0] * N_UNDERSPEC + [1] * (N_ITEMS - N_UNDERSPEC))
    ids = [f"{'U' if c == 0 else 'C'}{i}" for i, c in enumerate(comp_flag)]
    u = rng.normal(0, sd_u, N); it = rng.normal(0, sd_i, N_ITEMS)
    cu = rng.normal(0, c_sd_u, N); ci = rng.normal(0, c_sd_i, N_ITEMS)
    rows = []
    for pid in range(N):
        g = pid % 3
        order = list(range(N_ITEMS)); rng.shuffle(order)
        for oidx, j in enumerate(order):
            comp = comp_flag[j]; cond = CONDITIONS[(j + g) % 3]
            fk = 1 if cond == "fake" else 0; dp = 1 if cond == "dep" else 0
            eta = (b0 + b_complete * comp + b_fake * fk + b_dep * dp
                   + b_cfake * comp * fk + b_cdep * comp * dp + u[pid] + it[j])
            accept = int(rng.random() < 1 / (1 + np.exp(-eta)))
            cval = (c0 + c_complete * comp + c_fake * fk + c_dep * dp
                    + c_cfake * comp * fk + c_cdep * comp * dp + cu[pid] + ci[j])
            conf = int(np.clip(round(rng.normal(cval, c_resid)), 1, 5))
            gap = "" if (accept == 1 or comp == 1) else int(rng.random() < 0.6)
            rows.append(dict(participant_id=f"P{pid:03d}", label="", item_id=ids[j], condition=cond,
                             complete=comp, accept=accept, confidence=conf, gap_correct=gap,
                             rt_sec=round(rng.uniform(8, 40), 1), order_index=oidx, group_g=g, lang="en",
                             passed_comprehension=1, passed_attention=1,
                             total_time_sec=rng.uniform(300, 700), straightline_confidence=0,
                             duplicate_id=0, age_group=3, ai_use=3))
    return pd.DataFrame(rows)

def _print(title, res):
    print(f"\n=== {title} ===")
    with pd.option_context("display.width", 170, "display.max_columns", 20):
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
    _print("DEMO A - pre-registered effect (fake raises accept/confidence on underspecified; dep restores)",
           run_confirmatory(simulate(N=65, seed=args.seed)))
    _print("DEMO B - NULL (no condition effect)",
           run_confirmatory(simulate(N=65, seed=args.seed, b_fake=0.0, b_dep=0.0, b_cfake=0.0, b_cdep=0.0,
                                     c_fake=0.0, c_dep=0.0, c_cfake=0.0, c_cdep=0.0)))

if __name__ == "__main__":
    main()
