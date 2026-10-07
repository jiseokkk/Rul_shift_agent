"""여러 run 을 같은 잣대로 나란히 비교: 채점 지표 + 실패 분석(docs/v1_failure_analysis.md)의 행동 지표.

  python agent/scripts/compare_runs.py --runs Qwen2.5-32B-AWQ_full_v1_seed42_20260917-020322__or500 deepseek-v4-pro-0813_or500_seed42_... \
      --labels qwen2.5-32b deepseek-v4-pro --out compare_or500

eval/ 이 없는 run 은 먼저 채점한다. 결과: reports/{out}.md (표) 와 표준 출력.
행동 지표: 구간별 경보율, 판정 뒤집힘, lag-1 자기상관, confidence 분포, 지목 센서, rationale 의 정상 범위 slope 오독, 토큰.
기준선: 항상-1 (t_hat = τ_s) 의 DR 을 같은 unit_table 에서 계산.
"""
from __future__ import annotations

import argparse
import json
import re

import numpy as np
import pandas as pd

from _bootstrap import AGENT, load_cfg
from src.eval.legacy_v1 import evaluate_run_v1
from src.llm.schema import SENSOR_NAMES

UNUSUAL = re.compile(r"unusual|abnormal|anomal|significant|not explained|inconsistent|deviat|suspicious|far from", re.I)
SLOPE_NUM = re.compile(r"slope[^.;]{0,40}?(-?\d+\.\d+)", re.I)


def load_run(run_id: str, acfg: dict) -> dict:
    rd = AGENT / "runs" / run_id
    if not (rd / "eval_v1" / "cycle_table.csv").exists():
        evaluate_run_v1(rd, acfg, acfg.get("theta_name", "theta_primary"))
    dec = pd.read_csv(rd / "decisions.csv", low_memory=False)
    T = pd.read_csv(rd / "eval_v1" / "cycle_table.csv")
    U = pd.read_csv(rd / "eval_v1" / "unit_table.csv")
    return {"dir": rd, "dec": dec, "T": T, "U": U}


def alarm_rates(T: pd.DataFrame) -> dict:
    ok = T[~T["error"].astype(bool)]
    clean = ok[ok.pre_tau_s].drop_duplicates(["unit", "cycle"])
    harmless = ok[(~ok.pre_tau_s) & (ok.label == 0)]
    degraded = ok[ok.label == 1]
    return {"경보율 clean(τ_s 이전)": clean.pred.mean(), "경보율 오염·미저하": harmless.pred.mean(), "경보율 저하": degraded.pred.mean(),
            "n clean": len(clean), "n 오염·미저하": len(harmless), "n 저하": len(degraded)}


def cycle_scores(T: pd.DataFrame) -> dict:
    ok = T[~T["error"].astype(bool)]
    pos = ok[ok.label == 1]
    neg = pd.concat([ok[ok.pre_tau_s].drop_duplicates(["unit", "cycle"]), ok[(~ok.pre_tau_s) & (ok.label == 0)]])
    tp, fn = (pos.pred == 1).sum(), (pos.pred == 0).sum()
    fp, tn = (neg.pred == 1).sum(), (neg.pred == 0).sum()
    rec = tp / max(tp + fn, 1); prec = tp / max(tp + fp, 1)
    return {"recall": rec, "precision": prec, "FAR": fp / max(fp + tn, 1), "F1": 2 * prec * rec / max(prec + rec, 1e-9)}


def unit_scores(U: pd.DataFrame, w: int, D: int) -> dict:
    deg, non = U[U.degraded.astype(bool)], U[~U.degraded.astype(bool)]
    out = {"detection_rate": (deg.result == "TP").mean(), "early_rate": (deg.result == "Early").mean(),
           "late_rate": (deg.result == "Late").mean(), "miss_rate": (deg.result == "Miss").mean(),
           "scenario_FAR": non.any_alarm_post.astype(bool).mean(), "pre_alarm_rate": U.pre_alarm.astype(bool).mean(),
           "isolation_rate": deg[deg.result == "TP"].iso_hit.astype(float).mean()}
    lag = deg.tau_d - deg.tau_s
    out["항상-1 DR (τ_d−τ_s ≤ D)"] = (lag <= D).mean()
    out["DR − 항상-1 DR"] = out["detection_rate"] - out["항상-1 DR (τ_d−τ_s ≤ D)"]
    # 판별 가능 층: 라벨 지연이 w 보다 큰 저하 시나리오만
    hard = deg[lag > w]
    out[f"DR, τ_d−τ_s > {w} 층"] = (hard.result == "TP").mean() if len(hard) else np.nan
    out["n 저하 / 비저하"] = f"{len(deg)} / {len(non)}"
    return out


def stability(dec: pd.DataFrame) -> dict:
    d = dec[dec.error.isna()].sort_values(["unit", "scenario_id", "cycle"])
    flips, runs1, runs0, ac = [], [], [], []
    for _, g in d.groupby(["unit", "scenario_id"]):
        p = g.degraded.astype(float).to_numpy()
        if len(p) < 3:
            continue
        flips.append(np.mean(p[1:] != p[:-1]))
        if p.std() > 0:
            ac.append(np.corrcoef(p[1:], p[:-1])[0, 1])
        # 연속 길이
        cur, val = 1, p[0]
        for x in p[1:]:
            if x == val:
                cur += 1
            else:
                (runs1 if val == 1 else runs0).append(cur); cur, val = 1, x
        (runs1 if val == 1 else runs0).append(cur)
    return {"판정 뒤집힘 비율": np.mean(flips), "lag-1 자기상관 (중앙값)": float(np.nanmedian(ac)) if ac else np.nan,
            "정상 연속 길이 중앙값": np.median(runs0) if runs0 else np.nan, "저하 연속 길이 중앙값": np.median(runs1) if runs1 else np.nan}


def confidence_stats(dec: pd.DataFrame, T: pd.DataFrame) -> dict:
    d = dec[dec.error.isna()]
    c = d.confidence.round(2)
    vc = c.value_counts(normalize=True)
    out = {"confidence 고유값 수": int(c.nunique()), "상위 3개 값 비율": float(vc.head(3).sum()),
           "상위 3개 값": ", ".join(f"{v:.2f}" for v in vc.head(3).index),
           "구간 경계값 {0.85,0.60,0.35} 비율": float(c.isin([0.85, 0.60, 0.35]).mean()),
           "저하 판정 시 confidence 표준편차": float(d[d.degraded == 1].confidence.std())}
    ok = T[~T["error"].astype(bool)].dropna(subset=["confidence"])
    try:
        from sklearn.metrics import roc_auc_score
        out["confidence AUROC vs 라벨"] = float(roc_auc_score(ok.label, ok.confidence)) if ok.label.nunique() == 2 else np.nan
    except Exception:
        out["confidence AUROC vs 라벨"] = np.nan
    return out


def sensor_stats(dec: pd.DataFrame, T: pd.DataFrame) -> dict:
    d = dec[dec.error.isna() & (dec.degraded == 1)].copy()
    d["sens"] = d.suspected_sensors.apply(lambda s: json.loads(s) if isinstance(s, str) else [])
    allc = pd.Series([s for L in d.sens for s in L]).value_counts()
    out = {"지목 빈도 1·2위": ", ".join(f"{k} {v / max(len(d), 1):.2f}" for k, v in allc.head(2).items()),
           "14개 전부 지목 비율": float(d.sens.apply(lambda L: len(set(L)) >= 14).mean()),
           "지목 센서 수 중앙값": float(d.sens.apply(len).median())}
    lab = T[["unit", "scenario_id", "cycle", "label", "pre_tau_s", "sensor"]]
    m = d.merge(lab, on=["unit", "scenario_id", "cycle"])
    deg = m[m.label == 1]
    inj = deg.apply(lambda r: any(s in str(r.sensor).split("+") for s in r.sens), axis=1) if len(deg) else pd.Series(dtype=float)
    out["저하 경보 중 주입 센서 포함률"] = float(inj.mean()) if len(deg) else np.nan
    out["미주입 NRc·Nc 지목 비율 (경보 중)"] = float(d.sens.apply(lambda L: bool({"NRc", "Nc"} & set(L))).mean())
    return out


def rationale_stats(dec: pd.DataFrame) -> dict:
    d = dec[dec.error.isna() & (dec.degraded == 1)]
    r = d.rationale.fillna("").astype(str)
    cites_slope = r.str.contains("slope", case=False)
    cites_jump = r.str.contains("jump", case=False)
    normal_called_unusual, n_slope = 0, 0
    for txt in r:
        m = SLOPE_NUM.search(txt)
        if not m:
            continue
        v = float(m.group(1))
        n_slope += 1
        if -1.5 <= v <= -0.5 and UNUSUAL.search(txt):
            normal_called_unusual += 1
    return {"경보 rationale 중 slope 인용": float(cites_slope.mean()), "경보 rationale 중 jump 인용": float(cites_jump.mean()),
            "정상 범위 slope(−1.5~−0.5)를 이상으로 서술": normal_called_unusual / max(n_slope, 1), "  (slope 수치 인용 n)": n_slope,
            "rationale 단어 수 중앙값": float(r.str.split().apply(len).median())}


def token_stats(dec: pd.DataFrame, price: tuple[float, float] | None) -> dict:
    fresh = dec[~dec.cache_hit.astype(bool)]
    out = {"판정 수": len(dec), "LLM 호출": len(fresh), "오류": int(dec.error.notna().sum()),
           "prompt 토큰 평균": float(fresh.prompt_tokens.mean()), "completion 토큰 평균": float(fresh.completion_tokens.mean()),
           "재시도 발생 비율": float((fresh.n_retries > 0).mean()), "flags 발생 비율": float((dec["flags"].fillna("[]") != "[]").mean())}
    if price:
        out["추정 비용 USD"] = float((fresh.prompt_tokens.fillna(0) * price[0] + fresh.completion_tokens.fillna(0) * price[1]).sum() / 1e6)
    return out


def chance_baseline(dec: pd.DataFrame, U: pd.DataFrame, w: int, D: int, reps: int = 20, seed: int = 0) -> dict:
    """circular-shift 우연 기준선: 저하 시나리오의 τ_s 이후 판정열을 무작위 회전해 같은 규칙으로 TP 를 센다."""
    deg = U[U.degraded.astype(bool)]
    rng = np.random.default_rng(seed)
    real, chance, hreal, hchance = [], [], [], []
    for r in deg.itertuples(index=False):
        g = dec[(dec.unit == r.unit) & (dec.scenario_id == r.scenario_id) & (dec.cycle >= r.tau_s)].sort_values("cycle")
        p = g.degraded.fillna(0).astype(int).to_numpy(); cyc = g.cycle.to_numpy()
        if len(p) == 0:
            continue

        def tp_of(pp):
            idx = np.flatnonzero(pp)
            return float(r.tau_d - w <= cyc[idx[0]] <= r.tau_d + D) if len(idx) else 0.0

        a, c = tp_of(p), float(np.mean([tp_of(np.roll(p, int(rng.integers(len(p))))) for _ in range(reps)]))
        real.append(a); chance.append(c)
        if r.tau_d - r.tau_s > w:
            hreal.append(a); hchance.append(c)
    return {"DR": float(np.mean(real)), "우연 DR": float(np.mean(chance)), "n 저하": len(real),
            f"DR, τ_d−τ_s>{w} 층": float(np.mean(hreal)) if hreal else np.nan, f"우연 DR, τ_d−τ_s>{w} 층": float(np.mean(hchance)) if hchance else np.nan,
            f"n τ_d−τ_s>{w} 층": len(hreal)}


def unit_counts_by(U: pd.DataFrame, by: str) -> pd.DataFrame:
    rows = []
    for k, g in U.groupby(by):
        deg, non = g[g.degraded.astype(bool)], g[~g.degraded.astype(bool)]
        rows.append({by: k, "n_degraded": len(deg), "TP": int((deg.result == "TP").sum()), "Early": int((deg.result == "Early").sum()),
                     "Late": int((deg.result == "Late").sum()), "Miss": int((deg.result == "Miss").sum()),
                     "n_nondegraded": len(non), "FA": int(non.any_alarm_post.astype(bool).sum()), "pre_alarm": int(g.pre_alarm.astype(bool).sum())})
    return pd.DataFrame(rows)


def write_xlsx(path, labels: list[str], runs: list[dict], sections: dict, chances: list[dict], prices: list, run_ids: list[str],
               sample: pd.DataFrame | None, w: int, D: int) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    F, FB = Font(name="Arial", size=10), Font(name="Arial", size=10, bold=True)
    FBLUE, FGRAY = Font(name="Arial", size=10, color="0000FF"), Font(name="Arial", size=9, italic=True, color="666666")
    HEAD = PatternFill("solid", fgColor="D9E1F2")
    wb = Workbook()

    def sheet(name):
        ws = wb.create_sheet(name[:31])
        ws.sheet_view.showGridLines = True
        return ws

    def put(ws, r, c, v, font=F, fill=None, nf=None, align=None):
        cell = ws.cell(row=r, column=c, value=v); cell.font = font
        if fill: cell.fill = fill
        if nf: cell.number_format = nf
        if align: cell.alignment = Alignment(horizontal=align)
        return cell

    def header(ws, r, cols, c0=1):
        for j, h in enumerate(cols):
            put(ws, r, c0 + j, h, FB, HEAD)

    def widths(ws, ws_widths):
        for i, wd in enumerate(ws_widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = wd

    n = len(labels)
    # ---- README
    ws = wb.active; ws.title = "README"
    lines = ["run 비교 — LLM 만 교체한 v1 에이전트 (도구·프롬프트·평가 동일)", "",
             *[f"{l}: runs/{r}" for l, r in zip(labels, run_ids)], "",
             f"채점 규약: docs/design_v1.md §7 · w = D = {w} · 채점 범위 t ≥ 55 · eval_mask 제외 · ERROR 제외",
             "cycle 단위 음성은 τ_s 이전 (unit, cycle) 중복 제거. 우연 기준선 = 저하 시나리오의 τ_s 이후 판정열을 무작위 회전(20회 평균).", "",
             "시트: 요약(모든 지표 나란히, 차이 = 뒤 모델 − 앞 모델) · 기준선 · cycle_유형별 · unit_유형별/센서별/시점별 · 시나리오_상세 · 표본_구성 · 실행_정보",
             "파란 글씨 = 입력값(단가). 비율·차이 열은 수식이라 카운트를 고치면 다시 계산된다.",
             "행동 지표 정의: docs/v1_failure_analysis.md (경보율 구간, 판정 뒤집힘, confidence 경계값 복사, slope 오독, 지목 센서).",
             f"작성: agent/scripts/compare_runs.py --xlsx · {pd.Timestamp.now():%Y-%m-%d %H:%M}"]
    for i, t in enumerate(lines, 1):
        put(ws, i, 1, t, FB if i == 1 else F)
    widths(ws, [120])

    # ---- 요약
    ws = sheet("요약")
    header(ws, 1, ["구분", "지표", *labels, *( [f"차이 ({labels[-1]} − {labels[0]})"] if n >= 2 else [])])
    r = 2
    for sec, rows in sections.items():
        for k, vals in rows.items():
            put(ws, r, 1, sec); put(ws, r, 2, k)
            numeric = True
            for j, l in enumerate(labels):
                v = vals.get(l, np.nan)
                if isinstance(v, (int, float, np.integer, np.floating)) and not (isinstance(v, float) and np.isnan(v)):
                    put(ws, r, 3 + j, float(v), nf="0.000" if isinstance(v, (float, np.floating)) and abs(v) < 100 else "#,##0")
                else:
                    put(ws, r, 3 + j, "" if (isinstance(v, float) and np.isnan(v)) else str(v)); numeric = numeric and False
            if n >= 2 and numeric:
                a, b = get_column_letter(3), get_column_letter(2 + n)
                put(ws, r, 3 + n, f"={b}{r}-{a}{r}", nf="+0.000;-0.000;0")
            r += 1
    ws.freeze_panes = "C2"; widths(ws, [14, 42] + [18] * n + [22])

    # ---- 기준선
    ws = sheet("기준선")
    keys = list(chances[0].keys())
    header(ws, 1, ["지표", *labels, *( [f"차이 ({labels[-1]} − {labels[0]})"] if n >= 2 else [])])
    for i, k in enumerate(keys, 2):
        put(ws, i, 1, k)
        for j, ch in enumerate(chances):
            v = ch[k]; put(ws, i, 2 + j, v, nf="0.000" if isinstance(v, float) else "0")
        if n >= 2 and isinstance(chances[0][k], float):
            put(ws, i, 2 + n, f"={get_column_letter(1 + n)}{i}-B{i}", nf="+0.000;-0.000;0")
    r = len(keys) + 3
    put(ws, r, 1, "DR − 우연 DR", FB)
    for j in range(n):
        col = get_column_letter(2 + j); put(ws, r, 2 + j, f"={col}2-{col}3", nf="+0.000;-0.000;0")
    put(ws, r + 1, 1, f"DR − 우연 DR, τ_d−τ_s>{w} 층", FB)
    for j in range(n):
        col = get_column_letter(2 + j); put(ws, r + 1, 2 + j, f"={col}5-{col}6", nf="+0.000;-0.000;0")
    put(ws, r + 3, 1, "항상-1 판정기의 DR = τ_d−τ_s ≤ D 인 저하 시나리오 비율 (요약 시트 참조). 우연 기준선은 각 판정기의 경보 밀도를 유지한 채 위치만 섞은 값.", FGRAY)
    widths(ws, [34] + [18] * n + [22])

    # ---- cycle 유형별: 카운트는 값, recall/FAR/precision 은 수식
    ws = sheet("cycle_유형별")
    cols = ["type", "n_cycles", "TP", "FN", "FP", "TN", "recall", "precision", "FAR"]
    c0 = 1; rowmap = {}
    for j, (l, R) in enumerate(zip(labels, runs)):
        put(ws, 1, c0, l, FB); header(ws, 2, cols, c0)
        T = R["T"]; E = T[~T["error"].astype(bool)]
        for i, (t, g) in enumerate(E.groupby("type"), 3):
            tp = int(((g.label == 1) & (g.pred == 1)).sum()); fn = int(((g.label == 1) & (g.pred == 0)).sum())
            fp = int(((g.label == 0) & (g.pred == 1)).sum()); tn = int(((g.label == 0) & (g.pred == 0)).sum())
            put(ws, i, c0, t); put(ws, i, c0 + 1, len(g), nf="#,##0")
            for k, v in enumerate((tp, fn, fp, tn)):
                put(ws, i, c0 + 2 + k, v, nf="#,##0")
            TPc, FNc, FPc, TNc = (get_column_letter(c0 + 2 + k) for k in range(4))
            put(ws, i, c0 + 6, f"=IF({TPc}{i}+{FNc}{i}=0,\"\",{TPc}{i}/({TPc}{i}+{FNc}{i}))", nf="0.000")
            put(ws, i, c0 + 7, f"=IF({TPc}{i}+{FPc}{i}=0,\"\",{TPc}{i}/({TPc}{i}+{FPc}{i}))", nf="0.000")
            put(ws, i, c0 + 8, f"=IF({FPc}{i}+{TNc}{i}=0,\"\",{FPc}{i}/({FPc}{i}+{TNc}{i}))", nf="0.000")
            rowmap.setdefault(t, {})[j] = (i, c0)
        c0 += len(cols) + 1
    if n >= 2:
        put(ws, 1, c0, f"차이 ({labels[-1]} − {labels[0]})", FB); header(ws, 2, ["type", "Δrecall", "ΔFAR"], c0)
        for i, (t, m) in enumerate(sorted(rowmap.items()), 3):
            (ra, ca), (rb, cb) = m[0], m[n - 1]
            put(ws, i, c0, t)
            put(ws, i, c0 + 1, f"={get_column_letter(cb + 6)}{rb}-{get_column_letter(ca + 6)}{ra}", nf="+0.000;-0.000;0")
            put(ws, i, c0 + 2, f"={get_column_letter(cb + 8)}{rb}-{get_column_letter(ca + 8)}{ra}", nf="+0.000;-0.000;0")
    ws.freeze_panes = "A3"; widths(ws, [12] + [10] * 40)

    # ---- unit 유형별 / 센서별 / 시점별: 카운트는 값, 비율은 수식
    for by, name in [("type", "unit_유형별"), ("sensor", "unit_센서별"), ("timing_p", "unit_시점별")]:
        ws = sheet(name)
        cols = [by, "n_degraded", "TP", "Early", "Late", "Miss", "n_nondegraded", "FA", "pre_alarm", "detection_rate", "early_rate", "late_rate", "miss_rate", "scenario_FAR", "pre_alarm_rate"]
        c0 = 1; rowmap = {}
        for j, (l, R) in enumerate(zip(labels, runs)):
            put(ws, 1, c0, l, FB); header(ws, 2, cols, c0)
            C = unit_counts_by(R["U"], by)
            for i, row in enumerate(C.itertuples(index=False), 3):
                put(ws, i, c0, row[0] if by != "timing_p" else float(row[0]))
                for k, v in enumerate(row[1:], 1):
                    put(ws, i, c0 + k, int(v), nf="0")
                nd, TPc, Ec, Lc, Mc, nn, FAc, PAc = (get_column_letter(c0 + k) for k in range(1, 9))
                for k, f in enumerate([f"=IF({nd}{i}=0,\"\",{TPc}{i}/{nd}{i})", f"=IF({nd}{i}=0,\"\",{Ec}{i}/{nd}{i})",
                                       f"=IF({nd}{i}=0,\"\",{Lc}{i}/{nd}{i})", f"=IF({nd}{i}=0,\"\",{Mc}{i}/{nd}{i})",
                                       f"=IF({nn}{i}=0,\"\",{FAc}{i}/{nn}{i})", f"=IF({nd}{i}+{nn}{i}=0,\"\",{PAc}{i}/({nd}{i}+{nn}{i}))"]):
                    put(ws, i, c0 + 9 + k, f, nf="0.000")
                rowmap.setdefault(row[0], {})[j] = (i, c0)
            c0 += len(cols) + 1
        if n >= 2:
            put(ws, 1, c0, f"차이 ({labels[-1]} − {labels[0]})", FB); header(ws, 2, [by, "ΔDR", "Δscenario_FAR"], c0)
            for i, (t, m) in enumerate(sorted(rowmap.items(), key=lambda kv: str(kv[0])), 3):
                if 0 not in m or n - 1 not in m:
                    continue
                (ra, ca), (rb, cb) = m[0], m[n - 1]
                put(ws, i, c0, t)
                put(ws, i, c0 + 1, f"={get_column_letter(cb + 9)}{rb}-{get_column_letter(ca + 9)}{ra}", nf="+0.000;-0.000;0")
                put(ws, i, c0 + 2, f"={get_column_letter(cb + 13)}{rb}-{get_column_letter(ca + 13)}{ra}", nf="+0.000;-0.000;0")
        ws.freeze_panes = "A3"; widths(ws, [14] + [9] * 60)

    # ---- 시나리오 상세 (unit_table 병합)
    ws = sheet("시나리오_상세")
    base = ["unit", "scenario_id", "type", "sensor", "param", "dir", "timing_p", "T_u", "tau_s", "tau_d", "degraded"]
    per = ["t_hat", "result", "delay", "pre_alarm", "any_alarm_post", "iso_hit"]
    M = runs[0]["U"][base].copy()
    for l, R in zip(labels, runs):
        M = M.merge(R["U"][["unit", "scenario_id", *per]].rename(columns={c: f"{c} [{l}]" for c in per}), on=["unit", "scenario_id"], how="left")
    M = M.sort_values(["degraded", "unit", "scenario_id"], ascending=[False, True, True])
    header(ws, 1, list(M.columns))
    for i, row in enumerate(M.itertuples(index=False), 2):
        for k, v in enumerate(row, 1):
            if isinstance(v, (float, np.floating)) and np.isnan(v):
                v = None
            elif isinstance(v, (np.integer,)):
                v = int(v)
            elif isinstance(v, (np.floating,)):
                v = float(v)
            elif isinstance(v, (np.bool_, bool)):
                v = bool(v)
            put(ws, i, k, v)
    ws.freeze_panes = "C2"; ws.auto_filter.ref = ws.dimensions; widths(ws, [6, 34, 9, 13, 7, 5, 8, 6, 7, 7, 9] + [9] * 6 * n)

    # ---- 표본 구성
    if sample is not None:
        ws = sheet("표본_구성"); r = 1
        put(ws, r, 1, f"시나리오 {len(sample)}개 · 유형별 균형 (scripts/make_balanced_sample.py)", FB); r += 2
        for col in ["timing_p", "sensor", "param", "dir"]:
            ct = pd.crosstab(sample.type, sample[col].fillna("na"))
            put(ws, r, 1, f"유형 × {col}", FB); r += 1
            header(ws, r, ["type", *map(str, ct.columns), "합계"]); r += 1
            r0 = r
            for t, row in ct.iterrows():
                put(ws, r, 1, t)
                for k, v in enumerate(row, 2):
                    put(ws, r, k, int(v), nf="0")
                put(ws, r, 2 + len(row), f"=SUM(B{r}:{get_column_letter(1 + len(row))}{r})", nf="0"); r += 1
            put(ws, r, 1, "합계", FB)
            for k in range(2, 3 + len(ct.columns)):
                cl = get_column_letter(k); put(ws, r, k, f"=SUM({cl}{r0}:{cl}{r - 1})", FB, nf="0")
            r += 2
        put(ws, r, 1, "저하 비율 (라벨 theta_primary)", FB); put(ws, r, 2, float(sample.degraded.mean()), nf="0.000")
        widths(ws, [14] + [10] * 12)

    # ---- 실행 정보: 단가는 입력(파란색), 비용은 수식
    ws = sheet("실행_정보")
    header(ws, 1, ["항목", *labels])
    items = [("run_id", [rid for rid in run_ids]), ("판정 수", [len(R["dec"]) for R in runs]),
             ("LLM 호출 (캐시 미스)", [int((~R["dec"].cache_hit.astype(bool)).sum()) for R in runs]),
             ("오류", [int(R["dec"].error.notna().sum()) for R in runs]),
             ("prompt 토큰 합계", [float(R["dec"][~R["dec"].cache_hit.astype(bool)].prompt_tokens.fillna(0).sum()) for R in runs]),
             ("completion 토큰 합계", [float(R["dec"][~R["dec"].cache_hit.astype(bool)].completion_tokens.fillna(0).sum()) for R in runs]),
             ("입력 단가 USD / 1M 토큰 (입력값)", [p[0] if p else 0.0 for p in prices]),
             ("출력 단가 USD / 1M 토큰 (입력값)", [p[1] if p else 0.0 for p in prices])]
    for i, (k, vals) in enumerate(items, 2):
        put(ws, i, 1, k)
        for j, v in enumerate(vals):
            put(ws, i, 2 + j, v, FBLUE if "입력값" in k else F, nf=None if isinstance(v, str) else "#,##0.000" if "단가" in k else "#,##0")
    i = len(items) + 2
    put(ws, i, 1, "추정 비용 USD (= 토큰 × 단가)", FB)
    for j in range(n):
        cl = get_column_letter(2 + j); put(ws, i, 2 + j, f"=({cl}6*{cl}8+{cl}7*{cl}9)/1000000", FB, nf="0.00")
    put(ws, i + 1, 1, "prompt 토큰 / 호출", F)
    for j in range(n):
        cl = get_column_letter(2 + j); put(ws, i + 1, 2 + j, f"=IF({cl}4=0,\"\",{cl}6/{cl}4)", nf="0")
    put(ws, i + 2, 1, "completion 토큰 / 호출", F)
    for j in range(n):
        cl = get_column_letter(2 + j); put(ws, i + 2, 2 + j, f"=IF({cl}4=0,\"\",{cl}7/{cl}4)", nf="0")
    put(ws, i + 4, 1, "단가 출처: OpenRouter 모델 API (2026-10-01). 로컬 vLLM 은 0. OpenRouter 크레딧 구매 수수료 5.5% 별도.", FGRAY)
    widths(ws, [36] + [40] * n)
    wb.save(path)


def fmt(v):
    if isinstance(v, float):
        return "" if np.isnan(v) else (f"{v:.3f}" if abs(v) < 100 else f"{v:,.0f}")
    return str(v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--labels", nargs="*", default=None)
    ap.add_argument("--prices", nargs="*", default=None, help="run 별 'in,out' USD/M 토큰. 예: 0,0 0.133,0.40")
    ap.add_argument("--out", default="compare")
    ap.add_argument("--xlsx", action="store_true", help="reports/{out}.xlsx 도 만든다")
    ap.add_argument("--sample", default=None, help="표본 csv 이름 (configs/{name}.csv). xlsx 의 표본_구성 시트")
    a = ap.parse_args()
    acfg = load_cfg("agent")
    labels = a.labels or a.runs
    prices = [tuple(map(float, p.split(","))) for p in a.prices] if a.prices else [None] * len(a.runs)
    sections, runs_loaded, chances = {}, [], []
    w, D = int(acfg.get("w", 5)), int(acfg.get("D", 5))
    for rid, lab, pr in zip(a.runs, labels, prices):
        R = load_run(rid, acfg)
        runs_loaded.append(R)
        chances.append(chance_baseline(R["dec"], R["U"], w, D))
        blocks = {"채점 (cycle)": cycle_scores(R["T"]), "구간별 경보율": alarm_rates(R["T"]),
                  "채점 (시나리오)": unit_scores(R["U"], int(acfg.get("w", 5)), int(acfg.get("D", 5))), "판정 안정성": stability(R["dec"]),
                  "confidence": confidence_stats(R["dec"], R["T"]), "지목 센서": sensor_stats(R["dec"], R["T"]),
                  "rationale": rationale_stats(R["dec"]), "토큰·비용": token_stats(R["dec"], pr)}
        for sec, vals in blocks.items():
            for k, v in vals.items():
                sections.setdefault(sec, {}).setdefault(k, {})[lab] = v
    for k in chances[0]:
        for lab, ch in zip(labels, chances):
            sections.setdefault("기준선 (circular-shift 우연)", {}).setdefault(k, {})[lab] = ch[k]
    lines = [f"# run 비교 — {a.out}", "", "run: " + " · ".join(f"{l} = `{r}`" for l, r in zip(labels, a.runs)), ""]
    for sec, rows in sections.items():
        lines += [f"## {sec}", "", "| 지표 | " + " | ".join(labels) + " |", "|---|" + "---|" * len(labels)]
        for k, vals in rows.items():
            lines.append(f"| {k} | " + " | ".join(fmt(vals.get(l, np.nan)) for l in labels) + " |")
        lines.append("")
    out = AGENT / "reports" / f"{a.out}.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"→ {out}")
    if a.xlsx:
        sample = pd.read_csv(AGENT / "configs" / f"{a.sample}.csv") if a.sample else None
        xp = AGENT / "reports" / f"{a.out}.xlsx"
        write_xlsx(xp, labels, runs_loaded, sections, chances, prices, a.runs, sample, w, D)
        print(f"→ {xp}")


if __name__ == "__main__":
    main()
