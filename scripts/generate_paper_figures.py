"""Generate all figures for the Manifold Destiny paper.

All terminology matches the paper: Consumptor, zero-information floor,
All terminology matches the paper text.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FIGURES_DIR = REPO_ROOT / "paper" / "figures"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    # arXiv prefers outline/TrueType fonts. Matplotlib's default PDF backend
    # can emit Type3 fonts; fonttype=42 embeds TrueType outlines instead.
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "font.size": 11,
    "axes.labelsize": 13,
    "axes.titlesize": 13,
    "xtick.labelsize": 11,
    "ytick.labelsize": 11,
    "legend.fontsize": 10,
    "figure.figsize": (8, 5),
    "figure.dpi": 150,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
})

BLUE = "#2196F3"
RED = "#F44336"
GREEN = "#4CAF50"
GRAY = "#9E9E9E"
PURPLE = "#9C27B0"
ORANGE = "#FF9800"


def fig0_process_flow():
    """Architecture process flow diagram."""
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5.5)
    ax.axis("off")

    # Top row: Problem domain -> Consumptor -> Verifier
    ax.add_patch(mpatches.FancyBboxPatch((0.5, 3.5), 2, 1, boxstyle="round,pad=0.15",
                                         facecolor=BLUE, alpha=0.2, edgecolor=BLUE, linewidth=2))
    ax.text(1.5, 4.0, "Problem domain\n(states)", ha="center", va="center", fontsize=10, fontweight="bold")

    ax.add_patch(mpatches.FancyBboxPatch((3.5, 3.5), 2, 1, boxstyle="round,pad=0.15",
                                         facecolor=PURPLE, alpha=0.2, edgecolor=PURPLE, linewidth=2))
    ax.text(4.5, 4.0, "Consumptor\n(probe, retain)", ha="center", va="center", fontsize=10, fontweight="bold")

    ax.add_patch(mpatches.FancyBboxPatch((7, 3.5), 2, 1, boxstyle="round,pad=0.15",
                                         facecolor=GREEN, alpha=0.2, edgecolor=GREEN, linewidth=2))
    ax.text(8, 4.0, "Verifier\n(accept / reject)", ha="center", va="center", fontsize=10, fontweight="bold")

    # Arrows top row
    ax.annotate("", xy=(3.4, 4.15), xytext=(2.6, 4.15), arrowprops=dict(arrowstyle="->", color=GRAY, lw=1.8))
    ax.text(3.0, 4.45, "states", ha="center", fontsize=9, color=GRAY)

    ax.annotate("", xy=(6.9, 4.15), xytext=(5.6, 4.15), arrowprops=dict(arrowstyle="->", color=PURPLE, lw=1.8))
    ax.text(6.25, 4.45, "probe", ha="center", fontsize=9, color=PURPLE)

    ax.annotate("", xy=(5.6, 3.85), xytext=(6.9, 3.85), arrowprops=dict(arrowstyle="->", color=GREEN, lw=1.8))
    ax.text(6.25, 3.55, "accept / reject", ha="center", fontsize=9, color=GREEN)

    # Bottom row: Verified abstractions
    ax.add_patch(mpatches.FancyBboxPatch((3.5, 1.5), 2, 1, boxstyle="round,pad=0.15",
                                         facecolor=PURPLE, alpha=0.15, edgecolor=PURPLE, linewidth=1.5, linestyle="--"))
    ax.text(4.5, 2.0, "Verified\nabstractions", ha="center", va="center", fontsize=9, fontstyle="italic")

    ax.annotate("", xy=(4.5, 2.6), xytext=(4.5, 3.4), arrowprops=dict(arrowstyle="->", color=PURPLE, lw=1.5, linestyle="--"))
    ax.text(5.2, 3.0, "retain", ha="center", fontsize=9, color=PURPLE, fontstyle="italic")

    ax.annotate("", xy=(3.8, 3.4), xytext=(3.8, 2.6), arrowprops=dict(arrowstyle="->", color=PURPLE, lw=1.5, linestyle="--"))
    ax.text(3.3, 3.0, "apply", ha="center", fontsize=9, color=PURPLE, fontstyle="italic")

    # New instance and decision
    ax.add_patch(mpatches.FancyBboxPatch((0.5, 1.5), 2, 1, boxstyle="round,pad=0.15",
                                         facecolor=BLUE, alpha=0.15, edgecolor=BLUE, linewidth=1.5, linestyle="--"))
    ax.text(1.5, 2.0, "New instance\n(held-out)", ha="center", va="center", fontsize=9, fontstyle="italic")

    ax.annotate("", xy=(3.4, 2.15), xytext=(2.6, 2.15), arrowprops=dict(arrowstyle="->", color=GRAY, lw=1.5, linestyle="--"))
    ax.text(3.0, 2.45, "query", ha="center", fontsize=9, color=GRAY)

    ax.add_patch(mpatches.FancyBboxPatch((7, 1.5), 2, 1, boxstyle="round,pad=0.15",
                                         facecolor=RED, alpha=0.15, edgecolor=RED, linewidth=1.5))
    ax.text(8, 2.0, "Decision\n(verified)", ha="center", va="center", fontsize=9)

    ax.annotate("", xy=(6.9, 2.15), xytext=(5.6, 2.15), arrowprops=dict(arrowstyle="->", color=GRAY, lw=1.5))
    ax.text(6.25, 2.45, "output", ha="center", fontsize=9, color=GRAY)

    ax.text(5, 5.2, "Consumptor architecture", ha="center", fontsize=13, fontweight="bold")

    fig.savefig(FIGURES_DIR / "fig0_process_flow.pdf")
    plt.close(fig)
    print("  fig0_process_flow.pdf")


def fig1_scaling_curve():
    """Consumptor success rate vs zero-information floor across k=1,2,3.

    The gap between the two curves IS the argument — shade it and label it.
    """
    ks = [1, 2, 3]
    fisher_floor = [0.5, 0.25, 0.125]
    consumptor = [1.0, 1.0, 1.0]

    fig, ax = plt.subplots()
    ax.plot(ks, consumptor, "o-", color=BLUE, linewidth=2.5, markersize=9,
            label="Consumptor (with verifier feedback)", zorder=3)
    ax.plot(ks, fisher_floor, "s--", color=RED, linewidth=2.5, markersize=9,
            label="Zero-information floor (masked)", zorder=3)

    # Shade the gap — this IS the verifier-mediated information channel
    ax.fill_between(ks, fisher_floor, consumptor, color=BLUE, alpha=0.12, zorder=1)

    ax.set_xlabel("Number of decision points ($k$)")
    ax.set_ylabel("Success rate")
    ax.set_title("Scaling: Consumptor vs zero-information floor")
    ax.set_xticks(ks)
    ax.set_ylim(0, 1.15)
    ax.grid(True, alpha=0.25)

    # Floor annotations placed well BELOW the data points, larger and further out
    for k, ff in zip(ks, fisher_floor):
        ax.annotate(f"$1/2^{k}$", (k, ff), textcoords="offset points",
                    xytext=(20, -30), fontsize=12, color=RED, fontweight="bold")

    # Channel label placed in the gap, centered
    ax.text(2, 0.55, "verifier-mediated\ninformation channel",
            ha="center", va="center", fontsize=10, color=BLUE, fontstyle="italic")

    # Legend OUTSIDE the plot — eliminates all overlap with data and labels
    ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1.0), framealpha=0.95,
              borderaxespad=0)
    fig.subplots_adjust(right=0.68)

    fig.savefig(FIGURES_DIR / "fig1_scaling_curve.pdf")
    plt.close(fig)
    print("  fig1_scaling_curve.pdf")


def fig2_compositional_probes():
    """Compositional probe scaling: linear vs exponential.

    Compositional construction reaches success 1.0 in k probes (one per
    proof step).  Flattened exhaustive search over a minimal tactic
    vocabulary |T| = 2 requires 2^k - 1 probes in the worst case.
    """
    ks = [2, 3, 4]
    # Compositional: success climbs from 1/2^k to 1.0 at probe = k
    comp_data = {
        2: ([0, 1, 2], [0.25, 0.5, 1.0]),
        3: ([0, 1, 2, 3], [0.125, 0.25, 0.5, 1.0]),
        4: ([0, 1, 2, 3, 4], [0.0625, 0.125, 0.25, 0.5, 1.0]),
    }
    markers = {2: ("o", BLUE), 3: ("s", GREEN), 4: ("^", PURPLE)}

    fig, ax = plt.subplots()
    for k in ks:
        probes, rates = comp_data[k]
        m, c = markers[k]
        ax.plot(probes, rates, f"{m}-", color=c, linewidth=2, markersize=8,
                label=f"k = {k}  (compositional: {k} probes; flattened: $2^{{{k}}}-1$ = {2**k - 1})")

    ax.axhline(y=1.0, color=GRAY, linestyle=":", alpha=0.3)
    ax.set_xlabel("Probe budget")
    ax.set_ylabel("Success rate")
    ax.set_title("Compositional vs flattened probe scaling")
    ax.set_ylim(0, 1.15)
    ax.set_xlim(-0.5, 6)
    ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1.0), fontsize=9,
              framealpha=0.95, borderaxespad=0)
    ax.grid(True, alpha=0.3)
    # Make room for the outside legend
    fig.subplots_adjust(right=0.72)

    fig.savefig(FIGURES_DIR / "fig2_compositional_probes.pdf")
    plt.close(fig)
    print("  fig2_compositional_probes.pdf")


def fig3_entanglement_ladder():
    """CHSH score vs entanglement parameter theta (sorted by theta)."""
    # Sort thetas in ascending order
    theta_labels_raw = ["0", "π/12", "π/8", "π/6", "3π/16", "5π/24", "π/4"]
    thetas_raw = [0, np.pi/12, np.pi/8, np.pi/6, 3*np.pi/16, 5*np.pi/24, np.pi/4]
    S_values_raw = [1.4495, 1.861, 2.0175, 2.179, 2.247, 2.291, 2.297]

    # Sort by theta value
    sorted_indices = np.argsort(thetas_raw)
    thetas = [thetas_raw[i] for i in sorted_indices]
    theta_labels = [theta_labels_raw[i] for i in sorted_indices]
    S_values = [S_values_raw[i] for i in sorted_indices]

    fig, ax = plt.subplots()
    ax.plot(range(len(thetas)), S_values, "o-", color=PURPLE, linewidth=2.5,
            markersize=9, zorder=3)
    ax.axhline(y=2.0, color=RED, linestyle="--", linewidth=1.2, alpha=0.8,
               label="Classical CHSH bound ($S = 2$)")
    ax.axhline(y=2*np.sqrt(2), color=GREEN, linestyle=":", linewidth=1.2, alpha=0.7,
               label="Tsirelson bound ($S = 2\\sqrt{2}$)")

    # Annotation: generous breathing room, curved arrow, text well clear of data
    ax.annotate("First exceeds classical bound\n$\\theta = \\pi/8$",
                (2, 2.0175), textcoords="offset points",
                xytext=(70, -70), fontsize=9.5, fontweight="bold", color=ORANGE,
                arrowprops=dict(arrowstyle="->", color=ORANGE, lw=1.5,
                                connectionstyle="arc3,rad=0.15"))

    ax.set_xticks(range(len(thetas)))
    ax.set_xticklabels(theta_labels)
    ax.set_xlabel("Entanglement parameter $\\theta$")
    ax.set_ylabel("CHSH score $S$")
    ax.set_title("CHSH score vs entanglement parameter")
    ax.set_ylim(1.3, 2.95)
    ax.set_xlim(-0.3, 6.5)
    ax.legend(loc="lower right", framealpha=0.9)
    ax.grid(True, alpha=0.25)

    fig.savefig(FIGURES_DIR / "fig3_entanglement_ladder.pdf")
    plt.close(fig)
    print("  fig3_entanglement_ladder.pdf")


def fig4_probe_budget():
    """Probes required for recovery: compositional (k) vs elimination (2^k - 1).

    Directly visualizes the exponential cost of flattened elimination over
    GF(2) candidates versus linear compositional construction.  This is the
    worst-case elimination bound: 2^k candidates, 2^k - 1 probes.
    """
    ks = [1, 2, 3, 4, 5]
    compositional = ks                           # k probes
    flattened = [2**k - 1 for k in ks]           # 2^k - 1 probes

    x = np.arange(len(ks))
    width = 0.35

    fig, ax = plt.subplots()
    bars1 = ax.bar(x - width/2, compositional, width, color=BLUE, alpha=0.85,
                   edgecolor="white", linewidth=0.5, label="Compositional ($k$ probes)")
    bars2 = ax.bar(x + width/2, flattened, width, color=RED, alpha=0.85,
                   edgecolor="white", linewidth=0.5, label="Elimination ($2^k - 1$ probes)")

    # Value labels on bars
    for bar in bars1:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, h + 0.3, f"{int(h)}",
                ha="center", va="bottom", fontsize=9, color=BLUE)
    for bar in bars2:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, h + 0.3, f"{int(h)}",
                ha="center", va="bottom", fontsize=9, color=RED)

    ax.set_xlabel("Number of decision points ($k$)")
    ax.set_ylabel("Probes required (worst case)")
    ax.set_title("Compositional vs elimination probe budget")
    ax.set_xticks(x)
    ax.set_xticklabels([f"$k={k}$" for k in ks])
    ax.set_ylim(0, max(flattened) * 1.15)
    ax.legend(loc="upper left")
    ax.grid(True, alpha=0.3, axis="y")

    fig.savefig(FIGURES_DIR / "fig4_probe_budget.pdf")
    plt.close(fig)
    print("  fig4_probe_budget.pdf")


def main():
    print("=== GENERATING PAPER FIGURES ===")
    print(f"Output: {FIGURES_DIR}")
    print()

    # fig0 is generated by GPT Image 2 (process-diagram-production skill),
    # not matplotlib. Do not regenerate it here.
    fig1_scaling_curve()
    fig2_compositional_probes()
    fig3_entanglement_ladder()
    fig4_probe_budget()

    print()
    print(f"=== DONE — {len(list(FIGURES_DIR.glob('*.pdf')))} figures generated ===")


if __name__ == "__main__":
    main()
