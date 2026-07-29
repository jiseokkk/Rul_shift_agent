"""N-CMAPSS DS02-006 loader.

Extracts one (or several, for training) fixed-length windows per engine cycle.
Each window is 50 decimated time steps over the 18 input channels
(14 measured sensors + 4 operating-condition descriptors).  RUL labels come
from the dataset's Y array (cycles-to-failure) and are piecewise-linear capped.

The dev arrays hold units {2,5,10,16,18,20}; the test arrays hold {11,14,15}.
"""
import h5py
import numpy as np

import han.Rul_shift_agent.core.config as C


# --------------------------------------------------------------------------- #
# Raw HDF5 access
# --------------------------------------------------------------------------- #
def _load_split(split):
    """Return dict of arrays for 'dev' or 'test' split (only what we need)."""
    with h5py.File(C.DATA_H5, "r") as f:
        A = f[f"A_{split}"][:]          # unit, cycle, Fc, hs
        Xs = f[f"X_s_{split}"][:]       # 14 measured sensors
        W = f[f"W_{split}"][:]          # 4 operating-condition descriptors
        Y = f[f"Y_{split}"][:].reshape(-1)   # RUL (cycles)
    X = np.concatenate([Xs, W], axis=1).astype(np.float32)   # (N, 18) in INPUT_VARS order
    return {"A": A, "X": X, "Y": Y}


def _split_for_unit(unit):
    return "dev" if unit in (C.TRAIN_UNITS + [C.VAL_UNIT]) else "test"


# --------------------------------------------------------------------------- #
# Per-cycle window extraction
# --------------------------------------------------------------------------- #
def _windows_from_flight(seq, window, decimation, stride=None):
    """Decimate a single flight's (T,18) array and cut length-`window` windows.

    Returns a list of (window,18) arrays.  With stride=None a single canonical
    window (the middle of the flight, cruise-dominated) is returned — used for
    deterministic per-cycle decision/eval.  With an int stride, sliding windows
    are returned — used for training augmentation.
    """
    dec = seq[::decimation]
    if len(dec) < window:                      # pad short flights at the front
        pad = np.repeat(dec[:1], window - len(dec), axis=0)
        dec = np.concatenate([pad, dec], axis=0)
    if stride is None:
        start = (len(dec) - window) // 2       # middle window
        return [dec[start:start + window]]
    out = []
    for s in range(0, len(dec) - window + 1, stride):
        out.append(dec[s:s + window])
    if not out:
        out = [dec[:window]]
    return out


def load_unit_cycles(unit, biased_channels=None, bias_delta=None, onset_cycle=None):
    """Yield per-cycle canonical windows for a unit, in cycle order.

    Optional sensor-bias injection (Direction A): for cycles >= onset_cycle, add
    `bias_delta[c]` (raw units) to channel index `c` for each c in
    `biased_channels`.  The bias hits the *observed* window only; the RUL label
    (true cycles-to-failure) is untouched, so labels stay valid.

    Returns dict with parallel arrays:
        cycles (Ncyc,), windows (Ncyc,50,18), rul (Ncyc,), fc (int)
    """
    split = _split_for_unit(unit)
    d = _load_split(split)
    m = d["A"][:, 0] == unit
    A, X, Y = d["A"][m], d["X"][m], d["Y"][m]
    fc = int(np.unique(A[:, 2])[0])

    cycles = np.unique(A[:, 1]).astype(int)
    cycles.sort()
    win_list, rul_list, cyc_list = [], [], []
    for c in cycles:
        cm = A[:, 1] == c
        seq = X[cm].copy()
        if biased_channels is not None and onset_cycle is not None and c >= onset_cycle:
            for ch in biased_channels:
                seq[:, ch] += bias_delta[ch]
        w = _windows_from_flight(seq, C.WINDOW, C.DECIMATION, stride=None)[0]
        rul = float(min(np.median(Y[cm]), C.RUL_CAP))
        win_list.append(w)
        rul_list.append(rul)
        cyc_list.append(int(c))
    return {
        "unit": unit,
        "fc": fc,
        "cycles": np.array(cyc_list, dtype=int),
        "windows": np.stack(win_list).astype(np.float32),   # (Ncyc,50,18)
        "rul": np.array(rul_list, dtype=np.float32),
    }


def load_training_windows():
    """Sliding-window training set over the 5 flight-class-3 dev units.

    Returns X (Nwin,50,18) float32, y (Nwin,) float32 (capped RUL).
    """
    d = _load_split("dev")
    Xall, yall = [], []
    for unit in C.TRAIN_UNITS:
        m = d["A"][:, 0] == unit
        A, X, Y = d["A"][m], d["X"][m], d["Y"][m]
        for c in np.unique(A[:, 1]).astype(int):
            cm = A[:, 1] == c
            rul = float(min(np.median(Y[cm]), C.RUL_CAP))
            for w in _windows_from_flight(X[cm], C.WINDOW, C.DECIMATION,
                                          stride=C.TRAIN_STRIDE):
                Xall.append(w)
                yall.append(rul)
    return np.stack(Xall).astype(np.float32), np.array(yall, dtype=np.float32)


def pooled_training_timesteps(max_rows=400_000):
    """Pooled decimated per-timestep samples over the dev training units.

    Used to fit the Tier-1 feature models (W-conditioned baseline + cross-channel
    consistency) and to compute per-channel training mean/std for z-scores.
    Returns array (M,18) float32.
    """
    d = _load_split("dev")
    rows = []
    for unit in C.TRAIN_UNITS:
        m = d["A"][:, 0] == unit
        A, X = d["A"][m], d["X"][m]
        for c in np.unique(A[:, 1]).astype(int):
            cm = A[:, 1] == c
            rows.append(X[cm][::C.DECIMATION])
    pool = np.concatenate(rows, axis=0).astype(np.float32)
    if len(pool) > max_rows:                 # deterministic subsample for speed
        idx = np.linspace(0, len(pool) - 1, max_rows).astype(int)
        pool = pool[idx]
    return pool


if __name__ == "__main__":
    # quick smoke test
    for u in [2, 20, 11, 14, 15]:
        d = load_unit_cycles(u)
        print(f"unit {u:2d} Fc{d['fc']}  cycles={len(d['cycles'])}  "
              f"win={d['windows'].shape}  rul[min..max]={d['rul'].min():.0f}..{d['rul'].max():.0f}")
    Xtr, ytr = load_training_windows()
    print("train windows:", Xtr.shape, "y range", ytr.min(), ytr.max())
    print("pooled timesteps:", pooled_training_timesteps().shape)
