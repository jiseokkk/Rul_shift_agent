"""EDA Tool — window 통계 계산, cycle 집계, Agent 입력 evidence 조립 (설계서 4, 5).

시간 단위: sample(10s) → window(5 min, cycle 내부 비중첩) → cycle.

    EDATool(cfg, ref)                      # 정상 기준(reference)만 들고 시작. 이력 비어 있음
      .observe_window(cycle, win)          # 비행 중: window 하나 → z_w, std_ratio, T², contribution
      .end_cycle(cycle)                    # 착륙: window 통계 → cycle 집계(Δμ, Δσ, exceedance), 이력에 추가
      .is_decision_cycle(cycle)            # warm-up 이후 & 이전 cycle L_c 개 확보
      .evidence(cycle)                     # 판정용 dict (현재 window 시계열 + 이전 L_c cycle 집계 + T²)
      .tables()                            # 기록용 표 (window_stats / cycle_sensor / cycle)

Tool 은 도착한 cycle 까지만 안다. 미래 cycle 은 메모리에 없다.

이 Tool 이 **하지 않는** 것 (설계서 4.1, CLAUDE.md 규칙 4):
    - Fault 여부 결정, threshold 판정, Top-K 선택, 센서 제거 → 항상 전 센서를 반환
    - GT(manifest, true RUL, onset) 접근
센서 순서만 T² contribution 내림차순으로 정렬한다 (가독성. 전 센서를 다 주므로 Top-K 금지와
충돌하지 않음).

raw 통계(raw_mean 등)는 tables() 에만 나가고 evidence(LLM 입력)에는 들어가지 않는다 (규칙 5).
"""
from __future__ import annotations

import numpy as np

from .. import data
from ..reference import calibration

# cycle_sensor 표 컬럼 (순서 고정 — prompts / 테스트가 이 이름을 쓴다)
SENSOR_COLS = [
    "z_w_median", "z_w_max", "z_w_min", "exceed_k", "exceed_n", "first_exceed",
    "std_ratio_median", "raw_vs_global", "contrib_frac_median",
    "delta_mu", "delta_sigma",
]
INT_SENSOR_COLS = ("exceed_k", "exceed_n", "first_exceed")
CYCLE_COLS = ["n_windows", "t2_median", "t2_max", "short_flight"]

# cycle 별로 보관하는 window 단위 배열 (float32 — 프롬프트 반올림이 저장 포맷에 무관하게 같도록)
WINDOW_KEYS = ("z_w", "std_ratio", "t2", "contrib_frac",
               "res_mean", "res_std", "raw_mean", "raw_std", "raw_vs_global")


# =========================================================================== #
# 1. window 통계 (설계서 4.2, 5.1)
# =========================================================================== #
def _iqr(a: np.ndarray, axis: int) -> np.ndarray:
    q75, q25 = np.percentile(a, [75, 25], axis=axis)
    return q75 - q25


def compute_window_stats(win: np.ndarray, knn, cal_arr: dict, n_sensors: int,
                         global_arr: dict | None = None) -> dict:
    """win: (n_w, samples, 18) window 묶음 → 각 window 의 raw / residual / 정규화 통계.

    knn        : KNNReference (E[x|W])
    cal_arr    : calibration.as_arrays() (sigma_w, std_ref, mu_r, Sigma_r_inv)
    global_arr : calibration.global_as_arrays() (raw_vs_global 용, 없으면 생략)
    반환 배열은 (n_w, p) 또는 (n_w,), window 는 비행 순서.
    """
    win = np.asarray(win, dtype=np.float32)
    n_w, spw, _ = win.shape
    p = int(n_sensors)

    raw = win[:, :, :p].astype(np.float64)
    flat = win.reshape(-1, win.shape[-1])
    res = knn.residuals(flat, p).astype(np.float64).reshape(n_w, spw, p)

    res_mean, res_std = calibration.window_residual_stats(res)
    z_w = res_mean / cal_arr["sigma_w"]
    std_ratio = res_std / cal_arr["std_ref"]

    t2 = calibration.hotelling_t2(res_mean, cal_arr["mu_r"], cal_arr["Sigma_r_inv"])
    contrib = calibration.t2_contributions(res_mean, cal_arr["mu_r"], cal_arr["Sigma_r_inv"])
    with np.errstate(divide="ignore", invalid="ignore"):
        contrib_frac = np.where(t2[:, None] > 0, contrib / t2[:, None], 0.0)

    out = {
        "n_windows": n_w,
        "raw_mean": raw.mean(axis=1), "raw_median": np.median(raw, axis=1),
        "raw_std": raw.std(axis=1), "raw_iqr": _iqr(raw, 1),
        "res_mean": res_mean, "res_median": np.median(res, axis=1),
        "res_std": res_std, "res_iqr": _iqr(res, 1),
        "z_w": z_w, "std_ratio": std_ratio,
        "t2": t2, "contrib": contrib, "contrib_frac": contrib_frac,
    }
    if global_arr is not None:
        gs = np.where(global_arr["std"] > 0, global_arr["std"], np.nan)
        out["raw_vs_global"] = (out["raw_mean"] - global_arr["mean"]) / gs
    return out


# =========================================================================== #
# 2. cycle 집계 (설계서 4.2, 4.3)
# =========================================================================== #
def aggregate_cycle(ws: dict, q95: np.ndarray, min_windows_short: int = 6) -> dict:
    """한 cycle 의 window 통계 → {"sensor": {col: (p,)}, "cycle": {col: scalar}}.

    delta_mu / delta_sigma 는 이전 cycle 이 필요하므로 contrast() 가 따로 채운다.
    """
    z, sr = ws["z_w"], ws["std_ratio"]
    n_w = int(ws["n_windows"])
    q95 = np.asarray(q95, dtype=np.float64)

    exceed = np.abs(z) > q95
    exceed_k = exceed.sum(axis=0).astype(np.int64)
    first = np.where(exceed.any(axis=0), exceed.argmax(axis=0) + 1, -1)   # 1-based

    sensor = {
        "z_w_median": np.median(z, axis=0),
        "z_w_max": z.max(axis=0),
        "z_w_min": z.min(axis=0),
        "exceed_k": exceed_k,
        "exceed_n": np.full(z.shape[1], n_w, dtype=np.int64),
        "first_exceed": first.astype(np.int64),
        "std_ratio_median": np.median(sr, axis=0),
        "raw_vs_global": (np.median(ws["raw_vs_global"], axis=0)
                          if "raw_vs_global" in ws else np.full(z.shape[1], np.nan)),
        "contrib_frac_median": np.median(ws["contrib_frac"], axis=0),
        "delta_mu": np.full(z.shape[1], np.nan),
        "delta_sigma": np.full(z.shape[1], np.nan),
    }
    cycle = {
        "n_windows": n_w,
        "t2_median": float(np.median(ws["t2"])),
        "t2_max": float(np.max(ws["t2"])),
        "short_flight": bool(n_w < min_windows_short),
    }
    return {"sensor": sensor, "cycle": cycle}


def contrast(cur: dict, prev: list[dict]) -> None:
    """Step / Spread contrast 를 cur 에 in-place 로 채운다 (설계서 4.3).

        Delta_mu    = z_w_median(t)       - median_{prev}(z_w_median)
        Delta_sigma = std_ratio_median(t) - median_{prev}(std_ratio_median)

    prev 가 비어 있으면(warm-up) NaN 으로 남긴다.
    """
    if not prev:
        return
    zm = np.stack([q["sensor"]["z_w_median"] for q in prev], axis=0)
    sm = np.stack([q["sensor"]["std_ratio_median"] for q in prev], axis=0)
    cur["sensor"]["delta_mu"] = cur["sensor"]["z_w_median"] - np.median(zm, axis=0)
    cur["sensor"]["delta_sigma"] = cur["sensor"]["std_ratio_median"] - np.median(sm, axis=0)


def fill_contrasts(per_cycle: list[dict], L_c: int) -> None:
    """cycle 오름차순 리스트 전체에 contrast 를 채운다 (배치 계산 / 테스트용)."""
    for i, cur in enumerate(per_cycle):
        contrast(cur, per_cycle[max(0, i - L_c):i])


def to_tables(cycles: list[int], per_cycle: list[dict], sensors: list[str],
              ) -> tuple[list[dict], list[dict]]:
    """(cycle_sensor rows, cycle rows) — CSV 로 바로 쓸 수 있는 dict 리스트."""
    cs_rows, c_rows = [], []
    for c, agg in zip(cycles, per_cycle):
        for j, s in enumerate(sensors):
            row = {"cycle": int(c), "sensor": s}
            for col in SENSOR_COLS:
                v = agg["sensor"][col][j]
                row[col] = int(v) if col in INT_SENSOR_COLS else float(v)
            cs_rows.append(row)
        c_rows.append({"cycle": int(c), **{k: agg["cycle"][k] for k in CYCLE_COLS}})
    return cs_rows, c_rows


# =========================================================================== #
# 3. Tool (스트림 상태 + evidence 조립)
# =========================================================================== #
class EDATool:
    def __init__(self, cfg, ref: dict):
        self.cfg = cfg
        self.sensors: list[str] = cfg.sensors
        self.p = cfg.n_sensors
        self.spw = cfg.samples_per_window
        self.min_short = cfg.min_windows_short_flight
        self.L_c = cfg.L_c
        self.warm_up = cfg.warm_up
        self.L_w_sec = int(cfg.exp.time["L_w_sec"])

        self.knn = ref["knn"]
        self.cal = ref["calibration"]
        self.cal_arr = calibration.as_arrays(self.cal)
        self.g_arr = (calibration.global_as_arrays(ref["global"])
                      if ref.get("global") is not None else None)
        self.reset()

    # ------------------------------------------------------------------ #
    def reset(self, scenario_id: str | None = None, unit: int | None = None) -> None:
        """새 시나리오 시작. 이력을 비운다."""
        self.scenario_id = scenario_id
        self.unit = unit
        self.cycles: list[int] = []                     # window 가 1개 이상인 cycle, 도착 순
        self.aggs: dict[int, dict] = {}                 # cycle → aggregate_cycle 결과
        self.windows: dict[int, dict[str, np.ndarray]] = {}   # cycle → window 배열 (float32)
        self.skipped: list[int] = []                    # window 0개로 건너뛴 cycle
        self._buf: list[dict] = []
        self._buf_cycle: int | None = None

    # ------------------------------------------------------------------ 비행 중
    def observe_window(self, cycle: int, win: np.ndarray) -> None:
        """window 하나 (samples, 18) 도착 → 통계 계산 후 현재 cycle 버퍼에 추가."""
        cycle = int(cycle)
        if self._buf_cycle is not None and cycle != self._buf_cycle:
            raise RuntimeError(f"cycle {self._buf_cycle} 가 end_cycle 되지 않은 채 "
                               f"cycle {cycle} 의 window 가 도착했다")
        self._buf_cycle = cycle
        win = np.asarray(win, dtype=np.float32)
        if win.ndim == 2:
            win = win[None]
        self._buf.append(compute_window_stats(win, self.knn, self.cal_arr, self.p, self.g_arr))

    # ------------------------------------------------------------------ 착륙
    def end_cycle(self, cycle: int) -> bool:
        """비행 종료. 버퍼의 window 통계를 cycle 집계로 확정하고 이력에 추가.

        window 가 하나도 없는 초단기 비행이면 False (cycle 은 skipped 에 기록).
        """
        cycle = int(cycle)
        buf, self._buf, self._buf_cycle = self._buf, [], None
        if not buf:
            self.skipped.append(cycle)
            return False

        ws = {k: np.concatenate([b[k] for b in buf], axis=0)
              for k in buf[0] if k != "n_windows"}
        ws["n_windows"] = int(sum(b["n_windows"] for b in buf))

        agg = aggregate_cycle(ws, self.cal_arr["q95"], self.min_short)
        prev = [self.aggs[c] for c in self.cycles[-self.L_c:]] if self.L_c > 0 else []
        contrast(agg, prev)

        self.cycles.append(cycle)
        self.aggs[cycle] = agg
        self.windows[cycle] = {k: ws[k].astype(np.float32) for k in WINDOW_KEYS if k in ws}
        return True

    def observe_cycle(self, cycle: int, seq: np.ndarray) -> bool:
        """cycle 전체 시계열을 window 로 잘라 observe_window → end_cycle 까지 한 번에."""
        for win in data.split_windows(seq, self.spw):
            self.observe_window(cycle, win)
        return self.end_cycle(cycle)

    # ------------------------------------------------------------------ 판정
    def is_decision_cycle(self, cycle: int) -> bool:
        """warm-up 이후 & 이전 cycle L_c 개 확보 (설계서 12.1 / agent_spec 3.4)."""
        cycle = int(cycle)
        if cycle not in self.aggs:
            return False
        return cycle > self.warm_up and self.cycles.index(cycle) >= self.L_c

    def evidence(self, cycle: int) -> dict:
        """(scenario, cycle) 의 Agent 입력 evidence. 이력에 있는 cycle 만 사용한다.

        구조:
            meta         : scenario_id, unit, cycle, n_windows, short_flight, L_w_sec
            calibration  : q95_pooled, q95_per_sensor, std_ratio_ref(=1.0), t2_median, t2_q95
            multivariate : cycles, t2_median[], t2_max[], contribution[(sensor, frac)]
            sensors      : contribution 내림차순, 각 항목에 prev(L_c cycle 집계) + current(window 시계열)
        """
        cycle = int(cycle)
        if cycle not in self.aggs:
            raise ValueError(f"{self.scenario_id}: cycle {cycle} 은 이력에 없다")
        i = self.cycles.index(cycle)
        prev_cycles = self.cycles[max(0, i - self.L_c):i]
        mv_cycles = prev_cycles + [cycle]

        def sval(c: int, col: str, j: int):
            v = self.aggs[c]["sensor"][col][j]
            return int(v) if col in INT_SENSOR_COLS else float(v)

        cur_agg = self.aggs[cycle]
        cur_win = self.windows[cycle]
        contrib_med = np.median(cur_win["contrib_frac"], axis=0)
        order = np.argsort(-contrib_med)              # 내림차순, 전 센서 유지

        sensor_blocks = []
        for j in order:
            s = self.sensors[j]
            sensor_blocks.append({
                "sensor": s,
                "contribution": float(contrib_med[j]),
                "prev": {
                    "cycles": prev_cycles,
                    "z_w_median": [sval(c, "z_w_median", j) for c in prev_cycles],
                    "z_w_max": [sval(c, "z_w_max", j) for c in prev_cycles],
                    "exceed_k": [sval(c, "exceed_k", j) for c in prev_cycles],
                    "exceed_n": [sval(c, "exceed_n", j) for c in prev_cycles],
                    "std_ratio_median": [sval(c, "std_ratio_median", j) for c in prev_cycles],
                },
                "current": {
                    "n_windows": sval(cycle, "exceed_n", j),
                    "exceed_k": sval(cycle, "exceed_k", j),
                    "first_exceed": sval(cycle, "first_exceed", j),
                    "delta_mu": sval(cycle, "delta_mu", j),
                    "delta_sigma": sval(cycle, "delta_sigma", j),
                    "z_w": cur_win["z_w"][:, j].tolist(),
                    "std_ratio": cur_win["std_ratio"][:, j].tolist(),
                },
            })

        return {
            "meta": {
                "scenario_id": self.scenario_id,
                "unit": self.unit if self.unit is not None else "?",
                "cycle": cycle,
                "n_windows": int(cur_agg["cycle"]["n_windows"]),
                "short_flight": bool(cur_agg["cycle"]["short_flight"]),
                "L_w_sec": self.L_w_sec,
            },
            "calibration": {
                "q95_pooled": float(self.cal["q95_pooled"]),
                "q95_per_sensor": {s: float(v) for s, v in zip(self.cal["sensors"], self.cal["q95"])},
                "std_ratio_ref": 1.0,
                "t2_median": float(self.cal["t2_median"]),
                "t2_q95": float(self.cal["t2_q95"]),
            },
            "multivariate": {
                "cycles": mv_cycles,
                "t2_median": [float(self.aggs[c]["cycle"]["t2_median"]) for c in mv_cycles],
                "t2_max": [float(self.aggs[c]["cycle"]["t2_max"]) for c in mv_cycles],
                "contribution": [(self.sensors[j], float(contrib_med[j])) for j in order],
            },
            "sensors": sensor_blocks,
        }

    # ------------------------------------------------------------------ 기록
    def tables(self) -> dict[str, list[dict]]:
        """실험 후 파 볼 때 쓰는 표 3개. LLM 은 이 표를 보지 않는다.

        window_stats : (cycle, window_idx[1-based], start_sample, sensor) 한 줄.
                       start_sample 로 원본 series.npz 에서 raw 구간을 바로 찾을 수 있다.
        cycle_sensor : cycle × sensor 집계 (SENSOR_COLS)
        cycle        : cycle 수준 (CYCLE_COLS)
        """
        cs_rows, c_rows = to_tables(self.cycles, [self.aggs[c] for c in self.cycles], self.sensors)
        w_rows = []
        for c in self.cycles:
            w = self.windows[c]
            n_w = len(w["z_w"])
            for k in range(n_w):
                for j, s in enumerate(self.sensors):
                    row = {"cycle": c, "window_idx": k + 1, "start_sample": k * self.spw,
                           "sensor": s, "t2": float(w["t2"][k])}
                    for key in ("z_w", "std_ratio", "contrib_frac", "res_mean", "res_std",
                                "raw_mean", "raw_std", "raw_vs_global"):
                        if key in w:
                            row[key] = float(w[key][k, j])
                    w_rows.append(row)
        return {"window_stats": w_rows, "cycle_sensor": cs_rows, "cycle": c_rows}
