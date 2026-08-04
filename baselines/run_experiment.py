"""Stage 3: locked-benchmark run — 50 scenarios x 9 detectors x 2 views.

Per plan §8 Stage 3 / §4.5 outputs:
  results/scores/<id>.npz          per-cycle score vectors (§5 schema)
  results/0804_stage3/per_scenario.csv|md   output 1 (5-status, T_fault/T_clean,
                                            advance, latency raw/conf, preFPR)
  results/0804_stage3/aggregates.json       block x detector x view rates
  results/0804_stage3/blockA_coverage.png   output 2 (discrete markers)
  results/0804_stage3/blindspot_matrix.png  output 4
  results/0804_stage3/ladder_table.md       output 5
  results/0804_stage3/matched_count.md      output 6
Run:
  PYTHONPATH=/home/iai4/Desktop <python> -m han.Rul_shift_agent.baselines.run_experiment
"""
import csv
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import han.Rul_shift_agent.core.config as C
from han.Rul_shift_agent.baselines import common as B
from han.Rul_shift_agent.baselines.stage2_calibrate import (DetectorSuite,
                                                            detector_keys)

SCORE_DIR = os.path.join(C.RES_DIR, "scores")
OUT_DIR = os.path.join(C.RES_DIR, "0804_stage3")
THRESH_PATH = os.path.join(C.OUT_DIR, "thresholds.json")


def load_manifest():
    with open(os.path.join(B.DATASET_ROOT, "manifest.csv")) as f:
        return [r for r in csv.DictReader(f)]


def first_raw(stat, cycles, view, threshold, onset):
    pos = B.view_positions(len(cycles), view)
    cyc = cycles[pos]
    hit = (stat[pos] > threshold) & (cyc >= onset)
    idx = np.where(hit)[0]
    return int(cyc[idx[0]]) if len(idx) else None


def main():
    suite = DetectorSuite()
    th = json.load(open(THRESH_PATH))
    manifest = [r for r in load_manifest() if r["split"] == "test"]
    os.makedirs(SCORE_DIR, exist_ok=True)
    os.makedirs(OUT_DIR, exist_ok=True)

    # ---- score all 50 scenarios (log per §5) ------------------------------
    scores = {}
    specs = {}
    for r in manifest:
        sid = r["scenario_id"]
        path = os.path.join(B.DATASET_ROOT, r["path"])
        s = suite.scores_from_scenario(path)
        specs[sid] = json.load(open(os.path.join(path, "spec.json")))
        np.savez(os.path.join(SCORE_DIR, f"{sid}.npz"),
                 cycles=s["cycles"], n_c=s["n_c"],
                 **{k: s[k] for k in detector_keys()})
        scores[sid] = s
        print(f"[stage3] scored {sid}")

    # ---- clean alarm references (paired-clean, per unit x det x view) -----
    clean_al = {}
    for u in (11, 14, 15):
        s = scores[f"ctrl_u{u}"]
        for key in detector_keys():
            for view in B.VIEWS:
                clean_al[(u, key, view)] = B.alarm_analysis(
                    s[key], s["cycles"], view, th[key][view]["threshold"])

    # ---- per-scenario evaluation ------------------------------------------
    rows = []
    for r in manifest:
        sid = r["scenario_id"]
        s = scores[sid]
        sp = specs[sid]
        unit, onset, life = int(r["unit"]), int(sp["onset_cycle"]), len(s["cycles"])
        is_ctrl = sp["mode"] == "none"
        for key in detector_keys():
            for view in B.VIEWS:
                al = B.alarm_analysis(s[key], s["cycles"], view,
                                      th[key][view]["threshold"])
                if is_ctrl:
                    fa = B.fa_per_100(al, len(al["pos"]), B.VIEWS[view]["every"])
                    rows.append(dict(
                        scenario_id=sid, detector=key, view=view, block="ctrl",
                        sigma="", direction="", status="control",
                        fa_raw_100=round(fa["raw_per_100cyc"], 2),
                        fa_conf_100=round(fa["events_per_100cyc"], 2)))
                    continue
                res = B.classify_scenario(al, clean_al[(unit, key, view)],
                                          onset, life)
                h_pen = life - onset
                rows.append(dict(
                    scenario_id=sid, detector=key, view=view,
                    block=r["block"], sigma=r["sigma_mult"],
                    direction=r["direction"], status=res["status"],
                    t_fault=res["t_fault"], t_clean=res["t_clean"],
                    alarm_advance=res["alarm_advance"],
                    latency=res["latency"],
                    latency_raw=(lambda fr: None if fr is None else fr - onset)(
                        first_raw(s[key], s["cycles"], view,
                                  th[key][view]["threshold"], onset)),
                    penalized_delay=(res["latency"]
                                     if res["operational_success"] else h_pen),
                    pre_onset_fpr=round(res["pre_onset_fpr"], 3),
                    had_pre_onset_alarm=res["had_pre_onset_alarm"],
                    operational_success=res["operational_success"],
                    conditional_success=res["conditional_success"]))

    fields = list(dict.fromkeys(sum([list(r.keys()) for r in rows], [])))
    with open(os.path.join(OUT_DIR, "per_scenario.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(rows)

    # ---- aggregates -------------------------------------------------------
    fault_rows = [r for r in rows if r["block"] != "ctrl"]

    def agg(sel):
        n = len(sel)
        return {"n": n,
                "operational": round(sum(r["operational_success"] for r in sel) / n, 3),
                "conditional": round(sum(r["conditional_success"] for r in sel) / n, 3),
                "sat": sum(r["status"] == "SAT" for r in sel),
                "no_effect": sum(r["status"] == "no_effect" for r in sel),
                "miss": sum(r["status"] == "miss" for r in sel),
                "preFA": sum(r["status"] == "preFA_then_detected" for r in sel),
                "mean_latency_success": (round(float(np.mean(
                    [r["latency"] for r in sel if r["operational_success"]])), 1)
                    if any(r["operational_success"] for r in sel) else None),
                "mean_penalized_delay": round(float(np.mean(
                    [r["penalized_delay"] for r in sel])), 1)}

    groups = {}
    for view in B.VIEWS:
        for key in detector_keys():
            for blk in ["A", "B", "C", "D", "E", "F"]:
                sel = [r for r in fault_rows
                       if r["view"] == view and r["detector"] == key
                       and r["block"] == blk]
                if sel:
                    groups[f"{view}|{key}|{blk}"] = agg(sel)
    with open(os.path.join(OUT_DIR, "aggregates.json"), "w") as f:
        json.dump(groups, f, indent=1)

    # ---- output 2: Block A sigma coverage (native, discrete markers) ------
    fig, axes = plt.subplots(3, 3, figsize=(13, 9), sharex=True, sharey=True)
    a_rows = [r for r in fault_rows if r["block"] == "A"
              and r["view"] == "native"]
    for ax, key in zip(axes.ravel(), detector_keys()):
        for r in a_rows:
            if r["detector"] != key:
                continue
            sig = float(r["sigma"])
            d = int(r["direction"])
            ok = r["operational_success"]
            ax.scatter(sig, 1.0 if ok else 0.0,
                       marker="^" if d > 0 else "v",
                       c="tab:green" if ok else "tab:red", s=45, alpha=0.8)
        sigs = sorted({float(r["sigma"]) for r in a_rows})
        cov = [np.mean([r["operational_success"] for r in a_rows
                        if r["detector"] == key and float(r["sigma"]) == s_])
               for s_ in sigs]
        ax.plot(sigs, cov, "-", c="gray", lw=1, alpha=0.7)
        ax.set_title(key, fontsize=9)
        ax.set_xscale("log"); ax.set_ylim(-0.1, 1.1)
    fig.suptitle("Block A: scenario-level detection coverage vs sigma "
                 "(native view; ^ = +, v = -; line = coverage)", fontsize=11)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "blockA_coverage.png"), dpi=120)
    plt.close(fig)

    # ---- output 4: blind-spot matrix (native operational rate) ------------
    blocks = ["A_low", "A_mid", "A_high", "B", "C", "D", "E_gain",
              "E_noise", "E_stuck", "F"]

    def block_of(r):
        if r["block"] == "A":
            s_ = float(r["sigma"])
            return "A_low" if s_ < 0.5 else ("A_mid" if s_ <= 1.0 else "A_high")
        if r["block"] == "E":
            m = specs[r["scenario_id"]]["mode"]
            return f"E_{m}"
        return r["block"]

    M = np.zeros((len(blocks), len(detector_keys())))
    for i, blk in enumerate(blocks):
        for j, key in enumerate(detector_keys()):
            sel = [r for r in fault_rows if r["view"] == "native"
                   and r["detector"] == key and block_of(r) == blk]
            M[i, j] = np.mean([r["operational_success"] for r in sel]) if sel else np.nan
    fig, ax = plt.subplots(figsize=(10, 6))
    im = ax.imshow(M, cmap="RdYlGn", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(detector_keys())),
                  detector_keys(), rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(len(blocks)), blocks, fontsize=9)
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            if not np.isnan(M[i, j]):
                ax.text(j, i, f"{M[i, j]:.2f}", ha="center", va="center",
                        fontsize=8)
    ax.set_title("Operational detection rate (native view) — blind-spot matrix")
    fig.colorbar(im, shrink=0.8)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "blindspot_matrix.png"), dpi=120)
    plt.close(fig)

    # ---- output 5: input-ladder table (natural-unit FPR + Block F) --------
    lad = ["| detector | ctrl_u14 FA raw/conf | ctrl_u15 FA raw/conf | "
           "Block F op.rate | Block F SAT |", "|---|---|---|---|---|"]
    for key in detector_keys():
        cells = []
        for u in (14, 15):
            rr = [r for r in rows if r["scenario_id"] == f"ctrl_u{u}"
                  and r["detector"] == key and r["view"] == "native"][0]
            cells.append(f"{rr['fa_raw_100']}/{rr['fa_conf_100']}")
        fsel = [r for r in fault_rows if r["view"] == "native"
                and r["detector"] == key and r["block"] == "F"]
        a = agg(fsel)
        lad.append(f"| {key} | {cells[0]} | {cells[1]} | "
                   f"{a['operational']} | {a['sat']}/4 |")
    with open(os.path.join(OUT_DIR, "ladder_table.md"), "w") as f:
        f.write("\n".join(lad) + "\n")

    # ---- output 6: matched-count diagnostic -------------------------------
    dec11, cyc11, _ = B.load_scenario_series(
        os.path.join(B.DATASET_ROOT, "controls", "ctrl_u11"))
    lines = ["# Matched-count diagnostic (§4.5-6)", "",
             "confirmed-alarm FPR on clean series, native view", ""]
    def conf_fpr(vecs_scores, cycles):
        out = {}
        for key in detector_keys():
            al = B.alarm_analysis(vecs_scores[key], cycles, "native",
                                  th[key]["native"]["threshold"])
            out[key] = float(al["confirmed"].mean())
        return out
    fpr_full = conf_fpr(scores["ctrl_u11"], cyc11)
    sub = {key: [] for key in detector_keys()}
    for seed in range(10):
        rng = np.random.default_rng(100 + seed)
        vecs, _ = suite.vp.unit_vectors(dec11, subsample_k=4, rng=rng)
        sc = {}
        for v in B.VARIANTS:
            Z = suite.rs(v, vecs[v])
            from han.Rul_shift_agent.baselines.cusum.core import cusum_bank
            sc[f"cusum_{v}"], _ = cusum_bank(Z, k=C.CUSUM_K)
            sc[f"t2_{v}"], sc[f"spe_{v}"] = suite.pca[v].scores(Z)
        f4 = conf_fpr(sc, cyc11)
        for key in detector_keys():
            sub[key].append(f4[key])
    fpr_u14 = conf_fpr(scores["ctrl_u14"],
                       scores["ctrl_u14"]["cycles"])
    lines.append("| detector | u11 full (22w) | u11 4w mean±std [range] | "
                 "u14 (4w natural) | u14 excess vs u11-4w |")
    lines.append("|---|---|---|---|---|")
    for key in detector_keys():
        a = np.array(sub[key])
        lines.append(f"| {key} | {fpr_full[key]:.3f} | "
                     f"{a.mean():.3f}±{a.std():.3f} [{a.min():.3f}-{a.max():.3f}] | "
                     f"{fpr_u14[key]:.3f} | {fpr_u14[key]-a.mean():+.3f} |")
    with open(os.path.join(OUT_DIR, "matched_count.md"), "w") as f:
        f.write("\n".join(lines) + "\n")

    print(f"\n[stage3] rows={len(rows)}  -> {OUT_DIR}")


if __name__ == "__main__":
    main()
