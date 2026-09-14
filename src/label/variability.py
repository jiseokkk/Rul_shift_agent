"""Phase D-2: clean 예측의 자연 변동성 → θ 후보.

V1  |ŷ(t) − ŷ(t−1)|  (기준 seed, hold-out 전체)        → θ_primary = percentile
V2  cycle 별 3 seed 예측 표준편차                         → V1 교차 검증
V3  test RMSE (B-3)                                        → θ_alt2
clean-only 대조: |ŷ_seed_other(t) − ŷ_base(t)| 에 히스테리시스를 적용한 진입율 (θ 검증)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.label.hysteresis import hysteresis_label

PCTS = (50, 75, 90, 95, 99, 99.9)


def percentiles(arr: np.ndarray) -> dict:
    arr = np.asarray(arr, dtype=float)
    out = {f"p{p:g}": float(np.percentile(arr, p)) for p in PCTS}
    out.update({"n": int(arr.size), "mean": float(arr.mean()), "max": float(arr.max())})
    return out


def v1_adjacent(pred_frames: dict) -> np.ndarray:
    parts = [np.abs(np.diff(df.sort_values("time")["pred"].to_numpy())) for df in pred_frames.values()]
    return np.concatenate(parts)


def v2_seed_std(pred_by_seed: dict) -> np.ndarray:
    """pred_by_seed: seed → {unit → df}. 모든 seed 에 공통인 unit·time 에서 std(ddof=0)."""
    seeds = list(pred_by_seed)
    units = set.intersection(*[set(pred_by_seed[s]) for s in seeds])
    parts = []
    for u in sorted(units):
        mats = []
        for s in seeds:
            mats.append(pred_by_seed[s][u].sort_values("time")["pred"].to_numpy())
        n = min(len(x) for x in mats)
        parts.append(np.std(np.stack([x[:n] for x in mats]), axis=0))
    return np.concatenate(parts)


def clean_control_deltas(pred_by_seed: dict, base_seed: int) -> dict:
    """{other_seed: {unit: (times, delta)}}"""
    out = {}
    base = pred_by_seed[base_seed]
    for s, frames in pred_by_seed.items():
        if s == base_seed:
            continue
        out[s] = {}
        for u, df in frames.items():
            a = base[u].sort_values("time")
            b = df.sort_values("time")
            m = a.merge(b, on="time", suffixes=("_a", "_b"))
            out[s][u] = (m["time"].to_numpy(), np.abs(m["pred_b"].to_numpy() - m["pred_a"].to_numpy()))
    return out


def clean_control_entry_rate(control: dict, theta: float, k: int, m: int, ratio: float) -> dict:
    """진입율 두 가지: unit 단위(한 번이라도 진입한 unit 비율), cycle 단위(라벨 1 cycle 비율)."""
    n_units = n_enter = n_cycles = n_pos = 0
    for s, frames in control.items():
        for u, (times, d) in frames.items():
            res = hysteresis_label(d, theta, k, m, ratio)
            n_units += 1
            n_enter += int(res["tau_d_idx"] is not None)
            n_cycles += len(d)
            n_pos += int(res["label"].sum())
    return {"theta": float(theta), "unit_entry_rate": n_enter / max(1, n_units),
            "cycle_positive_rate": n_pos / max(1, n_cycles), "n_units": n_units, "n_cycles": n_cycles}


def build_clean_variability(pred_by_seed: dict, base_seed: int, test_rmse: float | None,
                            k: int, m: int, ratio: float, primary_pct: float = 95,
                            max_control_rate: float = 0.05) -> dict:
    """clean_variability.json 내용."""
    v1 = v1_adjacent(pred_by_seed[base_seed])
    v2 = v2_seed_std(pred_by_seed) if len(pred_by_seed) > 1 else np.array([0.0])
    v1p, v2p = percentiles(v1), percentiles(v2)
    control = clean_control_deltas(pred_by_seed, base_seed)

    def theta_at(pct):
        return max(float(np.percentile(v1, pct)), float(np.percentile(v2, pct)))

    cands = {}
    for pct in sorted({90, 95, 99, primary_pct}):
        th = theta_at(pct)
        cands[f"p{pct:g}"] = {"theta": th, "v1": float(np.percentile(v1, pct)), "v2": float(np.percentile(v2, pct)),
                              "control": clean_control_entry_rate(control, th, k, m, ratio) if control else None}

    chosen_pct = primary_pct
    chosen = cands[f"p{primary_pct:g}"]
    note = f"θ_primary = max(V1 p{primary_pct:g}, V2 p{primary_pct:g})"
    if chosen["control"] and chosen["control"]["cycle_positive_rate"] > max_control_rate:
        chosen_pct = 99
        chosen = cands["p99"]
        note += f"; clean-only 대조 cycle 양성률 > {max_control_rate:.0%} 이므로 99p 로 상향 (결정 규칙 1)"

    return {
        "base_seed": base_seed, "seeds": sorted(pred_by_seed), "k": k, "m": m, "theta_low_ratio": ratio,
        "V1_adjacent_change": v1p, "V2_seed_std": v2p, "V3_test_rmse": test_rmse,
        "candidates": cands,
        "recommended": {"theta_primary": chosen["theta"], "percentile": chosen_pct,
                        "theta_alt2": test_rmse, "note": note},
    }
