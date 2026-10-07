"""run 하나를 시나리오 단위 v2 로 채점해 runs/{run_id}/eval/ 에 표·리포트 저장. 설계: docs/eval_v2_scenario.md

민감도 분석(Δ·w·H·k 스윕, θ 대안)은 설계 단계라 평가에서 제외했다 (2026-10-07). 필요하면 first_alarms.csv 에 classify 를 다시 걸면 된다.

산출: scenario_table.csv (Δ·w·H 기본값 분류), first_alarms.csv (분류 전 첫 경보), report.md, metrics.json
v1 (cycle 단위) 채점은 legacy_v1.evaluate_run_v1 → eval_v1/.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.data.truth import load_index
from src.eval.baselines import agent_alarm_rate, baseline_table
from src.eval.scenario_table import MAIN_COLS, classify, first_alarms, metrics_by, pre_contam_by_timing, scenario_metrics
from src.eval.stats import unit_bootstrap

CI_METRICS = ["detection_rate", "pre_contam_rate", "pre_degr_rate", "miss_rate", "scenario_FAR", "isolation_rate"]


def _md(df: pd.DataFrame, fmt: str = "{:.3f}") -> str:
    if df is None or not len(df):
        return "(없음)"
    cols = list(df.columns)
    L = ["| " + " | ".join(str(c) for c in cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            if isinstance(v, (float, np.floating)) and not pd.isna(v):
                cells.append(fmt.format(v) if not float(v).is_integer() or abs(v) >= 1e6 else f"{int(v)}")
            else:
                cells.append("" if pd.isna(v) else str(v))
        L.append("| " + " | ".join(cells) + " |")
    return "\n".join(L)


def eval_cfg(acfg: dict) -> dict:
    return dict(acfg["eval"])


def evaluate_run(run_dir: Path, acfg: dict, theta_name: str | None = None, n_boot: int | None = None) -> dict:
    run_dir = Path(run_dir)
    e = eval_cfg(acfg)
    theta = theta_name or acfg.get("theta_name", "theta_primary")
    jf, Delta, w, H, k = int(acfg["judge_from"]), int(e["Delta"]), int(e["w"]), int(e["H"]), int(e["k"])
    n_boot = int(e.get("n_boot", 2000) if n_boot is None else n_boot)

    dec = pd.read_csv(run_dir / "decisions.csv", low_memory=False)
    idx = load_index(theta_name=theta)
    FA = first_alarms(dec, idx, jf, k)
    S = classify(FA, Delta, w, H)
    m = scenario_metrics(S)
    p_match = agent_alarm_rate(dec, jf)

    out = run_dir / "eval"; out.mkdir(exist_ok=True)
    FA.to_csv(out / "first_alarms.csv", index=False)
    S.to_csv(out / "scenario_table.csv", index=False)

    main = pd.DataFrame([{"method": "LLM Agent", **{c: m[c] for c in MAIN_COLS}}])
    base = baseline_table(FA, jf, Delta, w, H, p_match, n_rep=int(e.get("random_reps", 100)), cols=MAIN_COLS)
    main = pd.concat([base, main], ignore_index=True)
    ci = unit_bootstrap(S, CI_METRICS, n_boot=n_boot) if n_boot > 0 else None

    timing = pre_contam_by_timing(S)

    L = [f"# 평가 v2 (시나리오 단위) — {run_dir.name}", "",
         f"라벨 {theta} · 첫 판정 t₀ = {jf} · Δ = {Delta}, w = {w}, H = {H}, k = {k} · 첫 경보 원칙 (t₀ 이후 첫 경보, 오염 전 포함) · "
         f"ERROR 는 경보 아님 (오류율 {m['error_rate']:.4f}) · 규약 docs/eval_v2_scenario.md", "",
         f"시나리오 {len(S)} = 저하 {m['n_degraded']} + 비저하 {m['n_nondegraded']} · unit {S['unit'].nunique()} · "
         f"판정 로그가 창 끝에 못 미친 시나리오 {m['n_uncovered']}", "",
         "## 1. 메인 표 (기준선 고정)", "", _md(main), "",
         "## 2. unit bootstrap 95% CI" + (f" ({n_boot}회)" if ci is not None else " (생략)"), "", _md(ci) if ci is not None else "", "",
         "## 3. 유형별", "", _md(metrics_by(S, ["type"])), "",
         "## 4. 센서별", "", _md(metrics_by(S, ["sensor"])), "",
         "## 5. 오염 시점별", "", _md(metrics_by(S, ["timing_p"])), "",
         "### 오염 전 경보율 (저하·비저하 합산, 오염 전 구간 길이 = τ_s − 55)", "", _md(timing), "",
         "## 6. 저하 시나리오 상세", "",
         _md(S[S["degraded"]][["unit", "scenario_id", "type", "sensor", "tau_s", "tau_d", "window_lo", "window_hi", "t_hat", "result", "delay", "iso_hit"]], "{:.0f}"), "",
         "## 7. 비저하 시나리오 상세", "",
         _md(S[~S["degraded"]][["unit", "scenario_id", "type", "sensor", "tau_s", "window_hi", "t_hat", "result"]], "{:.0f}"), ""]
    (out / "report.md").write_text("\n".join(L), encoding="utf-8")
    res = {"config": {"theta": theta, "judge_from": jf, "Delta": Delta, "w": w, "H": H, "k": k, "p_match": p_match},
           "metrics": m, "baselines": base.to_dict("records"), "ci": ci.to_dict("records") if ci is not None else None,
           "report": str(out / "report.md")}
    (out / "metrics.json").write_text(json.dumps(res, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
    return res
