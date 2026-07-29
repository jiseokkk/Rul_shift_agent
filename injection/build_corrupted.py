"""Build corrupted N-CMAPSS datasets from a list of FaultSpecs.

Output layout (design doc §7):
    dataset/corrupted_NCMAPSS/
        manifest.json
        <scenario_name>/
            spec.json      calibrated FaultSpec + metadata
            data.h5        corrupted test-split arrays (unit-filtered), same schema as source
            preview.png    clean vs corrupted trace of the injected channel

RUL labels (Y) are copied verbatim — only the observed sensors are corrupted.

Run:
    cd /home/iai4/Desktop
    /home/iai4/miniconda3/envs/LLMshift/bin/python -m han.Rul_shift_agent.injection.build_corrupted
"""
import json
import os

import h5py
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import han.Rul_shift_agent.core.config as C
import han.Rul_shift_agent.injection.inject as I
from han.Rul_shift_agent.core.preprocess import FeatureExtractor

SRC_H5 = "/home/iai4/Desktop/han/Rul_shift_agent/dataset/data_set/N-CMAPSS_DS02-006.h5"
OUT_ROOT = "/home/iai4/Desktop/han/Rul_shift_agent/dataset/corrupted_NCMAPSS"


# --------------------------------------------------------------------------- #
def load_unit_test_rows(unit):
    """Raw test-split rows for one unit, in file order (cycle-sorted not required)."""
    with h5py.File(SRC_H5, "r") as f:
        A = f["A_test"][:]
        m = A[:, 0] == unit
        d = {
            "A": A[m],
            "X_s": f["X_s_test"][:][m],
            "X_v": f["X_v_test"][:][m],
            "W": f["W_test"][:][m],
            "Y": f["Y_test"][:][m],
        }
        d["vars"] = {k: f[k][:] for k in ("A_var", "W_var", "X_s_var", "X_v_var")}
    return d


def clear_name(spec, unit, target_cons):
    """Human-readable, unambiguous folder name."""
    if len(spec.channels) == 1:
        scope = C.XS_VARS[spec.channels[0]]
    elif set(spec.channels) == set(C.TEMP_IDX):
        scope = "temp4"
    else:
        scope = "+".join(C.XS_VARS[c] for c in spec.channels)
    direction = "adverse" if spec.sign < 0 else "favorable"
    return (f"unit{unit}__{scope}__{spec.mode}-{spec.profile}{spec.ramp_len}"
            f"__difficulty-cons{target_cons:g}__onset{int(spec.onset_frac*100)}pct__{direction}")


def build_one(spec, unit, det, fx, target_cons):
    """Calibrate to the rule detector's own difficulty (temp_consistency_z_abs=target_cons)."""
    d = load_unit_test_rows(unit)
    cyc_col = d["A"][:, 1].astype(int)
    cycles = np.unique(cyc_col); cycles.sort()
    life = int(cycles.max())
    onset = I.resolve_onset(spec, life)

    clean_wins = []
    for c in cycles:
        seq = np.concatenate([d["X_s"][cyc_col == c], d["W"][cyc_col == c]], axis=1)
        clean_wins.append(I.canonical_window(seq))
    clean_wins = np.stack(clean_wins)

    spec.delta, realised = I.calibrate_to_detector(
        target_cons, list(spec.channels), clean_wins, cycles, onset,
        spec.ramp_len, fx, det)

    Xs_corrupt = I.inject_raw(d["X_s"], cyc_col, spec, onset, life)

    name = clear_name(spec, unit, target_cons)
    outdir = os.path.join(OUT_ROOT, name)
    os.makedirs(outdir, exist_ok=True)
    _save_h5(os.path.join(outdir, "data.h5"), d, Xs_corrupt)
    _save_spec(os.path.join(outdir, "spec.json"), spec, unit, life, onset, realised,
               target_cons, name)
    _preview(os.path.join(outdir, "preview.png"), d, Xs_corrupt, cyc_col, cycles,
             spec, onset, realised, target_cons)
    return {"name": name, "unit": unit, "onset_cycle": onset, "life": life,
            "difficulty_target_cons": target_cons, "realised_cons": round(realised, 3),
            "delta_raw": {C.XS_VARS[k]: round(v, 4) for k, v in spec.delta.items()},
            "dir": outdir}


def _save_h5(path, d, Xs_corrupt):
    """Same schema as source (test split, unit-filtered). Drop-in for data_ncmapss loader."""
    with h5py.File(path, "w") as f:
        f.create_dataset("A_test", data=d["A"])
        f.create_dataset("X_s_test", data=Xs_corrupt.astype(np.float64))
        f.create_dataset("X_v_test", data=d["X_v"])
        f.create_dataset("W_test", data=d["W"])
        f.create_dataset("Y_test", data=d["Y"])
        for k, v in d["vars"].items():
            f.create_dataset(k, data=v)


def _save_spec(path, spec, unit, life, onset, realised, target_cons, name):
    from dataclasses import asdict
    obj = asdict(spec)
    obj["delta"] = {C.XS_VARS[k]: v for k, v in spec.delta.items()}
    obj["channels_named"] = [C.XS_VARS[c] for c in spec.channels]
    obj.update(name=name, unit=unit, life=life, onset_cycle=onset,
               difficulty_stat="temp_consistency_z_abs (rule detector threshold=3)",
               difficulty_target_cons=target_cons, realised_cons=round(realised, 4),
               source_h5=SRC_H5,
               note="Only X_s (observed sensors) corrupted; Y (RUL labels) untouched. "
                    "Difficulty calibrated to the rule detector's own statistic so "
                    "scenarios with different channel scope are directly comparable.")
    with open(path, "w") as f:
        json.dump(obj, f, indent=2)


def _preview(path, d, Xs_corrupt, cyc_col, cycles, spec, onset, realised, target_cons):
    ch = 2 if 2 in spec.channels else spec.channels[0]   # prefer T48 for comparability
    name = C.XS_VARS[ch]
    clean_m = np.array([d["X_s"][cyc_col == c, ch].mean() for c in cycles])
    corr_m = np.array([Xs_corrupt[cyc_col == c, ch].mean() for c in cycles])

    fig, ax = plt.subplots(2, 1, figsize=(9, 6.5), sharex=True,
                           gridspec_kw={"height_ratios": [3, 1]})
    ax[0].plot(cycles, clean_m, "-o", ms=3, color="#2b6cb0", label="clean (original)")
    ax[0].plot(cycles, corr_m, "-o", ms=3, color="#c53030", label="corrupted")
    ax[0].axvline(onset, ls="--", color="gray", lw=1)
    ax[0].annotate(f"onset (cycle {onset}, {int(spec.onset_frac*100)}% life)",
                   (onset, ax[0].get_ylim()[1]), fontsize=8, color="gray",
                   ha="left", va="top")
    ax[0].set_ylabel(f"{name}  per-cycle mean")
    ax[0].set_title(f"{clear_name(spec, d['A'][0,0].astype(int), target_cons)}\n"
                    f"detector difficulty cons: target {target_cons:g} -> "
                    f"realised {realised:.2f}", fontsize=9)
    ax[0].legend(loc="best", fontsize=9)
    ax[0].grid(alpha=0.25)

    ax[1].plot(cycles, corr_m - clean_m, "-", color="#805ad5")
    ax[1].axhline(0, color="k", lw=0.6)
    ax[1].axvline(onset, ls="--", color="gray", lw=1)
    ax[1].set_ylabel("injected\nbias (raw)")
    ax[1].set_xlabel("cycle")
    ax[1].grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


# --------------------------------------------------------------------------- #
def main():
    os.makedirs(OUT_ROOT, exist_ok=True)
    det, fx = I._Detector(), FeatureExtractor()

    # Difficulty is set on the rule detector's OWN statistic (temp_consistency_z_abs)
    # so the two scenarios are matched: same detection difficulty, different channel
    # scope.  cons=4 sits just past the rule threshold (3) — the ambiguous zone where
    # the LLM layer has room to add value.  drift, 15-cycle ramp, onset 45%, adverse.
    TARGET_CONS = 4.0
    single = I.FaultSpec(mode="drift", channels=(C.XS_VARS.index("T48"),),
                         profile="ramp", ramp_len=15, onset_frac=0.45, sign=-1)
    temp4 = I.FaultSpec(mode="drift", channels=tuple(C.TEMP_IDX),
                        profile="ramp", ramp_len=15, onset_frac=0.45, sign=-1)

    entries = [build_one(single, C.DIR_A_UNIT, det, fx, TARGET_CONS),
               build_one(temp4, C.DIR_A_UNIT, det, fx, TARGET_CONS)]

    with open(os.path.join(OUT_ROOT, "manifest.json"), "w") as f:
        json.dump({"source": SRC_H5, "difficulty_stat": "temp_consistency_z_abs",
                   "difficulty_target_cons": TARGET_CONS,
                   "n_scenarios": len(entries), "scenarios": entries}, f, indent=2)

    print("=" * 72)
    print(f"built {len(entries)} scenario(s) -> {OUT_ROOT}")
    for e in entries:
        print(f"  {e['name']}")
        print(f"     unit {e['unit']}  life {e['life']}  onset cycle {e['onset_cycle']}")
        print(f"     difficulty cons: target {e['difficulty_target_cons']} -> "
              f"realised {e['realised_cons']}")
        print(f"     injected bias (raw units): {e['delta_raw']}")
    print("=" * 72)


if __name__ == "__main__":
    main()
