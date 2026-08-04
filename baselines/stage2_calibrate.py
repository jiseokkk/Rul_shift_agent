"""Stage 2: calibration + realized-FA + threshold stability + devset difficulty.

Products (outputs/):
  thresholds.json      -- 9 variants x 2 views = 18 thresholds (+ bootstrap CI)
  stage2_report.json   -- realized FA, stability table, devset pre-check
Run:
  PYTHONPATH=/home/iai4/Desktop <python> -m han.Rul_shift_agent.baselines.stage2_calibrate
"""
import json
import os

import numpy as np

import han.Rul_shift_agent.core.config as C
import han.Rul_shift_agent.core.data_ncmapss as D
from han.Rul_shift_agent.baselines import common as B
from han.Rul_shift_agent.baselines.cusum.core import cusum_bank
from han.Rul_shift_agent.baselines.pca.core import PCAMonitor

THRESH_PATH = os.path.join(C.OUT_DIR, "thresholds.json")
REPORT_PATH = os.path.join(C.OUT_DIR, "stage2_report.json")


class DetectorSuite:
    """9 detector variants: {cusum,t2,spe} x {xs,xsw,regime}."""

    def __init__(self):
        self.vp = B.VectorPipeline()
        train_vecs, self.train_units = B.train_cycle_vectors()
        self.rs = B.Restandardizer(train_vecs)
        self.pca = {v: PCAMonitor(self.rs(v, train_vecs[v]))
                    for v in B.VARIANTS}

    def scores_from_dec(self, dec_list):
        """Decimated flights -> {"cusum_xs": (Ncyc,), ..., 9 keys}."""
        vecs, n_c = self.vp.unit_vectors(dec_list)
        out = {"n_c": n_c}
        for v in B.VARIANTS:
            Z = self.rs(v, vecs[v])
            stat, _ = cusum_bank(Z, k=C.CUSUM_K)
            t2, spe = self.pca[v].scores(Z)
            out[f"cusum_{v}"] = stat
            out[f"t2_{v}"] = t2
            out[f"spe_{v}"] = spe
        return out

    def scores_from_scenario(self, scenario_path):
        dec, cycles, rul = B.load_scenario_series(scenario_path)
        s = self.scores_from_dec(dec)
        s["cycles"] = cycles
        return s


def detector_keys():
    return [f"{d}_{v}" for d in B.DETECTORS for v in B.VARIANTS]


def calibrate(scores_u20):
    """u20 clean scores -> thresholds per detector x view (+ block bootstrap CI)."""
    rng = np.random.default_rng(42)
    cycles = scores_u20["cycles"]
    th = {}
    for key in detector_keys():
        stat = scores_u20[key]
        th[key] = {}
        for view, cfg in B.VIEWS.items():
            pos = B.view_positions(len(cycles), view)
            s = stat[pos]
            q = cfg["q"]
            t = float(np.quantile(s, q))
            # circular block bootstrap (block=5) for quantile CI (plan §4.2)
            n, blk = len(s), 5
            reps = []
            for _ in range(1000):
                starts = rng.integers(0, n, size=int(np.ceil(n / blk)))
                idx = (starts[:, None] + np.arange(blk)[None, :]).ravel() % n
                reps.append(np.quantile(s[idx[:n]], q))
            th[key][view] = {"threshold": t, "q": q, "n_points": int(len(s)),
                             "ci95": [float(np.quantile(reps, 0.025)),
                                      float(np.quantile(reps, 0.975))]}
    return th


def realized_fa(scores, thresholds, label):
    out = {}
    cycles = scores["cycles"]
    for key in detector_keys():
        out[key] = {}
        for view, cfg in B.VIEWS.items():
            al = B.alarm_analysis(scores[key], cycles, view,
                                  thresholds[key][view]["threshold"])
            out[key][view] = B.fa_per_100(al, len(al["pos"]), cfg["every"])
    return {label: out}


def main():
    suite = DetectorSuite()
    dev_dir = os.path.join(B.DATASET_ROOT, "devset")

    # --- calibration on u20 clean (self-contained ctrl_u20) ----------------
    s_u20 = suite.scores_from_scenario(os.path.join(dev_dir, "ctrl_u20"))
    thresholds = calibrate(s_u20)
    with open(THRESH_PATH, "w") as f:
        json.dump(thresholds, f, indent=1)

    report = {"realized_fa_u20": realized_fa(s_u20, thresholds, "u20")["u20"]}

    # --- threshold stability: apply u20 thresholds to clean TRAIN units ----
    stab = {}
    q_pos = {}
    for u in C.TRAIN_UNITS:
        d = D.load_unit_series(u, native=False)
        s = suite.scores_from_dec(d["series"])
        s["cycles"] = d["cycles"]
        stab[f"u{u}"] = realized_fa(s, thresholds, "x")["x"]
        for key in detector_keys():
            pos = B.view_positions(len(d["cycles"]), "native")
            q_pos.setdefault(key, {})[f"u{u}"] = float(
                np.quantile(s[key][pos], 0.99))
    for key in detector_keys():
        q_pos[key]["u20"] = thresholds[key]["native"]["threshold"]
    report["stability_fa_train_units"] = stab
    report["q99_native_by_unit"] = q_pos
    report["stability_note"] = ("train units are IN-SAMPLE for the feature/PCA "
                                "fit -- their scores are biased low; table is "
                                "a diagnostic, not a calibration substitute")

    # --- devset difficulty pre-check (native view, paired vs ctrl_u20) -----
    clean_al = {}
    for key in detector_keys():
        clean_al[key] = B.alarm_analysis(
            s_u20[key], s_u20["cycles"], "native",
            thresholds[key]["native"]["threshold"])
    dev_check = {}
    for name in sorted(os.listdir(dev_dir)):
        if name == "ctrl_u20":
            continue
        sp = json.load(open(os.path.join(dev_dir, name, "spec.json")))
        sc = suite.scores_from_scenario(os.path.join(dev_dir, name))
        row = {}
        for key in detector_keys():
            al = B.alarm_analysis(sc[key], sc["cycles"], "native",
                                  thresholds[key]["native"]["threshold"])
            r = B.classify_scenario(al, clean_al[key], sp["onset_cycle"],
                                    len(sc["cycles"]))
            row[key] = {"status": r["status"], "latency": r["latency"]}
        dev_check[name] = row
    report["devset_precheck_native"] = dev_check

    with open(REPORT_PATH, "w") as f:
        json.dump(report, f, indent=1)

    # --- console summary ---------------------------------------------------
    print("== thresholds (native / comparison) ==")
    for key in detector_keys():
        t = thresholds[key]
        print(f"  {key:12s} {t['native']['threshold']:9.3f} "
              f"(CI {t['native']['ci95'][0]:.2f}-{t['native']['ci95'][1]:.2f}) | "
              f"{t['comparison']['threshold']:9.3f}")
    print("\n== realized FA on u20 (native raw/conf per100cyc) ==")
    for key in detector_keys():
        fa = report["realized_fa_u20"][key]["native"]
        print(f"  {key:12s} raw {fa['raw_per_100cyc']:5.2f}  "
              f"conf {fa['events_per_100cyc']:5.2f}")
    print("\n== devset pre-check (native, status by scenario) ==")
    for name, row in dev_check.items():
        s = " ".join(f"{k.split('_')[0][0]}{k.split('_')[1][:2]}:"
                     f"{row[k]['status'][:4]}" for k in detector_keys())
        print(f"  {name:36s} {s}")
    print(f"\nsaved -> {THRESH_PATH}, {REPORT_PATH}")


if __name__ == "__main__":
    main()
