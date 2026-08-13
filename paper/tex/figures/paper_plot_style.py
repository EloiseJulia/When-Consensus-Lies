"""Shared publication style for *When Consensus Lies* figures.

Serif (Times), quiet axes, colorblind-safe cohesive palette, vector PDF output.
No titles inside figures; captions live in LaTeX.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

FONT_SIZE = 10
DPI = 300
FIG_DIR = "."

# Cohesive paper palette: cool ink/blue base with restrained warm accents.
CB = {
    "ink": "#2D3748",
    "muted": "#718096",
    "gray": "#8A96A3",
    "light_gray": "#D9E0E8",
    "grid": "#E7ECF2",
    "blue": "#3B6EA5",
    "sky": "#7BA7CF",
    "deep_blue": "#244C78",
    "danger": "#D9534F",
    "orange": "#D59A2E",
    "amber": "#E3B34C",
    "green": "#2E9E7B",
    "safe": "#2E9E7B",
    "pink": "#B779A8",
    "paper": "#FFFFFF",
    "panel": "#FAFBFC",
}

STYLE_RCPARAMS = {
    "font.size": FONT_SIZE,
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
    "axes.labelsize": FONT_SIZE,
    "axes.titlesize": FONT_SIZE + 1,
    "xtick.labelsize": FONT_SIZE - 1,
    "ytick.labelsize": FONT_SIZE - 1,
    "legend.fontsize": FONT_SIZE - 1,
    "axes.edgecolor": CB["light_gray"],
    "axes.labelcolor": CB["ink"],
    "axes.linewidth": 0.75,
    "xtick.color": CB["ink"],
    "ytick.color": CB["ink"],
    "xtick.major.width": 0.7,
    "ytick.major.width": 0.7,
    "xtick.major.size": 3.0,
    "ytick.major.size": 3.0,
    "figure.dpi": DPI,
    "savefig.dpi": DPI,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.04,
    "axes.grid": False,
    "grid.color": CB["grid"],
    "grid.linewidth": 0.55,
    "grid.linestyle": "-",
    "grid.alpha": 1.0,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.facecolor": CB["paper"],
    "figure.facecolor": CB["paper"],
    "text.usetex": False,
    "mathtext.fontset": "stix",
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "lines.linewidth": 1.5,
    "lines.markersize": 5.0,
    "legend.frameon": True,
    "legend.framealpha": 0.96,
    "legend.facecolor": "#FFFFFF",
    "legend.edgecolor": CB["light_gray"],
}

matplotlib.rcParams.update(STYLE_RCPARAMS)

def apply_axes_style(ax, grid_axis="y"):
    """Apply the shared quiet axis treatment to one axes."""
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(CB["light_gray"])
        ax.spines[side].set_linewidth(0.75)
    ax.tick_params(colors=CB["ink"], width=0.7, length=3)
    ax.yaxis.label.set_color(CB["ink"])
    ax.xaxis.label.set_color(CB["ink"])
    ax.set_axisbelow(True)
    if grid_axis:
        ax.grid(True, axis=grid_axis, color=CB["grid"], linewidth=0.55, linestyle="-")
    else:
        ax.grid(False)

def style_legend(legend):
    """Style a legend consistently."""
    if legend is None:
        return None
    frame = legend.get_frame()
    frame.set_facecolor("#FFFFFF")
    frame.set_edgecolor(CB["light_gray"])
    frame.set_linewidth(0.7)
    frame.set_alpha(0.96)
    return legend

def save_fig(fig, name):
    fig.savefig(f"{FIG_DIR}/{name}.pdf")
    fig.savefig(f"{FIG_DIR}/{name}.png", dpi=200)
    print(f"saved {name}.pdf / .png")
