"""도구 공통 인터페이스.

observe(cycle, ...) : cycle 순서대로 데이터를 하나씩 받아 이력을 쌓는다. 미래 데이터는 받을 수 없다.
summary()           : 현재 시점의 LLM 용 요약 (단위 없는 값만)
stats_row()         : 현재 시점의 내부 통계량 (원단위 포함, stats/ 저장용)
"""
from __future__ import annotations

import numpy as np

MAD_SCALE = 1.4826  # 정규분포에서 MAD → σ


def mad(a: np.ndarray) -> float:
    a = np.asarray(a, dtype=float)
    if a.size == 0:
        return 0.0
    m = np.median(a)
    return float(np.median(np.abs(a - m)))


def robust_sigma(a: np.ndarray, floor: float) -> float:
    return max(MAD_SCALE * mad(a), floor)


def slope(y: np.ndarray) -> float:
    y = np.asarray(y, dtype=float)
    if y.size < 2:
        return 0.0
    x = np.arange(y.size, dtype=float)
    return float(np.polyfit(x, y, 1)[0])


class Tool:
    name = "tool"

    def observe(self, cycle: int, **data) -> None:
        raise NotImplementedError

    def summary(self) -> dict:
        raise NotImplementedError

    def stats_row(self) -> dict:
        raise NotImplementedError
