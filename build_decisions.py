"""Build decision-point packets for every scenario (draft §3.5.2).

Scenarios (identical inputs later served to ALL methods):
  no_shift   : unit 11 clean                          (Direction A base)
  adverse    : unit 11, -2 sigma temp bias @ cycle 23 (over-optimistic model)
  favorable  : unit 11, +2 sigma temp bias @ cycle 23 (over-pessimistic model)
  natural    : units 14 (Fc1) + 15 (Fc2) clean        (Direction B natural shift)

Each packet carries everything downstream methods need:
  - rul point estimate (from the biased model) + MC-Dropout std + rul history
  - base sensor statistics + global z (draft)  ... and Tier-1 features:
      regime_z (operating-condition-conditioned) and consistency_z (cross-channel)
  - operational context (flight class, altitude, fan/core speed)
  - per-channel global z-series is preserved so CUSUM (baselines.py) can run on it
Ground-truth decision labels come from the TRUE RUL, valid under sensor bias.
"""
import json

import numpy as np

import han.Rul_shift_agent.config as C
import han.Rul_shift_agent.data_ncmapss as D
from han.Rul_shift_agent.preprocess import FeatureExtractor
from han.Rul_shift_agent.rul_tool import RULTool

PKT_PATH = C.PKT_DIR + "/packets.json"


def gt_label(true_rul):
    if true_rul <= C.REPLACE_RUL:
        return "replace"
    if true_rul <= C.INSPECT_RUL:
        return "inspect"
    return "continue"


def decision_cycles(cycles):
    """Every DECISION_EVERY-th cycle, in order."""
    cyc = np.sort(np.asarray(cycles))
    return cyc[:: C.DECISION_EVERY]


def _bias_delta(sign):
    ch_std = np.load(C.OUT_DIR + "/feature_models.npz")["ch_std"]
    return {ch: sign * C.BIAS_SIGMA * float(ch_std[ch]) for ch in C.TEMP_IDX}


def _scenario_units(scenario):
    if scenario in ("no_shift", "adverse", "favorable"):
        return [C.DIR_A_UNIT]
    return C.DIR_B_UNITS   # natural


def build_scenario(scenario, tool, fx):
    packets = []
    for unit in _scenario_units(scenario):
        kw = {}
        onset = None
        if scenario == "adverse":
            kw = dict(biased_channels=C.TEMP_IDX, bias_delta=_bias_delta(-1),
                      onset_cycle=C.BIAS_ONSET_CYCLE)
            onset = C.BIAS_ONSET_CYCLE
        elif scenario == "favorable":
            kw = dict(biased_channels=C.TEMP_IDX, bias_delta=_bias_delta(+1),
                      onset_cycle=C.BIAS_ONSET_CYCLE)
            onset = C.BIAS_ONSET_CYCLE

        d = D.load_unit_cycles(unit, **kw)
        cyc2idx = {int(c): i for i, c in enumerate(d["cycles"])}
        dcycles = decision_cycles(d["cycles"])

        # RUL point estimate + MC std at each decision cycle
        idxs = [cyc2idx[int(c)] for c in dcycles]
        wins = d["windows"][idxs]
        rul_pt = tool.predict(wins)
        rul_mc_mean, rul_mc_std = tool.predict_mc(wins)

        rul_hist = []
        for k, c in enumerate(dcycles):
            c = int(c)
            i = cyc2idx[c]
            true_rul = float(d["rul"][i])
            feat = fx(d["windows"][i])
            rul_hist.append(round(float(rul_pt[k]), 2))
            pkt = {
                "scenario": scenario,
                "unit": unit,
                "fc": d["fc"],
                "cycle": c,
                "true_rul": round(true_rul, 1),
                "gt_label": gt_label(true_rul),
                "shift_onset_cycle": onset,
                "is_post_onset": bool(onset is not None and c >= onset),
                "rul": {
                    "point": round(float(rul_pt[k]), 2),
                    "mc_mean": round(float(rul_mc_mean[k]), 2),
                    "mc_std": round(float(rul_mc_std[k]), 3),          # Tier-1 #3
                    "history": list(rul_hist[-C.HISTORY_K:]),
                },
                "context": {
                    "flight_class": d["fc"],
                    "altitude_mean": round(float(feat["mean"]["alt"]), 1),
                    "mach_mean": round(float(feat["mean"]["Mach"]), 4),
                    "fan_speed_Nf": round(float(feat["mean"]["Nf"]), 2),
                    "core_speed_Nc": round(float(feat["mean"]["Nc"]), 2),
                },
                "features": feat,
                # per-channel global z-series consumed by CUSUM baseline
                "z_global_vec": [feat["z_global"][v] for v in C.INPUT_VARS],
            }
            packets.append(pkt)
    return packets


def main():
    tool = RULTool()
    fx = FeatureExtractor()
    all_packets = []
    counts = {}
    for scenario in ("no_shift", "adverse", "favorable", "natural"):
        pk = build_scenario(scenario, tool, fx)
        counts[scenario] = len(pk)
        all_packets.extend(pk)
    with open(PKT_PATH, "w") as f:
        json.dump(all_packets, f, indent=1)
    print(f"[build_decisions] wrote {len(all_packets)} packets -> {PKT_PATH}")
    for s, n in counts.items():
        print(f"    {s:10s}: {n} decision points")
    # ground-truth label distribution
    from collections import Counter
    for s in counts:
        labs = Counter(p["gt_label"] for p in all_packets if p["scenario"] == s)
        print(f"    {s:10s} gt: {dict(labs)}")


if __name__ == "__main__":
    main()
