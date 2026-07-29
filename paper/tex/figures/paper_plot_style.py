"""Shared publication style (paper-figure skill spec).
Serif (Times), font 10, no top/right spines, vector PDF, no chart junk,
colorblind-safe (Okabe-Ito). No titles inside figures (captions live in LaTeX).
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

FONT_SIZE = 10
DPI = 300
FIG_DIR = "."

matplotlib.rcParams.update({
    "font.size": FONT_SIZE,
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
    "axes.labelsize": FONT_SIZE,
    "axes.titlesize": FONT_SIZE + 1,
    "xtick.labelsize": FONT_SIZE - 1,
    "ytick.labelsize": FONT_SIZE - 1,
    "legend.fontsize": FONT_SIZE - 1,
    "figure.dpi": DPI,
    "savefig.dpi": DPI,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.05,
    "axes.grid": False,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "text.usetex": False,
    "mathtext.fontset": "stix",
    "pdf.fonttype": 42,
})

# Okabe-Ito colorblind-safe palette
CB = {
    "blue":   "#0072B2",
    "orange": "#D55E00",
    "green":  "#009E73",
    "gray":   "#7F7F7F",
    "sky":    "#56B4E9",
    "amber":  "#E69F00",
    "pink":   "#CC79A7",
    "ink":    "#222222",
}

def save_fig(fig, name):
    fig.savefig(f"{FIG_DIR}/{name}.pdf")
    fig.savefig(f"{FIG_DIR}/{name}.png", dpi=200)
    print(f"saved {name}.pdf / .png")
