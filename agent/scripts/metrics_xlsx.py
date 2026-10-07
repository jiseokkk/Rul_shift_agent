"""run 하나의 채점 결과를 full_metrics.xlsx 형식(cycle 단위 · unit 단위 · 항상 1/항상 0 기준선)으로 뽑는다.

  python agent/scripts/metrics_xlsx.py --run-id deepseek-v4-pro-0813_or500_seed42_20261001-003315 --out or500_metrics_deepseek-v4-pro

시트: 구성 · cycle 단위 · unit 단위 · cycle 유형별/센서별/시점별 · unit 유형별/센서별/시점별 · 시나리오 상세
카운트는 값, 비율은 수식. 항상 1 = 모든 cycle 을 1 로 판정 (t_hat = τ_s), 항상 0 = 모든 cycle 을 0.
eval/ 이 없으면 먼저 채점한다 (src/eval/report.py).
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

from _bootstrap import AGENT, load_cfg
from src.eval.legacy_v1 import evaluate_run_v1

F, FB = Font(name="Arial", size=10), Font(name="Arial", size=10, bold=True)
FN = Font(name="Arial", size=9, italic=True, color="666666")
HEAD = PatternFill("solid", fgColor="D9E1F2")


def put(ws, r, c, v, font=F, fill=None, nf=None):
    if isinstance(v, (np.integer,)):
        v = int(v)
    elif isinstance(v, (np.floating,)):
        v = None if np.isnan(v) else float(v)
    elif isinstance(v, (np.bool_,)):
        v = bool(v)
    elif isinstance(v, float) and np.isnan(v):
        v = None
    cell = ws.cell(row=r, column=c, value=v)
    cell.font = font
    if fill:
        cell.fill = fill
    if nf:
        cell.number_format = nf
    return cell


def header(ws, r, cols, c0=1):
    for j, h in enumerate(cols):
        put(ws, r, c0 + j, h, FB, HEAD)


def widths(ws, ws_widths):
    for i, wd in enumerate(ws_widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = wd


def confusion(E: pd.DataFrame) -> tuple[int, int, int, int]:
    return (int(((E.label == 1) & (E.pred == 1)).sum()), int(((E.label == 1) & (E.pred == 0)).sum()),
            int(((E.label == 0) & (E.pred == 1)).sum()), int(((E.label == 0) & (E.pred == 0)).sum()))


def cycle_block(ws, r0, title, groups: list[tuple[str, pd.DataFrame]], key_name: str) -> int:
    """유형별 등: 카운트 값 + Recall/FAR/Precision/F1 수식. 다음 빈 행 번호를 돌려준다."""
    put(ws, r0, 1, title, FB)
    header(ws, r0 + 1, [key_name, "cycle", "TP", "FN", "FP", "TN", "Recall", "FAR", "Precision", "F1"])
    r = r0 + 2
    for k, g in groups:
        tp, fn, fp, tn = confusion(g)
        put(ws, r, 1, k)
        for j, v in enumerate((len(g), tp, fn, fp, tn), 2):
            put(ws, r, j, v, nf="#,##0")
        put(ws, r, 7, f'=IFERROR(C{r}/(C{r}+D{r}),"")', nf="0.000")
        put(ws, r, 8, f'=IFERROR(E{r}/(E{r}+F{r}),"")', nf="0.000")
        put(ws, r, 9, f'=IFERROR(C{r}/(C{r}+E{r}),"")', nf="0.000")
        put(ws, r, 10, f'=IFERROR(2*C{r}/(2*C{r}+D{r}+E{r}),"")', nf="0.000")
        r += 1
    return r + 1


def unit_block(ws, r0, title, groups: list[tuple[str, pd.DataFrame]], key_name: str, D: int) -> int:
    put(ws, r0, 1, title, FB)
    header(ws, r0 + 1, [key_name, "저하 n", "TP", "Early", "Late", "Miss", "DR", "항상1 DR", "Early 비율", "MDD", "Isolation", "비저하 n", "FA", "시나리오 FAR"])
    r = r0 + 2
    for k, g in groups:
        deg, non = g[g.degraded.astype(bool)], g[~g.degraded.astype(bool)]
        tp = deg[deg.result == "TP"]
        put(ws, r, 1, k)
        for j, v in enumerate((len(deg), len(tp), (deg.result == "Early").sum(), (deg.result == "Late").sum(), (deg.result == "Miss").sum()), 2):
            put(ws, r, j, int(v), nf="0")
        put(ws, r, 7, f'=IFERROR(C{r}/B{r},"")', nf="0.000")
        put(ws, r, 8, float(((deg.tau_d - deg.tau_s) <= D).mean()) if len(deg) else None, nf="0.000")
        put(ws, r, 9, f'=IFERROR(D{r}/B{r},"")', nf="0.000")
        put(ws, r, 10, float(tp.delay.mean()) if len(tp) else None, nf="0.00")
        put(ws, r, 11, float(tp.iso_hit.astype(float).mean()) if len(tp) and "iso_hit" in tp else None, nf="0.000")
        put(ws, r, 12, len(non), nf="0")
        put(ws, r, 13, int(non.any_alarm_post.astype(bool).sum()), nf="0")
        put(ws, r, 14, f'=IFERROR(M{r}/L{r},"")', nf="0.000")
        r += 1
    return r + 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--out", default=None, help="reports/{out}.xlsx (기본: {run-id}_metrics)")
    a = ap.parse_args()
    acfg = load_cfg("agent")
    w, D, jf = int(acfg.get("w", 5)), int(acfg.get("D", 5)), int(acfg["judge_from"])
    rd = AGENT / "runs" / a.run_id
    if not (rd / "eval_v1" / "cycle_table.csv").exists():
        evaluate_run_v1(rd, acfg, acfg.get("theta_name", "theta_primary"))
    dec = pd.read_csv(rd / "decisions.csv", low_memory=False)
    T = pd.read_csv(rd / "eval_v1" / "cycle_table.csv")
    U = pd.read_csv(rd / "eval_v1" / "unit_table.csv")
    E = T[~T["error"].astype(bool)]
    tp, fn, fp, tn = confusion(E)
    clean = E[(E.label == 0) & E.pre_tau_s]
    post0 = E[(E.label == 0) & ~E.pre_tau_s]
    deg, non = U[U.degraded.astype(bool)], U[~U.degraded.astype(bool)]
    lag = deg.tau_d - deg.tau_s
    wb = Workbook()

    # ---------------- 구성
    ws = wb.active; ws.title = "구성"
    put(ws, 1, 1, "구성", FB); header(ws, 2, ["항목", "수"])
    rows = [("run_id", a.run_id), ("시나리오 전체", len(U)), ("저하 라벨 있음", len(deg)), ("저하 라벨 없음", len(non)),
            ("판정 cycle", len(dec)), ("채점 cycle (마스크·중복 제외)", len(T)), ("LLM 고유 호출", int((~dec.cache_hit.astype(bool)).sum()))]
    for i, (k, v) in enumerate(rows, 3):
        put(ws, i, 1, k); put(ws, i, 2, v, nf=None if isinstance(v, str) else "#,##0")
    r = len(rows) + 4
    for by, title in [("type", "유형별"), ("sensor", "센서별"), ("timing_p", "시점별")]:
        put(ws, r, 1, title, FB); header(ws, r + 1, [by, "전체", "저하", "비저하", "저하율"]); r += 2
        for k, g in U.groupby(by):
            nd = int(g.degraded.astype(bool).sum())
            put(ws, r, 1, k); put(ws, r, 2, len(g), nf="0"); put(ws, r, 3, nd, nf="0"); put(ws, r, 4, len(g) - nd, nf="0")
            put(ws, r, 5, f"=IFERROR(C{r}/B{r},\"\")", nf="0.000"); r += 1
        r += 1
    put(ws, r, 1, "유형×강도", FB); header(ws, r + 1, ["type", "param_s", "전체", "저하", "비저하", "저하율"]); r += 2
    for (t, p), g in U.groupby(["type", U.param.fillna("na")]):
        nd = int(g.degraded.astype(bool).sum())
        put(ws, r, 1, t); put(ws, r, 2, p); put(ws, r, 3, len(g), nf="0"); put(ws, r, 4, nd, nf="0"); put(ws, r, 5, len(g) - nd, nf="0")
        put(ws, r, 6, f"=IFERROR(D{r}/C{r},\"\")", nf="0.000"); r += 1
    widths(ws, [30, 14, 10, 10, 10, 10])

    # ---------------- cycle 단위
    ws = wb.create_sheet("cycle 단위")
    header(ws, 1, ["", "판정 1", "판정 0", "합계"])
    put(ws, 2, 1, "라벨 1 (저하 중)", FB); put(ws, 2, 2, tp, nf="#,##0"); put(ws, 2, 3, fn, nf="#,##0"); put(ws, 2, 4, "=B2+C2", nf="#,##0")
    put(ws, 3, 1, "라벨 0 (저하 아님)", FB); put(ws, 3, 2, fp, nf="#,##0"); put(ws, 3, 3, tn, nf="#,##0"); put(ws, 3, 4, "=B3+C3", nf="#,##0")
    put(ws, 4, 1, "합계", FB); put(ws, 4, 2, "=B2+B3", nf="#,##0"); put(ws, 4, 3, "=C2+C3", nf="#,##0"); put(ws, 4, 4, "=D2+D3", nf="#,##0")
    header(ws, 6, ["지표", "식", "값", "항상 1", "항상 0"])
    metrics = [
        ("Recall (FDR)", "TP / (TP+FN)", "=IFERROR(B2/D2,\"\")", 1, 0),
        ("FAR", "FP / (FP+TN)", "=IFERROR(B3/D3,\"\")", 1, 0),
        ("Precision", "TP / (TP+FP)", "=IFERROR(B2/B4,\"\")", "=D2/D4", None),
        ("F1", "2PR/(P+R)", "=IFERROR(2*C7*C9/(C7+C9),\"\")", "=2*D9/(1+D9)", None),
        ("판정 1 비율", "(TP+FP) / 전체", "=B4/D4", 1, 0),
        ("양성 비율", "(TP+FN) / 전체", "=D2/D4", "=D2/D4", "=D2/D4"),
        ("FAR · clean 구간", "τ_s 이전 FP 비율", "=IFERROR(C20/B20,\"\")", 1, 0),
        ("FAR · 오염 후 미저하", "τ_s 이후 라벨0 FP 비율", "=IFERROR(C21/B21,\"\")", 1, 0),
        ("채점 cycle 수", "", len(T), None, None),
        ("ERROR (FailRate)", "", int(T["error"].sum()), None, None),
    ]
    for i, (k, f, v, a1, a0) in enumerate(metrics, 7):
        put(ws, i, 1, k, FB); put(ws, i, 2, f)
        put(ws, i, 3, v, nf="#,##0" if isinstance(v, int) else "0.000")
        put(ws, i, 4, a1, nf="0.000"); put(ws, i, 5, a0, nf="0.000")
    header(ws, 19, ["부류", "cycle 수", "판정 1", "FAR"])
    put(ws, 20, 1, "clean (τ_s 이전)", FB); put(ws, 20, 2, len(clean), nf="#,##0"); put(ws, 20, 3, int((clean.pred == 1).sum()), nf="#,##0"); put(ws, 20, 4, "=IFERROR(C20/B20,\"\")", nf="0.000")
    put(ws, 21, 1, "오염 후 미저하 (라벨 0)", FB); put(ws, 21, 2, len(post0), nf="#,##0"); put(ws, 21, 3, int((post0.pred == 1).sum()), nf="#,##0"); put(ws, 21, 4, "=IFERROR(C21/B21,\"\")", nf="0.000")
    put(ws, 23, 1, f"채점 범위 t ≥ {jf} · eval_mask 제외 · ERROR 제외 · τ_s 이전 음성은 (unit, cycle) 중복 제거. '항상 1'·'항상 0' 은 모든 cycle 을 1 또는 0 으로 판정한 기준선.", FN)
    widths(ws, [24, 24, 14, 12, 12])

    # ---------------- unit 단위
    ws = wb.create_sheet("unit 단위")
    header(ws, 1, ["분류", "조건", "시나리오 수", "비율"])
    cls = [("일치 (TP)", f"τ_d−{w} ≤ t_hat ≤ τ_d+{D}", "TP"), ("Early", f"τ_s ≤ t_hat < τ_d−{w}", "Early"),
           ("Late", f"t_hat > τ_d+{D}", "Late"), ("Miss", "알람 없음", "Miss")]
    for i, (k, cond, res) in enumerate(cls, 2):
        put(ws, i, 1, k, FB); put(ws, i, 2, cond); put(ws, i, 3, int((deg.result == res).sum()), nf="0"); put(ws, i, 4, f"=IFERROR(C{i}/$C$6,\"\")", nf="0.000")
    put(ws, 6, 1, "합계", FB); put(ws, 6, 3, "=SUM(C2:C5)", nf="0"); put(ws, 6, 4, "=SUM(D2:D5)", nf="0.000")
    header(ws, 8, ["지표", "식", "값", "항상 1", "항상 0", "비고"])
    a1_dr = float((lag <= D).mean()) if len(deg) else None
    a1_tp = deg[lag <= D]
    tpU = deg[deg.result == "TP"]
    um = [
        ("Detection Rate", "일치 / 저하 시나리오", "=D2", "=C21", 0, f"'항상 1' 은 t_hat = τ_s 라 라벨 지연 ≤ {D} 인 시나리오가 TP"),
        ("Early rate", "Early / 저하 시나리오", "=D3", "=1-C21", 0, None),
        ("Late rate", "Late / 저하 시나리오", "=D4", 0, 0, None),
        ("Miss rate", "Miss / 저하 시나리오", "=D5", 0, 1, None),
        ("MDD (Mean Detection Delay)", "mean(t_hat − τ_d), TP만", float(tpU.delay.mean()) if len(tpU) else None,
         float((a1_tp.tau_s - a1_tp.tau_d).mean()) if len(a1_tp) else None, None, f"중앙값 {tpU.delay.median():.1f}" if len(tpU) else None),
        ("delay 중앙값 (알람 전체)", "median(t_hat − τ_d), Early·Late 포함", float(deg.delay.dropna().median()) if deg.delay.notna().any() else None,
         float((deg.tau_s - deg.tau_d).median()) if len(deg) else None, None, None),
        ("Isolation (TP)", "TP 중 의심 센서 ∋ 주입 센서", float(tpU.iso_hit.astype(float).mean()) if len(tpU) and "iso_hit" in tpU else None, None, None, None),
        ("시나리오 FAR", "τ_s 이후 알람 1회 이상 / 비저하 시나리오", "=IFERROR(C23/C22,\"\")", 1, 0, None),
        ("pre_alarm rate", "τ_s 이전 알람 있음 / 전체 시나리오", "=IFERROR(C24/(C22+C6),\"\")", 1, 0, None),
        ("저하 / 비저하 시나리오 수", "", f"{len(deg)} / {len(non)}", None, None, None),
    ]
    for i, (k, f, v, b1, b0, note) in enumerate(um, 9):
        put(ws, i, 1, k, FB); put(ws, i, 2, f)
        put(ws, i, 3, v, nf=None if isinstance(v, str) else "0.000"); put(ws, i, 4, b1, nf="0.000"); put(ws, i, 5, b0, nf="0.000")
        if note:
            put(ws, i, 6, note, FN)
    header(ws, 20, ["보조 카운트", "", "값"])
    aux = [(f"항상-1 DR = 저하 중 τ_d−τ_s ≤ {D} 비율", a1_dr), ("비저하 시나리오 수", len(non)),
           ("비저하 중 τ_s 이후 알람 있음", int(non.any_alarm_post.astype(bool).sum())), ("τ_s 이전 알람 있음 (전체)", int(U.pre_alarm.astype(bool).sum()))]
    for i, (k, v) in enumerate(aux, 21):
        put(ws, i, 1, k); put(ws, i, 3, v, nf="0.000" if isinstance(v, float) else "0")
    put(ws, 26, 1, f"t_hat = τ_s 이후 첫 판정 1. w = D = {w}. Isolation 은 TP 시나리오에서 t_hat 시점 suspected_sensors 에 주입 센서가 포함된 비율.", FN)
    widths(ws, [30, 36, 14, 12, 12, 60])

    # ---------------- cycle 유형별 / 센서별 / 시점별
    for by, name in [("type", "cycle 유형별"), ("sensor", "cycle 센서별"), ("timing_p", "cycle 시점별")]:
        ws = wb.create_sheet(name)
        r = cycle_block(ws, 1, name, [(k, g) for k, g in E.groupby(by)], by)
        if by == "type":
            cycle_block(ws, r, "유형×강도", [(f"{t} {p}", g) for (t, p), g in E.groupby(["type", E.param.fillna("na")])], "type param")
        widths(ws, [16] + [10] * 9)

    # ---------------- unit 유형별 / 센서별 / 시점별
    for by, name in [("type", "unit 유형별"), ("sensor", "unit 센서별"), ("timing_p", "unit 시점별")]:
        ws = wb.create_sheet(name)
        r = unit_block(ws, 1, name, [(k, g) for k, g in U.groupby(by)], by, D)
        if by == "type":
            unit_block(ws, r, "유형×강도", [(f"{t} {p}", g) for (t, p), g in U.groupby(["type", U.param.fillna("na")])], "type param", D)
        widths(ws, [16] + [9] * 13)

    # ---------------- 시나리오 상세
    ws = wb.create_sheet("시나리오 상세")
    header(ws, 1, list(U.columns))
    for i, row in enumerate(U.itertuples(index=False), 2):
        for j, v in enumerate(row, 1):
            put(ws, i, j, v)
    ws.freeze_panes = "C2"; ws.auto_filter.ref = ws.dimensions
    widths(ws, [6, 34, 9, 13, 7, 5, 8, 6, 7, 7, 9, 7, 9, 12, 7, 7, 7, 12, 7, 10])

    out = AGENT / "reports" / f"{a.out or a.run_id + '_metrics'}.xlsx"
    wb.save(out)
    print(f"→ {out}")


if __name__ == "__main__":
    main()
