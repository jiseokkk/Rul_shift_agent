"""기준선 판정기. 설계: docs/eval_v2_scenario.md §3.7

에이전트 판정 로그와 같은 모양의 first_alarms 표를 만들어 같은 classify 로 채점한다.
  항상 0   경보 없음                                항상 1   t_hat = judge_from
  무작위   매 cycle 독립 확률 p 로 경보. p 는 비교 대상 에이전트의 cycle 당 경보율. n_rep 회 평균
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.eval.scenario_table import classify, scenario_metrics


def _blank(FA: pd.DataFrame) -> pd.DataFrame:
    B = FA.copy()
    B["suspected"], B["n_error"] = "[]", 0
    return B


def always_zero(FA: pd.DataFrame) -> pd.DataFrame:
    B = _blank(FA)
    B["t_hat"] = pd.array([np.nan] * len(B), dtype="Float64")
    return B


def always_one(FA: pd.DataFrame, judge_from: int) -> pd.DataFrame:
    B = _blank(FA)
    B["t_hat"] = pd.array([judge_from] * len(B), dtype="Float64")
    return B


def random_alarms(FA: pd.DataFrame, p: float, judge_from: int, rng: np.random.Generator) -> pd.DataFrame:
    """시나리오마다 첫 경보 ~ judge_from + Geometric(p) − 1, 수명 안이면 채택."""
    B = _blank(FA)
    g = rng.geometric(p, size=len(B)) if p > 0 else np.full(len(B), np.inf)
    t = judge_from + g - 1
    t = np.where(t <= B["T_u"].to_numpy(float), t, np.nan)
    B["t_hat"] = pd.array(t, dtype="Float64")
    return B


def agent_alarm_rate(decisions: pd.DataFrame, judge_from: int) -> float:
    g = decisions[decisions["cycle"] >= judge_from]
    return float((g["degraded"] == 1).sum() / max(len(g), 1))


def baseline_table(FA: pd.DataFrame, judge_from: int, Delta: int, w: int, H: int, p_match: float,
                   n_rep: int = 100, seed: int = 0, cols: list[str] | None = None) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = [{"method": "항상 0", **scenario_metrics(classify(always_zero(FA), Delta, w, H))},
            {"method": "항상 1", **scenario_metrics(classify(always_one(FA, judge_from), Delta, w, H))}]
    for p, name in [(p_match, f"무작위 p={p_match:.3f} (에이전트 경보율)"), (0.05, "무작위 p=0.050")]:
        reps = pd.DataFrame([scenario_metrics(classify(random_alarms(FA, p, judge_from, rng), Delta, w, H)) for _ in range(n_rep)])
        rows.append({"method": name, **reps.mean(numeric_only=True).to_dict()})
    T = pd.DataFrame(rows)
    return T[["method"] + cols] if cols else T
