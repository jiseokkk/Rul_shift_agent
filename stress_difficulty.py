"""Difficulty stress test — is the Direction-A result 'too easy'?

The headline FNR=0 is largely because Direction A injects a *constant additive
bias* of a *large magnitude* (2 sigma) on a *subset* of channels — the textbook
off-manifold sensor-fault signature that a linear cross-channel / regime residual
detector is almost perfectly matched to. This script sweeps the injection to show
where the framework actually degrades:

  1. magnitude sweep  : temp-channel step bias from 0.25 sigma up to 2.0 sigma
  2. gradual ramp     : bias grows linearly from onset (no clean step)
  3. all-channel bias : bias every measured sensor (tests whether channel-subset
                        matters vs the additive/off-manifold nature)

Rule agent only (fast, deterministic) so we isolate the *feature* difficulty.
"""
import numpy as np

import config as C
import data_ncmapss as D
from preprocess import FeatureExtractor
from rul_tool import RULTool
from build_decisions import gt_label, decision_cycles
from agent import run_rule, finalize
from evaluate import per_scenario, shift_detection

CH_STD = None


def bias_map(sigma, channels, ramp=False):
    """Return a per-channel additive delta (in raw units). ramp handled in loader."""
    return {ch: -sigma * float(CH_STD[ch]) for ch in channels}   # -sigma = adverse


def build_adverse(sigma, channels, tool, fx, ramp=False):
    """Build adverse-scenario packets for unit 11 at a given bias config."""
    unit = C.DIR_A_UNIT
    onset = C.BIAS_ONSET_CYCLE
    # load clean, then inject manually so we can do ramps
    clean = D.load_unit_cycles(unit)
    cyc2idx = {int(c): i for i, c in enumerate(clean["cycles"])}
    wins = clean["windows"].copy()
    life = clean["cycles"].max()
    for i, c in enumerate(clean["cycles"]):
        if c < onset:
            continue
        scale = 1.0 if not ramp else min(1.0, (c - onset) / max(1, (life - onset)))
        for ch in channels:
            wins[i, :, ch] += -sigma * float(CH_STD[ch]) * scale

    dcyc = decision_cycles(clean["cycles"])
    idxs = [cyc2idx[int(c)] for c in dcyc]
    w = wins[idxs]
    rul_pt = tool.predict(w)
    _, rul_std = tool.predict_mc(w)
    packets, hist = [], []
    for k, c in enumerate(dcyc):
        c = int(c); i = cyc2idx[c]
        feat = fx(wins[i])
        hist.append(round(float(rul_pt[k]), 2))
        packets.append({
            "scenario": "adverse", "unit": unit, "fc": clean["fc"], "cycle": c,
            "true_rul": round(float(clean["rul"][i]), 1),
            "gt_label": gt_label(float(clean["rul"][i])),
            "shift_onset_cycle": onset, "is_post_onset": c >= onset,
            "rul": {"point": round(float(rul_pt[k]), 2), "mc_mean": round(float(rul_pt[k]), 2),
                    "mc_std": round(float(rul_std[k]), 3), "history": list(hist[-C.HISTORY_K:])},
            "context": {"flight_class": clean["fc"], "altitude_mean": feat["mean"]["alt"],
                        "mach_mean": feat["mean"]["Mach"], "fan_speed_Nf": feat["mean"]["Nf"],
                        "core_speed_Nc": feat["mean"]["Nc"]},
            "features": feat,
            "z_global_vec": [feat["z_global"][v] for v in C.INPUT_VARS],
        })
    return packets


def eval_cfg(packets, tool, fx):
    votes = run_rule(packets)
    rows = finalize(packets, votes)
    ps = per_scenario(rows, "agent")["adverse"]
    det = shift_detection([{**r, "_flag": r.get("confirmed_shift") or
                            (r["agent"] != "continue" and r.get("shift_detected"))} for r in rows], "_flag")
    # mean discriminator magnitude post-onset
    cons = np.mean([p["features"]["agg"]["temp_consistency_z_abs"]
                    for p in packets if p["is_post_onset"]])
    return ps, det, cons


def main():
    global CH_STD
    CH_STD = np.load(C.OUT_DIR + "/feature_models.npz")["ch_std"]
    tool = RULTool()
    fx = FeatureExtractor()

    print(f"{'config':28s}{'FNR':>6s}{'FPR':>6s}{'F1':>6s}{'shiftR':>8s}{'lat':>5s}{'meanCons':>10s}")
    print("-" * 69)

    # 1) magnitude sweep, temp channels, step
    for s in [0.25, 0.5, 0.75, 1.0, 1.5, 2.0]:
        pk = build_adverse(s, C.TEMP_IDX, tool, fx)
        ps, det, cons = eval_cfg(pk, tool, fx)
        print(f"{'temp4 step ' + f'{s:.2f}sigma':28s}{ps['FNR']:>6.2f}{ps['FPR']:>6.2f}"
              f"{ps['F1']:>6.2f}{det['recall']:>8.2f}{str(det['latency_cycles']):>5s}{cons:>10.2f}")

    print()
    # 2) gradual ramp (reaches 2 sigma at end of life)
    for s in [1.0, 2.0]:
        pk = build_adverse(s, C.TEMP_IDX, tool, fx, ramp=True)
        ps, det, cons = eval_cfg(pk, tool, fx)
        print(f"{'temp4 RAMP ->' + f'{s:.1f}sigma':28s}{ps['FNR']:>6.2f}{ps['FPR']:>6.2f}"
              f"{ps['F1']:>6.2f}{det['recall']:>8.2f}{str(det['latency_cycles']):>5s}{cons:>10.2f}")

    print()
    # 3) all-channel bias (does the channel-subset matter, or just additivity?)
    ALL = list(range(len(C.XS_VARS)))
    for s in [0.5, 2.0]:
        pk = build_adverse(s, ALL, tool, fx)
        ps, det, cons = eval_cfg(pk, tool, fx)
        print(f"{'all14 step ' + f'{s:.2f}sigma':28s}{ps['FNR']:>6.2f}{ps['FPR']:>6.2f}"
              f"{ps['F1']:>6.2f}{det['recall']:>8.2f}{str(det['latency_cycles']):>5s}{cons:>10.2f}")


if __name__ == "__main__":
    main()
