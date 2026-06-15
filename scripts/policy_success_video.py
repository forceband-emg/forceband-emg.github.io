#!/usr/bin/env python3
"""Generate the policy-success animation from paper Table 2.

Turns Table 2 (pick&place vs squeeze success on the UR-5, out of 10, across nine
objects for Continuous-gripper / Binary-gripper / ForceBand) into a 2-row animated
grouped-bar chart whose bars grow in (style of static/images/baselines.mp4), then
encodes it to static/videos/policy_success.mp4 with a poster. Story: only ForceBand
produces the squeeze — the gripper baselines score ~0 on it.
Run:  python3 scripts/policy_success_video.py   (--still for one settled frame)
Edit the data below and re-run if Table 2 changes.
"""
import os, sys, shutil, tempfile, subprocess
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.offsetbox import TextArea, HPacker, AnchoredOffsetbox

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIDEO_OUT = os.path.join(ROOT, "static/videos/policy_success.mp4")
POSTER_OUT = os.path.join(ROOT, "static/images/posters/policy_success.jpg")
STILL = len(sys.argv) > 1 and sys.argv[1] == "--still"

# palette: ForceBand in brand orange, gripper baselines muted (consistent with the
# other generated charts — scripts/results_force_video.py).
CONT, BIN, FB = "#9b9b9b", "#0f77b4", "#d6590b"
INK, GRID, LBL, ARROW = "#1a1a1a", "#e7e9ee", "#333333", "#8b0000"

# sizing (uniform across both panels; large + bold like scripts/placement_ablation_video.py)
TITLE_FS, YLAB_FS, TICK_FS, XTICK_FS = 36, 32, 26, 25
VAL_FS, LEG_FS, NA_FS, CALL_FS = 24, 27, 24, 26

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "figure.facecolor": "white",
    "savefig.facecolor": "white",
})

# ---- data (Table 2): success out of 10; squeeze None = N/A (squeeze not needed) ----
objects = ["Mustard", "Face Wash", "Toothpaste", "BBQ Small", "BBQ",
           "Chips", "Mustard Small", "Chocolate", "Ketchup"]
weights = [650, 280, 176, 290, 580, 43, 244, 210, 410]
short = ["Mustard", "Face Wash", "Toothpaste", "BBQ Small", "BBQ",
         "Chips", "Mustard S.", "Chocolate", "Ketchup"]
xlabels = [f"{s}\n{w} g" for s, w in zip(short, weights)]
METHODS = ["Continuous", "Binary", "ForceBand"]
LEGEND = ["Continuous gripper", "Binary gripper", "ForceBand"]
COLORS = [CONT, BIN, FB]
PP = {  # pick & place success /10
    "Continuous": [7, 6, 4, 6, 8, 3, 3, 0, 7],
    "Binary":     [10, 10, 8, 9, 7, 10, 10, 10, 10],
    "ForceBand":  [10, 10, 9, 8, 6, 8, 10, 10, 10],
}
SQ = {  # squeeze success /10 (None = N/A)
    "Continuous": [0, 4, 2, 0, 0, None, 0, 0, 0],
    "Binary":     [0, 0, 0, 0, 0, None, 0, 0, 0],
    "ForceBand":  [10, 10, 9, 8, 6, None, 10, 9, 10],
}
YMAX = 13.5

# ---- timing ----
FPS, DUR = 30, 4.0
NF = int(FPS * DUR)
GROW, SETTLE = 1.5, 1.65
LBL0, LBL1 = 1.0, 1.6

clamp = lambda v, a, b: max(a, min(b, v))
ease = lambda p: 1 - (1 - p) ** 3


def two_color_title(ax, label, arrow):
    pack = HPacker(children=[
        TextArea(label, textprops=dict(color=INK, fontsize=TITLE_FS, weight="bold")),
        TextArea(arrow, textprops=dict(color=ARROW, fontsize=TITLE_FS, weight="bold")),
    ], align="center", pad=0, sep=3)
    ax.add_artist(AnchoredOffsetbox(loc="lower center", child=pack, pad=0, frameon=False,
                                    bbox_to_anchor=(0.5, 1.01), bbox_transform=ax.transAxes,
                                    borderpad=0))


def style(ax, ylabel, show_x):
    n = len(objects)
    ax.set_xticks(np.arange(n))
    ax.set_xticklabels(xlabels if show_x else [], fontsize=XTICK_FS)
    ax.set_xlim(-0.5, n - 0.5)
    ax.set_ylim(0, YMAX)
    ax.set_yticks([0, 5, 10])
    ax.set_ylabel(ylabel, fontsize=YLAB_FS)
    ax.yaxis.grid(True, color=GRID, lw=1.5)
    ax.set_axisbelow(True)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.spines["left"].set_color("#c9ccd3")
    ax.spines["bottom"].set_color("#c9ccd3")
    ax.tick_params(length=0, labelsize=TICK_FS)


def callout(ax, i0, i1, label, alpha):
    """A bracket + label below the x-tick labels, grouping objects i0..i1 (e.g. the
    'firm squeeze' / 'gentle contact' / 'OOD sequence' behaviour notes)."""
    if alpha <= 0:
        return
    trans = ax.get_xaxis_transform()        # x in data coords, y in axes fraction
    y, cap = -0.42, 0.04
    xa, xb = i0 - 0.40, i1 + 0.40
    ax.plot([xa, xa, xb, xb], [y + cap, y, y, y + cap], transform=trans, color=ARROW,
            lw=3.0, alpha=alpha, clip_on=False, zorder=8, solid_capstyle="round")
    ax.text((xa + xb) / 2, y - 0.055, label, transform=trans, ha="center", va="top",
            fontsize=CALL_FS, color=ARROW, fontweight="bold", alpha=alpha,
            clip_on=False, zorder=8)


def bars(ax, data, e, la):
    x = np.arange(len(objects))
    w = 0.8 / len(METHODS)
    for si, name in enumerate(METHODS):
        pos = x - 0.4 + w / 2 + si * w
        for gi, val in enumerate(data[name]):
            if val is None:
                continue
            h = e * val
            ax.bar(pos[gi], h, width=w * 0.9, color=COLORS[si], edgecolor="none", zorder=3)
            if la > 0 and val > 0:
                ax.text(pos[gi], h + YMAX * 0.012, f"{val:d}", ha="center", va="bottom",
                        fontsize=VAL_FS, color=LBL, alpha=la, zorder=5)
    if la > 0:  # mark groups where the squeeze was not needed (all N/A)
        for gi in range(len(objects)):
            if all(data[m][gi] is None for m in METHODS):
                ax.text(gi, YMAX * 0.04, "N/A", ha="center", va="bottom", style="italic",
                        fontsize=NA_FS, color="#999", alpha=la, zorder=5)


def draw(t):
    e = ease(clamp(t / GROW, 0, 1))
    la = clamp((t - LBL0) / (LBL1 - LBL0), 0, 1)
    fig, (axA, axB) = plt.subplots(2, 1, figsize=(19.2, 10.8), dpi=100, sharex=True)
    fig.subplots_adjust(left=0.06, right=0.99, top=0.85, bottom=0.245, hspace=0.34)

    # one shared legend, above both panels (keeps it clear of the many "10" bar labels)
    fig.legend(handles=[Patch(color=c, label=n) for c, n in zip(COLORS, LEGEND)],
               loc="upper center", ncol=3, fontsize=LEG_FS, frameon=False,
               columnspacing=2.4, handlelength=1.4, bbox_to_anchor=(0.5, 0.995))

    bars(axA, PP, e, la)
    style(axA, "Success / 10", show_x=False)
    two_color_title(axA, "(A) Pick & place ", "↑")

    bars(axB, SQ, e, la)
    style(axB, "Success / 10", show_x=True)
    two_color_title(axB, "(B) Squeeze ", "↑")
    # behaviour notes under the relevant object ticks (replaces the old rollout placeholders)
    callout(axB, 0, 4, "Firm squeeze", la)        # Mustard … BBQ
    callout(axB, 5, 5, "Gentle contact", la)      # Chips, 43 g
    callout(axB, 6, 8, "OOD sequence", la)        # Mustard S. / Chocolate / Ketchup
    return fig


def main():
    if STILL:
        draw(99.0).savefig("/tmp/policy_success_still.png", dpi=100)
        print("wrote /tmp/policy_success_still.png")
        return
    tmp = tempfile.mkdtemp(prefix="policy_success_")
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
