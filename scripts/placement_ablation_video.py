#!/usr/bin/env python3
"""Generate the "Anatomy beats symmetry" (electrode-placement) animation.

Turns paper Table 1 (static/images/paper/table_placement.png) into a 2-panel
line/curve plot, then animates the curves drawing in left-to-right (the line
analog of the bar-grow style in static/images/baselines.mp4) and encodes to
static/videos/placement_ablation.mp4 with a poster.
Run:  python3 scripts/placement_ablation_video.py
Edit the data below and re-run if Table 1 changes.
"""
import os, shutil, tempfile, subprocess, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.offsetbox import TextArea, HPacker, AnchoredOffsetbox

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIDEO_OUT = os.path.join(ROOT, "static/videos/placement_ablation.mp4")
POSTER_OUT = os.path.join(ROOT, "static/images/posters/placement_ablation.jpg")
STILL = len(sys.argv) > 1 and sys.argv[1] == "--still"

# palette (consistent with scripts/results_force_video.py)
MAE_C, RMSE_C = "#d6590b", "#0f77b4"
ARROW, INK, GRID, LBL = "#8b0000", "#1a1a1a", "#e7e9ee", "#333333"

# sizing (large + bold, so it stays legible when the clip is scaled down in the column)
# lines + value/legend/axis/callout text 2x; tick labels + titles 1.5x.
LW, MS, MEW = 12.0, 32, 5.6
TITLE_FS, YLAB_FS, TICK_FS, XTICK_FS, VAL_FS, LEG_FS, CALL_FS = 42, 44, 28, 30, 40, 40, 52
A_YMAX, B_YMAX = 4.7, 2.45

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "figure.facecolor": "white",
    "savefig.facecolor": "white",
})

# ---- data (Table 1) ----
A_groups = ["1 ch", "2 ch", "4 ch", "8 ch"]
A_series = {"MAE": [1.89, 1.76, 0.93, 0.85], "RMSE": [3.69, 3.06, 2.00, 1.92]}
B_groups = ["8-ch\neven", "8-ch\nours"]
B_series = {"MAE": [0.94, 0.77], "RMSE": [1.77, 1.33]}
COLORS = [MAE_C, RMSE_C]

# ---- timing ----
FPS, DUR = 30, 4.0
NF = int(FPS * DUR)
GROW, SETTLE = 1.5, 1.95
LBL0, LBL1 = 1.0, 1.6
CB0, CB1 = 1.35, 1.9

clamp = lambda v, a, b: max(a, min(b, v))
ease = lambda p: 1 - (1 - p) ** 3


def two_color_title(ax, label, arrow):
    pack = HPacker(children=[
        TextArea(label, textprops=dict(color=INK, fontsize=TITLE_FS, weight="bold")),
        TextArea(arrow, textprops=dict(color=ARROW, fontsize=TITLE_FS, weight="bold")),
    ], align="center", pad=0, sep=3)
    ax.add_artist(AnchoredOffsetbox(loc="lower center", child=pack, pad=0, frameon=False,
                                    bbox_to_anchor=(0.5, 1.012), bbox_transform=ax.transAxes,
                                    borderpad=0))


def style(ax, groups, ymin, ymax, ylabel):
    n = len(groups)
    ax.set_xticks(np.arange(n))
    ax.set_xticklabels(groups, fontsize=XTICK_FS)
    ax.set_xlim(-0.4, n - 1 + 0.4)
    ax.set_ylim(ymin, ymax)
    ax.set_ylabel(ylabel, fontsize=YLAB_FS)
    ax.yaxis.grid(True, color=GRID, lw=1.5)
    ax.set_axisbelow(True)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.spines["left"].set_color("#c9ccd3")
    ax.spines["bottom"].set_color("#c9ccd3")
    ax.tick_params(length=0, labelsize=TICK_FS)


def curve(ax, groups, series, colors, ymin, ymax, e, la):
    """Draw each series as a line that progressively reveals left-to-right."""
    x = np.arange(len(groups))
    n = len(x)
    rng = ymax - ymin
    tpar = e * (n - 1)                       # distance drawn along the polyline
    k = int(np.floor(tpar + 1e-9))
    frac = tpar - k
    for si, (name, vals) in enumerate(series.items()):
        y = np.asarray(vals, float)
        full = n if k >= n - 1 else k + 1    # points fully revealed (get markers + labels)
        rx, ry = list(x[:full]), list(y[:full])
        if full < n and frac > 0:            # partial segment toward the next point
            rx.append(x[k] + frac * (x[k + 1] - x[k]))
            ry.append(y[k] + frac * (y[k + 1] - y[k]))
        ax.plot(rx, ry, color=colors[si], lw=LW, zorder=3, solid_capstyle="round")
        ax.plot(x[:full], y[:full], ls="none", marker="o", ms=MS, mfc=colors[si],
                mec="white", mew=MEW, zorder=4)
        if la > 0:
            for gi in range(full):
                ax.text(x[gi], y[gi] + rng * 0.045, f"{vals[gi]:.2f}", ha="center",
                        va="bottom", fontsize=VAL_FS, color=LBL, alpha=la, zorder=5)


def handles(series, colors):
    return [Line2D([0], [0], color=c, marker="o", mfc=c, mec="white", mew=2.0,
                   lw=LW, ms=MS, label=n) for n, c in zip(series, colors)]


def draw(t):
    e = ease(clamp(t / GROW, 0, 1))
    la = clamp((t - LBL0) / (LBL1 - LBL0), 0, 1)
    cb = clamp((t - CB0) / (CB1 - CB0), 0, 1)

    fig, (axA, axB) = plt.subplots(1, 2, figsize=(19.2, 10.8), dpi=100,
                                   gridspec_kw={"width_ratios": [1.7, 1]})
    fig.subplots_adjust(left=0.075, right=0.99, top=0.895, bottom=0.14, wspace=0.20)

    # (A) channel count
    curve(axA, A_groups, A_series, COLORS, 0.0, A_YMAX, e, la)
    style(axA, A_groups, 0.0, A_YMAX, "Error [N]")
    two_color_title(axA, "(A) More channels, less error ", "↓")
    axA.legend(handles=handles(A_series, COLORS), loc="upper right", fontsize=LEG_FS,
               frameon=True, facecolor="white", edgecolor="none", framealpha=0.85)

    # (B) layout: even vs anatomical
    curve(axB, B_groups, B_series, COLORS, 0.0, B_YMAX, e, la)
    style(axB, B_groups, 0.0, B_YMAX, "Error [N]")
    two_color_title(axB, "(B) Even vs ours ", "↓")
    # -18% MAE callout: the RMSE line sits above the "ours" MAE point, so place the
    # big note low and centered (clear of the right edge) and arrow up to that point.
    if cb > 0:
        axB.annotate("−18% MAE", xy=(0.93, 0.80), xytext=(0.45, 0.33), ha="center",
                     va="top", color=ARROW, fontsize=CALL_FS, fontweight="bold",
                     alpha=cb, zorder=7,
                     arrowprops=dict(arrowstyle="-|>", color=ARROW, lw=4.0, alpha=cb,
                                     connectionstyle="arc3,rad=-0.25"))
    axB.legend(handles=handles(B_series, COLORS), loc="upper right", fontsize=LEG_FS,
               frameon=True, facecolor="white", edgecolor="none", framealpha=0.85)
    return fig


def main():
    if STILL:
        draw(99.0).savefig("/tmp/placement_still.png", dpi=100)
        print("wrote /tmp/placement_still.png")
        return
    tmp = tempfile.mkdtemp(prefix="placement_")
    try:
        last = None
        for i in range(NF):
            t = i / FPS
            path = os.path.join(tmp, f"frame_{i:04d}.png")
            if last is None or t <= SETTLE + 1e-6:
                fig = draw(t)
                fig.savefig(path, dpi=100)
                plt.close(fig)
                last = path
            else:
                shutil.copyfile(last, path)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", last,
                        "-q:v", "3", POSTER_OUT], check=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS),
                        "-i", os.path.join(tmp, "frame_%04d.png"),
                        "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p",
                        "-preset", "slow", "-crf", "20", "-movflags", "+faststart",
                        "-an", VIDEO_OUT], check=True)
        print("wrote", VIDEO_OUT)
        print("wrote", POSTER_OUT)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
