"""시나리오(event) 단위 채점 v2. 설계: docs/eval_v2_scenario.md §3

두 단계로 나눈다. 첫 경보 추출은 판정 로그에만 의존하고, 분류는 (Δ, w, H) 만 받는다.

  first_alarms(decisions, idx, judge_from, k)  → 시나리오별 t_hat (judge_from 이후 첫 경보, τ_s 이전 포함), 지목 센서, 오류 수
  classify(FA, Delta, w, H)                    → 시나리오별 결과 하나

저하 시나리오  (창 W = [max(τ_s, τ_d − w), min(τ_d + Δ, T_u)])
  PreContam  t_hat < τ_s                         오염이 없는데 울림
  PreDegr    τ_s ≤ t_hat < max(τ_s, τ_d − w)     오염은 봤지만 출력 저하 전에 울림
  TP         t_hat ∈ W
  Miss       창 끝까지 경보 없음 (Late 포함)
비저하 시나리오 (관찰 끝 = min(τ_s + H, T_u))
  FP_clean   t_hat < τ_s        FP_contam  τ_s ≤ t_hat ≤ 관찰 끝        TN  그때까지 경보 없음
경보 = 판정 1 이 k 번 연속된 구간의 첫 cycle. ERROR 는 경보 아님. 첫 경보 하나로 결과가 정해진다.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

DEG_RESULTS = ["TP", "PreContam", "PreDegr", "Miss"]
NON_RESULTS = ["TN", "FP_clean", "FP_contam"]
META_COLS = ["type", "sensor", "param", "dir", "timing_p", "T_u", "tau_s", "tau_d", "degraded"]


def _first_run_start(cycles: np.ndarray, on: np.ndarray, k: int) -> int | None:
    """on 이 k 번 연속 True 인 첫 구간의 시작 cycle. cycles 는 오름차순 연속이 아니어도 되나 연속 판정은 행 순서 기준."""
    if k <= 1:
        hit = np.flatnonzero(on)
        return int(cycles[hit[0]]) if len(hit) else None
    run = 0
    for i, v in enumerate(on):
        run = run + 1 if v else 0
        if run >= k:
            return int(cycles[i - k + 1])
    return None


def first_alarms(decisions: pd.DataFrame, idx: pd.DataFrame, judge_from: int, k: int = 1) -> pd.DataFrame:
    """한 행 = 시나리오. t_hat, suspected(t_hat 시점), n_error, last_cycle + 메타."""
    meta = idx.drop_duplicates(["unit", "scenario_id"]).set_index(["unit", "scenario_id"])
    rows = []
    for (u, sid), g in decisions.groupby(["unit", "scenario_id"], sort=True):
        m = meta.loc[(u, sid)]
        g = g[g["cycle"] >= judge_from].sort_values("cycle")
        on = (g["degraded"] == 1).to_numpy()  # NaN(ERROR) → False
        t_hat = _first_run_start(g["cycle"].to_numpy(), on, k)
        sus = []
        if t_hat is not None:
            s = g.loc[g["cycle"] == t_hat, "suspected_sensors"].iloc[0]
            sus = json.loads(s) if isinstance(s, str) else list(s or [])
        rows.append({"unit": int(u), "scenario_id": sid, **{c: m[c] for c in META_COLS},
                     "tau_d": int(m["tau_d"]) if pd.notna(m["tau_d"]) else np.nan, "degraded": bool(m["degraded"]),
                     "t_hat": t_hat, "suspected": json.dumps(sus), "n_error": int(g["degraded"].isna().sum()),
                     "n_judged": int(len(g)), "last_cycle": int(g["cycle"].max()) if len(g) else np.nan})
    FA = pd.DataFrame(rows)
    FA["t_hat"] = FA["t_hat"].astype("Float64")
    return FA


def classify(FA: pd.DataFrame, Delta: int, w: int = 0, H: int = 40) -> pd.DataFrame:
    """first_alarms 표에 result · delay · window · iso 컬럼을 붙인다. 원 표는 바꾸지 않는다."""
    S = FA.copy()
    t = S["t_hat"].astype(float).to_numpy()  # NaN = 경보 없음
    has = ~np.isnan(t)
    deg = S["degraded"].to_numpy(bool)
    tau_s, T_u = S["tau_s"].to_numpy(float), S["T_u"].to_numpy(float)
    tau_d = S["tau_d"].astype(float).to_numpy()
    lo = np.where(deg, np.maximum(tau_s, tau_d - w), np.nan)
    hi = np.where(deg, np.minimum(tau_d + Delta, T_u), np.minimum(tau_s + H, T_u))
    res = np.full(len(S), "", dtype=object)
    d = deg
    res[d & (~has | (t > hi))] = "Miss"
    res[d & has & (t < tau_s)] = "PreContam"
    res[d & has & (t >= tau_s) & (t < lo)] = "PreDegr"
    res[d & has & (t >= lo) & (t <= hi)] = "TP"
    n = ~deg
    res[n & (~has | (t > hi))] = "TN"
    res[n & has & (t < tau_s)] = "FP_clean"
    res[n & has & (t >= tau_s) & (t <= hi)] = "FP_contam"
    S["result"] = res
    S["window_lo"], S["window_hi"] = lo, hi
    S["delay"] = np.where(res == "TP", t - tau_d, np.nan)
    S["covered"] = S["last_cycle"].to_numpy(float) >= hi  # 판정 로그가 창 끝까지 있나 (절단 실행 점검)
    inj = S["sensor"].astype(str).str.split("+").map(set)
    sus = S["suspected"].map(lambda s: set(json.loads(s)))
    S["iso_hit"] = [bool(i & s) if r == "TP" else np.nan for i, s, r in zip(inj, sus, res)]
    S["iso_jaccard"] = [len(i & s) / len(i | s) if r == "TP" and (i | s) else np.nan for i, s, r in zip(inj, sus, res)]
    return S


def scenario_metrics(S: pd.DataFrame) -> dict:
    deg, non = S[S["degraded"]], S[~S["degraded"]]
    tp = deg[deg["result"] == "TP"]
    rate = lambda df, r: float((df["result"] == r).mean()) if len(df) else np.nan
    return {"n_degraded": int(len(deg)), "n_nondegraded": int(len(non)),
            "detection_rate": rate(deg, "TP"), "pre_contam_rate": rate(deg, "PreContam"),
            "pre_degr_rate": rate(deg, "PreDegr"), "miss_rate": rate(deg, "Miss"),
            "delay_mean": float(tp["delay"].mean()) if len(tp) else np.nan,
            "delay_median": float(tp["delay"].median()) if len(tp) else np.nan,
            "scenario_FAR": float(non["result"].isin(["FP_clean", "FP_contam"]).mean()) if len(non) else np.nan,
            "FAR_clean": rate(non, "FP_clean"), "FAR_contam": rate(non, "FP_contam"),
            "isolation_rate": float(tp["iso_hit"].astype(float).mean()) if len(tp) else np.nan,
            "iso_jaccard": float(tp["iso_jaccard"].mean()) if len(tp) else np.nan,
            "pre_contam_all": float((S["t_hat"].astype(float) < S["tau_s"]).mean()) if len(S) else np.nan,
            "error_rate": float(S["n_error"].sum() / max(S["n_judged"].sum(), 1)),
            "n_uncovered": int((~S["covered"]).sum())}


MAIN_COLS = ["n_degraded", "detection_rate", "pre_contam_rate", "pre_degr_rate", "miss_rate", "delay_median",
             "n_nondegraded", "scenario_FAR", "FAR_clean", "FAR_contam", "isolation_rate"]


def metrics_by(S: pd.DataFrame, by: list[str], cols: list[str] = MAIN_COLS) -> pd.DataFrame:
    rows = []
    for key, g in S.groupby(by, dropna=False):
        key = key if isinstance(key, tuple) else (key,)
        m = scenario_metrics(g)
        rows.append({**dict(zip(by, key)), **{c: m[c] for c in cols}})
    return pd.DataFrame(rows)


def end_cycles(idx: pd.DataFrame, Delta: int, H: int) -> pd.DataFrame:
    """runner 가 LLM 호출을 멈출 cycle (evaluation truncation, §3.5). 저하 τ_d + Δ, 비저하 τ_s + H, 수명 안으로.

    채점 쪽에서 계산해 시나리오 목록 CSV 의 end_cycle 열로 전달한다. runner 는 이 숫자만 읽는다 (truth 모듈 import 금지 유지).
    """
    m = idx.drop_duplicates(["unit", "scenario_id"])
    deg = m["degraded"].astype(bool)
    end = np.where(deg, m["tau_d"].astype(float) + Delta, m["tau_s"].astype(float) + H)
    end = np.minimum(end, m["T_u"].astype(float)).astype(int)
    return pd.DataFrame({"unit": m["unit"].astype(int).to_numpy(), "scenario_id": m["scenario_id"].to_numpy(), "end_cycle": end})


def pre_contam_by_timing(S: pd.DataFrame) -> pd.DataFrame:
    """오염 시점별 오염 전 경보율 (저하·비저하 합산). 오염 전 판정은 시나리오 종류와 무관하다."""
    S = S.assign(pre_len=S["tau_s"] - 55, pre=S["t_hat"].astype(float) < S["tau_s"])
    return S.groupby("timing_p").agg(n=("pre", "size"), pre_len_median=("pre_len", "median"),
                                     pre_contam_rate=("pre", "mean")).reset_index()
