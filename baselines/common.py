"""Shared protocol for the 0804 CUSUM/PCA baseline experiment (docs §3-§5).

- Cycle-vector pipeline (representation v2): decimated full-flight series ->
  sliding windows (50, stride 50) -> window features -> cycle mean.
  Three input variants: vec_xs (14) / vec_xsw (18) / vec_regime (28).
- Detector-input restandardization: cycle-level features are re-scaled by the
  clean-train cycle-vector mean/std so that CUSUM's k=0.5 means half of ONE
  cycle-level sigma (window-mean aggregation shrinks variance ~1/N_c; without
  this k would silently mean ~1.1 sigma_cycle).  Disclosed in the report.
- Dual evaluation views on the same score sequence (§4.1):
  native = every cycle (q=0.99), comparison = every 3rd cycle (q=0.97).
- Hysteresis: 2 consecutive exceedances at the view's evaluation points.
- Paired-clean valid detection (§4.3): c0 <= T_fault < T_clean.
"""
import os

import numpy as np

import han.Rul_shift_agent.core.config as C
import han.Rul_shift_agent.core.data_ncmapss as D

FEAT_PATH = os.path.join(C.OUT_DIR, "feature_models.npz")
TRAIN_VEC_PATH = os.path.join(C.OUT_DIR, "train_cycle_vectors.npz")
DATASET_ROOT = os.path.join(os.path.dirname(C.OUT_DIR), "dataset",
                            "corrupted_dataset")

VARIANT_DIMS = {"xs": 14, "xsw": 18, "regime": 28}
DETECTORS = ["cusum", "t2", "spe"]
VARIANTS = ["xs", "xsw", "regime"]        # 3 x 3 = 9 detector variants
VIEWS = {"native": {"every": 1, "q": 0.99},
         "comparison": {"every": C.DECISION_EVERY, "q": 0.97}}
HYSTERESIS_N = 2
_XS_N = len(C.XS_VARS)


# --------------------------------------------------------------------------- #
# Cycle-vector pipeline
# --------------------------------------------------------------------------- #
class VectorPipeline:
    """Turns decimated per-cycle series into the three cycle-vector variants."""

    def __init__(self):
        z = np.load(FEAT_PATH)
        self.ch_mean, self.ch_std = z["ch_mean"], z["ch_std"]
        self.w_mean, self.w_std = z["w_mean"], z["w_std"]
        self.regime_coef = z["regime_coef"]
        self.regime_resid_std = z["regime_resid_std"]
        self.poly_powers = z["poly_powers"]
        self.xs_mean, self.xs_std = z["xs_mean"], z["xs_std"]
        self.cons_coef, self.cons_int = z["cons_coef"], z["cons_int"]
        self.cons_resid_std = z["cons_resid_std"]

    def _poly(self, Wn):
        out = np.ones((Wn.shape[0], self.poly_powers.shape[0]))
        for p, powers in enumerate(self.poly_powers):
            term = np.ones(Wn.shape[0])
            for k in range(4):
                if powers[k]:
                    term = term * Wn[:, k] ** powers[k]
            out[:, p] = term
        return out

    def cycle_vector(self, dec, win_idx=None):
        """One decimated flight (L,18) -> dict of the 3 variants + N_c.

        win_idx: optional window subset (matched-count diagnostic, §4.5-6)."""
        wins = D.full_flight_windows(dec)                    # (N_c,50,18)
        if win_idx is not None:
            wins = wins[win_idx]
        n_c, win = wins.shape[0], wins.shape[1]
        wmean = wins.mean(axis=1)                            # (N_c,18)
        zg = (wmean - self.ch_mean) / self.ch_std
        vec_xsw = zg.mean(axis=0)                            # (18,)

        flat = wins.reshape(-1, 18).astype(np.float64)
        Wn = (flat[:, _XS_N:] - self.w_mean) / self.w_std
        pred = self._poly(Wn) @ self.regime_coef.T           # (N,14)
        rz = ((flat[:, :_XS_N] - pred).reshape(n_c, win, _XS_N).mean(axis=1)
              / self.regime_resid_std).mean(axis=0)          # (14,)
        Xn = (flat[:, :_XS_N] - self.xs_mean) / self.xs_std
        cpred = Xn @ self.cons_coef.T + self.cons_int
        cz = ((Xn - cpred).reshape(n_c, win, _XS_N).mean(axis=1)
              / self.cons_resid_std).mean(axis=0)            # (14,)
        return {"xs": vec_xsw[:_XS_N], "xsw": vec_xsw,
                "regime": np.concatenate([rz, cz]), "n_c": n_c}

    def unit_vectors(self, dec_list, subsample_k=None, rng=None):
        """List of decimated flights -> {variant: (Ncyc,dim)}, n_c (Ncyc,).

        subsample_k: keep only k random windows per cycle (matched-count)."""
        rows = []
        for d in dec_list:
            idx = None
            if subsample_k is not None:
                n = D.full_flight_windows(d).shape[0]
                if n > subsample_k:
                    idx = np.sort(rng.choice(n, size=subsample_k, replace=False))
            rows.append(self.cycle_vector(d, win_idx=idx))
        return ({v: np.stack([r[v] for r in rows]) for v in VARIANTS},
                np.array([r["n_c"] for r in rows]))


def load_scenario_series(path):
    """corrupted_dataset scenario folder -> (dec_list, cycles, rul)."""
    z = np.load(os.path.join(path, "series.npz"))
    b = z["cycle_bounds"]
    dec = [z["series"][b[i]:b[i + 1]] for i in range(len(b) - 1)]
    return dec, z["cycles"].astype(int), z["true_rul"]


def train_cycle_vectors(rebuild=False):
    """Clean-train cycle vectors (PCA fit pool + restandardization scales).

    Cached to outputs/train_cycle_vectors.npz.  Returns
    {variant: (Ncyc_tot,dim)}, unit_index (Ncyc_tot,).
    """
    if os.path.exists(TRAIN_VEC_PATH) and not rebuild:
        z = np.load(TRAIN_VEC_PATH)
        return {v: z[v] for v in VARIANTS}, z["unit"]
    vp = VectorPipeline()
    vecs = {v: [] for v in VARIANTS}
    units = []
    for u in C.TRAIN_UNITS:
        d = D.load_unit_series(u, native=False)
        uv, _ = vp.unit_vectors(d["series"])
        for v in VARIANTS:
            vecs[v].append(uv[v])
        units += [u] * len(d["cycles"])
    out = {v: np.concatenate(vecs[v], axis=0) for v in VARIANTS}
    np.savez(TRAIN_VEC_PATH, unit=np.array(units), **out)
    return out, np.array(units)


class Restandardizer:
    """Cycle-level re-scaling by clean-train cycle-vector mean/std (§3.1 note)."""

    def __init__(self, train_vecs):
        self.mean = {v: train_vecs[v].mean(0) for v in VARIANTS}
        self.std = {v: train_vecs[v].std(0) + 1e-8 for v in VARIANTS}

    def __call__(self, variant, X):
        return (X - self.mean[variant]) / self.std[variant]


# --------------------------------------------------------------------------- #
# Views, hysteresis, alarms, paired-clean status
# --------------------------------------------------------------------------- #
def view_positions(n_cycles, view):
    """Evaluation-point positions (0-indexed into the cycle sequence)."""
    e = VIEWS[view]["every"]
    return np.arange(e - 1, n_cycles, e)


def alarm_analysis(stat, cycles, view, threshold):
    """Score sequence (per cycle) -> raw/confirmed alarms at a view's points.

    Returns dict: pos (eval positions), cyc (their cycle ids), exceed (bool),
    confirmed (bool, 2-consecutive), events (cycle ids of off->on transitions
    of the confirmed state), raw_count.
    """
    pos = view_positions(len(cycles), view)
    s = stat[pos]
    exceed = s > threshold
    confirmed = np.zeros_like(exceed)
    confirmed[1:] = exceed[1:] & exceed[:-1]
    prev = np.concatenate([[False], confirmed[:-1]])
    onsets = confirmed & ~prev
    return {"pos": pos, "cyc": cycles[pos], "exceed": exceed,
            "confirmed": confirmed, "events": cycles[pos][onsets],
            "raw_count": int(exceed.sum())}


def first_confirmed(events, at_or_after=None):
    ev = np.asarray(events)
    if at_or_after is not None:
        ev = ev[ev >= at_or_after]
    return int(ev[0]) if len(ev) else None


def classify_scenario(fault_al, clean_al, onset, life):
    """5-way status (§4.3) + paired-clean validity + metrics fields."""
    t_clean = first_confirmed(clean_al["events"])
    t_clean_cens = t_clean if t_clean is not None else life + 1
    pre_mask = fault_al["cyc"] < onset
    had_pre = bool(fault_al["confirmed"][pre_mask].any())
    # SAT: confirmed alarm active on the last pre-onset point AND still active
    # at the first post-onset point (continuous through onset)
    post_mask = fault_al["cyc"] >= onset
    sat = False
    if pre_mask.any() and post_mask.any():
        last_pre = np.where(pre_mask)[0][-1]
        first_post = np.where(post_mask)[0][0]
        sat = bool(fault_al["confirmed"][last_pre]
                   and fault_al["confirmed"][first_post])
    t_fault = first_confirmed(fault_al["events"], at_or_after=onset)
    valid = (t_fault is not None) and (t_fault < t_clean_cens)
    if sat:
        status = "SAT"
    elif t_fault is None:
        status = "miss"
    elif not valid:
        status = "no_effect"
    elif had_pre:
        status = "preFA_then_detected"
    else:
        status = "clean_detected"
    return {
        "status": status,
        "t_fault": t_fault, "t_clean": t_clean,
        "alarm_advance": (t_clean_cens - t_fault) if t_fault is not None else None,
        "latency": (t_fault - onset) if t_fault is not None else None,
        "had_pre_onset_alarm": had_pre,
        "detected_after_onset": t_fault is not None,
        "sat": sat,
        "operational_success": status == "clean_detected",
        "conditional_success": status in ("clean_detected", "preFA_then_detected"),
        "pre_onset_fpr": float(fault_al["confirmed"][pre_mask].mean())
        if pre_mask.any() else 0.0,
    }


def fa_per_100(al, n_points, every):
    """Clean-series FA rates: raw exceedances and confirmed off->on events,
    both per 100 cycles (points converted to cycles by the view cadence)."""
    n_cycles = n_points * every
    return {"raw_per_100cyc": 100.0 * al["raw_count"] / n_cycles,
            "events_per_100cyc": 100.0 * len(al["events"]) / n_cycles}
