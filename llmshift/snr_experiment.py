"""Two experiments on the refined bias injection (unit 11, rule agent, deterministic).

Difficulty is measured by `cons` = temp_consistency_z_abs, the statistic the rule
detector actually thresholds on (agent.py: real_shift fires when cons>3.0 &
|regime|>5.0, or max_cons>6.0).  Calibrating to `cons` means "cons = X" genuinely
maps to the detector's difficulty.  (Earlier drafts called this "SNR"; the metric
is the same idea but is now defined on the detector statistic and named `cons`.)

A) DIFFICULTY SWEEP — scope = temp4, ramp.  Sweep target cons in {1,2,3,4,6}.
   Locate the cliff (rule threshold is cons>3, so recall should climb near 3-4).

B) sigma vs cons — which knob holds difficulty constant across channel scopes?
   Scopes = {single T48, temp2 (T48+T50), temp4}.
   - sigma method: inject a FIXED sigma into every scope.
   - cons  method: calibrate every scope to the SAME target cons.
   Spread of recall across scopes (max-min) measures control: lower = better.
   sigma cannot hold difficulty constant (same sigma -> different detector signal
   per scope); cons can, by construction.

Injection: drift, 15-cycle ramp, onset 45% life (cycle 27), adverse sign.
Run:
   PYTHONPATH=/home/iai4/Desktop \
     /home/iai4/miniconda3/envs/LLMshift/bin/python \
     -m han.Rul_shift_agent.llmshift.snr_experiment
"""
import json
import numpy as np

import han.Rul_shift_agent.core.config as C
import han.Rul_shift_agent.core.data_ncmapss as D
import han.Rul_shift_agent.injection.inject as I
from han.Rul_shift_agent.core.preprocess import FeatureExtractor
from han.Rul_shift_agent.core.rul_tool import RULTool
from han.Rul_shift_agent.core.build_decisions import gt_label, decision_cycles
from han.Rul_shift_agent.llmshift.agent import run_rule, finalize
from han.Rul_shift_agent.core.evaluate import per_scenario, shift_detection

ONSET_FRAC = 0.45
RAMP_LEN = 15
UNIT = C.DIR_A_UNIT

SCOPES = {
    "single(T48)":   [C.XS_VARS.index("T48")],
    "temp2(T48,T50)": [C.XS_VARS.index("T48"), C.XS_VARS.index("T50")],
    "temp4":         list(C.TEMP_IDX),
}

_CLEAN = None
def clean():
    global _CLEAN
    if _CLEAN is None:
        _CLEAN = D.load_unit_cycles(UNIT)
    return _CLEAN


def inject_windows(delta_map, channels, onset, ramp_len=RAMP_LEN):
    c = clean()
    wins = c["windows"].copy()
    for i, cyc in enumerate(c["cycles"]):
        if cyc < onset:
            continue
        scale = min(1.0, (cyc - onset) / max(1, ramp_len))
        for ch in channels:
            wins[i, :, ch] += delta_map[ch] * scale
    return wins


def detector_signal(wins, onset, fx):
    """Post-onset plateau mean of temp_consistency_z_abs — the rule detector's stat."""
    c = clean()
    vals = []
    for i, cyc in enumerate(c["cycles"]):
        scale = min(1.0, (cyc - onset) / max(1, RAMP_LEN)) if cyc >= onset else 0.0
        if scale < 0.99:
            continue
        vals.append(fx(wins[i])["agg"]["temp_consistency_z_abs"])
    return float(np.mean(vals))


def calibrate_detector(target, channels, onset, fx, det, tol=0.03):
    """Bisect magnitude scalar s (sigma units) so detector_signal == target."""
    def sig_at(s):
        dm = {ch: -s * float(det.ch_std[ch]) for ch in channels}
        return detector_signal(inject_windows(dm, channels, onset), onset, fx)
    lo, hi = 0.0, 12.0
    for _ in range(45):
        mid = 0.5 * (lo + hi)
        if sig_at(mid) < target:
            lo = mid
        else:
            hi = mid
    s = 0.5 * (lo + hi)
    return {ch: -s * float(det.ch_std[ch]) for ch in channels}, sig_at(s)


def build_packets(wins, onset, tool, fx):
    c = clean()
    cyc2idx = {int(cy): i for i, cy in enumerate(c["cycles"])}
    dcyc = decision_cycles(c["cycles"])
    idxs = [cyc2idx[int(cy)] for cy in dcyc]
    rul_pt = tool.predict(wins[idxs])
    _, rul_std = tool.predict_mc(wins[idxs])
    packets, hist = [], []
    for k, cy in enumerate(dcyc):
        cy = int(cy); i = cyc2idx[cy]
        feat = fx(wins[i])
        hist.append(round(float(rul_pt[k]), 2))
        packets.append({
            "scenario": "adverse", "unit": UNIT, "fc": c["fc"], "cycle": cy,
            "true_rul": round(float(c["rul"][i]), 1),
            "gt_label": gt_label(float(c["rul"][i])),
            "shift_onset_cycle": onset, "is_post_onset": cy >= onset,
            "rul": {"point": round(float(rul_pt[k]), 2), "mc_mean": round(float(rul_pt[k]), 2),
                    "mc_std": round(float(rul_std[k]), 3), "history": list(hist[-C.HISTORY_K:])},
            "context": {"flight_class": c["fc"], "altitude_mean": feat["mean"]["alt"],
                        "mach_mean": feat["mean"]["Mach"], "fan_speed_Nf": feat["mean"]["Nf"],
                        "core_speed_Nc": feat["mean"]["Nc"]},
            "features": feat,
            "z_global_vec": [feat["z_global"][v] for v in C.INPUT_VARS],
        })
    return packets


def evaluate(packets, onset):
    votes = run_rule(packets)
    rows = finalize(packets, votes)
    ps = per_scenario(rows, "agent")["adverse"]
    flagged = [{**r, "_flag": r.get("confirmed_shift") or
                (r["agent"] != "continue" and r.get("shift_detected"))} for r in rows]
    det = shift_detection(flagged, "_flag", onset=onset)
    return ps, det


def main():
    tool, fx, det = RULTool(), FeatureExtractor(), I._Detector()
    life = int(clean()["cycles"].max())
    onset = int(round(ONSET_FRAC * life))
    results = {"onset_cycle": onset, "life": life, "detector_stat": "temp_consistency_z_abs"}

    # ---------------- A) difficulty sweep, temp4 ----------------
    print("=" * 80)
    print("A) DIFFICULTY SWEEP  (scope=temp4, ramp)  — rule fires at cons>3")
    print("-" * 80)
    print(f"{'target':>7} | {'realised cons':>13} | {'recall':>7} {'FNR':>6} "
          f"{'F1':>6} {'latency':>8}")
    A = []
    for tgt in [1.0, 2.0, 3.0, 4.0, 6.0]:
        dm, got = calibrate_detector(tgt, SCOPES["temp4"], onset, fx, det)
        wins = inject_windows(dm, SCOPES["temp4"], onset)
        ps, dt = evaluate(build_packets(wins, onset, tool, fx), onset)
        A.append({"target": tgt, "realised_cons": round(got, 2), "recall": dt["recall"],
                  "FNR": ps["FNR"], "F1": ps["F1"], "latency": dt["latency_cycles"]})
        print(f"{tgt:>7.1f} | {got:>13.2f} | {dt['recall']:>7.2f} {ps['FNR']:>6.2f} "
              f"{ps['F1']:>6.2f} {str(dt['latency_cycles']):>8}")
    results["A_difficulty_sweep_temp4"] = A

    # ---------------- B) sigma vs cons across scopes ----------------
    print()
    print("=" * 80)
    print("B) sigma vs cons — hold difficulty constant across channel scopes?")
    print("-" * 80)

    SIGMA_FIX = 0.5
    CONS_TARGET = 4.0
    print(f"  [sigma method]  fixed {SIGMA_FIX} sigma per channel, every scope:")
    print(f"    {'scope':>16} | {'det cons':>9} {'recall':>7} {'FNR':>6}")
    sig = []
    for name, chans in SCOPES.items():
        dm = {ch: -SIGMA_FIX * float(det.ch_std[ch]) for ch in chans}
        wins = inject_windows(dm, chans, onset)
        got = detector_signal(wins, onset, fx)
        ps, dt = evaluate(build_packets(wins, onset, tool, fx), onset)
        sig.append({"scope": name, "det_cons": round(got, 2), "recall": dt["recall"],
                    "FNR": ps["FNR"]})
        print(f"    {name:>16} | {got:>9.2f} {dt['recall']:>7.2f} {ps['FNR']:>6.2f}")

    print(f"  [cons method]   calibrated to detector cons = {CONS_TARGET}, every scope:")
    print(f"    {'scope':>16} | {'det cons':>9} {'recall':>7} {'FNR':>6}")
    snr = []
    for name, chans in SCOPES.items():
        dm, got = calibrate_detector(CONS_TARGET, chans, onset, fx, det)
        wins = inject_windows(dm, chans, onset)
        ps, dt = evaluate(build_packets(wins, onset, tool, fx), onset)
        snr.append({"scope": name, "det_cons": round(got, 2), "recall": dt["recall"],
                    "FNR": ps["FNR"]})
        print(f"    {name:>16} | {got:>9.2f} {dt['recall']:>7.2f} {ps['FNR']:>6.2f}")

    results["B_sigma_method"] = sig
    results["B_snr_method"] = snr
    sig_spread = max(r["recall"] for r in sig) - min(r["recall"] for r in sig)
    snr_spread = max(r["recall"] for r in snr) - min(r["recall"] for r in snr)
    results["B_recall_spread"] = {"sigma": round(sig_spread, 2), "snr": round(snr_spread, 2)}
    print()
    print(f"  recall spread across scopes (lower = better difficulty control):")
    print(f"     sigma method : {sig_spread:.2f}")
    print(f"     cons method  : {snr_spread:.2f}")
    print(f"  --> {'cons controls difficulty better' if snr_spread < sig_spread else 'sigma better'}")

    out = C.RES_DIR + "/snr_experiment.json"
    with open(out, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nsaved -> {out}")


if __name__ == "__main__":
    main()
