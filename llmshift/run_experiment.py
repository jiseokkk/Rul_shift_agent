"""Run the refined-injection experiment through the current decision pipeline.

Replaces the legacy +-2sigma temp step with the cons-calibrated drift-ramp
injection, keeps the benign controls, and evaluates the rule agent.

Scenarios (unit 11 = Direction A, units 14/15 = Direction B natural shift):
  no_shift         unit 11 clean                                  (must NOT alarm)
  adverse_single   unit 11  T48    drift-ramp15  cons=4  sign -   (hide degradation; MUST catch)
  adverse_temp4    unit 11  temp4  drift-ramp15  cons=4  sign -   (same difficulty, 4 channels)
  favorable        unit 11  T48    drift-ramp15  cons=4  sign +   (over-pessimistic; don't over-react)
  natural          units 14,15 clean (Fc1/Fc2)                    (benign shift; must NOT alarm)

Metrics: per-scenario FNR (miss real maintenance need) / FPR (false alarm) / F1,
plus shift-detection recall & latency on the adverse scenarios.

Writes packets to packets/packets_refined.json for a later LLM run.
Run:
  PYTHONPATH=/home/iai4/Desktop \
    /home/iai4/miniconda3/envs/LLMshift/bin/python \
    -m han.Rul_shift_agent.llmshift.run_experiment
"""
import argparse
import json
import numpy as np

import han.Rul_shift_agent.core.config as C
import han.Rul_shift_agent.core.data_ncmapss as D
import han.Rul_shift_agent.injection.inject as I
from han.Rul_shift_agent.core.preprocess import FeatureExtractor
from han.Rul_shift_agent.core.build_decisions import gt_label, decision_cycles
from han.Rul_shift_agent.llmshift.agent import run_rule, run_llm, finalize
from han.Rul_shift_agent.core.evaluate import decision_metrics


def shift_recall(srows, onset):
    """Shift-detection recall & latency on this scenario's post-onset points.

    NOTE: evaluate.shift_detection() hardcodes scenario=='adverse' and cannot be
    used here (our scenarios are 'adverse_single' / 'adverse_temp4').
    """
    post = [r for r in srows if r["cycle"] >= onset]
    flags = [(r["cycle"], bool(r.get("confirmed_shift") or
             (r["agent"] != "continue" and r.get("shift_detected")))) for r in post]
    tp = sum(1 for _, f in flags if f)
    first = next((c for c, f in sorted(flags) if f), None)
    return {"recall": round(tp / len(flags), 2) if flags else 0.0,
            "latency_cycles": (first - onset) if first is not None else None,
            "n_post": len(flags)}

ONSET_FRAC = 0.45
RAMP_LEN = 15
CONS_TARGET = 4.0
T48 = C.XS_VARS.index("T48")

# scenario -> (units, channels|None, sign)  ; None channels = clean (no injection)
SCEN = {
    "no_shift":       ([C.DIR_A_UNIT], None, 0),
    "adverse_single": ([C.DIR_A_UNIT], [T48], -1),
    "adverse_temp4":  ([C.DIR_A_UNIT], list(C.TEMP_IDX), -1),
    "favorable":      ([C.DIR_A_UNIT], [T48], +1),
    "natural":        (C.DIR_B_UNITS, None, 0),
}


def inject_ramp(windows, cycles, channels, delta_map, onset):
    wins = windows.copy()
    for i, c in enumerate(cycles):
        if c < onset:
            continue
        scale = min(1.0, (c - onset) / max(1, RAMP_LEN))
        for ch in channels:
            wins[i, :, ch] += delta_map[ch] * scale
    return wins


def build_scenario(name, tool, fx, det):
    units, channels, sign = SCEN[name]
    packets = []
    meta = {}
    for unit in units:
        d = D.load_unit_cycles(unit)
        cycles = d["cycles"]
        life = int(cycles.max())
        onset = int(round(ONSET_FRAC * life)) if channels else None
        wins = d["windows"]

        if channels:                       # calibrate to cons=4 and inject ramp
            delta, realised = I.calibrate_to_detector(
                CONS_TARGET, channels, wins, cycles, onset, RAMP_LEN, fx, det)
            if sign > 0:                   # favorable: same magnitude, opposite direction
                delta = {ch: -v for ch, v in delta.items()}
            wins = inject_ramp(wins, cycles, channels, delta, onset)
            meta[unit] = {"onset": onset, "realised_cons": round(realised, 2),
                          "delta": {C.XS_VARS[k]: round(v, 2) for k, v in delta.items()}}

        cyc2idx = {int(c): i for i, c in enumerate(cycles)}
        dcyc = decision_cycles(cycles)
        idxs = [cyc2idx[int(c)] for c in dcyc]
        rul_pt = tool.predict(wins[idxs])
        _, rul_std = tool.predict_mc(wins[idxs])
        hist = []
        for k, c in enumerate(dcyc):
            c = int(c); i = cyc2idx[c]
            feat = fx(wins[i]); tr = float(d["rul"][i])
            hist.append(round(float(rul_pt[k]), 2))
            packets.append({
                "scenario": name, "unit": unit, "fc": d["fc"], "cycle": c,
                "true_rul": round(tr, 1), "gt_label": gt_label(tr),
                "shift_onset_cycle": onset,
                "is_post_onset": bool(onset is not None and c >= onset),
                "rul": {"point": round(float(rul_pt[k]), 2), "mc_mean": round(float(rul_pt[k]), 2),
                        "mc_std": round(float(rul_std[k]), 3), "history": list(hist[-C.HISTORY_K:])},
                "context": {"flight_class": d["fc"],
                            "altitude_mean": round(float(feat["mean"]["alt"]), 1),
                            "mach_mean": round(float(feat["mean"]["Mach"]), 4),
                            "fan_speed_Nf": round(float(feat["mean"]["Nf"]), 2),
                            "core_speed_Nc": round(float(feat["mean"]["Nc"]), 2)},
                "features": feat,
                "z_global_vec": [feat["z_global"][v] for v in C.INPUT_VARS],
            })
    return packets, meta


PKT_REFINED = C.PKT_DIR + "/packets_refined.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", choices=["rule", "llm"], default="rule")
    ap.add_argument("--gpu_mem", type=float, default=0.90)
    ap.add_argument("--reuse", action="store_true", help="reuse saved packets_refined.json")
    args = ap.parse_args()

    tool, fx, det = RULTool_(), FeatureExtractor(), I._Detector()
    if args.reuse:
        import os
        with open(PKT_REFINED) as f:
            all_pk = json.load(f)
        meta_path = C.RES_DIR + "/experiment_refined_meta.json"
        metas = json.load(open(meta_path)) if os.path.exists(meta_path) else {}
    else:
        all_pk, metas = [], {}
        for name in SCEN:
            pk, meta = build_scenario(name, tool, fx, det)
            all_pk.extend(pk); metas[name] = meta
        with open(PKT_REFINED, "w") as f:
            json.dump(all_pk, f, indent=1)
        with open(C.RES_DIR + "/experiment_refined_meta.json", "w") as f:
            json.dump(metas, f, indent=2)

    if args.agent == "llm":
        raw = C.PKT_DIR + "/refined_llm_raw.jsonl"
        votes = run_llm(all_pk, gpu_mem=args.gpu_mem, raw_path=raw)
    else:
        votes = run_rule(all_pk)
    rows = finalize(all_pk, votes)

    print("=" * 74)
    print(f"REFINED-INJECTION EXPERIMENT — {args.agent} agent  "
          f"(cons=4, drift-ramp15, onset45%)")
    print("=" * 74)
    print(f"{'scenario':>16} | {'n':>3} {'FNR':>6} {'FPR':>6} {'F1':>6} | "
          f"{'shiftRecall':>11} {'latency':>8}  cons")
    print("-" * 74)
    summary = {}
    for name in SCEN:
        srows = [r for r in rows if r["scenario"] == name]
        dm = decision_metrics(srows, "agent")
        line = f"{name:>16} | {dm['n']:>3} {dm['FNR']:>6.2f} {dm['FPR']:>6.2f} {dm['F1']:>6.2f} | "
        det_str = ""
        if name.startswith("adverse"):
            onset = list(metas[name].values())[0]["onset"]
            sd = shift_recall(srows, onset)
            cons = list(metas[name].values())[0]["realised_cons"]
            det_str = f"{sd['recall']:>11.2f} {str(sd['latency_cycles']):>8}  {cons}"
            summary[name] = {**dm, "shift_recall": sd["recall"], "latency": sd["latency_cycles"]}
        else:
            det_str = f"{'—':>11} {'—':>8}"
            summary[name] = dm
        print(line + det_str)
    print("-" * 74)
    print("read: adverse_* want FNR low + shiftRecall high; no_shift/natural want FPR low.")

    out = C.RES_DIR + f"/experiment_refined_{args.agent}.json"
    with open(out, "w") as f:
        json.dump({"agent": args.agent,
                   "config": {"cons_target": CONS_TARGET, "ramp_len": RAMP_LEN,
                              "onset_frac": ONSET_FRAC}, "meta": metas,
                   "summary": summary}, f, indent=2)
    print(f"\npackets -> {PKT_REFINED}")
    print(f"summary -> {out}")


def RULTool_():
    from han.Rul_shift_agent.core.rul_tool import RULTool
    return RULTool()


if __name__ == "__main__":
    main()
