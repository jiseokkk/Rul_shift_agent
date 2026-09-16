"""Phase D-5: reports/D_label_summary.md (6 항목)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.analysis import plotting
from src.common import md_table, read_parquet


def _rate_table(df: pd.DataFrame, rows_key: str, cols_key: str):
    piv = df.pivot_table(index=rows_key, columns=cols_key, values="degraded", aggfunc="mean")
    return piv


def write_report(paths, index_long: pd.DataFrame, clean_var: dict | None, primary: str = "theta_primary",
                 sens: pd.DataFrame | None = None) -> Path:
    fig_dir = paths.reports_dir / "figures"
    P = index_long[index_long["theta_name"] == primary].copy()
    P["degraded"] = P["degraded"].astype(bool)
    lines = ["# Phase D-5 — 라벨 요약", ""]
    tv = P["theta_value"].iloc[0] if len(P) else "n/a"
    tv = f"{tv:.4g}" if isinstance(tv, float) else str(tv)
    lines.append(f"- 기준 θ: {primary} = {tv}, k={P['k'].iloc[0]}, m={P['m'].iloc[0]}, θ_low ratio={P['theta_low_ratio'].iloc[0]}")
    lines.append(f"- (unit, scenario) 수: {len(P)}, 저하 비율: {P['degraded'].mean():.3f}")
    lines.append("")

    # 1. 유형 × 강도 저하율 heatmap
    lines.append("## 1. 유형 × 강도별 저하 (unit, scenario) 비율")
    P["param_str"] = P["param"].map(lambda v: "na" if pd.isna(v) else f"{v:g}")
    piv = P.pivot_table(index="type", columns="param_str", values="degraded", aggfunc="mean")
    rows = [dict(type=t, **{c: (float(piv.loc[t, c]) if not pd.isna(piv.loc[t, c]) else "") for c in piv.columns}) for t in piv.index]
    lines.append(md_table(rows, fmt="{:.2f}"))
    if plotting.heatmap(piv.to_numpy(dtype=float), list(piv.index), list(piv.columns),
                        fig_dir / "D_degraded_rate_type_param.png", "degraded rate: type × param"):
        lines.append("![heatmap](figures/D_degraded_rate_type_param.png)\n")

    # 2. 유형별 지연 분포
    lines.append("## 2. 유형별 지연 τ_d − τ_s (저하 케이스만)")
    rows = []
    for t, g in P[P["degraded"]].groupby("type"):
        d = g["delay"].dropna().astype(float)
        if len(d):
            rows.append({"type": t, "n": int(len(d)), "min": float(d.min()), "p25": float(d.quantile(0.25)),
                         "median": float(d.median()), "p75": float(d.quantile(0.75)), "max": float(d.max())})
    lines.append(md_table(rows, fmt="{:.1f}"))
    if plotting.hist({t: g["delay"].dropna().to_numpy() for t, g in P[P["degraded"]].groupby("type")},
                     fig_dir / "D_delay_by_type.png", "delay τ_d − τ_s by type", "cycles", bins=40, log_y=False):
        lines.append("![delay](figures/D_delay_by_type.png)\n")

    # 2-1. 긴 지연 (delay > 50)
    LONG = 50
    D = P[P["degraded"]].copy()
    D["param_str"] = D["param"].map(lambda v: "na" if pd.isna(v) else f"{v:g}")
    lg = D[D["delay"].astype(float) > LONG]
    lines.append(f"### 2-1. 긴 지연 (delay > {LONG} cycle)")
    lines.append(f"- 해당 (unit, scenario): {len(lg)} / {len(D)} 저하 케이스 = {len(lg) / max(1, len(D)):.3f}")
    if len(lg):
        rows = []
        for t in sorted(D["type"].unique()):
            gt, lt = D[D["type"] == t], lg[lg["type"] == t]
            rows.append({"type": t, "저하 n": len(gt), "긴 지연 n": len(lt),
                         "비율": len(lt) / max(1, len(gt)),
                         "delay median": float(lt["delay"].median()) if len(lt) else None,
                         "delay max": float(lt["delay"].max()) if len(lt) else None})
        lines.append(md_table(rows, fmt="{:.3f}"))
        piv = D.assign(lng=D["delay"].astype(float) > LONG).pivot_table(
            index="type", columns="param_str", values="lng", aggfunc="mean")
        rows = [dict(type=t, **{c: (float(piv.loc[t, c]) if not pd.isna(piv.loc[t, c]) else "")
                                for c in piv.columns}) for t in piv.index]
        lines.append("**유형 × 강도별 긴 지연 비율**")
        lines.append(md_table(rows, fmt="{:.2f}"))
    lines.append("")

    # 3. 시점별 저하율 (포화 여부 분리)
    lines.append("## 3. 시점별 저하율 — 포화(T_u − τ_s > 125) 여부 분리")
    piv = P.pivot_table(index="timing_p", columns="saturated_at_tau_s", values="degraded", aggfunc="mean")
    cnt = P.pivot_table(index="timing_p", columns="saturated_at_tau_s", values="degraded", aggfunc="size")
    rows = []
    for p in piv.index:
        row = {"timing_p": p}
        for c in piv.columns:
            row[f"sat={c} rate"] = float(piv.loc[p, c]) if not pd.isna(piv.loc[p, c]) else ""
            row[f"sat={c} n"] = int(cnt.loc[p, c]) if not pd.isna(cnt.loc[p, c]) else 0
        rows.append(row)
    lines.append(md_table(rows, fmt="{:.2f}"))

    # 4. 복귀 발생 비율과 위치
    lines.append("## 4. 복귀(1→0) 발생 비율과 위치")
    rev = P[P["n_reversions"] > 0]
    lines.append(f"- 복귀가 한 번 이상 발생한 (unit, scenario): {len(rev)} / {len(P)} = {len(rev) / max(1, len(P)):.3f}")
    pos = []
    for r in rev.itertuples(index=False):
        st = read_parquet(paths.state(primary, int(r.unit), r.scenario_id))
        lab = st["label"].to_numpy()
        t = st["time"].to_numpy()
        exits = t[1:][(lab[:-1] == 1) & (lab[1:] == 0)]
        pos.extend((exits / int(r.T_u)).tolist())
    if pos:
        pos = np.asarray(pos)
        lines.append(f"- 복귀 시점 / T_u: median {np.median(pos):.2f}, 수명 말기(>0.9) 비율 {(pos > 0.9).mean():.2f}, n={pos.size}")
    lines.append("")

    # 5. θ 후보 간 라벨 일치율
    lines.append("## 5. θ 세 후보 간 cycle 라벨 일치율")
    names = sorted(index_long["theta_name"].unique())
    agree = {}
    keys = list(P[["unit", "scenario_id"]].itertuples(index=False, name=None))
    sample = keys if len(keys) <= 600 else [keys[i] for i in np.linspace(0, len(keys) - 1, 600).astype(int)]
    for a in names:
        for b in names:
            if a >= b:
                continue
            tot = same = 0
            n11 = n10 = n01 = 0          # 양성 cycle 교집합/차집합 (Jaccard, κ 용)
            for (u, sid) in sample:
                la = read_parquet(paths.state(a, int(u), sid))["label"].to_numpy()
                lb = read_parquet(paths.state(b, int(u), sid))["label"].to_numpy()
                n = min(len(la), len(lb))
                la, lb = la[:n].astype(bool), lb[:n].astype(bool)
                tot += n
                same += int((la == lb).sum())
                n11 += int((la & lb).sum())
                n10 += int((la & ~lb).sum())
                n01 += int((~la & lb).sum())
            po = same / max(1, tot)
            # Cohen's κ: 우연 일치 p_e 를 양쪽 주변확률로 계산
            pa, pb = (n11 + n10) / max(1, tot), (n11 + n01) / max(1, tot)
            pe = pa * pb + (1 - pa) * (1 - pb)
            kappa = (po - pe) / (1 - pe) if (1 - pe) > 1e-12 else float("nan")
            agree[(a, b)] = {"agreement": po, "kappa": kappa,
                             "jaccard_pos": n11 / max(1, n11 + n10 + n01),
                             "pos_rate_a": pa, "pos_rate_b": pb}
    lines.append(md_table([{"a": a, "b": b, **v} for (a, b), v in agree.items()], fmt="{:.3f}"))
    lines.append("")
    lines.append("- `agreement` 는 전 cycle raw 일치율, `kappa` 는 우연 일치를 보정한 Cohen's κ, "
                 "`jaccard_pos` 는 양성 cycle 집합의 Jaccard 이다.")
    lines.append("- 양성률이 낮으면 raw 일치율은 높게 나오므로 κ·Jaccard 를 함께 본다 "
                 "(`pos_rate_a/b` 는 각 θ 의 양성 cycle 비율).")
    if len(keys) > len(sample):
        lines.append(f"(일치율은 {len(sample)} 개 (unit, scenario) 표본 기준)\n")
    rows = []
    for t in names:
        g = index_long[index_long["theta_name"] == t]
        rows.append({"theta_name": t, "degraded_rate": float(g["degraded"].astype(bool).mean()),
                     "delay_median": float(g["delay"].dropna().median()) if g["delay"].notna().any() else None})
    lines.append(md_table(rows, fmt="{:.3f}"))

    # 6. clean-only 대조
    lines.append("## 6. clean-only 대조의 저하 진입율 (θ 검증)")
    if clean_var:
        rows = []
        for name, c in clean_var["candidates"].items():
            ctrl = c["control"] or {}
            rows.append({"cand": name, "theta": c["theta"], "unit_entry_rate": ctrl.get("unit_entry_rate"),
                         "cycle_positive_rate": ctrl.get("cycle_positive_rate")})
        lines.append(md_table(rows, fmt="{:.4g}"))
    else:
        lines.append("(clean_variability.json 없음)\n")

    if sens is not None and len(sens):
        lines.append("## 부록. (k, m) 민감도 (θ_primary 고정)")
        lines.append(md_table(sens.to_dict("records"), fmt="{:.3f}"))

    out = paths.reports_dir / "D_label_summary.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out
