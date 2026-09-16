"""Phase D-2: δ 분포 분석 → reports/D_delta_distribution.md (θ 결정 근거)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.analysis import plotting
from src.common import md_table, read_parquet


def collect_delta_stats(paths, index_meta: pd.DataFrame, thetas: list[float]) -> pd.DataFrame:
    """(unit, scenario) 별 τ_s 이후 δ 요약."""
    rows = []
    for r in index_meta.itertuples(index=False):
        d = read_parquet(paths.delta(int(r.unit), r.scenario_id))
        after = d[d["time"] >= int(r.tau_s)]["delta"].to_numpy()
        row = {"unit": int(r.unit), "scenario_id": r.scenario_id, "type": r.type, "sensor": r.sensor,
               "param": r.param, "dir": r.dir, "timing_p": r.timing_p, "tau_s": int(r.tau_s), "T_u": int(r.T_u),
               "n_after": int(after.size),
               "delta_mean": float(after.mean()) if after.size else np.nan,
               "delta_p50": float(np.percentile(after, 50)) if after.size else np.nan,
               "delta_p95": float(np.percentile(after, 95)) if after.size else np.nan,
               "delta_max": float(after.max()) if after.size else np.nan,
               "saturated": bool((int(r.T_u) - int(r.tau_s)) > 125)}
        for th in thetas:
            row[f"frac_gt_{th:.3g}"] = float((after > th).mean()) if after.size else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def _group_table(stats: pd.DataFrame, by: list[str], thetas: list[float]) -> list[dict]:
    rows = []
    for key, g in stats.groupby(by, dropna=False):
        key = key if isinstance(key, tuple) else (key,)
        row = dict(zip(by, key))
        row.update({"n": int(len(g)), "delta_mean": float(g["delta_mean"].mean()),
                    "delta_p95(mean)": float(g["delta_p95"].mean()), "delta_max(mean)": float(g["delta_max"].mean())})
        for th in thetas:
            row[f"frac>{th:.3g}"] = float(g[f"frac_gt_{th:.3g}"].mean())
        rows.append(row)
    return rows


def write_report(paths, stats: pd.DataFrame, clean_var: dict, thetas: list[float], label_cfg: dict,
                 grid: dict) -> Path:
    fig_dir = paths.reports_dir / "figures"
    lines = ["# Phase D-2 — δ 분포와 θ 결정 근거", ""]
    rec = clean_var["recommended"]
    lines.append(f"- 기준 seed {clean_var['base_seed']}, seeds {clean_var['seeds']}, k={clean_var['k']}, m={clean_var['m']}, θ_low = {clean_var['theta_low_ratio']}·θ_high")
    lines.append(f"- **권고 θ_primary = {rec['theta_primary']:.4g}** ({rec['note']})")
    alt2 = rec["theta_alt2"]
    lines.append(f"- θ_alt2 (test RMSE) = {alt2:.4g}" if alt2 is not None else "- θ_alt2 (test RMSE) = n/a")
    lines.append("")
    lines.append("## clean 자연 변동성")
    rows = [dict(metric="V1 abs(ŷ(t)−ŷ(t−1))", **clean_var["V1_adjacent_change"]),
            dict(metric="V2 seed std", **clean_var["V2_seed_std"])]
    lines.append(md_table(rows, fmt="{:.4g}"))
    lines.append("### θ 후보와 clean-only 대조 진입율 (결정 규칙 1: cycle 양성률 ≤ 5%)")
    rows = []
    for name, c in clean_var["candidates"].items():
        ctrl = c["control"] or {}
        rows.append({"cand": name, "theta": c["theta"], "V1": c["v1"], "V2": c["v2"],
                     "ctrl unit_entry": ctrl.get("unit_entry_rate"), "ctrl cycle_pos": ctrl.get("cycle_positive_rate")})
    lines.append(md_table(rows, fmt="{:.4g}"))

    lines.append("## τ_s 이후 δ 요약 — 유형 × 강도")
    lines.append(md_table(_group_table(stats, ["type", "param"], thetas), fmt="{:.3g}"))
    lines.append("## 유형 × 센서")
    lines.append(md_table(_group_table(stats, ["type", "sensor"], thetas), fmt="{:.3g}"))
    lines.append("## 유형 × 시점")
    lines.append(md_table(_group_table(stats, ["type", "timing_p"], thetas), fmt="{:.3g}"))
    lines.append("## 시점 × 포화 여부 (T_u − τ_s > 125)")
    lines.append(md_table(_group_table(stats, ["timing_p", "saturated"], thetas), fmt="{:.3g}"))

    lines.append("## 결정 규칙 2 확인: 최저 강도 bias 에서 δ > θ_primary 비율")
    low = stats[(stats["type"] == "bias")]
    if len(low):
        a_min = low["param"].min()
        g = low[low["param"] == a_min]
        col = f"frac_gt_{rec['theta_primary']:.3g}"
        frac = float(g[col].mean()) if col in g else float("nan")
        lines.append(f"- bias α={a_min}: τ_s 이후 δ > θ_primary 인 cycle 비율 평균 = {frac:.3f} (거의 0 이면 α 하한 인하 또는 θ 하향 검토)")
        lines.append("")

    # figures: 시나리오별 δ p95 (τ_s 이후) 의 유형별 분포
    figs = []
    by_type = {t: g["delta_p95"].dropna().to_numpy() for t, g in stats.groupby("type")}
    if plotting.hist(by_type, fig_dir / "D_delta_p95_by_type.png", "per-scenario δ p95 (after τ_s) by type", "δ p95 [cycle]"):
        figs.append("figures/D_delta_p95_by_type.png")
    lines.append("## 그림")
    for f in figs:
        lines.append(f"![{f}]({f})")
    lines.append("")
    lines.append("## 다음 단계")
    lines.append(f"1. `configs/label.yaml` 의 `thetas.theta_primary.value` 에 확정값 기록 (null 이면 위 권고값 자동 사용)")
    lines.append("2. `decision` 란에 날짜·근거 기록 후 `scripts/08_build_labels.py` 실행")
    out = paths.reports_dir / "D_delta_distribution.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out
