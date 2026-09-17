"""run 하나를 채점해 runs/{run_id}/eval/ 에 표·리포트 저장."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.data.truth import load_index, load_labels
from src.eval.cycle_table import build_cycle_table, cycle_metrics, cycle_metrics_by, dedup_negatives
from src.eval.unit_table import build_unit_table, unit_metrics, unit_metrics_by


def _md(df: pd.DataFrame, fmt: str = "{:.3f}") -> str:
    if df is None or not len(df):
        return "(없음)"
    cols = list(df.columns)
    L = ["| " + " | ".join(str(c) for c in cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            cells.append(fmt.format(v) if isinstance(v, (float, np.floating)) and not pd.isna(v) else ("" if pd.isna(v) else str(v)))
        L.append("| " + " | ".join(cells) + " |")
    return "\n".join(L)


def evaluate_run(run_dir: Path, acfg: dict, theta_name: str = "theta_primary") -> dict:
    run_dir = Path(run_dir)
    dec = pd.read_csv(run_dir / "decisions.csv")
    idx = load_index(theta_name=theta_name)
    keys = dec[["unit", "scenario_id"]].drop_duplicates()
    labels = {(int(r.unit), r.scenario_id): load_labels(int(r.unit), r.scenario_id, theta_name=theta_name) for r in keys.itertuples()}
    jf, w, D = int(acfg["judge_from"]), int(acfg["w"]), int(acfg["D"])

    T_all = build_cycle_table(dec, idx, labels, jf)
    T = dedup_negatives(T_all)
    cm = cycle_metrics(T)
    cm_nodedup = cycle_metrics(T_all)
    U = build_unit_table(dec, idx, jf, w, D)
    um = unit_metrics(U)

    out = run_dir / "eval"; out.mkdir(exist_ok=True)
    T.to_csv(out / "cycle_table.csv", index=False)
    U.to_csv(out / "unit_table.csv", index=False)
    by_type_c = cycle_metrics_by(T, ["type"]); by_type_u = unit_metrics_by(U, ["type"])
    by_sensor_u = unit_metrics_by(U, ["sensor"]); by_timing_u = unit_metrics_by(U, ["timing_p"])

    L = [f"# 평가 — {run_dir.name}", "",
         f"라벨 {theta_name} · 채점 범위 t ≥ {jf} · eval_mask 제외 · ERROR 제외 · w = D = {w}", "",
         "## cycle 단위 (τ_s 이전 음성 (unit, cycle) 중복 제거)", "",
         _md(pd.DataFrame([{k: cm[k] for k in ("n_cycles", "n_error", "fail_rate", "TP", "FN", "FP", "TN", "recall", "precision", "FAR", "F1", "pos_rate")}])), "",
         f"참고: 중복 제거 없이 계산하면 precision {cm_nodedup['precision']:.3f}, FAR {cm_nodedup['FAR']:.3f}, 양성 비율 {cm_nodedup['pos_rate']:.3f}", "",
         f"FAR 부류 (추후 분석용): clean {cm['FAR_clean']:.3f} (n={cm['FAR_clean_n']}), 오염 후 미저하 {cm['FAR_post']:.3f} (n={cm['FAR_post_n']})", "",
         "### 유형별 (cycle)", "", _md(by_type_c), "",
         "## unit(시나리오) 단위", "",
         _md(pd.DataFrame([um])), "",
         "### 유형별", "", _md(by_type_u), "", "### 센서별", "", _md(by_sensor_u), "", "### 시점별", "", _md(by_timing_u), "",
         "### 저하 시나리오 상세", "",
         _md(U[U["degraded"]][["unit", "scenario_id", "tau_s", "tau_d", "t_hat", "result", "delay", "pre_alarm", "iso_hit"]] if "iso_hit" in U else U[U["degraded"]], "{:.0f}"), "",
         "### 비저하 시나리오 상세", "",
         _md(U[~U["degraded"]][["unit", "scenario_id", "tau_s", "t_hat", "result", "pre_alarm"]], "{:.0f}"), ""]
    (out / "report.md").write_text("\n".join(L), encoding="utf-8")
    return {"cycle": cm, "unit": um, "report": str(out / "report.md")}
