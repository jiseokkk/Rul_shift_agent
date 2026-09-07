"""정상 기준 통계 (설계서 3.1, 3.5, 4.4) — Global reference + Calibration.

Global reference (Clean Train pooling)
    센서별 mean / median / std / IQR. LLM 입력에는 안 들어가고(규칙 5) raw_vs_global
    계산과 sigma_w/sigma_global 비율 기록에만 쓴다.

Calibration (Clean Validation window)
    전부 "정상 상태에서 이 통계량이 얼마나 흔들리는지"이며 threshold 가 아니다:
    sigma_w[i]        window residual mean 의 표준편차 (센서별)     → z_w 분모
    q95[i]            |z_w| 의 95% 분위 (센서별), q95_pooled 는 전 센서 합산
    std_ref[i]        window residual std 의 중앙값                 → std_ratio 분모
    mu_r, Sigma_r     window residual mean 벡터의 평균/공분산       → T2
    t2_median, t2_q95 Clean Val window T2 분포
    sigma_ratio[i]    sigma_w / sigma_global (설계서 1.3, 17장)

Sigma_r 이 ill-conditioned 이면 ridge 를 얹고 condition_number / ridge 에 남긴다.
"""
from __future__ import annotations

import numpy as np

from ..utils import read_json, write_json

RIDGE_COND_LIMIT = 1e8      # 이 조건수를 넘으면 ridge 적용
RIDGE_SCALE = 1e-6          # ridge = RIDGE_SCALE * trace(Sigma)/p


# =========================================================================== #
# Global reference
# =========================================================================== #
def fit_global(pool: np.ndarray, sensors: list[str]) -> dict:
    """pool: (M,18) pooled train 샘플. 앞 len(sensors) 열이 측정 센서."""
    xs = np.asarray(pool[:, :len(sensors)], dtype=np.float64)
    q75, q25 = np.percentile(xs, [75, 25], axis=0)
    return {
        "sensors": list(sensors),
        "mean": xs.mean(axis=0).tolist(),
        "median": np.median(xs, axis=0).tolist(),
        "std": xs.std(axis=0).tolist(),
        "iqr": (q75 - q25).tolist(),
        "n_samples": int(len(xs)),
    }


def global_as_arrays(ref: dict) -> dict[str, np.ndarray]:
    return {k: np.asarray(ref[k], dtype=np.float64)
            for k in ("mean", "median", "std", "iqr")}


# =========================================================================== #
# Calibration
# =========================================================================== #
def window_residual_stats(residuals_w: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(n_w, samples, p) residual → (window residual mean, window residual std), 각 (n_w, p)."""
    r = np.asarray(residuals_w, dtype=np.float64)
    return r.mean(axis=1), r.std(axis=1)


def fit(res_mean: np.ndarray, res_std: np.ndarray, sensors: list[str],
        sigma_global: np.ndarray | None = None) -> dict:
    """Clean Validation 전체 window 의 residual 통계 (N_win, p) → calibration dict."""
    res_mean = np.asarray(res_mean, dtype=np.float64)
    res_std = np.asarray(res_std, dtype=np.float64)
    p = res_mean.shape[1]
    if p != len(sensors):
        raise ValueError(f"센서 수 불일치: residual {p} vs sensors {len(sensors)}")

    sigma_w = res_mean.std(axis=0)
    if np.any(sigma_w <= 0):
        bad = [sensors[i] for i in np.flatnonzero(sigma_w <= 0)]
        raise ValueError(f"sigma_w <= 0 인 센서: {bad}")

    z = res_mean / sigma_w
    q95 = np.percentile(np.abs(z), 95, axis=0)
    q95_pooled = float(np.percentile(np.abs(z).ravel(), 95))
    std_ref = np.median(res_std, axis=0)
    std_ref = np.where(std_ref > 0, std_ref, 1e-12)

    mu_r = res_mean.mean(axis=0)
    Sigma_r = np.cov(res_mean, rowvar=False)
    cond = float(np.linalg.cond(Sigma_r))
    ridge = 0.0
    if not np.isfinite(cond) or cond > RIDGE_COND_LIMIT:
        ridge = float(RIDGE_SCALE * np.trace(Sigma_r) / p)
        Sigma_r = Sigma_r + ridge * np.eye(p)
        cond = float(np.linalg.cond(Sigma_r))

    t2 = hotelling_t2(res_mean, mu_r, np.linalg.inv(Sigma_r))

    out = {
        "sensors": list(sensors),
        "sigma_w": sigma_w.tolist(),
        "q95": q95.tolist(),
        "q95_pooled": q95_pooled,
        "std_ref": std_ref.tolist(),
        "mu_r": mu_r.tolist(),
        "Sigma_r": Sigma_r.tolist(),
        "Sigma_r_inv": np.linalg.inv(Sigma_r).tolist(),
        "condition_number": cond,
        "ridge": ridge,
        "t2_median": float(np.median(t2)),
        "t2_q95": float(np.percentile(t2, 95)),
        "n_windows": int(len(res_mean)),
    }
    if sigma_global is not None:
        sg = np.asarray(sigma_global, dtype=np.float64)
        out["sigma_global"] = sg.tolist()
        out["sigma_ratio"] = (sigma_w / np.where(sg > 0, sg, np.nan)).tolist()
    return out


def hotelling_t2(res_mean: np.ndarray, mu_r: np.ndarray,
                 Sigma_inv: np.ndarray) -> np.ndarray:
    """(N,p) → (N,) Hotelling T^2."""
    d = np.asarray(res_mean, dtype=np.float64) - np.asarray(mu_r, dtype=np.float64)
    return np.einsum("ij,jk,ik->i", d, Sigma_inv, d)


def t2_contributions(res_mean: np.ndarray, mu_r: np.ndarray,
                     Sigma_inv: np.ndarray) -> np.ndarray:
    """센서별 contribution c_i = (r_i - mu_i)·[Sigma^-1 (r - mu)]_i, sum_i c_i = T^2."""
    d = np.asarray(res_mean, dtype=np.float64) - np.asarray(mu_r, dtype=np.float64)
    return d * (d @ np.asarray(Sigma_inv, dtype=np.float64).T)


def as_arrays(cal: dict) -> dict[str, np.ndarray]:
    keys = ("sigma_w", "q95", "std_ref", "mu_r", "Sigma_r", "Sigma_r_inv")
    out = {k: np.asarray(cal[k], dtype=np.float64) for k in keys}
    out["t2_median"] = float(cal["t2_median"])
    out["t2_q95"] = float(cal["t2_q95"])
    out["q95_pooled"] = float(cal["q95_pooled"])
    return out


# --------------------------------------------------------------------------- #
# 저장 / 로드 (json)
# --------------------------------------------------------------------------- #
def save(obj: dict, path: str) -> None:
    write_json(path, obj)


def load(path: str) -> dict:
    return read_json(path)


# --------------------------------------------------------------------------- #
# 진단 표 (CLI `inspect`) — 설계서 1.3, 17장: alpha 가 z_w 스케일에서 얼마인지
# --------------------------------------------------------------------------- #
def sigma_table(cal: dict) -> str:
    lines = ["sigma_w / sigma_global (설계서 1.3, 17장)",
             f"  {'sensor':>6s} {'sigma_w':>12s} {'sigma_global':>14s} {'ratio':>8s}"
             f"   {'alpha=0.5':>10s} {'alpha=1.0':>10s} {'alpha=2.0':>10s}  (z_w 환산)"]
    sg = cal.get("sigma_global")
    for i, s in enumerate(cal["sensors"]):
        sw = cal["sigma_w"][i]
        if not sg:
            lines.append(f"  {s:>6s} {sw:12.5f}")
            continue
        ratio = sg[i] / sw if sw > 0 else float("nan")
        lines.append(f"  {s:>6s} {sw:12.5f} {sg[i]:14.4f} {sw / sg[i]:8.4f}"
                     f"   {0.5 * ratio:10.1f} {1.0 * ratio:10.1f} {2.0 * ratio:10.1f}")
    lines += ["", f"  |z_w| q95 (pooled) = {cal['q95_pooled']:.2f}",
              f"  T2 median = {cal['t2_median']:.1f}, q95 = {cal['t2_q95']:.1f}, "
              f"Sigma_r cond = {cal['condition_number']:.2e}, ridge = {cal['ridge']:.3g}",
              "  ※ alpha·sigma_global 이 z_w 몇에 해당하는지 = alpha × (sigma_global/sigma_w)"]
    return "\n".join(lines)
