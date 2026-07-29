"""Baseline-grid experiment (plan: docs/0729_ncmapss_shift_detection_baseline_plan.md).

Builds the difficulty x scenario grid of sensor-bias datasets and runs the
minimal detector suite under a common protocol, to locate blind spots and pick
the appropriate difficulty band.  Detection axis ONLY (plan section 8.1/8.2);
RUL impact is recorded as metadata for the dangerous-silent-shift analysis.

Scenario grid (sigma = raw channel std units):
  Case 0  controls          : no_shift (u11), natural (u14/u15 clean, Fc1/Fc2)
  Case 1  single T48        : {step, ramp15} x {0.5,1,2}s x {neg,pos}
          + refinement      : ramp15 x {0.15,0.25,0.35}s x {neg,pos}
  Case 2  temp4 inconsistent: ramp15 x {0.5,1,2}s x {neg,pos}, mixed-sign pattern
  Case 3  coordinated PC1   : ramp15 x {0.5,1,2,3,4}s x {neg,pos}
  Case 4  fault on natural  : u14/u15, T48 ramp15 1s x {neg,pos}  (unit-scenario decoupling)

Protocol (plan section 7, decisions 0729 in section 13.3):
  - thresholds: FA <= 1/100 cycles on clean validation unit 20 -> q-quantile of
    the u20 decision-cadence statistic, q = 1 - DECISION_EVERY/100 = 0.97
  - common 2-consecutive-point hysteresis; raw AND hysteresis both reported
  - rule agent keeps its fixed cause gate (not quantile-calibrated; stated)

Datasets are persisted to dataset/corrupted_grid/<scenario>__u<unit>/
(windows.npz + spec.json) for reproducibility and later MC-TIRE training.

Run:
  PYTHONPATH=/home/iai4/Desktop /home/iai4/miniconda3/envs/LLMshift/bin/python \
      -m han.Rul_shift_agent.baselines.grid_experiment
"""
import json
import os

import numpy as np

import han.Rul_shift_agent.core.config as C
import han.Rul_shift_agent.core.data_ncmapss as D
from han.Rul_shift_agent.core.preprocess import FeatureExtractor
from han.Rul_shift_agent.core.build_decisions import gt_label, decision_cycles
from han.Rul_shift_agent.llmshift.agent import run_rule, finalize
from han.Rul_shift_agent.baselines.cusum import cusum_stats

MAGS = [0.5, 1.0, 2.0]
MAGS_FINE = [0.15, 0.25, 0.35]          # Case-1 cliff hunt
MAGS_C3_HI = [3.0, 4.0]                 # Case-3 dangerous-silent hunt
RAMP_LEN = 15
ONSET_FRAC = 0.45
HYST_N = 2
FA_PER_100 = 1.0                        # allowed clean false alarms per 100 cycles
Q = 1.0 - FA_PER_100 * C.DECISION_EVERY / 100.0     # 0.97
T48 = C.XS_VARS.index("T48")
INCONSISTENT = {0: +1.0, 1: -0.6, 2: +0.8, 3: -1.2}

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # repo root
DSET_DIR = os.path.join(HERE, "dataset", "corrupted_grid")
RES_PATH = C.RES_DIR + "/grid_experiment.json"
MD_PATH = C.RES_DIR + "/grid_experiment.md"


# --------------------------------------------------------------------------- #
# Scenario grid
# --------------------------------------------------------------------------- #
def pc1_loading(fx):
    """First principal direction of healthy per-cycle sensor z-vectors (14 XS),
    normalised to max|v|=1 so `sigma * v` is comparable to Case-1 magnitudes."""
    zs = []
    for u in C.TRAIN_UNITS:
        d = D.load_unit_cycles(u)
        for w in d["windows"]:
            m = w.mean(0)[:14]
            zs.append((m - fx.ch_mean[:14]) / fx.ch_std[:14])
    Z = np.array(zs) - np.array(zs).mean(0)
    _, _, vt = np.linalg.svd(Z, full_matrices=False)
    v = vt[0]
    return v / np.abs(v).max()


def make_grid(fx):
    grid = [
        {"name": "no_shift", "case": 0, "units": [C.DIR_A_UNIT], "pattern": None},
        {"name": "natural", "case": 0, "units": C.DIR_B_UNITS, "pattern": None},
    ]

    def add(name, case, units, profile, mag, sign, pattern):
        grid.append({"name": name, "case": case, "units": units, "profile": profile,
                     "mag": mag, "sign": sign, "pattern": pattern})

    for prof in ("step", "ramp"):
        for s in MAGS:
            for sign, sg in ((-1, "neg"), (+1, "pos")):
                add(f"c1_T48_{prof}_{s:g}s_{sg}", 1, [C.DIR_A_UNIT],
                    prof, s, sign, {T48: 1.0})
    for s in MAGS_FINE:                                   # refinement (ramp only)
        for sign, sg in ((-1, "neg"), (+1, "pos")):
            add(f"c1_T48_ramp_{s:g}s_{sg}", 1, [C.DIR_A_UNIT],
                "ramp", s, sign, {T48: 1.0})
    for s in MAGS:
        for sign, sg in ((-1, "neg"), (+1, "pos")):
            add(f"c2_temp4mix_ramp_{s:g}s_{sg}", 2, [C.DIR_A_UNIT],
                "ramp", s, sign, dict(INCONSISTENT))
    v1 = pc1_loading(fx)
    pc1 = {i: float(v1[i]) for i in range(14)}
    for s in MAGS + MAGS_C3_HI:
        for sign, sg in ((-1, "neg"), (+1, "pos")):
            add(f"c3_coord_pc1_ramp_{s:g}s_{sg}", 3, [C.DIR_A_UNIT],
                "ramp", s, sign, dict(pc1))
    for unit in C.DIR_B_UNITS:                            # fault on natural units
        for sign, sg in ((-1, "neg"), (+1, "pos")):
            add(f"c4_natural_fault_u{unit}_{sg}", 4, [unit],
                "ramp", 1.0, sign, {T48: 1.0})

    # ---- FaultSpec axis sweeps (anchor: T48, ramp15, 1sigma) ---- #
    def add_m(name, case, profile, mag, sign, pattern, mode):
        grid.append({"name": name, "case": case, "units": [C.DIR_A_UNIT],
                     "profile": profile, "mag": mag, "sign": sign,
                     "pattern": pattern, "mode": mode})

    for sign, sg in ((-1, "neg"), (+1, "pos")):           # M: fault modes
        add_m(f"m_gain_T48_ramp_1s_{sg}", 5, "ramp", 1.0, sign, {T48: 1.0}, "gain")
    add_m("m_noise_T48_ramp_1s", 5, "ramp", 1.0, +1, {T48: 1.0}, "noise")
    add_m("m_stuck_T48", 5, "step", 1.0, +1, {T48: 1.0}, "stuck")
    for sign, sg in ((-1, "neg"), (+1, "pos")):           # P: temporal profiles
        add_m(f"p_exp_T48_1s_{sg}", 6, "exp", 1.0, sign, {T48: 1.0}, "add")
        add_m(f"p_int_T48_1s_{sg}", 6, "intermittent", 1.0, sign, {T48: 1.0}, "add")
    for sign, sg in ((-1, "neg"), (+1, "pos")):           # S: all14 uniform scope
        add_m(f"s_all14_ramp_1s_{sg}", 7, "ramp", 1.0, sign,
              {i: 1.0 for i in range(14)}, "add")
    return grid


# --------------------------------------------------------------------------- #
# Packet building + dataset persistence
# --------------------------------------------------------------------------- #
def profile_scale(profile, c, onset, rng):
    """Magnitude multiplier b(c) in [0,1] for cycle c >= onset."""
    if profile == "step":
        return 1.0
    if profile == "ramp":
        return min(1.0, (c - onset) / RAMP_LEN)
    if profile == "exp":
        return float(1.0 - np.exp(-(c - onset) / RAMP_LEN))
    if profile == "intermittent":       # latent 30% firing until 2L past onset
        if c - onset >= 2 * RAMP_LEN:
            return 1.0
        return 1.0 if rng.random() < 0.3 else 0.0
    raise ValueError(profile)


def inject_windows(windows, cycles, delta, onset, profile, mode="add",
                   fx=None, seed=0):
    """Window-level corruption. delta = {ch: magnitude in raw units} (for gain:
    interpreted relative to ch_mean; for noise: used as the noise std; for
    stuck: ignored — channel frozen at its onset-cycle window)."""
    wins = windows.copy()
    rng = np.random.default_rng(seed)
    frozen = {}
    for i, c in enumerate(cycles):
        if c < onset:
            continue
        b = profile_scale(profile, c, onset, rng)
        for ch, dv in delta.items():
            if mode == "add":
                wins[i, :, ch] += dv * b
            elif mode == "gain":
                wins[i, :, ch] *= 1.0 + (dv / float(fx.ch_mean[ch])) * b
            elif mode == "noise":
                wins[i, :, ch] += rng.normal(0.0, abs(dv) * max(b, 1e-9),
                                             size=wins.shape[1])
            elif mode == "stuck":
                if ch not in frozen:
                    frozen[ch] = windows[i, :, ch].copy()
                wins[i, :, ch] = frozen[ch]
            else:
                raise ValueError(mode)
    return wins


_CLEAN_CACHE = {}
def clean_ref(unit, tool):
    if unit in _CLEAN_CACHE:
        return _CLEAN_CACHE[unit]
    d = D.load_unit_cycles(unit)
    cycles = d["cycles"]
    cyc2idx = {int(c): i for i, c in enumerate(cycles)}
    dcyc = [int(c) for c in decision_cycles(cycles)]
    idxs = [cyc2idx[c] for c in dcyc]
    _CLEAN_CACHE[unit] = {"data": d, "dcyc": dcyc, "idxs": idxs,
                          "rul_clean": tool.predict(d["windows"][idxs])}
    return _CLEAN_CACHE[unit]


def save_dataset(scen, unit, wins, cycles, true_rul, spec):
    out = os.path.join(DSET_DIR, f"{scen['name']}__u{unit}")
    os.makedirs(out, exist_ok=True)
    np.savez_compressed(os.path.join(out, "windows.npz"),
                        windows=wins.astype(np.float32),
                        cycles=np.asarray(cycles),
                        true_rul=np.asarray(true_rul, dtype=np.float32))
    with open(os.path.join(out, "spec.json"), "w") as f:
        json.dump(spec, f, indent=2)


def build_packets(scen, tool, fx):
    packets, meta = [], {}
    for unit in scen["units"]:
        ref = clean_ref(unit, tool)
        d, dcyc, idxs = ref["data"], ref["dcyc"], ref["idxs"]
        cycles = d["cycles"]
        life = int(cycles.max())
        onset = None
        wins = d["windows"]

        if scen["pattern"]:
            onset = int(round(ONSET_FRAC * life))
            mode = scen.get("mode", "add")
            delta = {ch: scen["sign"] * scen["mag"] * float(fx.ch_std[ch]) * coef
                     for ch, coef in scen["pattern"].items()}
            wins = inject_windows(wins, cycles, delta, onset, scen["profile"],
                                  mode=mode, fx=fx, seed=scen.get("seed", 0))
            meta[unit] = {"onset": onset, "life": life, "mode": mode,
                          "delta": {C.XS_VARS[k]: round(v, 3) for k, v in delta.items()}}

        rul_pt = tool.predict(wins[idxs])
        _, rul_std = tool.predict_mc(wins[idxs])
        hist, cons_plateau, regime_plateau = [], [], []
        for k, c in enumerate(dcyc):
            i = idxs[k]
            feat = fx(wins[i])
            tr = float(d["rul"][i])
            hist.append(round(float(rul_pt[k]), 2))
            if onset is not None and c >= onset + (0 if scen["profile"] == "step" else RAMP_LEN):
                cons_plateau.append(feat["agg"]["temp_consistency_z_abs"])
                regime_plateau.append(feat["agg"]["temp_regime_z_signed"])
            packets.append({
                "scenario": scen["name"], "unit": unit, "fc": d["fc"], "cycle": c,
                "true_rul": round(tr, 1), "gt_label": gt_label(tr),
                "shift_onset_cycle": onset,
                "is_post_onset": bool(onset is not None and c >= onset),
                "rul": {"point": round(float(rul_pt[k]), 2),
                        "mc_mean": round(float(rul_pt[k]), 2),
                        "mc_std": round(float(rul_std[k]), 3),
                        "history": list(hist[-C.HISTORY_K:])},
                "features": feat,
                "z_global_vec": [feat["z_global"][v] for v in C.INPUT_VARS],
            })
        if onset is not None:
            post = [k for k, c in enumerate(dcyc) if c >= onset]
            rul_diff = np.abs(rul_pt[post] - ref["rul_clean"][post])
            true_post = np.array([float(d["rul"][idxs[k]]) for k in post])
            rmse = lambda a, b: round(float(np.sqrt(np.mean(
                (np.minimum(a, C.RUL_CAP) - np.minimum(b, C.RUL_CAP)) ** 2))), 2)
            meta[unit].update({
                "realised_cons_plateau": round(float(np.mean(cons_plateau)), 2) if cons_plateau else None,
                "realised_regime_plateau": round(float(np.mean(regime_plateau)), 2) if regime_plateau else None,
                "rul_impact_meanabs": round(float(rul_diff.mean()), 2),
                "rul_rmse_clean": rmse(ref["rul_clean"][post], true_post),
                "rul_rmse_corrupt": rmse(rul_pt[post], true_post),
            })
            spec = {"scenario_id": f"{scen['name']}__u{unit}", "unit": unit,
                    "flight_class": int(d["fc"]), "case": scen["case"],
                    "fault_channels": [C.XS_VARS[ch] for ch in scen["pattern"]],
                    "fault_pattern": {C.XS_VARS[ch]: v for ch, v in scen["pattern"].items()},
                    "fault_profile": scen["profile"], "ramp_length": RAMP_LEN,
                    "injection_onset": onset, "onset_frac": ONSET_FRAC,
                    "direction": "neg" if scen["sign"] < 0 else "pos",
                    "sigma_magnitude": scen["mag"], **meta[unit],
                    "clean_rul_prediction": [round(float(x), 2) for x in ref["rul_clean"]],
                    "corrupted_rul_prediction": [round(float(x), 2) for x in rul_pt],
                    "decision_cycles": dcyc}
            save_dataset(scen, unit, wins, cycles, d["rul"], spec)
    return packets, meta


# --------------------------------------------------------------------------- #
# Detectors under the common protocol
# --------------------------------------------------------------------------- #
def q_thresh(vals, q=Q):
    return float(np.quantile(np.asarray(vals, dtype=float), q))


class PCAMonitor:
    """PCA T^2 / SPE(Q) on the same z_global vectors CUSUM sees.
    Fit on clean TRAIN_UNITS (per-cycle); limits = Q-quantile of the clean
    validation unit's decision-cadence statistics (FA<=1/100cyc protocol)."""

    def __init__(self, fx, ev_target=0.90):
        Z = []
        for u in C.TRAIN_UNITS:
            d = D.load_unit_cycles(u)
            for w in d["windows"]:
                f = fx(w)
                Z.append([f["z_global"][v] for v in C.INPUT_VARS])
        Z = np.array(Z)
        self.mu = Z.mean(0)
        Zc = Z - self.mu
        _, S, Vt = np.linalg.svd(Zc, full_matrices=False)
        ev = (S ** 2) / (len(Z) - 1)
        k = int(np.searchsorted(np.cumsum(ev) / ev.sum(), ev_target) + 1)
        self.P = Vt[:k].T
        self.lam = ev[:k]
        self.k = k

    def stats(self, zvec):
        x = np.asarray(zvec) - self.mu
        t = x @ self.P
        t2 = float(np.sum(t * t / self.lam))
        resid = x - self.P @ t
        return t2, float(resid @ resid)

    def calibrate(self, val_zseq):
        pairs = [self.stats(z) for z in val_zseq]
        self.t2_lim = q_thresh([t for t, _ in pairs])
        self.spe_lim = q_thresh([s for _, s in pairs])


def val_zseq(fx):
    d = D.load_unit_cycles(C.VAL_UNIT)
    cyc2idx = {int(c): i for i, c in enumerate(d["cycles"])}
    return np.array([[fx(d["windows"][cyc2idx[int(c)]])["z_global"][v]
                      for v in C.INPUT_VARS] for c in decision_cycles(d["cycles"])])


def hyst_confirm(alarms, n=HYST_N):
    out, run = [], 0
    for a in alarms:
        run = run + 1 if a else 0
        out.append(run >= n)
    return out


# --------------------------------------------------------------------------- #
# Metrics (plan section 8.1, raw + hysteresis)
# --------------------------------------------------------------------------- #
def series_metrics(dcyc, raw_alarms, onset):
    conf = hyst_confirm(raw_alarms)

    def side(al):
        span = dcyc[-1] - dcyc[0] + 1
        if onset is None:
            fa = int(sum(al))
            first = next((c for c, a in zip(dcyc, al) if a), None)
            return {"fa_points": fa, "n_points": len(dcyc),
                    "fa_per_100cyc": round(100.0 * fa / span, 1),
                    "first_fa_cycle": first}
        post = [(c, a) for c, a in zip(dcyc, al) if c >= onset]
        pre = [(c, a) for c, a in zip(dcyc, al) if c < onset]
        tp = sum(a for _, a in post)
        fp = sum(a for _, a in pre)
        prec = tp / (tp + fp) if (tp + fp) else None
        rec = tp / max(1, len(post))
        f1 = (2 * prec * rec / (prec + rec)) if (prec not in (None, 0) and rec) else (0.0 if tp == 0 else None)
        first = next((c for c, a in post if a), None)
        return {"event_detected": bool(first is not None),
                "latency_cycles": None if first is None else int(first - onset),
                "point_recall": round(rec, 2),
                "precision": None if prec is None else round(prec, 2),
                "f1": None if f1 is None else round(f1, 2),
                "pre_onset_fa": int(fp)}

    return {"raw": side(raw_alarms), "hyst": side(conf)}


def pooled_harmful(point_log):
    """Plan section 8.2: positives = injected post-onset points; negatives =
    controls (all points) + injected pre-onset points.  Per detector."""
    out = {}
    for det in sorted({r["det"] for r in point_log}):
        rows = [r for r in point_log if r["det"] == det]
        tp = sum(1 for r in rows if r["pos"] and r["alarm"])
        fn = sum(1 for r in rows if r["pos"] and not r["alarm"])
        fp = sum(1 for r in rows if not r["pos"] and r["alarm"])
        tn = sum(1 for r in rows if not r["pos"] and not r["alarm"])
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        out[det] = {"precision": round(prec, 2), "recall": round(rec, 2),
                    "f1": round(2 * prec * rec / (prec + rec), 2) if prec + rec else 0.0,
                    "fpr": round(fp / (fp + tn), 2) if fp + tn else 0.0,
                    "tp": tp, "fp": fp, "fn": fn, "tn": tn}
    return out


DETS = ["CUSUM", "PCA_T2", "PCA_SPE", "RULE"]


def main():
    from han.Rul_shift_agent.core.rul_tool import RULTool
    tool, fx = RULTool(), FeatureExtractor()

    print(f"[grid] calibrating (FA<=1/100cyc protocol, q={Q:.2f} on unit {C.VAL_UNIT})")
    vz = val_zseq(fx)
    h = q_thresh(cusum_stats(vz))
    pca = PCAMonitor(fx)
    pca.calibrate(vz)
    print(f"[grid] CUSUM h={h:.2f} | PCA k={pca.k} T2_lim={pca.t2_lim:.1f} "
          f"SPE_lim={pca.spe_lim:.2f}")

    grid = make_grid(fx)
    results, point_log = {}, []
    for scen in grid:
        packets, meta = build_packets(scen, tool, fx)
        rows = finalize(packets, run_rule(packets))

        res_units = {}
        for unit in scen["units"]:
            up = [p for p in packets if p["unit"] == unit]
            ur = [r for r in rows if r["unit"] == unit]
            dcyc = [p["cycle"] for p in up]
            onset = up[0]["shift_onset_cycle"]
            zseq = np.array([p["z_global_vec"] for p in up])

            stats = cusum_stats(zseq)
            t2spe = [pca.stats(z) for z in zseq]
            det = {"CUSUM": [bool(s > h) for s in stats],
                   "PCA_T2": [bool(t > pca.t2_lim) for t, _ in t2spe],
                   "PCA_SPE": [bool(s > pca.spe_lim) for _, s in t2spe],
                   "RULE": [bool(r["shift_detected"]) for r in ur]}

            res_units[unit] = {name: series_metrics(dcyc, alarms, onset)
                               for name, alarms in det.items()}
            for name, alarms in det.items():           # pooled 8.2 log (hysteresis)
                conf = hyst_confirm(alarms)
                for c, a in zip(dcyc, conf):
                    point_log.append({"det": name, "alarm": bool(a),
                                      "pos": bool(onset is not None and c >= onset)})
        results[scen["name"]] = {"case": scen["case"], "meta": meta, "units": res_units}
        tag = next(iter(meta.values()), {})
        print(f"[grid] {scen['name']:<30} cons={tag.get('realised_cons_plateau', '—')} "
              f"rulΔ={tag.get('rul_impact_meanabs', '—')}")

    pooled = pooled_harmful(point_log)

    with open(RES_PATH, "w") as f:
        json.dump({"protocol": {"fa_per_100cyc": FA_PER_100, "q": Q, "hyst_n": HYST_N},
                   "pooled_harmful": pooled, "scenarios": results}, f, indent=1)

    # ---------------- blind-spot matrix ---------------- #
    lines = ["| scenario | cons | RULΔ | " + " | ".join(DETS) + " |",
             "|---|---|---|" + "---|" * len(DETS)]
    print("\n" + "=" * 104)
    print(f"{'scenario':<30} {'cons':>6} {'RULΔ':>6} | " +
          " | ".join(f"{d:>8}" for d in DETS))
    print("-" * 104)
    for name, r in results.items():
        for unit, dets in r["units"].items():
            m = r["meta"].get(unit, {})
            cons = m.get("realised_cons_plateau", "—")
            ruld = m.get("rul_impact_meanabs", "—")
            cells = []
            for dn in DETS:
                e = dets[dn]["hyst"]
                if "event_detected" in e:
                    cells.append(f"L{e['latency_cycles']}" if e["event_detected"] else "MISS")
                else:
                    cells.append("clean" if e["fa_points"] == 0 else f"FA{e['fa_points']}")
            label = name if len(r["units"]) == 1 else f"{name}(u{unit})"
            print(f"{label:<30} {str(cons):>6} {str(ruld):>6} | " +
                  " | ".join(f"{c:>8}" for c in cells))
            lines.append(f"| {label} | {cons} | {ruld} | " + " | ".join(cells) + " |")

    print("\npooled harmful-shift metrics (8.2, hysteresis):")
    print(f"{'detector':>8} {'P':>6} {'R':>6} {'F1':>6} {'FPR':>6}")
    plines = ["", "## Pooled harmful-shift metrics (8.2, hysteresis)", "",
              "| detector | precision | recall | F1 | FPR |", "|---|---|---|---|---|"]
    for det, m in pooled.items():
        print(f"{det:>8} {m['precision']:>6.2f} {m['recall']:>6.2f} "
              f"{m['f1']:>6.2f} {m['fpr']:>6.2f}")
        plines.append(f"| {det} | {m['precision']} | {m['recall']} | {m['f1']} | {m['fpr']} |")

    with open(MD_PATH, "w") as f:
        f.write("# Grid experiment — blind-spot matrix\n\n" +
                f"Protocol: FA<=1/100cyc (q={Q:.2f} on u{C.VAL_UNIT}), hysteresis {HYST_N}. "
                "L{n} = detected at latency n cycles; MISS = never; FA{n} = false-alarm "
                "points (controls).\n\n" + "\n".join(lines + plines) + "\n")
    print(f"\n[grid] results  -> {RES_PATH}\n[grid] matrix   -> {MD_PATH}"
          f"\n[grid] datasets -> {DSET_DIR}")


if __name__ == "__main__":
    main()
