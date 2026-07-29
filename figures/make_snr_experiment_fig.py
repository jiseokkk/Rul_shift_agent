"""Figure for the cons-difficulty experiments (results/snr_experiment.json).

(A) difficulty sweep: rule-detector recall vs detector consistency signal — the
    cliff sits at the rule threshold (cons=3), confirming the ambiguous zone.
(B) sigma vs cons: same sigma -> wildly different difficulty per scope; cons-
    calibrated -> constant difficulty.  Grouped recall bars + spread callout.
"""
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import han.Rul_shift_agent.core.config as C

R = json.load(open(C.RES_DIR + "/snr_experiment.json"))
OUT = C.FIG_DIR + "/snr_experiment_summary.png"
BLUE, RED, GREEN, GRAY = "#2b6cb0", "#c53030", "#2f855a", "#718096"


def main():
    fig, (axA, axB) = plt.subplots(1, 2, figsize=(13.5, 5.2))

    # ---- Panel A: difficulty sweep ----
    A = R["A_difficulty_sweep_temp4"]
    cons = [r["realised_cons"] for r in A]
    rec = [r["recall"] for r in A]
    axA.plot(cons, rec, "-o", color=BLUE, lw=2, ms=7)
    axA.axvline(3.0, ls="--", color=RED, lw=1.5)
    axA.annotate("rule threshold\ncons > 3", (3.0, 0.08), color=RED, fontsize=9,
                 ha="left", va="bottom")
    axA.axvspan(2.5, 4.5, color="orange", alpha=0.12)
    axA.annotate("ambiguous zone\n(recall ~0.45–0.64)", (4.4, 0.30), color="#b7791f",
                 fontsize=9, ha="right", va="center")
    for r in A:
        axA.annotate(f"{r['recall']:.2f}", (r["realised_cons"], r["recall"]),
                     fontsize=8, ha="center", va="bottom", color=BLUE)
    axA.set_xlabel("detector signal  (temp_consistency_z_abs)")
    axA.set_ylabel("rule-detector recall")
    axA.set_title("(A) Difficulty sweep — the cliff is real, at cons≈3",
                  fontsize=11, weight="bold")
    axA.set_ylim(-0.05, 0.85); axA.grid(alpha=0.25)

    # ---- Panel B: sigma vs cons grouped bars ----
    sig = R["B_sigma_method"]; snr = R["B_snr_method"]
    scopes = [r["scope"] for r in sig]
    x = np.arange(len(scopes)); w = 0.36
    axB.bar(x - w/2, [r["recall"] for r in sig], w, color=RED, alpha=0.85,
            label="σ method (fixed 0.5σ)")
    axB.bar(x + w/2, [r["recall"] for r in snr], w, color=GREEN, alpha=0.85,
            label="cons method (target cons=4)")
    for i, r in enumerate(sig):
        axB.annotate(f"cons\n{r['det_cons']:.1f}", (i - w/2, r["recall"] + 0.02),
                     fontsize=7.5, ha="center", va="bottom", color=RED)
    for i, r in enumerate(snr):
        axB.annotate(f"cons\n{r['det_cons']:.1f}", (i + w/2, r["recall"] + 0.02),
                     fontsize=7.5, ha="center", va="bottom", color=GREEN)
    axB.set_xticks(x); axB.set_xticklabels(scopes, fontsize=9)
    axB.set_ylabel("rule-detector recall  (= difficulty)")
    axB.set_title("(B) σ can't hold difficulty constant — cons can",
                  fontsize=11, weight="bold")
    axB.set_ylim(0, 1.02); axB.grid(alpha=0.2, axis="y")
    axB.legend(loc="upper center", fontsize=9)
    sp = R["B_recall_spread"]
    callout = (f"recall spread across scopes (lower=better):\n"
               f"  σ    = {sp['sigma']:.2f}  (swings wildly)\n"
               f"  cons = {sp['snr']:.2f}  (≈flat)")
    axB.annotate(callout, (0.5, 0.02), xycoords="axes fraction", fontsize=8.5,
                 ha="center", va="bottom",
                 bbox=dict(boxstyle="round", fc="#f7fafc", ec=GRAY))

    fig.suptitle("cons-controlled injection: the difficulty cliff is real, and cons "
                 "holds it constant where σ cannot", fontsize=12.5, weight="bold", y=1.02)
    fig.tight_layout()
    fig.savefig(OUT, dpi=120, bbox_inches="tight")
    print("saved ->", OUT)


if __name__ == "__main__":
    main()
