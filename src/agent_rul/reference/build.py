"""정상 Reference 일괄 fit → artifacts/reference/ (CLI `build-reference`).

    Clean Train unit {2,5,10,18}  → Global reference + KNN DB
    Clean Valid unit {16,20}      → sigma_w, q95, std_ref, Sigma_r, T2 calibration

산출물 (경로는 config.Paths): global.json, knn.npz, calibration.json
"""
from __future__ import annotations

import os

import numpy as np

from .. import data
from . import calibration
from .knn import KNNReference


def build_all(cfg, verbose: bool = True) -> dict:
    ref_dir = cfg.paths.reference_dir
    os.makedirs(ref_dir, exist_ok=True)
    p = cfg.n_sensors
    dec = int(cfg.exp.time["hdf5_decimation"])
    spw = cfg.samples_per_window
    say = print if verbose else (lambda *a, **k: None)

    # ---------- 1. Global reference (clean train) -----------------------
    train_units = list(cfg.exp.units["train"])
    say(f"[reference] pooled train 샘플 로드 (units={train_units}) ...")
    pool = data.pooled_samples(
        cfg.paths.ncmapss_h5, train_units, decimation=dec,
        max_rows=int(cfg.exp.knn["max_train_samples"]),
        cache_dir=cfg.paths.cache_dir)
    say(f"     pool={pool.shape}")

    g = calibration.fit_global(pool, cfg.sensors)
    calibration.save(g, cfg.paths.global_json)

    # ---------- 2. KNN W-conditioned reference --------------------------
    say(f"[reference] KNN DB 구축 (K={cfg.exp.knn['K']}) ...")
    knn = KNNReference.fit(pool, p, K=int(cfg.exp.knn["K"]),
                           query_chunk=int(cfg.exp.knn["query_chunk"]))
    knn.save(cfg.paths.knn_npz)

    # ---------- 3. Calibration (clean validation) -----------------------
    calib_units = list(cfg.exp.units["calib"])
    say(f"[reference] calibration window residual 계산 (units={calib_units}) ...")
    res_mean_all, res_std_all = [], []
    for _unit, _cyc, seq in data.iter_unit_cycles(
            cfg.paths.ncmapss_h5, calib_units, decimation=dec,
            cache_dir=cfg.paths.cache_dir):
        w = data.split_windows(seq, spw)
        if len(w) == 0:
            continue
        flat = w.reshape(-1, w.shape[-1])
        res = knn.residuals(flat, p).reshape(len(w), spw, p)
        m, s = calibration.window_residual_stats(res)
        res_mean_all.append(m)
        res_std_all.append(s)
    res_mean = np.concatenate(res_mean_all, axis=0)
    res_std = np.concatenate(res_std_all, axis=0)
    say(f"     clean val windows={len(res_mean)}")

    cal = calibration.fit(res_mean, res_std, cfg.sensors,
                          sigma_global=np.asarray(g["std"], dtype=np.float64))
    cal["train_units"] = train_units
    cal["calib_units"] = calib_units
    cal["K"] = int(cfg.exp.knn["K"])
    cal["samples_per_window"] = spw
    calibration.save(cal, cfg.paths.calibration_json)

    say(f"[reference] 완료 → {ref_dir}")
    say(f"     |z_w| q95 (pooled) = {cal['q95_pooled']:.2f}")
    say(f"     T2 median = {cal['t2_median']:.1f}, q95 = {cal['t2_q95']:.1f}")
    say(f"     Sigma_r cond = {cal['condition_number']:.2e}, ridge = {cal['ridge']:.3g}")
    return {"global": g, "calibration": cal, "knn": knn}


def load_all(cfg) -> dict:
    """artifacts/reference/ 의 세 산출물."""
    return {
        "global": calibration.load(cfg.paths.global_json),
        "calibration": calibration.load(cfg.paths.calibration_json),
        "knn": KNNReference.load(cfg.paths.knn_npz),
    }
