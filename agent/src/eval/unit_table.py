"""unit(시나리오) 단위 채점. 설계: docs/design_v1.md §7-2

t_hat = τ_s 이후 첫 판정 1 (ERROR 건너뜀). delay = t_hat − τ_d.
  τ_d − w ≤ t_hat ≤ τ_d + D → TP,  τ_s ≤ t_hat < τ_d − w → Early,  t_hat > τ_d + D → Late,  없음 → Miss
pre_alarm = judge_from ≤ t < τ_s 구간에 판정 1 이 있었나 (cycle 표에서 FP 로 이미 벌점).
비저하 시나리오: any_alarm = τ_s 이후 판정 1 이 있었나 (시나리오 FAR).
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd


def build_unit_table(decisions: pd.DataFrame, idx: pd.DataFrame, judge_from: int, w: int, D: int) -> pd.DataFrame:
    meta = idx.set_index(["unit", "scenario_id"])
    rows = []
    for (u, sid), g in decisions.groupby(["unit", "scenario_id"]):
        m = meta.loc[(u, sid)]
        tau_s = int(m["tau_s"]); degraded = bool(m["degraded"])
        tau_d = int(m["tau_d"]) if pd.notna(m["tau_d"]) else None
        g = g[g["cycle"] >= judge_from].sort_values("cycle")
        ok = g[g["degraded"].notna()]
        alarms = ok[ok["degraded"] == 1]
        pre_alarm = bool((alarms["cycle"] < tau_s).any())
        post = alarms[alarms["cycle"] >= tau_s]
        t_hat = int(post["cycle"].iloc[0]) if len(post) else None
        row = {"unit": u, "scenario_id": sid, "type": m["type"], "sensor": m["sensor"], "param": m["param"], "dir": m["dir"],
               "timing_p": m["timing_p"], "T_u": int(m["T_u"]), "tau_s": tau_s, "tau_d": tau_d, "degraded": degraded,
               "t_hat": t_hat, "pre_alarm": pre_alarm, "any_alarm_post": t_hat is not None,
               "n_error": int(g["degraded"].isna().sum())}
        if degraded:
            if t_hat is None:
                res, delay = "Miss", None
            else:
                delay = t_hat - tau_d
                res = "TP" if -w <= delay <= D else ("Early" if delay < -w else "Late")
            row.update({"result": res, "delay": delay, "delay_from_tau_s": (t_hat - tau_s) if t_hat is not None else None})
            # isolation: t_hat 시점의 의심 센서에 주입 센서가 포함되나
            if t_hat is not None:
                s = post.iloc[0]["suspected_sensors"]
                sus = set(json.loads(s)) if isinstance(s, str) else set(s or [])
                inj = set(str(m["sensor"]).split("+"))
                row["iso_hit"] = bool(inj & sus)
                row["iso_jaccard"] = len(inj & sus) / len(inj | sus) if (inj | sus) else np.nan
        else:
            row.update({"result": "FP" if t_hat is not None else "TN", "delay": None, "delay_from_tau_s": None})
        rows.append(row)
    return pd.DataFrame(rows)


def unit_metrics(U: pd.DataFrame) -> dict:
    deg = U[U["degraded"]]
    non = U[~U["degraded"]]
    tp = deg[deg["result"] == "TP"]
    out = {"n_degraded": int(len(deg)), "n_nondegraded": int(len(non)),
           "detection_rate": float((deg["result"] == "TP").mean()) if len(deg) else np.nan,
           "early_rate": float((deg["result"] == "Early").mean()) if len(deg) else np.nan,
           "late_rate": float((deg["result"] == "Late").mean()) if len(deg) else np.nan,
           "miss_rate": float((deg["result"] == "Miss").mean()) if len(deg) else np.nan,
           "MDD_mean": float(tp["delay"].mean()) if len(tp) else np.nan,
           "MDD_median": float(tp["delay"].median()) if len(tp) else np.nan,
           "delay_all_median": float(deg["delay"].dropna().median()) if deg["delay"].notna().any() else np.nan,
           "scenario_FAR": float(non["any_alarm_post"].mean()) if len(non) else np.nan,
           "pre_alarm_rate": float(U["pre_alarm"].mean()) if len(U) else np.nan,
           "isolation_rate": float(tp["iso_hit"].mean()) if len(tp) and "iso_hit" in tp else np.nan}
    return out


def unit_metrics_by(U: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    rows = []
    for k, g in U.groupby(by):
        m = unit_metrics(g)
        rows.append({**dict(zip(by, k if isinstance(k, tuple) else (k,))),
                     **{c: m[c] for c in ("n_degraded", "detection_rate", "early_rate", "late_rate", "miss_rate", "MDD_median", "n_nondegraded", "scenario_FAR")}})
    return pd.DataFrame(rows)
