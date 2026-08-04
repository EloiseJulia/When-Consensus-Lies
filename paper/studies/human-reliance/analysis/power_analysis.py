# -*- coding: utf-8 -*-
"""Reproducible power + calibration simulation for the PRIMARY analysis (archived per reviewer request).
Uses the frozen simulate() and analyze_primary() so power <-> confirmatory inference are consistent.

Run:  python power_analysis.py            # ~a few minutes
"""
import sys, warnings
from collections import Counter
warnings.filterwarnings("ignore")
from preregistered_analysis import simulate, analyze_primary, _holm

KEYS = ["H-U1a", "H-U2a"]      # PRIMARY confirmatory family = the two behavioral accept contrasts
NULL_KW = dict(b_fake=0.0, b_dep=0.0, b_cfake=0.0, b_cdep=0.0,
               c_fake=0.0, c_dep=0.0, c_cfake=0.0, c_cdep=0.0)

def rejections(N, seed, null, effect_kw=None):
    kw = dict(NULL_KW) if null else dict(effect_kw or {})
    df = simulate(N=N, seed=seed, **kw)
    res = analyze_primary(df)
    holm = _holm({k: res[k]["p"] for k in KEYS})
    return {k: holm[k][2] for k in KEYS}

def grid(N, nsim, null, base_seed, effect_kw=None):
    c = Counter(); allc = anyc = 0
    for s in range(nsim):
        r = rejections(N, base_seed + s, null, effect_kw)
        for k in KEYS:
            c[k] += int(r[k])
        allc += int(all(r.values())); anyc += int(any(r.values()))
    per = {k: round(c[k] / nsim, 3) for k in KEYS}
    return per, round(allc / nsim, 3), round(anyc / nsim, 3)

def main():
    nsim = int(sys.argv[1]) if len(sys.argv) > 1 else 150
    print(f"nsim={nsim} per cell; Holm family-wise 0.05.\n")

    print("== CALIBRATION under the NULL (N=65) ==")
    per, allr, anyr = grid(65, nsim, True, base_seed=0)
    print("  per-test type-I (Holm):", per)
    print("  FWER P(reject any):", anyr, "  (should be <= ~0.05)\n")

    print("== POWER under the pre-registered effect ==")
    print("  (single/fake/dep underspecified accept ~ .40/.57/.42; confidence fake +0.7 star, dep restores)")
    for N in [50, 65, 80]:
        per, allr, anyr = grid(N, nsim, False, base_seed=100000)
        print(f"  N={N}:  per-test power={per}  P(all 4)={allr}")

    print("\n== POWER under a CONSERVATIVE effect (smaller: fake +0.5 logit / +0.45 star) ==")
    cons = dict(b_fake=0.5, b_dep=0.0, b_cfake=-0.5, b_cdep=0.0,
                c_fake=0.45, c_dep=0.0, c_cfake=-0.45, c_cdep=0.0)
    for N in [65, 90]:
        per, allr, anyr = grid(N, nsim, False, base_seed=200000, effect_kw=cons)
        print(f"  N={N}:  per-test power={per}  P(all 4)={allr}")

if __name__ == "__main__":
    main()
