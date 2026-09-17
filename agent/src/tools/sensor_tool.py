"""Sensor Tool v1 — 센서 14개 × 파생값 4개. 설계: docs/design_v1.md §4

기준은 이 unit 의 자기 이력(cycle 1~t)만. train 통계·고정 기준선 없음.
  jump        = (x_t − x_{t−1}) / (1.4826·MAD(이력 Δx))
  noise_ratio = std(Δx, 최근 N) / (1.4826·MAD(이력 Δx))
  flat_ratio  = 현재 연속 동일값 길이 / max(이력의 완료된 연속 동일값 최대 길이, 1)
  level_shift = (median(x, 최근 N) − median(x, 이력)) / max(1.4826·MAD(이력 x), 해상도)
분모 하한: 해상도 (정수 센서 보호). MAD(Δx) 에도 같은 하한.
"""
from __future__ import annotations

import numpy as np

from src.tools.base import Tool, mad, robust_sigma, slope

COLUMNS = ["jump", "noise_ratio", "flat_ratio", "level_shift"]


class SensorTool(Tool):
    name = "sensor"

    def __init__(self, sensors: list[str], resolution: dict[str, float], N: int = 10, short_history: int = 65):
        self.sensors = list(sensors)
        self.res = {s: float(resolution.get(s, 0.01)) for s in self.sensors}
        self.N = int(N)
        self.short_history = int(short_history)
        self.hist: dict[str, list[float]] = {s: [] for s in self.sensors}
        self.cycle: int | None = None
        self.cur_run: dict[str, int] = {s: 0 for s in self.sensors}
        self.max_completed_run: dict[str, int] = {s: 0 for s in self.sensors}

    # ---------------- 스트림 ----------------
    def observe(self, cycle: int, values: dict[str, float]) -> None:
        if self.cycle is not None and cycle != self.cycle + 1:
            raise ValueError(f"cycle 은 연속으로 들어와야 한다: {self.cycle} → {cycle}")
        self.cycle = int(cycle)
        for s in self.sensors:
            x = float(values[s])
            h = self.hist[s]
            if h and x == h[-1]:
                self.cur_run[s] += 1
            else:
                if h:
                    self.max_completed_run[s] = max(self.max_completed_run[s], self.cur_run[s])
                self.cur_run[s] = 1
            h.append(x)

    # ---------------- 계산 ----------------
    def _stats(self, s: str) -> dict:
        x = np.asarray(self.hist[s], dtype=float)
        t = x.size
        res = self.res[s]
        recent = x[-self.N:]
        dx_hist = np.diff(x) if t >= 2 else np.array([0.0])
        dx_recent = np.diff(recent) if recent.size >= 2 else np.array([0.0])
        sig_dx = robust_sigma(dx_hist, res)
        sig_x = robust_sigma(x, res)
        return {
            "x_t": float(x[-1]), "recent_median": float(np.median(recent)), "recent_std_dx": float(np.std(dx_recent)),
            "recent_slope": slope(recent), "hist_median": float(np.median(x)), "hist_mad_x": mad(x), "hist_mad_dx": mad(dx_hist),
            "cur_run": int(self.cur_run[s]), "hist_max_run": int(self.max_completed_run[s]),
            "jump": float(x[-1] - x[-2]) / sig_dx if t >= 2 else 0.0,
            "noise_ratio": float(np.std(dx_recent)) / sig_dx if dx_recent.size >= 2 else 0.0,
            "flat_ratio": float(self.cur_run[s] / max(self.max_completed_run[s], 1)),
            "level_shift": float(np.median(recent) - np.median(x)) / sig_x,
        }

    def summary(self) -> dict:
        """LLM 용. rows: sensor + 4개 파생값, |level_shift| 내림차순."""
        rows = []
        for s in self.sensors:
            st = self._stats(s)
            rows.append({"sensor": s, **{k: st[k] for k in COLUMNS}})
        rows.sort(key=lambda r: -abs(r["level_shift"]))
        return {"rows": rows, "columns": COLUMNS, "sort_key": "level_shift",
                "short_history": bool(self.cycle is not None and self.cycle < self.short_history), "cycle": self.cycle}

    def stats_row(self) -> list[dict]:
        return [{"cycle": self.cycle, "sensor": s, **self._stats(s)} for s in self.sensors]
