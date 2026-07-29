"""Baselines (draft §3.5.3).

Baseline 1 - Threshold: decision straight off the RUL point estimate.
Baseline 2 - CUSUM: per-channel two-sided CUSUM on the same per-cycle global
             z-scores the agent also sees; k = 0.5 sigma; alarm threshold h
             calibrated on the held-out validation unit (unit 20) for a zero
             in-distribution false-alarm rate.  While any channel's statistic
             exceeds h the decision is escalated one level (direction-blind).

CUSUM is a pure comparison baseline: its statistic is NOT fed to the agent.
"""
import json

import numpy as np

import han.Rul_shift_agent.core.config as C
import han.Rul_shift_agent.core.data_ncmapss as D
from han.Rul_shift_agent.core.preprocess import FeatureExtractor

PKT_PATH = C.PKT_DIR + "/packets.json"
BASE_PATH = C.RES_DIR + "/baseline_decisions.json"
H_PATH = C.OUT_DIR + "/cusum_h.json"


# --------------------------------------------------------------------------- #
# CUSUM core
# --------------------------------------------------------------------------- #
def cusum_stats(z_series, k=C.CUSUM_K):
    """z_series: (T, n_channels).  Returns per-step max two-sided statistic (T,)."""
    z = np.asarray(z_series, dtype=float)
    T, n = z.shape
    sp = np.zeros(n)
    sn = np.zeros(n)
    out = np.zeros(T)
    for t in range(T):
        sp = np.maximum(0.0, sp + z[t] - k)
        sn = np.maximum(0.0, sn - z[t] - k)
        out[t] = float(np.max(np.maximum(sp, sn)))
    return out


def calibrate_h(margin=1.0):
    """Calibrate h on clean validation unit 20 (flight class 3) for zero FAR."""
    fx = FeatureExtractor()
    val = D.load_unit_cycles(C.VAL_UNIT)
    cyc = np.sort(val["cycles"])[:: C.DECISION_EVERY]
    cyc2idx = {int(c): i for i, c in enumerate(val["cycles"])}
    z = []
    for c in cyc:
        feat = fx(val["windows"][cyc2idx[int(c)]])
        z.append([feat["z_global"][v] for v in C.INPUT_VARS])
    stat = cusum_stats(np.array(z))
    h = float(stat.max()) * margin + 1e-6
    with open(H_PATH, "w") as f:
        json.dump({"h": h, "k": C.CUSUM_K, "val_max_stat": float(stat.max())}, f, indent=2)
    return h


# --------------------------------------------------------------------------- #
# Decisions
# --------------------------------------------------------------------------- #
def threshold_decision(rul_point):
    if rul_point <= C.REPLACE_RUL:
        return "replace"
    if rul_point <= C.INSPECT_RUL:
        return "inspect"
    return "continue"


def _escalate(level, steps=1):
    return C.DECISIONS[min(len(C.DECISIONS) - 1, C.DEC_LEVEL[level] + steps)]


def run_baselines(packets, h):
    """Group by scenario+unit (ordered by cycle), run threshold + CUSUM.
    Annotates packets with detector info; returns list of baseline decision rows."""
    rows = []
    # group
    groups = {}
    for i, p in enumerate(packets):
        groups.setdefault((p["scenario"], p["unit"]), []).append(i)

    for key, idxs in groups.items():
        idxs.sort(key=lambda i: packets[i]["cycle"])
        zseq = np.array([packets[i]["z_global_vec"] for i in idxs])
        stat = cusum_stats(zseq)
        for pos, i in enumerate(idxs):
            p = packets[i]
            th = threshold_decision(p["rul"]["point"])
            alarm = bool(stat[pos] > h)
            cu = _escalate(th, 1) if alarm else th   # direction-blind escalation
            rows.append({
                "scenario": p["scenario"], "unit": p["unit"], "cycle": p["cycle"],
                "gt_label": p["gt_label"], "true_rul": p["true_rul"],
                "rul_point": p["rul"]["point"],
                "threshold": th, "cusum": cu,
                "cusum_stat": round(float(stat[pos]), 3), "cusum_alarm": alarm,
            })
    return rows


def main():
    with open(PKT_PATH) as f:
        packets = json.load(f)
    h = calibrate_h()
    print(f"[baselines] calibrated CUSUM h = {h:.3f} (zero FAR on unit 20)")
    rows = run_baselines(packets, h)
    with open(BASE_PATH, "w") as f:
        json.dump(rows, f, indent=1)
    print(f"[baselines] wrote {len(rows)} baseline decisions -> {BASE_PATH}")
    print(f"[baselines] CUSUM kept as pure baseline (not fed to the agent)")


if __name__ == "__main__":
    main()
