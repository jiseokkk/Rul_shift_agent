"""Summary figure for the bias-injection refinement (Notion / paper).

3 panels telling the story:
  (A) WHY  — detection cliff: old +-2sigma sits in the "free" zone; cliff ~0.4sigma
  (B) HOW  — cons control: pick target difficulty, solve for the raw magnitude
  (C) RESULT — the representative L2 scenario actually injected on unit 11 T48
"""
import json
import os

import h5py
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import han.Rul_shift_agent.config as C
import han.Rul_shift_agent.inject as I

SRC = "/home/iai4/Desktop/han/Rul_shift_agent/dataset/data_set/N-CMAPSS_DS02-006.h5"
CORR = ("/home/iai4/Desktop/han/Rul_shift_agent/dataset/corrupted_NCMAPSS/"
        "unit11__T48__drift-ramp15__difficulty-cons4__onset45pct__adverse")
OUT = os.path.join(C.FIG_DIR, "bias_injection_summary.png")

BLUE, RED, PUR, GRAY = "#2b6cb0", "#c53030", "#805ad5", "#718096"


def load_t48():
    with h5py.File(SRC, "r") as f:
        A = f["A_test"][:]; m = A[:, 0] == 11
        A = A[m]; Xs_clean = f["X_s_test"][:][m]
    with h5py.File(os.path.join(CORR, "data.h5"), "r") as f:
        Xs_corr = f["X_s_test"][:]
    cyc = A[:, 1].astype(int)
    cycles = np.unique(cyc); cycles.sort()
    t48 = 2
    clean = np.array([Xs_clean[cyc == c, t48].mean() for c in cycles])
    corr = np.array([Xs_corr[cyc == c, t48].mean() for c in cycles])
    return cycles, clean, corr


def main():
    spec = json.load(open(os.path.join(CORR, "spec.json")))
    onset = spec["onset_cycle"]
    cycles, clean, corr = load_t48()

    fig = plt.figure(figsize=(15, 5.2))
    gs = fig.add_gridspec(1, 3, width_ratios=[1, 1, 1.25], wspace=0.28)

    # ---------------- Panel A: detection cliff (WHY) ----------------
    axA = fig.add_subplot(gs[0])
    sig = np.array([0.25, 0.5, 0.75, 1.0, 1.5, 2.0])
    fnr = np.array([0.78, 0.00, 0.00, 0.00, 0.00, 0.00])   # stress_difficulty.py
    axA.plot(sig, fnr, "-o", color=RED, lw=2, ms=6)
    axA.axvspan(0.0, 0.4, color=RED, alpha=0.08)
    axA.axvspan(0.4, 2.15, color="green", alpha=0.06)
    axA.axvline(2.0, ls="--", color=GRAY, lw=1.3)
    axA.annotate("old ±2σ setting\n= \"free\" zone", (2.0, 0.45), color=GRAY,
                 fontsize=9, ha="right", va="center")
    axA.annotate("detection cliff\n~0.4σ", (0.33, 0.5), color=RED, fontsize=9,
                 ha="left", va="center")
    axA.annotate("0.25σ → FNR 0.78\n(total miss)", (0.25, 0.78), color=RED,
                 fontsize=8, ha="left", va="bottom")
    axA.set_xlabel("injected bias magnitude (σ)")
    axA.set_ylabel("FNR  (missed real faults)")
    axA.set_title("(A) WHY — old ±2σ is too easy", fontsize=11, weight="bold")
    axA.set_ylim(-0.05, 0.95); axA.set_xlim(0.1, 2.15)
    axA.grid(alpha=0.25)

    # ---------------- Panel B: cons control (HOW) ----------------
    axB = fig.add_subplot(gs[1])
    # illustrative monotone map: raw magnitude -> detector cons (slope from cons=4 calib)
    slope = 51.27 / 4.0                                     # T48 -51.27 raw -> cons 4
    mag = np.linspace(0, 90, 100)
    axB.plot(mag, mag / slope, "-", color=PUR, lw=2)
    for tgt, lab in [(2.0, "hard"), (4.0, "cliff (used)"), (6.0, "easy")]:
        raw = tgt * slope
        axB.plot([raw, raw, 0], [0, tgt, tgt], ":", color=GRAY, lw=1)
        axB.plot(raw, tgt, "o", color=PUR, ms=6)
        axB.annotate(f"cons {tgt:g}\n{lab}", (raw, tgt), fontsize=8,
                     ha="left", va="bottom", color=PUR)
    axB.annotate("pick difficulty →\nsolve for magnitude\n(bisection)", (5, 6.2),
                 fontsize=9, color="#444", ha="left", va="center")
    axB.set_xlabel("raw injected magnitude (T48, units)")
    axB.set_ylabel("detector signal  cons (temp_consistency_z_abs)")
    axB.set_title("(B) HOW — control difficulty (cons), not σ", fontsize=11, weight="bold")
    axB.set_xlim(0, 90); axB.set_ylim(0, 8)
    axB.grid(alpha=0.25)

    # ---------------- Panel C: the actual injection (RESULT) ----------------
    axC = fig.add_subplot(gs[2])
    axC.plot(cycles, clean, "-o", ms=3, color=BLUE, label="clean (true EGT)")
    axC.plot(cycles, corr, "-o", ms=3, color=RED, label="corrupted (sensor reports)")
    axC.axvline(onset, ls="--", color=GRAY, lw=1.2)
    axC.annotate(f"onset\ncycle {onset} (45% life)", (onset, clean.max()),
                 fontsize=8, color=GRAY, ha="right", va="top")
    # shade the growing gap post-onset
    axC.fill_between(cycles, clean, corr, where=cycles >= onset,
                     color=RED, alpha=0.12)
    axC.annotate("sensor hides degradation\n→ RUL overestimate (adverse)",
                 (cycles[-1], corr[-1]), fontsize=8, color=RED, ha="right", va="top")
    axC.set_xlabel("cycle")
    axC.set_ylabel("T48 (EGT) per-cycle mean")
    axC.set_title("(C) RESULT — T48 drift, ramp, cons 4", fontsize=11, weight="bold")
    axC.legend(loc="lower right", fontsize=8)
    axC.grid(alpha=0.25)

    fig.suptitle("Bias-injection refinement:  σ-based (easy, uncontrolled)  →  "
                 "cons-controlled physical fault scenarios",
                 fontsize=12.5, weight="bold", y=1.02)
    fig.savefig(OUT, dpi=120, bbox_inches="tight")
    print("saved ->", OUT)


if __name__ == "__main__":
    main()
