"""Evaluation (draft §4): decision quality + shift detection, all methods.

Positive (maintenance-required) class = {inspect, replace}.
  FNR = fraction of true-positive points assigned continue   (safety-critical)
  FPR = fraction of true-negative points assigned inspect/replace (cost)
  F1  = F1 of the positive class.

Shift detection (Direction A adverse): ground truth = post-onset points.
Latency = first post-onset cycle a method escalates off 'continue'.
"""
import glob
import json
import os

import config as C

SCENARIOS = ["no_shift", "adverse", "favorable", "natural"]


def _pos(label):
    return label in ("inspect", "replace")


def decision_metrics(rows, pred_key):
    tp = fp = fn = tn = 0
    for r in rows:
        gt, pr = _pos(r["gt_label"]), _pos(r[pred_key])
        tp += gt and pr
        fp += (not gt) and pr
        fn += gt and (not pr)
        tn += (not gt) and (not pr)
    P = tp + fn
    N = fp + tn
    fnr = fn / P if P else 0.0
    fpr = fp / N if N else 0.0
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / P if P else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    return {"FNR": round(fnr, 2), "FPR": round(fpr, 2), "F1": round(f1, 2),
            "n": len(rows), "P": P, "N": N}


def per_scenario(rows, pred_key):
    return {s: decision_metrics([r for r in rows if r["scenario"] == s], pred_key)
            for s in SCENARIOS}


def shift_detection(rows_with_flag, flag_key, onset=C.BIAS_ONSET_CYCLE):
    """rows: adverse scenario rows carrying a boolean shift flag + cycle."""
    rows = [r for r in rows_with_flag if r["scenario"] == "adverse"]
    tp = fp = fn = tn = 0
    first_detect = None
    for r in sorted(rows, key=lambda x: x["cycle"]):
        gt = r["cycle"] >= onset
        pr = bool(r.get(flag_key))
        tp += gt and pr
        fp += (not gt) and pr
        fn += gt and (not pr)
        tn += (not gt) and (not pr)
        if gt and pr and first_detect is None:
            first_detect = r["cycle"]
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    latency = (first_detect - onset) if first_detect is not None else None
    return {"precision": round(prec, 2), "recall": round(rec, 2), "F1": round(f1, 2),
            "first_detect_cycle": first_detect, "latency_cycles": latency}


def escalation_flag_rows(rows, pred_key):
    """Derive a 'escalated off continue' flag for latency/detection on any method."""
    return [{**r, "_flag": r[pred_key] != "continue"} for r in rows]


def main():
    base = json.load(open(C.RES_DIR + "/baseline_decisions.json"))
    metrics = {"decision_quality": {}, "shift_detection": {}}

    # baselines
    metrics["decision_quality"]["threshold"] = per_scenario(base, "threshold")
    metrics["decision_quality"]["cusum"] = per_scenario(base, "cusum")

    # agents (whichever decision files exist)
    agent_files = {os.path.basename(p).replace("agent_decisions_", "").replace(".json", ""): p
                   for p in glob.glob(C.RES_DIR + "/agent_decisions_*.json")}
    agent_rows = {}
    for name, path in agent_files.items():
        rows = json.load(open(path))
        agent_rows[name] = rows
        metrics["decision_quality"][f"agent_{name}"] = per_scenario(rows, "agent")

    # shift detection — CUSUM (alarm flag) vs agents (confirmed_shift flag)
    metrics["shift_detection"]["cusum"] = shift_detection(
        escalation_flag_rows(base, "cusum"), "_flag")
    for name, rows in agent_rows.items():
        # use the agent's shift signal (post-hysteresis confirmed) for detection
        flagged = [{**r, "_flag": r.get("confirmed_shift") or (r["agent"] != "continue" and r.get("shift_detected"))}
                   for r in rows]
        metrics["shift_detection"][f"agent_{name}"] = shift_detection(flagged, "_flag")

    with open(C.RES_DIR + "/metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    # pretty print
    print("\n=== DECISION QUALITY (FNR / FPR / F1) ===")
    hdr = f"{'method':16s}" + "".join(f"{s:>22s}" for s in SCENARIOS)
    print(hdr)
    for m, d in metrics["decision_quality"].items():
        cells = ""
        for s in SCENARIOS:
            q = d[s]
            cells += f"{q['FNR']:.2f}/{q['FPR']:.2f}/{q['F1']:.2f}".rjust(22)
        print(f"{m:16s}{cells}")
    print("\n=== SHIFT DETECTION (Direction A adverse) ===")
    for m, d in metrics["shift_detection"].items():
        print(f"{m:16s} P={d['precision']:.2f} R={d['recall']:.2f} F1={d['F1']:.2f}"
              f"  latency={d['latency_cycles']} cycles (first@{d['first_detect_cycle']})")
    print(f"\n[evaluate] metrics -> {C.RES_DIR}/metrics.json")


if __name__ == "__main__":
    main()
