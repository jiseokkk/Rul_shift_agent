"""Build the 0804 corrupted benchmark dataset (docs/0804_cusum_pca_baseline_experiment.md).

Inventory: 50 benchmark scenarios (controls 3 + A18 B2 C6 D8 E9 F4, split=test)
+ devset (ctrl_u20 + 5 injected u20 scenarios, split=dev -- Stage 2 difficulty
pre-check & future method tuning only, excluded from the locked benchmark).

Per scenario folder: series.npz (decimated full-flight series, cycle_bounds,
cycles, true_rul) + spec.json.  Plus previews/<id>.png and manifest.csv.

Verification per scenario (0804 Stage 1): pre-onset equality, non-target-channel
equality, RUL invariance, seed reproducibility, physical-delta match.
"""
import csv
import datetime
import json
import os
import subprocess

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import han.Rul_shift_agent.core.config as C
import han.Rul_shift_agent.core.data_ncmapss as D
from han.Rul_shift_agent.injection.engine import (FaultSpec, inject, profile_b,
                                                  spec_dict, ENGINE_VERSION)

ROOT = os.path.join(os.path.dirname(C.OUT_DIR), "dataset", "corrupted_dataset")
BLOCK_DIR = {
    "controls": "controls",
    "A": "blockA_min_shift",
    "B": "blockB_slow_drift",
    "C": "blockC_relation_break",
    "D": "blockD_subspace_aligned",
    "E": "blockE_fault_modes",
    "F": "blockF_natural_overlap",
    "DEV": "devset",
}
TEMP4_MIX = {"T24": 1.0, "T30": -0.6, "T48": 0.8, "T50": -1.2}


def _sig(s):
    return f"{s:g}".replace(".", "p").replace("-", "m")


def build_inventory(pc1_loading):
    inv = []

    def add(block, cat, split, unit, **kw):
        inv.append(dict(block=block, category=cat, split=split, unit=unit, **kw))

    # -- controls (benchmark) + dev control ---------------------------------
    for u in (11, 14, 15):
        add("controls", "control", "test", u, mode="none",
            scenario_id=f"ctrl_u{u}")
    add("DEV", "control", "dev", 20, mode="none", scenario_id="ctrl_u20")

    # -- Block A: add x T48 x u11 -------------------------------------------
    for prof, sigmas in (("ramp15", [0.15, 0.25, 0.35, 0.5, 1.0, 2.0]),
                         ("step", [0.5, 1.0, 2.0])):
        for s in sigmas:
            for d in (+1, -1):
                add("A", "sensor_fault", "test", 11, mode="add",
                    channels=("T48",), profile=prof,
                    ramp_len=15 if prof == "ramp15" else 0,
                    direction=d, sigma_mult=s,
                    scenario_id=f"A_add_T48_{prof}_{_sig(s)}_{'pos' if d>0 else 'neg'}_u11")

    # -- Block B: slow drift ------------------------------------------------
    for d in (+1, -1):
        add("B", "sensor_fault", "test", 11, mode="add", channels=("T48",),
            profile="ramp40", ramp_len=40, direction=d, sigma_mult=1.0,
            scenario_id=f"B_add_T48_ramp40_1_{'pos' if d>0 else 'neg'}_u11")

    # -- Block C: temp4-mix (fixed multi-sensor stress pattern) -------------
    for s in (0.5, 1.0, 2.0):
        for d in (+1, -1):
            add("C", "sensor_fault", "test", 11, mode="add",
                channels=tuple(TEMP4_MIX), channel_mult=dict(TEMP4_MIX),
                profile="ramp15", ramp_len=15, direction=d, sigma_mult=s,
                scenario_id=f"C_add_temp4_ramp15_{_sig(s)}_{'pos' if d>0 else 'neg'}_u11")

    # -- Block D: PCA principal-subspace-aligned (adversarial) --------------
    pc1_mult = {ch: float(pc1_loading[i]) for i, ch in enumerate(C.XS_VARS)}
    for a in (1.0, 2.0, 4.0):
        for d in (+1, -1):
            add("D", "adversarial", "test", 11, mode="add",
                channels=tuple(C.XS_VARS), channel_mult=pc1_mult,
                profile="ramp15", ramp_len=15, direction=d, sigma_mult=a,
                scenario_id=f"D_pc1_ramp15_a{_sig(a)}_{'pos' if d>0 else 'neg'}_u11")
    for d in (+1, -1):
        add("D", "adversarial", "test", 11, mode="add",
            channels=tuple(C.XS_VARS), profile="ramp15", ramp_len=15,
            direction=d, sigma_mult=1.0,
            scenario_id=f"D_all14_ramp15_1_{'pos' if d>0 else 'neg'}_u11")

    # -- Block E: fault-mode blind spots ------------------------------------
    for d in (+1, -1):
        add("E", "sensor_fault", "test", 11, mode="gain", channels=("T48",),
            profile="ramp15", ramp_len=15, direction=d, sigma_mult=1.0,
            scenario_id=f"E_gain_T48_ramp15_1_{'pos' if d>0 else 'neg'}_u11")
    for s in (1.0, 2.0):
        for seed in (0, 1, 2):
            add("E", "sensor_fault", "test", 11, mode="noise", channels=("T48",),
                profile="ramp15", ramp_len=15, sigma_mult=s, seed=seed,
                scenario_id=f"E_noise_T48_ramp15_{_sig(s)}_sd{seed}_u11")
    add("E", "sensor_fault", "test", 11, mode="stuck", channels=("T48",),
        profile="step", scenario_id="E_stuck_T48_u11")

    # -- Block F: natural overlap -------------------------------------------
    for u in (14, 15):
        for d in (+1, -1):
            add("F", "sensor_fault", "test", u, mode="add", channels=("T48",),
                profile="ramp15", ramp_len=15, direction=d, sigma_mult=1.0,
                scenario_id=f"F_add_T48_ramp15_1_{'pos' if d>0 else 'neg'}_u{u}")

    # -- devset: u20 tuning material ----------------------------------------
    for s, prof, dirs in ((0.5, "ramp15", (+1, -1)), (1.0, "ramp15", (+1, -1)),
                          (1.0, "step", (+1,))):
        for d in dirs:
            add("DEV", "sensor_fault", "dev", 20, mode="add", channels=("T48",),
                profile=prof, ramp_len=15 if prof == "ramp15" else 0,
                direction=d, sigma_mult=s,
                scenario_id=f"DEV_add_T48_{prof}_{_sig(s)}_{'pos' if d>0 else 'neg'}_u20")
    return inv


def to_spec(row):
    return FaultSpec(scenario_id=row["scenario_id"], block=row["block"],
                     category=row["category"], split=row["split"],
                     unit=row["unit"], mode=row["mode"],
                     channels=tuple(row.get("channels", ())),
                     profile=row.get("profile", "none"),
                     ramp_len=row.get("ramp_len", 0),
                     direction=row.get("direction", 0),
                     sigma_mult=row.get("sigma_mult", 0.0),
                     seed=row.get("seed", 0),
                     channel_mult=row.get("channel_mult", {}))


def verify(spec, clean, corr, corr2, cycles, ch_std, extras):
    """Stage 1 generation checks (native level). Raises AssertionError."""
    c0 = extras["onset_cycle"]
    ch_idx = [C.INPUT_VARS.index(ch) for ch in spec.channels]
    other = [j for j in range(C.N_INPUT) if j not in ch_idx]
    for pos, c in enumerate(cycles):
        assert np.array_equal(corr[pos][:, other], clean[pos][:, other]), \
            f"{spec.scenario_id}: non-target channel modified (cycle {c})"
        assert np.array_equal(corr[pos], corr2[pos]), \
            f"{spec.scenario_id}: seed reproducibility failed (cycle {c})"
        if c < c0:
            assert np.array_equal(corr[pos], clean[pos]), \
                f"{spec.scenario_id}: pre-onset modified (cycle {c})"
    if spec.mode == "add":
        # every post-onset cycle: mean shift must equal delta_raw * b(c)
        # (ramp40 never saturates within life -- check the envelope itself)
        for ch, j in zip(spec.channels, ch_idx):
            for pos, c in enumerate(cycles):
                if c < c0:
                    continue
                b = profile_b(spec, int(c), c0)
                got = float(np.mean(corr[pos][:, j].astype(np.float64)
                                    - clean[pos][:, j].astype(np.float64)))
                want = extras["delta_raw"][ch] * b
                assert abs(got - want) < 2e-3 + 1e-3 * abs(want), \
                    (f"{spec.scenario_id}: delta mismatch {ch} cycle {c} "
                     f"got {got} want {want}")
    if spec.mode == "noise":
        full = [p for p, c in enumerate(cycles) if c >= c0 + spec.ramp_len - 1]
        j = ch_idx[0]
        got = float(np.mean([np.std(corr[p][:, j] - clean[p][:, j]) for p in full]))
        want = spec.sigma_mult * ch_std[j]
        assert abs(got - want) / want < 0.05, \
            f"{spec.scenario_id}: noise sigma mismatch got {got} want {want}"
    if spec.mode == "stuck":
        j = ch_idx[0]
        pos0 = int(np.searchsorted(cycles, c0))
        v = extras["stuck"]["stuck_value"][spec.channels[0]]
        assert all(np.all(corr[p][:, j] == v) for p in range(pos0, len(cycles)))


def preview(spec, clean, corr, cycles, extras, path):
    ch = max(spec.channels, key=lambda c_: abs(extras["delta_raw"].get(c_, 0.0))) \
        if spec.channels else "T48"
    j = C.INPUT_VARS.index(ch)
    cm_clean = [float(s[:, j].mean()) for s in clean]
    cm_corr = [float(s[:, j].mean()) for s in corr]
    fig, ax = plt.subplots(figsize=(7, 3))
    ax.plot(cycles, cm_clean, label=f"clean {ch}", lw=1.2)
    ax.plot(cycles, cm_corr, label=f"corrupted {ch}", lw=1.2)
    ax.axvline(extras["onset_cycle"], color="r", ls="--", lw=0.8,
               label=f"onset c0={extras['onset_cycle']}")
    ax.set_xlabel("cycle"); ax.set_ylabel(f"{ch} cycle mean")
    ax.set_title(spec.scenario_id, fontsize=9)
    ax.legend(fontsize=7); fig.tight_layout()
    fig.savefig(path, dpi=110); plt.close(fig)


def save_series(folder, dec_list, cycles, rul):
    flat = np.concatenate(dec_list, axis=0).astype(np.float32)
    bounds = np.zeros(len(dec_list) + 1, dtype=np.int64)
    np.cumsum([len(s) for s in dec_list], out=bounds[1:])
    np.savez_compressed(os.path.join(folder, "series.npz"),
                        series=flat, cycle_bounds=bounds,
                        cycles=cycles.astype(np.int32),
                        true_rul=rul.astype(np.float32))


def main():
    z = np.load(os.path.join(C.OUT_DIR, "feature_models.npz"))
    ch_std, ch_mean = z["ch_std"], z["ch_mean"]
    pc1 = z["pc1_loading"]
    try:
        git = subprocess.check_output(
            ["git", "-C", os.path.dirname(C.OUT_DIR), "rev-parse", "--short", "HEAD"],
            text=True).strip()
    except Exception:
        git = "nogit"
    created = datetime.datetime.now().isoformat(timespec="seconds")

    os.makedirs(os.path.join(ROOT, "previews"), exist_ok=True)
    inv = build_inventory(pc1)
    units = sorted({r["unit"] for r in inv})
    cache = {u: D.load_unit_series(u, native=True) for u in units}

    rows = []
    for r in inv:
        spec = to_spec(r)
        ud = cache[spec.unit]
        clean, cycles, rul = ud["series"], ud["cycles"], ud["rul"]
        corr, extras = inject(clean, cycles, spec, ch_std, ch_mean)
        corr2, _ = inject(clean, cycles, spec, ch_std, ch_mean)
        verify(spec, clean, corr, corr2, cycles, ch_std, extras)

        folder = os.path.join(ROOT, BLOCK_DIR[spec.block], spec.scenario_id)
        os.makedirs(folder, exist_ok=True)
        save_series(folder, [D.decimate_flight(s) for s in corr], cycles, rul)
        sd = spec_dict(spec, extras, len(cycles), ud["fc"], git, created)
        if spec.block == "F":                       # §2.5: Block F only
            sd["background_shift"] = "natural_operating_condition"
            sd["fault_source"] = "synthetic_injection"
        with open(os.path.join(folder, "spec.json"), "w") as f:
            json.dump(sd, f, indent=1)
        if spec.mode != "none":
            preview(spec, clean, corr, cycles, extras,
                    os.path.join(ROOT, "previews", f"{spec.scenario_id}.png"))

        pr = extras["delta_raw"]
        primary = (max(spec.channels, key=lambda c_: abs(pr.get(c_, 0)))
                   if spec.channels else "")
        rows.append({
            "scenario_id": spec.scenario_id, "split": spec.split,
            "block": spec.block, "category": spec.category,
            "unit": spec.unit, "fc": ud["fc"], "life_cycles": len(cycles),
            "mode": spec.mode, "channels": "+".join(spec.channels),
            "profile": spec.profile, "ramp_len": spec.ramp_len,
            "sigma_mult": spec.sigma_mult, "direction": spec.direction,
            "seed": spec.seed, "onset_cycle": extras["onset_cycle"],
            "primary_channel": primary,
            "delta_raw_primary": round(pr.get(primary, 0.0), 4),
            "path": os.path.relpath(folder, ROOT),
        })
        print(f"[build] {spec.scenario_id}  ok")

    with open(os.path.join(ROOT, "manifest.csv"), "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        wr.writeheader(); wr.writerows(rows)

    n_test = sum(r["split"] == "test" for r in rows)
    n_dev = sum(r["split"] == "dev" for r in rows)
    print(f"\n[build] engine {ENGINE_VERSION}  git {git}")
    print(f"[build] benchmark(test) scenarios: {n_test}  devset: {n_dev}")
    print(f"[build] root: {ROOT}")


if __name__ == "__main__":
    main()
