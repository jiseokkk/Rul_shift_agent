"""Preprocessing module: sensor statistics + Tier-1 shift-evidence features.

Base statistics (draft §3.3) for every input channel over a decision window:
    mean, std, trend (linear slope), z-score vs global training baseline.

Tier-1 additions (author discussion):
  #1  Operating-condition-conditioned baseline (regime z-score).
      For each measured sensor s we fit E[s | W]  (W = alt, Mach, TRA, T2,
      polynomial) on the flight-class-3 training data.  The regime z-score is the
      window-mean residual, normalised by the training residual std.  A different
      flight class mainly changes the *W distribution*; if the sensor-vs-W
      relationship is preserved the regime z stays small even when the raw
      (global) z is large -> suppresses the natural-shift false alarms.

  #2  Cross-channel physical-consistency residual.
      For each measured sensor s we fit E[s | other measured sensors] on the
      training data.  A sensor bias (Direction A) breaks these physical
      relationships -> large consistency residual; a flight-class change moves
      the channels together along the physical manifold -> small residual.  This
      is the signal that separates an over-optimistic *sensor fault* from benign
      *operating-condition* variation.

Everything is fit on the 5 flight-class-3 dev units only (no leakage from test).
"""
import json
import os

import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures

import han.Rul_shift_agent.config as C
import han.Rul_shift_agent.data_ncmapss as D

FEAT_PATH = os.path.join(C.OUT_DIR, "feature_models.npz")
BASE_PATH = os.path.join(C.OUT_DIR, "train_baseline.json")

_XS_N = len(C.XS_VARS)     # 14 measured
_W_SL = slice(_XS_N, C.N_INPUT)   # columns 14:18 = W
_XS_SL = slice(0, _XS_N)          # columns 0:14 = measured sensors


# --------------------------------------------------------------------------- #
# Fit feature models (run once, saved to outputs/)
# --------------------------------------------------------------------------- #
def fit_feature_models():
    pool = D.pooled_training_timesteps()      # (M,18) raw decimated training timesteps
    Xs = pool[:, _XS_SL]                       # (M,14)
    W = pool[:, _W_SL]                         # (M,4)

    # per-channel global baseline (all 18 channels)
    ch_mean = pool.mean(0)
    ch_std = pool.std(0) + 1e-8

    # --- Tier-1 #1: E[sensor | W] (polynomial regime baseline) ---
    w_mean, w_std = W.mean(0), W.std(0) + 1e-8
    Wn = (W - w_mean) / w_std
    poly = PolynomialFeatures(degree=C.REGIME_POLY_DEGREE, include_bias=True)
    Phi = poly.fit_transform(Wn)                       # (M, P)
    reg_regime = LinearRegression(fit_intercept=False).fit(Phi, Xs)
    regime_pred = reg_regime.predict(Phi)
    regime_resid_std = (Xs - regime_pred).std(0) + 1e-8   # (14,)

    # --- Tier-1 #2: E[sensor | other measured sensors] (consistency) ---
    xs_mean, xs_std = Xs.mean(0), Xs.std(0) + 1e-8
    Xn = (Xs - xs_mean) / xs_std                       # standardised measured sensors
    cons_coef = np.zeros((_XS_N, _XS_N), dtype=np.float64)   # coef[j] uses others
    cons_int = np.zeros(_XS_N, dtype=np.float64)
    cons_resid_std = np.zeros(_XS_N, dtype=np.float64)
    for j in range(_XS_N):
        others = [k for k in range(_XS_N) if k != j]
        r = LinearRegression().fit(Xn[:, others], Xn[:, j])
        cons_coef[j, others] = r.coef_
        cons_int[j] = r.intercept_
        pred = r.predict(Xn[:, others])
        cons_resid_std[j] = (Xn[:, j] - pred).std() + 1e-8

    np.savez(
        FEAT_PATH,
        ch_mean=ch_mean, ch_std=ch_std,
        w_mean=w_mean, w_std=w_std,
        regime_coef=reg_regime.coef_,               # (14, P)
        regime_resid_std=regime_resid_std,          # (14,)
        poly_powers=poly.powers_,                   # (P,4) to rebuild features
        xs_mean=xs_mean, xs_std=xs_std,
        cons_coef=cons_coef, cons_int=cons_int, cons_resid_std=cons_resid_std,
    )
    with open(BASE_PATH, "w") as f:
        json.dump({"ch_mean": ch_mean.tolist(), "ch_std": ch_std.tolist(),
                   "vars": C.INPUT_VARS}, f, indent=2)
    print(f"[preprocess] feature models saved -> {FEAT_PATH}")
    return FEAT_PATH


# --------------------------------------------------------------------------- #
# Feature computation at a decision window
# --------------------------------------------------------------------------- #
class FeatureExtractor:
    """Loads the fitted models once and turns a (50,18) window into features."""

    def __init__(self):
        z = np.load(FEAT_PATH)
        self.ch_mean, self.ch_std = z["ch_mean"], z["ch_std"]
        self.w_mean, self.w_std = z["w_mean"], z["w_std"]
        self.regime_coef = z["regime_coef"]            # (14,P)
        self.regime_resid_std = z["regime_resid_std"]
        self.poly_powers = z["poly_powers"]            # (P,4)
        self.xs_mean, self.xs_std = z["xs_mean"], z["xs_std"]
        self.cons_coef, self.cons_int = z["cons_coef"], z["cons_int"]
        self.cons_resid_std = z["cons_resid_std"]

    def _poly(self, Wn):
        # Wn: (T,4) -> (T,P) matching PolynomialFeatures(powers_)
        out = np.ones((Wn.shape[0], self.poly_powers.shape[0]))
        for p, powers in enumerate(self.poly_powers):
            term = np.ones(Wn.shape[0])
            for k in range(4):
                if powers[k]:
                    term *= Wn[:, k] ** powers[k]
            out[:, p] = term
        return out

    def __call__(self, window):
        """window: (50,18) raw. Returns a dict of per-channel + aggregate features."""
        w = np.asarray(window, dtype=np.float64)
        T = w.shape[0]
        t = np.arange(T)

        mean = w.mean(0)
        std = w.std(0)
        # linear trend slope per channel
        tc = t - t.mean()
        denom = (tc ** 2).sum() + 1e-8
        trend = (tc[:, None] * (w - mean)).sum(0) / denom
        z_global = (mean - self.ch_mean) / self.ch_std     # (18,)

        # --- Tier-1 #1 regime z (measured sensors only) ---
        Wn = (w[:, _W_SL] - self.w_mean) / self.w_std      # (T,4)
        Phi = self._poly(Wn)                               # (T,P)
        regime_pred = Phi @ self.regime_coef.T             # (T,14)
        regime_resid = w[:, _XS_SL] - regime_pred          # (T,14)
        regime_z = regime_resid.mean(0) / self.regime_resid_std   # (14,)

        # --- Tier-1 #2 consistency residual (measured sensors only) ---
        Xn = (w[:, _XS_SL] - self.xs_mean) / self.xs_std   # (T,14)
        cons_pred = Xn @ self.cons_coef.T + self.cons_int  # (T,14)
        cons_resid = Xn - cons_pred                        # (T,14)
        cons_z = cons_resid.mean(0) / self.cons_resid_std  # (14,)

        ti = C.TEMP_IDX                                    # temp channel indices (0..3)
        feat = {
            "mean": {v: round(float(mean[i]), 4) for i, v in enumerate(C.INPUT_VARS)},
            "std": {v: round(float(std[i]), 4) for i, v in enumerate(C.INPUT_VARS)},
            "trend": {v: round(float(trend[i]), 5) for i, v in enumerate(C.INPUT_VARS)},
            "z_global": {v: round(float(z_global[i]), 3) for i, v in enumerate(C.INPUT_VARS)},
            "regime_z": {v: round(float(regime_z[i]), 3) for i, v in enumerate(C.XS_VARS)},
            "consistency_z": {v: round(float(cons_z[i]), 3) for i, v in enumerate(C.XS_VARS)},
            # aggregates the agent / baselines can key on
            "agg": {
                "temp_z_global_signed": round(float(z_global[ti].mean()), 3),
                "temp_regime_z_signed": round(float(regime_z[ti].mean()), 3),
                "temp_consistency_z_abs": round(float(np.abs(cons_z[ti]).mean()), 3),
                "all_z_global_absmean": round(float(np.abs(z_global[:_XS_N]).mean()), 3),
                "all_regime_z_absmean": round(float(np.abs(regime_z).mean()), 3),
                "all_consistency_z_absmean": round(float(np.abs(cons_z).mean()), 3),
                "max_consistency_z_abs": round(float(np.abs(cons_z).max()), 3),
            },
        }
        return feat


if __name__ == "__main__":
    fit_feature_models()
    fx = FeatureExtractor()
    for u in [11, 14, 15]:
        d = D.load_unit_cycles(u)
        f0 = fx(d["windows"][len(d["cycles"]) // 2])
        print(f"\nunit {u} Fc{d['fc']} (mid cycle) aggregates:")
        for k, v in f0["agg"].items():
            print(f"   {k:28s} {v}")
