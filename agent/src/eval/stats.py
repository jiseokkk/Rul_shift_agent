"""unit 단위 bootstrap 신뢰구간. 설계: docs/eval_v2_scenario.md §3.9

평가 단위는 시나리오지만 같은 unit 의 시나리오는 독립이 아니므로 (τ_s 이전 판정이 동일) unit 을 복원추출한다.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.eval.scenario_table import scenario_metrics


def unit_bootstrap(S: pd.DataFrame, metrics: list[str], n_boot: int = 2000, seed: int = 0, alpha: float = 0.05) -> pd.DataFrame:
    """반환: metric, point, lo, hi. unit 을 복원추출해 시나리오 표를 다시 쌓는다."""
    units = S["unit"].unique()
    by_unit = {u: g for u, g in S.groupby("unit")}
    rng = np.random.default_rng(seed)
    draws = []
    for _ in range(n_boot):
        pick = rng.choice(units, size=len(units), replace=True)
        R = pd.concat([by_unit[u] for u in pick], ignore_index=True)
        m = scenario_metrics(R)
        draws.append([m[k] for k in metrics])
    D = np.array(draws, dtype=float)
    pt = scenario_metrics(S)
    return pd.DataFrame({"metric": metrics, "point": [pt[k] for k in metrics],
                         "lo": np.nanpercentile(D, 100 * alpha / 2, axis=0), "hi": np.nanpercentile(D, 100 * (1 - alpha / 2), axis=0)})


def paired_diff_bootstrap(SA: pd.DataFrame, SB: pd.DataFrame, metrics: list[str], n_boot: int = 2000, seed: int = 0,
                          alpha: float = 0.05) -> pd.DataFrame:
    """같은 시나리오 집합을 채점한 두 표의 지표 차이 (A − B) 와 unit bootstrap CI."""
    key = ["unit", "scenario_id"]
    SA = SA.set_index(key).sort_index(); SB = SB.set_index(key).sort_index()
    common = SA.index.intersection(SB.index)
    SA, SB = SA.loc[common].reset_index(), SB.loc[common].reset_index()
    units = SA["unit"].unique()
    rng = np.random.default_rng(seed)
    gA = {u: g for u, g in SA.groupby("unit")}; gB = {u: g for u, g in SB.groupby("unit")}
    draws = []
    for _ in range(n_boot):
        pick = rng.choice(units, size=len(units), replace=True)
        mA = scenario_metrics(pd.concat([gA[u] for u in pick], ignore_index=True))
        mB = scenario_metrics(pd.concat([gB[u] for u in pick], ignore_index=True))
        draws.append([mA[k] - mB[k] for k in metrics])
    D = np.array(draws, dtype=float)
    pA, pB = scenario_metrics(SA), scenario_metrics(SB)
    return pd.DataFrame({"metric": metrics, "diff": [pA[k] - pB[k] for k in metrics],
                         "lo": np.nanpercentile(D, 100 * alpha / 2, axis=0), "hi": np.nanpercentile(D, 100 * (1 - alpha / 2), axis=0),
                         "n_scenarios": len(common)})
