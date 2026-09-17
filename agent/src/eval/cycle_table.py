"""cycle 단위 채점. 설계: docs/design_v1.md §7-1

- 채점 범위 t ≥ judge_from, eval_mask 구간(t ≥ mask_from) 제외, ERROR(degraded NaN) 제외
- 음성 중복 제거: t < τ_s 인 행은 (unit, cycle) 로 1개만 (scenario_id 정렬 첫 번째)
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def build_cycle_table(decisions: pd.DataFrame, idx: pd.DataFrame, labels: dict, judge_from: int) -> pd.DataFrame:
    """labels: {(unit, sid): pd.Series(index=time, label)}. 반환: 한 행 = 채점되는 (scenario, cycle)."""
    meta = idx.set_index(["unit", "scenario_id"])
    rows = []
    for (u, sid), g in decisions.groupby(["unit", "scenario_id"]):
        m = meta.loc[(u, sid)]
        lab = labels[(u, sid)]
        g = g[g["cycle"] >= judge_from]
        if pd.notna(m["mask_from_cycle"]):
            g = g[g["cycle"] < int(m["mask_from_cycle"])]
        for r in g.itertuples(index=False):
            err = pd.isna(r.degraded)
            rows.append({"unit": u, "scenario_id": sid, "cycle": int(r.cycle), "label": int(lab.loc[int(r.cycle)]),
                         "pred": None if err else int(r.degraded), "error": bool(err),
                         "confidence": r.confidence, "pre_tau_s": int(r.cycle) < int(m["tau_s"]),
                         "type": m["type"], "sensor": m["sensor"], "param": m["param"], "timing_p": m["timing_p"]})
    T = pd.DataFrame(rows)
    return T


def dedup_negatives(T: pd.DataFrame) -> pd.DataFrame:
    """τ_s 이전 행은 (unit, cycle) 당 1개만 남긴다."""
    pre = T[T["pre_tau_s"]].sort_values(["unit", "cycle", "scenario_id"]).drop_duplicates(["unit", "cycle"], keep="first")
    return pd.concat([pre, T[~T["pre_tau_s"]]], ignore_index=True)


def cycle_metrics(T: pd.DataFrame) -> dict:
    n_all = len(T)
    E = T[~T["error"]]
    tp = int(((E["label"] == 1) & (E["pred"] == 1)).sum())
    fn = int(((E["label"] == 1) & (E["pred"] == 0)).sum())
    fp = int(((E["label"] == 0) & (E["pred"] == 1)).sum())
    tn = int(((E["label"] == 0) & (E["pred"] == 0)).sum())
    rec = tp / (tp + fn) if tp + fn else np.nan
    prec = tp / (tp + fp) if tp + fp else np.nan
    far = fp / (fp + tn) if fp + tn else np.nan
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) and not np.isnan(prec) and not np.isnan(rec) else np.nan
    out = {"n_cycles": n_all, "n_error": int(T["error"].sum()), "fail_rate": float(T["error"].mean()) if n_all else np.nan,
           "TP": tp, "FN": fn, "FP": fp, "TN": tn, "recall": rec, "precision": prec, "FAR": far, "F1": f1,
           "pos_rate": (tp + fn) / max(1, len(E))}
    # FAR 부류 (추후 분석용으로 함께 계산)
    neg = E[E["label"] == 0]
    for name, mask in [("FAR_clean", neg["pre_tau_s"]), ("FAR_post", ~neg["pre_tau_s"])]:
        g = neg[mask]
        out[name] = float((g["pred"] == 1).mean()) if len(g) else np.nan
        out[name + "_n"] = int(len(g))
    return out


def cycle_metrics_by(T: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    rows = []
    for k, g in T.groupby(by):
        m = cycle_metrics(g)
        rows.append({**dict(zip(by, k if isinstance(k, tuple) else (k,))), **{c: m[c] for c in ("n_cycles", "TP", "FN", "FP", "TN", "recall", "FAR")}})
    return pd.DataFrame(rows)
