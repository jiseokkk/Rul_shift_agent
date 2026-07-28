"""Sensor-fault (bias) injection engine for N-CMAPSS  (design: docs/BIAS_INJECTION_DESIGN_ko.md).

A corruption scenario is a FaultSpec = (fault mode) x (temporal profile) x (channel
scope) x (magnitude, calibrated to a detector cons) x (onset, sign).  The engine
corrupts only the *observed* sensor columns; RUL labels (Y) are left untouched, so
"the sensor lies but the ground truth is real".

Difficulty is controlled not in raw sigma but in `cons` — the RULE DETECTOR's own
statistic, `temp_consistency_z_abs` (mean |consistency_z| over the 4 temperature
channels), the quantity agent.py actually thresholds on (real_shift needs cons>3).
Use `calibrate_to_detector(target_cons, ...)` for anything where difficulty must be
comparable across channel scopes — that is the current, correct calibrator.

Historical note: an earlier metric (once called "SNR") measured the *injected
channel's own* consistency contribution.  It was NOT aligned with the detector — a
single-channel fault is diluted 1/4 in the temp4 average — so it is kept only as the
legacy `calibrate_magnitude()` below.  Prefer `calibrate_to_detector`; all reporting
now uses `cons`.  consistency_z is the cross-channel residual from preprocess.py
(feature_models.npz).

This module intentionally has no torch / RUL-model dependency so it can build
corrupted datasets standalone.
"""
from dataclasses import dataclass, field, asdict

import numpy as np

import han.Rul_shift_agent.config as C


# --------------------------------------------------------------------------- #
# Scenario specification
# --------------------------------------------------------------------------- #
@dataclass
class FaultSpec:
    mode: str = "drift"          # offset | gain | drift | noise | stuck | lag | stealth | degrade
    channels: tuple = (2,)       # X_s indices to corrupt (T48 = 2). stealth/degrade span all 14.
    target_snr: float = 3.0      # detector-referenced difficulty (see module docstring)
    profile: str = "ramp"        # step | ramp | exp | intermittent
    onset_frac: float = 0.45     # onset as a fraction of the unit's life
    ramp_len: int = 15           # cycles from onset to full magnitude (ramp); tau (exp)
    sign: int = -1               # -1 adverse (hide degradation -> RUL overestimate) | +1 favorable
    seed: int = 0                # intermittent draw / onset jitter
    tier: str = "L2"             # label only

    # filled in by calibrate_magnitude()
    delta: dict = field(default_factory=dict)   # {channel_index: raw additive magnitude}

    def name(self):
        chs = "+".join(C.XS_VARS[c] for c in self.channels) if len(self.channels) <= 4 else f"all{len(self.channels)}"
        sg = "neg" if self.sign < 0 else "pos"
        return (f"{self.tier}_{self.mode}_{chs}_{self.profile}"
                f"{self.ramp_len if self.profile in ('ramp', 'exp') else ''}"
                f"_snr{self.target_snr:g}_onset{int(self.onset_frac*100)}_{sg}")


# --------------------------------------------------------------------------- #
# Temporal profile b(c) in [0,1]
# --------------------------------------------------------------------------- #
def profile_scale(spec, cycle, onset, life, rng=None):
    """Magnitude multiplier b(c) in [0,1] for a given absolute cycle."""
    if cycle < onset:
        return 0.0
    if spec.profile == "step":
        return 1.0
    if spec.profile == "ramp":
        return min(1.0, (cycle - onset) / max(1, spec.ramp_len))
    if spec.profile == "exp":
        return float(1.0 - np.exp(-(cycle - onset) / max(1e-6, spec.ramp_len)))
    if spec.profile == "intermittent":
        # latent phase: fire on ~30% of cycles until 2*ramp_len past onset, then always on
        if cycle - onset >= 2 * spec.ramp_len:
            return 1.0
        return 1.0 if (rng.random() < 0.3) else 0.0
    raise ValueError(f"unknown profile {spec.profile}")


# --------------------------------------------------------------------------- #
# Consistency-z detector signal (mirrors preprocess.FeatureExtractor, no torch)
# --------------------------------------------------------------------------- #
class _Detector:
    def __init__(self):
        z = np.load(C.OUT_DIR + "/feature_models.npz")
        self.xs_mean, self.xs_std = z["xs_mean"], z["xs_std"]
        self.cons_coef, self.cons_int = z["cons_coef"], z["cons_int"]
        self.cons_resid_std = z["cons_resid_std"]
        self.ch_std = z["ch_std"]

    def consistency_z(self, window):
        """window (T,18) raw -> per-channel consistency z (14,)."""
        Xn = (window[:, :14] - self.xs_mean) / self.xs_std
        pred = Xn @ self.cons_coef.T + self.cons_int
        resid = Xn - pred
        return resid.mean(0) / self.cons_resid_std


# --------------------------------------------------------------------------- #
# Canonical per-cycle windows (mirror data_ncmapss windowing, constant-offset exact)
# --------------------------------------------------------------------------- #
def canonical_window(seq):
    """(Traw,18) one cycle -> (50,18) middle decimated window (matches data_ncmapss)."""
    dec = seq[::C.DECIMATION]
    if len(dec) < C.WINDOW:
        pad = np.repeat(dec[:1], C.WINDOW - len(dec), axis=0)
        dec = np.concatenate([pad, dec], axis=0)
    start = (len(dec) - C.WINDOW) // 2
    return dec[start:start + C.WINDOW]


# --------------------------------------------------------------------------- #
# LEGACY calibration — per-injected-channel consistency (the old "SNR").
# Kept for reference only; NOT detector-aligned.  Use calibrate_to_detector().
# --------------------------------------------------------------------------- #
def calibrate_magnitude(spec, clean_windows, cycles, onset, life, det, tol=0.05):
    """[LEGACY] Return {channel: raw delta} so plateau-cycle mean |consistency_z|
    over the INJECTED channels == spec.target_snr.  Superseded by
    calibrate_to_detector(), which targets the detector's temp4-mean statistic.

    Single additive channel -> closed form (consistency model for channel j never
    uses channel j, so cons_z[j] is exactly linear in the raw offset).  Multi-channel
    / non-additive modes -> bisection on a scalar magnitude s (raw = s * ch_std).
    """
    plateau = [i for i, c in enumerate(cycles)
               if profile_scale(spec, int(c), onset, life) >= 0.99]
    if not plateau:                      # ramp never saturates within life -> use last cycle
        plateau = [len(cycles) - 1]

    # --- closed form for a single additive (offset/drift) channel ---
    if spec.mode in ("offset", "drift") and len(spec.channels) == 1:
        ch = spec.channels[0]
        raw = spec.target_snr * det.xs_std[ch] * det.cons_resid_std[ch]
        return {ch: spec.sign * float(raw)}

    # --- general bisection on scalar s (magnitude in ch_std units) ---
    def snr_at(s):
        vals = []
        for i in plateau:
            base = det.consistency_z(clean_windows[i])           # clean baseline
            w = clean_windows[i].copy()
            _apply_raw(spec, w, s, det, full_scale=1.0)
            cz = det.consistency_z(w)
            vals.append(np.mean([abs(cz[c] - base[c]) for c in spec.channels]))
        return float(np.mean(vals))

    lo, hi = 0.0, 8.0
    for _ in range(50):                      # pure bisection, no early break
        mid = 0.5 * (lo + hi)
        if snr_at(mid) < spec.target_snr:
            lo = mid
        else:
            hi = mid
    s = 0.5 * (lo + hi)
    return {c: spec.sign * float(s * det.ch_std[c]) for c in spec.channels}


def calibrate_to_detector(target_cons, channels, clean_windows, cycles, onset,
                          ramp_len, fx, det, tol=0.03):
    """Calibrate so the RULE DETECTOR's own statistic (temp_consistency_z_abs),
    averaged over plateau cycles, equals target_cons.

    This is the difficulty the rule agent actually thresholds on (agent.py:
    real_shift needs cons>3).  Use this — not the per-injected-channel SNR — when
    difficulty must be comparable across channel scopes.  Returns {ch: raw delta}.
    """
    plateau = [i for i, c in enumerate(cycles)
               if (c >= onset and min(1.0, (c - onset) / max(1, ramp_len)) >= 0.99)]
    if not plateau:
        plateau = [len(cycles) - 1]

    def cons_at(s):
        vals = []
        for i in plateau:
            w = clean_windows[i].copy()
            for ch in channels:
                w[:, ch] += -s * det.ch_std[ch]          # full-scale plateau offset
            vals.append(fx(w)["agg"]["temp_consistency_z_abs"])
        return float(np.mean(vals))

    lo, hi = 0.0, 12.0
    for _ in range(45):
        mid = 0.5 * (lo + hi)
        if cons_at(mid) < target_cons:
            lo = mid
        else:
            hi = mid
    s = 0.5 * (lo + hi)
    return {ch: -s * float(det.ch_std[ch]) for ch in channels}, cons_at(s)


def _apply_raw(spec, window, s, det, full_scale=1.0):
    """In-place corruption of one (T,18) window at magnitude scalar s (ch_std units)."""
    for c in spec.channels:
        window[:, c] += spec.sign * s * det.ch_std[c] * full_scale


# --------------------------------------------------------------------------- #
# Apply a calibrated spec to raw per-timestep sensor data
# --------------------------------------------------------------------------- #
def inject_raw(X_s, cycle_col, spec, onset, life):
    """Corrupt raw sensor matrix X_s (N,14) in place-safe copy, per-row by cycle.

    X_s        : (N,14) raw measured sensors for one unit (test split, cycle order)
    cycle_col  : (N,) integer cycle of each row
    Returns    : corrupted copy (N,14)
    """
    rng = np.random.default_rng(spec.seed)
    out = X_s.astype(np.float64).copy()
    # per-cycle scale (intermittent draws once per cycle for determinism)
    uniq = np.unique(cycle_col).astype(int)
    scale = {int(c): profile_scale(spec, int(c), onset, life, rng) for c in uniq}

    if spec.mode in ("offset", "drift", "gain"):
        for c in uniq:
            m = cycle_col == c
            b = scale[int(c)]
            if b == 0.0:
                continue
            for ch, d in spec.delta.items():
                if spec.mode == "gain":
                    out[m, ch] *= (1.0 + (d / _channel_ref(ch)) * b)
                else:                                   # offset / drift additive
                    out[m, ch] += d * b
    elif spec.mode == "noise":
        for c in uniq:
            m = cycle_col == c
            b = scale[int(c)]
            if b == 0.0:
                continue
            for ch, d in spec.delta.items():
                out[m, ch] += rng.normal(0.0, abs(d) * b, size=m.sum())
    elif spec.mode == "stuck":
        for ch in spec.delta:
            frozen = None
            for c in uniq:
                m = cycle_col == c
                if scale[int(c)] > 0 and frozen is None:
                    frozen = out[m, ch][0]
                if frozen is not None and scale[int(c)] > 0:
                    out[m, ch] = frozen
    else:
        raise NotImplementedError(f"mode {spec.mode} not wired for raw injection yet")
    return out


_CH_REF = None
def _channel_ref(ch):
    """Channel mean magnitude, for expressing gain as a fraction (loaded lazily)."""
    global _CH_REF
    if _CH_REF is None:
        _CH_REF = np.load(C.OUT_DIR + "/feature_models.npz")["ch_mean"]
    return _CH_REF[ch]


def resolve_onset(spec, life):
    return int(round(spec.onset_frac * life))
