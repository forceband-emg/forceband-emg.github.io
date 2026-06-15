#!/usr/bin/env python3
"""Generate the Results-section animation from paper Fig.5.

Recreates Fig.5 (force-estimation results) as an animated 2x2 grouped-bar chart
whose bars grow in (in the style of static/images/baselines.mp4), then encodes it
to static/videos/results_force.mp4 with a poster in static/images/posters/.

Requires: numpy, matplotlib, ffmpeg on PATH. Run:  python3 scripts/results_force_video.py
Re-run after the paper figure changes; update the data dicts below to match.
"""
import os, sys, shutil, tempfile, subprocess
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
from matplotlib.offsetbox import TextArea, HPacker, AnchoredOffsetbox

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIDEO_OUT = os.path.join(ROOT, "static/videos/results_force.mp4")
POSTER_OUT = os.path.join(ROOT, "static/images/posters/results_force.jpg")
STILL = len(sys.argv) > 1 and sys.argv[1] == "--still"

# ---- palette (sampled from static/images/paper/fig5_force_estimation.png) ----
OURS, FEEL, VISFT, VISRAW = "#d6590b", "#0f77b4", "#5bb9e9", "#9b9b9b"
ARROW, INK, GRID, LBL = "#8b0000", "#1a1a1a", "#e7e9ee", "#333333"
TWO = [OURS, FEEL]

# sizing (large + bold, like scripts/placement_ablation_video.py, so the text stays
# legible when the clip is scaled down in the column). Panels are ~half-height here
# (2x2 vs placement's 1x2), so titles/ticks sit just below placement's. Value labels
# and legends are UNIFORM across all four panels (consistency); the cap is set by the
# densest panel A, which packs 16 bars/row with some near-equal-height neighbours
# (e.g. PR AUC 0.89/0.86) whose labels collide if larger.
TITLE_FS, YLAB_FS, TICK_FS, XTICK_FS = 36, 38, 26, 28
VAL_FS, RAND_FS = 22, 22             # bar value labels + random-baseline labels (same everywhere)
LEG_FS = 24                          # legends (same everywhere)
RAND_LW, RAND_MS = 4.0, 18           # random-baseline dashed line width / marker size

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "figure.facecolor": "white",
    "savefig.facecolor": "white",
})

# ---- data (read off Fig.5) ----
A_groups = ["ROC AUC", "PR AUC", "F1", "Bal. Acc."]
A_series = {
    "Ours":        [0.94, 0.89, 0.85, 0.89],
    "FEEL":        [0.85, 0.86, 0.77, 0.76],
    "VISOR (ft.)": [0.70, 0.72, 0.66, 0.64],
    "VISOR (raw)": [0.61, 0.61, 0.70, 0.55],
}
A_colors = [OURS, FEEL, VISFT, VISRAW]
B_groups = ["MAE", "RMSE"]
B_series = {"Ours": [0.80, 1.36], "FEEL": [1.58, 2.80]}
fingers = ["Thumb", "Index", "Middle", "Ring", "Pinky"]
C_series = {"Ours": [0.93, 0.96, 0.81, 0.76, 0.59], "FEEL": [0.86, 0.78, 0.63, 0.38, 0.27]}
C_random = [0.45, 0.36, 0.26, 0.12, 0.07]
D_series = {"Ours": [1.45, 1.06, 0.86, 0.34, 0.26], "FEEL": [2.72, 2.09, 1.57, 0.75, 0.76]}

# ---- timing ----
FPS, DUR = 30, 4.0
NF = int(FPS * DUR)
GROW, SETTLE = 1.5, 1.65
LBL0, LBL1 = 1.0, 1.6
BL0, BL1 = 0.8, 1.5

clamp = lambda v, a, b: max(a, min(b, v))
ease = lambda p: 1 - (1 - p) ** 3


def two_color_title(ax, label, arrow):
    pack = HPacker(children=[
        TextArea(label, textprops=dict(color=INK, fontsize=TITLE_FS, weight="bold")),
        TextArea(arrow, textprops=dict(color=ARROW, fontsize=TITLE_FS, weight="bold")),
    ], align="center", pad=0, sep=3)
    ax.add_artist(AnchoredOffsetbox(loc="lower center", child=pack, pad=0, frameon=False,
                                    bbox_to_anchor=(0.5, 1.015), bbox_transform=ax.transAxes,
                                    borderpad=0))


def style(ax, groups, ymin, ymax, ylabel):
    ax.set_xticks(np.arange(len(groups)))
    ax.set_xticklabels(groups, fontsize=XTICK_FS)
    ax.set_ylim(ymin, ymax)
    ax.set_ylabel(ylabel, fontsize=YLAB_FS)
    ax.yaxis.grid(True, color=GRID, lw=1.5)
    ax.set_axisbelow(True)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.spines["left"].set_color("#c9ccd3")
    ax.spines["bottom"].set_color("#c9ccd3")
    ax.tick_params(length=0, labelsize=TICK_FS)


def bars(ax, groups, series, colors, ymin, ymax, e, la):
    n_s = len(series)
    x = np.arange(len(groups))
    w = 0.8 / n_s
    rng = ymax - ymin
    for si, (name, vals) in enumerate(series.items()):
        pos = x - 0.4 + w / 2 + si * w
        for gi, val in enumerate(vals):
            h = e * (val - ymin)
            ax.bar(pos[gi], h, bottom=ymin, width=w * 0.90, color=colors[si],
                   edgecolor="none", zorder=3)
            if la > 0:
                ax.text(pos[gi], ymin + h + rng * 0.012, f"{val:.2f}", ha="center",
                        va="bottom", fontsize=VAL_FS, color=LBL, alpha=la, zorder=5)


def draw(t):
    e = ease(clamp(t / GROW, 0, 1))
    la = clamp((t - LBL0) / (LBL1 - LBL0), 0, 1)
    ba = clamp((t - BL0) / (BL1 - BL0), 0, 1)
    fig, axs = plt.subplots(2, 2, figsize=(19.2, 10.8), dpi=100)
    fig.subplots_adjust(left=0.07, right=0.99, top=0.91, bottom=0.075,
                        hspace=0.42, wspace=0.16)
    (axA, axB), (axC, axD) = axs

    bars(axA, A_groups, A_series, A_colors, 0.4, 1.28, e, la)
    style(axA, A_groups, 0.4, 1.28, "Score")
    two_color_title(axA, "(A) Hand-level BCD ", "↑")
    axA.legend(handles=[Patch(color=c, label=n) for n, c in zip(A_series, A_colors)],
               loc="upper right", ncol=2, fontsize=LEG_FS, frameon=True, facecolor="white",
               edgecolor="none", framealpha=0.85, columnspacing=1.0, handlelength=1.3)

    bars(axB, B_groups, B_series, TWO, 0.0, 3.6, e, la)
    style(axB, B_groups, 0.0, 3.6, "Error [N]")
    two_color_title(axB, "(B) Hand-level Force Est. ", "↓")
    axB.legend(handles=[Patch(color=c, label=n) for n, c in zip(B_series, TWO)],
               loc="upper left", fontsize=LEG_FS, frameon=True, facecolor="white",
               edgecolor="none", framealpha=0.85)

    bars(axC, fingers, C_series, TWO, 0.0, 1.32, e, la)
    style(axC, fingers, 0.0, 1.32, "PR AUC")
    two_color_title(axC, "(C) Per-finger BCD: PR AUC ", "↑")
    xc = np.arange(len(fingers))
    axC.plot(xc, C_random, ls="--", lw=RAND_LW, color="#222", marker="o", ms=RAND_MS,
             mfc="white", mec="#222", mew=2.0, alpha=ba, zorder=6)
    if ba > 0:
        for gi, v in enumerate(C_random):
            above = v < 0.18          # low points: label above the marker, clear of the x-axis labels
            axC.text(xc[gi], v + (0.055 if above else -0.045), f"{v:.2f}", ha="center",
                     va="bottom" if above else "top", fontsize=RAND_FS, color=LBL,
                     alpha=ba, zorder=7)
    # single horizontal row keeps the 3-entry legend clear of the tall bars below it
    axC.legend(handles=[Patch(color=OURS, label="Ours"), Patch(color=FEEL, label="FEEL"),
                        Line2D([0], [0], color="#222", ls="--", marker="o", mfc="white",
                               mec="#222", label="random baseline")],
               loc="upper center", ncol=3, fontsize=LEG_FS, frameon=True, facecolor="white",
               edgecolor="none", framealpha=0.85, handlelength=1.6, columnspacing=1.2)

    bars(axD, fingers, D_series, TWO, 0.0, 3.1, e, la)
    style(axD, fingers, 0.0, 3.1, "MAE [N]")
    two_color_title(axD, "(D) Per-finger Force Est. ", "↓")
    axD.legend(handles=[Patch(color=c, label=n) for n, c in zip(D_series, TWO)],
               loc="upper right", fontsize=LEG_FS, frameon=True, facecolor="white",
               edgecolor="none", framealpha=0.85)
    return fig


def main():
    if STILL:
        draw(99.0).savefig("/tmp/results_force_still.png", dpi=100)
        print("wrote /tmp/results_force_still.png")
        return
    tmp = tempfile.mkdtemp(prefix="results_force_")
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
        # poster from the final settled frame
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", last,
                        "-q:v", "3", POSTER_OUT], check=True)
        # encode
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
