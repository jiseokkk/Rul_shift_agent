"""RUL Tool v1 — 배포 모델 출력 궤적 + MC dropout. 설계: docs/design_v1.md §5

  current ỹ, recent N 원값, slope(recent N, /cycle)
  jump     = (ỹ_t − ỹ_{t−1}) / max(1.4826·MAD(이력 Δỹ), floor)
  mc_ratio = std(MC_t) / max(median(std(MC_45..t)), floor)
이력 = cycle 45 ~ t. 외부 참조 없음.
"""
from __future__ import annotations

import numpy as np

from src.tools.base import Tool, mad, robust_sigma, slope


class RULTool(Tool):
    name = "rul"

    def __init__(self, N: int = 10, mad_floor: float = 0.1, mc_std_floor: float = 0.1):
        self.N = int(N)
        self.mad_floor = float(mad_floor)
        self.mc_std_floor = float(mc_std_floor)
        self.cycle: int | None = None
        self.y: list[float] = []
        self.mc_std: list[float] = []
        self.mc_mean: list[float] = []

    def observe(self, cycle: int, y_hat: float, mc_passes: np.ndarray) -> None:
        if self.cycle is not None and cycle != self.cycle + 1:
            raise ValueError(f"cycle 은 연속으로 들어와야 한다: {self.cycle} → {cycle}")
        self.cycle = int(cycle)
        self.y.append(float(y_hat))
        p = np.asarray(mc_passes, dtype=float)
        self.mc_std.append(float(np.std(p)))
        self.mc_mean.append(float(np.mean(p)))

    def _stats(self) -> dict:
        y = np.asarray(self.y, dtype=float)
        recent = y[-self.N:]
        dy_hist = np.diff(y) if y.size >= 2 else np.array([0.0])
        sig_dy = robust_sigma(dy_hist, self.mad_floor)
        jump = float(y[-1] - y[-2]) / sig_dy if y.size >= 2 else 0.0
        med_mc = max(float(np.median(self.mc_std)), self.mc_std_floor)
        return {
            "y_hat": float(y[-1]), "recent": [float(v) for v in recent], "slope": slope(recent),
            "jump": jump, "mc_mean": self.mc_mean[-1], "mc_std": self.mc_std[-1], "mc_ratio": self.mc_std[-1] / med_mc,
            "hist_mad_dy": mad(dy_hist), "hist_median_mc_std": float(np.median(self.mc_std)),
            "recent_std_dy": float(np.std(np.diff(recent))) if recent.size >= 2 else 0.0,
        }

    def summary(self) -> dict:
        st = self._stats()
        return {"cycle": self.cycle, "y_hat": st["y_hat"], "recent": st["recent"], "slope": st["slope"],
                "jump": st["jump"], "mc_ratio": st["mc_ratio"], "n_hist": len(self.y)}

    def stats_row(self) -> dict:
        st = self._stats()
        st.pop("recent")
        return {"cycle": self.cycle, **st}
