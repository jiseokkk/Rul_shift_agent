"""Ablation study (draft §3.6 extended with the Tier-1 / Tier-2 components).

Runs the rule-based reference agent (fast, deterministic) under configurations
that switch off one signal / mechanism at a time, and reports adverse-shift and
natural-shift decision quality.  This isolates the contribution of each addition:

  full            : all Tier-1 signals + Tier-2 mechanisms
  no_consistency  : drop cross-channel consistency residual (Tier-1 #2)
  no_regime       : drop operating-condition-conditioned z (Tier-1 #1)
  no_tier1        : drop BOTH -> agent sees only marginal global z (== CUSUM's view)
  no_uncertainty  : ignore MC-Dropout std (Tier-1 #3)
  no_hysteresis   : Tier-2 #5 off
  no_cost_aware   : Tier-2 #6 off
"""
import json

import han.Rul_shift_agent.config as C
from han.Rul_shift_agent.agent import ABL_FULL, run_rule, finalize
from han.Rul_shift_agent.evaluate import per_scenario, shift_detection

PKT_PATH = C.PKT_DIR + "/packets.json"

CONFIGS = {
    "full":           dict(ABL_FULL),
    "no_consistency": {**ABL_FULL, "use_consistency": False},
    "no_regime":      {**ABL_FULL, "use_regime": False},
    "no_tier1":       {**ABL_FULL, "use_consistency": False, "use_regime": False},
    "no_uncertainty": {**ABL_FULL, "use_uncertainty": False},
    "no_hysteresis":  {**ABL_FULL, "hysteresis": False},
    "no_cost_aware":  {**ABL_FULL, "cost_aware": False},
}


def main():
    packets = json.load(open(PKT_PATH))
    table = {}
    for name, abl in CONFIGS.items():
        votes = run_rule(packets, abl=abl)
        rows = finalize(packets, votes, abl=abl)
        ps = per_scenario(rows, "agent")
        det = shift_detection(
            [{**r, "_flag": r.get("confirmed_shift") or (r["agent"] != "continue" and r.get("shift_detected"))}
             for r in rows], "_flag")
        table[name] = {"adverse": ps["adverse"], "natural": ps["natural"],
                       "no_shift": ps["no_shift"], "shift_det_F1": det["F1"],
                       "latency": det["latency_cycles"]}
    with open(C.RES_DIR + "/ablation.json", "w") as f:
        json.dump(table, f, indent=2)

    print(f"\n=== ABLATION (rule agent) ===")
    print(f"{'config':16s}{'adverse FNR/FPR/F1':>22s}{'natural FNR/FPR/F1':>22s}"
          f"{'noShift F1':>12s}{'shiftF1':>9s}{'lat':>5s}")
    for name, d in table.items():
        a, n = d["adverse"], d["natural"]
        print(f"{name:16s}"
              f"{a['FNR']:.2f}/{a['FPR']:.2f}/{a['F1']:.2f}".rjust(22)
              + f"{n['FNR']:.2f}/{n['FPR']:.2f}/{n['F1']:.2f}".rjust(22)
              + f"{d['no_shift']['F1']:.2f}".rjust(12)
              + f"{d['shift_det_F1']:.2f}".rjust(9)
              + f"{str(d['latency']):>5s}")
    print(f"\n[ablation] -> {C.RES_DIR}/ablation.json")


if __name__ == "__main__":
    main()
