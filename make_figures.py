"""Figures 1-3 (draft §4).  Uses whichever agent decision file is available
(prefers the LLM agent, falls back to the rule agent)."""
import glob
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import han.Rul_shift_agent.rul_shift_agent.config as C

SCEN = ["no_shift", "adverse", "favorable", "natural"]
SCEN_LABEL = {"no_shift": "No shift", "adverse": "Adverse", "favorable": "Favorable",
              "natural": "Natural (Dir B)"}


def _agent_rows():
    for name in ("llm", "rule"):
        p = C.RES_DIR + f"/agent_decisions_{name}.json"
        if os.path.exists(p):
            return name, json.load(open(p))
    return None, None


def fig1_architecture():
    fig, ax = plt.subplots(figsize=(11, 4.6))
    ax.axis("off")
    boxes = [
        (0.02, "Raw sensor\nwindow\n(50x18)"),
        (0.21, "Preprocessing\nmean/std/trend, z_global\n+Tier1: regime_z,\nconsistency_z"),
        (0.42, "RUL tool (LSTM)\npoint estimate\n+Tier1: MC-Dropout std"),
        (0.63, "LLM decision agent\n(Qwen, reasoning)\n+CUSUM signal (Tier2)"),
        (0.84, "Decision policy\nhysteresis + cost-aware\n(Tier2) -> action"),
    ]
    for x, txt in boxes:
        ax.add_patch(plt.Rectangle((x, 0.35), 0.15, 0.32, fill=True,
                                   facecolor="#eaf2fb", edgecolor="#2c6fbb", lw=1.6))
        ax.text(x + 0.075, 0.51, txt, ha="center", va="center", fontsize=8.2)
    for x in [0.17, 0.38, 0.59, 0.80]:
        ax.annotate("", xy=(x + 0.04, 0.51), xytext=(x, 0.51),
                    arrowprops=dict(arrowstyle="->", lw=1.4, color="#444"))
    ax.text(0.5, 0.86, "Figure 1. Shift-aware decision framework (Tier-1/Tier-2 additions in blue)",
            ha="center", fontsize=10, weight="bold")
    ax.text(0.5, 0.12, "The RUL model is unchanged; the agent decides how much to trust it.",
            ha="center", fontsize=8.5, style="italic", color="#555")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    fig.savefig(C.FIG_DIR + "/figure1_architecture.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig2_bidirectional(metrics):
    dq = metrics["decision_quality"]
    methods = ["threshold", "cusum"]
    agent_key = "agent_llm" if "agent_llm" in dq else "agent_rule"
    methods.append(agent_key)
    colors = {"threshold": "#9aa0a6", "cusum": "#e8a33d", agent_key: "#2c6fbb"}

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2))
    for ax, metric, title in zip(axes, ["FNR", "FPR"],
                                 ["False Negative Rate (miss)", "False Positive Rate (false alarm)"]):
        x = np.arange(len(SCEN))
        w = 0.26
        for j, m in enumerate(methods):
            vals = [dq[m][s][metric] for s in SCEN]
            ax.bar(x + (j - 1) * w, vals, w, label=m.replace("agent_", "agent:"),
                   color=colors[m], edgecolor="white")
        ax.set_xticks(x); ax.set_xticklabels([SCEN_LABEL[s] for s in SCEN], fontsize=8.5)
        ax.set_title(title, fontsize=10); ax.set_ylim(0, 1.05)
        ax.axhline(0, color="#ccc", lw=0.8)
        ax.legend(fontsize=8, loc="upper right")
    fig.suptitle("Figure 2. Bidirectional shift analysis", fontsize=11, weight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(C.FIG_DIR + "/figure2_shift_analysis.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig3_case_traces(name, rows):
    packets = json.load(open(C.PKT_DIR + "/packets.json"))
    base = json.load(open(C.RES_DIR + "/baseline_decisions.json"))
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.6))
    for ax, scen, title in zip(axes, ["adverse", "favorable"],
                               ["Case A - Adverse (over-optimistic)", "Case B - Favorable (over-pessimistic)"]):
        pk = sorted([p for p in packets if p["scenario"] == scen], key=lambda p: p["cycle"])
        cyc = [p["cycle"] for p in pk]
        rul_pred = [p["rul"]["point"] for p in pk]
        rul_true = [p["true_rul"] for p in pk]
        ax.plot(cyc, rul_true, "k-", lw=2, label="true RUL")
        ax.plot(cyc, rul_pred, color="#c0392b", lw=1.6, marker="o", ms=3, label="RUL model (biased)")
        ax.axvline(C.BIAS_ONSET_CYCLE, color="#888", ls="--", lw=1, label="shift onset")
        ax.axhline(C.INSPECT_RUL, color="#2c6fbb", ls=":", lw=1, alpha=0.7)
        ax.axhline(C.REPLACE_RUL, color="#8e44ad", ls=":", lw=1, alpha=0.7)
        # decision markers along the bottom
        arow = {r["cycle"]: r for r in rows if r["scenario"] == scen}
        brow = {r["cycle"]: r for r in base if r["scenario"] == scen}
        ymark = {"continue": -6, "inspect": -3, "replace": 0}
        cmark = {"continue": "#2ca02c", "inspect": "#e8a33d", "replace": "#c0392b"}
        for c in cyc:
            if c in arow:
                ax.scatter(c, ymark[arow[c]["agent"]] - 8, c=cmark[arow[c]["agent"]], s=18, marker="s")
            if c in brow:
                ax.scatter(c, ymark[brow[c]["threshold"]] - 16, c=cmark[brow[c]["threshold"]], s=18, marker="^")
        ax.set_title(title, fontsize=10)
        ax.set_xlabel("cycle"); ax.set_ylabel("RUL (cycles)")
        ax.set_ylim(-28, 70)
        ax.legend(fontsize=7.5, loc="upper right")
        ax.text(0.02, 0.03, "sq=agent  tri=threshold  (green=cont, orange=insp, red=repl)",
                transform=ax.transAxes, fontsize=7, color="#555")
    fig.suptitle(f"Figure 3. Case traces (agent: {name})", fontsize=11, weight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(C.FIG_DIR + "/figure3_case_traces.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def main():
    metrics = json.load(open(C.RES_DIR + "/metrics.json"))
    name, rows = _agent_rows()
    fig1_architecture()
    fig2_bidirectional(metrics)
    if rows is not None:
        fig3_case_traces(name, rows)
    print(f"[make_figures] wrote figure1-3 -> {C.FIG_DIR}  (agent={name})")


if __name__ == "__main__":
    main()
