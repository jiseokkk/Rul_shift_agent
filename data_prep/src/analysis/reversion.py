"""Phase D 마감: 복귀(1→0) 진단.

복귀가 (A) 히스테리시스 flicker 인지, (B) 수명 말기 예측 수렴의 부산물인지,
(C) 진짜 중반 복귀인지 이벤트 단위로 판별하고 (k, m) 대안과 비교한다.

이벤트 분류 규칙 (작업 지시서 §1 Step, §2)
  A flicker   : reentry_within_20  또는  degraded_len_before < 10
  B 말기 수렴 : A 가 아니고  (yhat_clean_at_exit < θ_primary  또는  pos_in_life > 0.9)
  C 진짜 복귀 : A 도 B 도 아님

(k, m) 대안은 delta parquet 을 메모리에서 다시 라벨링해 비교한다. 기존 state parquet 은
읽지도 쓰지도 않으므로 현재 라벨이 바뀔 위험이 없다.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.common import md_table, read_parquet
from src.label.build_labels import label_one
from src.label.hysteresis import summarize

REENTRY_WINDOW = 20      # reentry_within_20 / delta_min_after20 의 창
SHORT_RUN = 10           # degraded_len_before < 10 이면 flicker
LATE_LIFE = 0.9          # pos_in_life > 0.9 이면 수명 말기

EVENT_COLS = ["unit", "scenario_id", "type", "sensor", "param", "timing_p", "tau_s", "T_u",
              "t_exit", "pos_in_life", "yhat_clean_at_exit", "delta_at_exit", "delta_min_after20",
              "degraded_len_before", "reentry_within_20", "reentry_gap", "is_final_exit", "pattern"]


# ---------------------------------------------------------------- 이벤트 추출
def exit_events(times: np.ndarray, label: np.ndarray, delta: np.ndarray,
                yhat_clean: np.ndarray, T_u: int, theta_primary: float) -> list[dict]:
    """한 (unit, scenario) 의 label 시퀀스에서 1→0 전이를 전부 이벤트로. 없으면 빈 리스트."""
    lab = np.asarray(label).astype(int)
    n = len(lab)
    ev = []
    for i in range(1, n):
        if not (lab[i - 1] == 1 and lab[i] == 0):
            continue
        t_exit = int(times[i])
        # 직전 연속 1 구간 길이
        j = i - 1
        while j >= 0 and lab[j] == 1:
            j -= 1
        run_len = i - 1 - j

        # [t_exit, t_exit+20) 창: 시간 기준(cycle) 으로 자른다
        w = (times >= t_exit) & (times < t_exit + REENTRY_WINDOW)
        d_min = float(np.min(delta[w])) if w.any() else float("nan")

        # 창 안의 0→1 재진입
        gap, reentry = float("nan"), False
        idx_w = np.nonzero(w)[0]
        for t2 in idx_w[1:]:
            if lab[t2 - 1] == 0 and lab[t2] == 1:
                reentry, gap = True, float(times[t2] - t_exit)
                break
        ev.append({
            "t_exit": t_exit,
            "pos_in_life": t_exit / T_u,
            "yhat_clean_at_exit": float(yhat_clean[i]),
            "delta_at_exit": float(delta[i]),
            "delta_min_after20": d_min,
            "degraded_len_before": int(run_len),
            "reentry_within_20": bool(reentry),
            "reentry_gap": gap,
            "is_final_exit": bool(lab[i:].sum() == 0),
        })
    for e in ev:
        e["pattern"] = classify(e, theta_primary)
    return ev


def classify(e: dict, theta_primary: float) -> str:
    if e["reentry_within_20"] or e["degraded_len_before"] < SHORT_RUN:
        return "A"
    if e["yhat_clean_at_exit"] < theta_primary or e["pos_in_life"] > LATE_LIFE:
        return "B"
    return "C"


# ---------------------------------------------------------------- 수집
def load_inputs(paths, index_meta: pd.DataFrame, base_seed: int, log=print) -> dict:
    """delta parquet 과 clean 예측을 한 번만 읽어 메모리에 둔다. (k,m) 대안이 이걸 재사용한다."""
    clean = {}
    for u in sorted(index_meta["unit"].unique()):
        c = read_parquet(paths.pred_clean(base_seed, int(u)))
        clean[int(u)] = c.set_index("time")["pred"]
    deltas = {}
    n = len(index_meta)
    for i, r in enumerate(index_meta.itertuples(index=False)):
        deltas[(int(r.unit), r.scenario_id)] = read_parquet(paths.delta(int(r.unit), r.scenario_id))
        if (i + 1) % 2000 == 0:
            log(f"[reversion] delta 읽기 {i + 1}/{n}")
    return {"clean": clean, "deltas": deltas}


def events_for_labels(paths, index_meta: pd.DataFrame, cache: dict, theta_primary: float,
                      spec: dict | None, k: int, m: int, ratio: float,
                      from_state: bool = False, theta_name: str = "theta_primary",
                      log=print) -> tuple[pd.DataFrame, pd.DataFrame]:
    """이벤트 테이블과 시나리오 집계를 만든다.

    from_state=True  : 디스크의 state parquet 을 그대로 읽는다 (현재 확정 라벨).
    from_state=False : spec/k/m/ratio 로 메모리에서 다시 라벨링한다 ((k,m) 대안 비교용).
    """
    ev_rows, sc_rows = [], []
    for r in index_meta.itertuples(index=False):
        unit, sid, T_u, tau_s = int(r.unit), r.scenario_id, int(r.T_u), int(r.tau_s)
        d = cache["deltas"][(unit, sid)]
        if from_state:
            st = read_parquet(paths.state(theta_name, unit, sid))
            times, lab, delta = st["time"].to_numpy(), st["label"].to_numpy(), st["delta"].to_numpy()
            degraded = bool(lab.sum() > 0)
            delay = None
            if degraded:
                first = int(times[np.argmax(lab == 1)])
                delay = first - tau_s
        else:
            df, res = label_one(d, spec, k, m, ratio)
            times, lab, delta = df["time"].to_numpy(), df["label"].to_numpy(), df["delta"].to_numpy()
            s = summarize(res, times, tau_s)
            degraded, delay = s["degraded"], s["delay"]

        yhat = cache["clean"][unit].reindex(times).to_numpy()
        ev = exit_events(times, lab, delta, yhat, T_u, theta_primary)
        meta = {"unit": unit, "scenario_id": sid, "type": r.type, "sensor": r.sensor,
                "param": r.param, "timing_p": r.timing_p, "tau_s": tau_s, "T_u": T_u}
        for e in ev:
            ev_rows.append({**meta, **e})
        sc_rows.append({**meta, "degraded": degraded, "delay": delay,
                        "n_reversions": len(ev),
                        "n_reentries": int(sum(e["reentry_within_20"] for e in ev)),
                        "has_late_exit": bool(any(e["pos_in_life"] > LATE_LIFE for e in ev)),
                        "n_A": sum(e["pattern"] == "A" for e in ev),
                        "n_B": sum(e["pattern"] == "B" for e in ev),
                        "n_C": sum(e["pattern"] == "C" for e in ev)})
    ev_df = pd.DataFrame(ev_rows, columns=EVENT_COLS) if ev_rows else pd.DataFrame(columns=EVENT_COLS)
    return ev_df, pd.DataFrame(sc_rows)


def pattern_shares(ev: pd.DataFrame) -> dict:
    n = max(1, len(ev))
    return {p: float((ev["pattern"] == p).sum()) / n for p in ("A", "B", "C")}


# ---------------------------------------------------------------- 판정
def verdict(shares: dict) -> tuple[list[str], list[str]]:
    """작업 지시서 §2 판정 규칙. 복수 해당 가능, A 조치가 우선."""
    v, act = [], []
    if shares["A"] >= 0.30:
        v.append(f"A(flicker) {shares['A']:.1%} ≥ 30% → **flicker 우세**")
        act.append("(k,m) → (7,10) 으로 변경하고 라벨 재생성. 재진단 후에도 A ≥ 30% 면 θ_low_ratio 0.5 → 0.3")
    if shares["B"] >= 0.50 and shares["A"] < 0.30:
        v.append(f"B(말기 수렴) {shares['B']:.1%} ≥ 50% 이고 A < 30% → **말기 수렴 우세**")
        act.append("라벨 유지. 평가 단계에 indeterminate 마스크 도입 (복귀 이후 & ŷ_clean < θ_primary)")
    if shares["C"] >= 0.20:
        v.append(f"C(진짜 중반 복귀) {shares['C']:.1%} ≥ 20% → **진짜 복귀 존재**")
        act.append("라벨 유지. 분석 축 추가. 사례 플롯으로 원인 확인")
    if not v:
        v.append(f"어느 규칙에도 해당 없음 (A {shares['A']:.1%}, B {shares['B']:.1%}, C {shares['C']:.1%})")
        act.append("라벨 유지")
    return v, act


# ---------------------------------------------------------------- 사례 플롯
def case_plot(paths, cache: dict, ev: pd.Series, out_path: Path, theta_primary: float,
              span: int = 30) -> bool:
    """C 패턴 이벤트 하나의 t_exit ± span cycle 구간 ŷ_clean · ŷ_shift · δ."""
    from src.analysis import plotting as P
    if not P.HAS_MPL:
        return False
    from src.analysis.scenario_fig import setup_font
    setup_font()
    d = cache["deltas"][(int(ev.unit), ev.scenario_id)]
    t = d["time"].to_numpy()
    w = (t >= ev.t_exit - span) & (t <= ev.t_exit + span)
    if not w.any():
        return False
    fig, (a1, a2) = P.plt.subplots(2, 1, figsize=(8, 5.5), sharex=True,
                                   gridspec_kw={"height_ratios": [3, 2], "hspace": 0.12})
    a1.plot(t[w], d["pred_clean"].to_numpy()[w], color="#1f77b4", lw=1.6, marker="o", ms=2.5, label="ŷ_clean")
    a1.plot(t[w], d["pred_shift"].to_numpy()[w], color="#d62728", lw=1.6, marker="o", ms=2.5, label="ŷ_shift")
    a1.set_ylabel("RUL")
    a2.plot(t[w], d["delta"].to_numpy()[w], color="#d62728", lw=1.6, marker="o", ms=2.5, label="|δ|")
    a2.axhline(theta_primary, color="#2ca02c", ls="--", lw=1.2, label=f"θ_high {theta_primary:.2f}")
    a2.axhline(theta_primary * 0.5, color="#2ca02c", ls=":", lw=1.0, label="θ_low")
    a2.set_ylabel("|δ|")
    a2.set_xlabel("cycle")
    for ax in (a1, a2):
        ax.axvline(ev.t_exit, color="#9467bd", ls="-", lw=1.6)
        ax.axvline(ev.tau_s, color="#ff7f0e", ls="--", lw=1.2)
        ax.grid(alpha=0.25, lw=0.5)
        ax.legend(fontsize=8, loc="best")
    a1.text(ev.t_exit, a1.get_ylim()[1], " 복귀", color="#9467bd", va="top", fontsize=9, fontweight="bold")
    param = "na" if pd.isna(ev.param) else f"{ev.param:g}"
    fig.suptitle(f"C 패턴 — unit {int(ev.unit)}  {ev.scenario_id}\n"
                 f"{ev.type}·{ev.sensor}·{param}·p{ev.timing_p:g}  "
                 f"복귀 t={int(ev.t_exit)} (수명 {ev.pos_in_life:.2f})  "
                 f"직전 저하 {int(ev.degraded_len_before)} cycle  ŷ_clean={ev.yhat_clean_at_exit:.1f}",
                 fontsize=10)
    fig.subplots_adjust(top=0.86, bottom=0.10, left=0.09, right=0.98)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=130)
    P.plt.close(fig)
    return True


# ---------------------------------------------------------------- 리포트
def _q(s, q):
    s = pd.Series(s).dropna()
    return float(s.quantile(q)) if len(s) else float("nan")


def write_report(paths, ev: pd.DataFrame, sc: pd.DataFrame, theta_primary: float,
                 km_table: pd.DataFrame, cache: dict, k: int, m: int, ratio: float) -> tuple[Path, dict, list, list]:
    from src.analysis import plotting as P
    fig_dir = paths.reports_dir / "figures"
    deg = sc[sc["degraded"]]
    rev_sc = sc[sc["n_reversions"] > 0]
    shares = pattern_shares(ev)
    L = ["# Phase D 마감 — 복귀(1→0) 진단", ""]

    # 1 요약
    L += ["## 1. 요약", "",
          f"- 기준 라벨: θ_primary = {theta_primary:.4g}, k={k}, m={m}, θ_low_ratio={ratio}",
          f"- 전체 (unit, scenario): {len(sc)}",
          f"- 저하 판정 시나리오: {len(deg)} ({len(deg) / max(1, len(sc)):.3f})",
          f"- 복귀 1회 이상 시나리오: {len(rev_sc)} / {len(sc)} = {len(rev_sc) / max(1, len(sc)):.3f}"
          f"  (저하 시나리오 대비 {len(rev_sc) / max(1, len(deg)):.3f})",
          f"- 총 복귀 이벤트: {len(ev)}",
          f"- 재진입({REENTRY_WINDOW} cycle 내) 이벤트: {int(ev['reentry_within_20'].sum())} ({ev['reentry_within_20'].mean():.3f})"
          if len(ev) else "- 복귀 이벤트 없음", ""]

    # 2 유형별
    L += ["## 2. 유형별", ""]
    rows = []
    for t in sorted(sc["type"].unique()):
        d_t, e_t = deg[deg["type"] == t], ev[ev["type"] == t]
        r_t = d_t[d_t["n_reversions"] > 0]
        rows.append({"type": t, "저하 n": len(d_t),
                     "복귀율": len(r_t) / max(1, len(d_t)), "이벤트 n": len(e_t),
                     "재진입률": float(e_t["reentry_within_20"].mean()) if len(e_t) else float("nan"),
                     "직전저하 median": _q(e_t["degraded_len_before"], 0.5),
                     "ŷ_clean median": _q(e_t["yhat_clean_at_exit"], 0.5),
                     "말기(>0.9) 비율": float((e_t["pos_in_life"] > LATE_LIFE).mean()) if len(e_t) else float("nan")})
    L += [md_table(rows, fmt="{:.3f}"), ""]

    # 3 유형 × 강도
    L += ["## 3. 유형 × 강도별 복귀율 / 재진입률", ""]
    deg2 = deg.assign(param_str=deg["param"].map(lambda v: "na" if pd.isna(v) else f"{v:g}"))
    ev2 = ev.assign(param_str=ev["param"].map(lambda v: "na" if pd.isna(v) else f"{v:g}"))
    piv_r = deg2.assign(rev=deg2["n_reversions"] > 0).pivot_table(index="type", columns="param_str", values="rev", aggfunc="mean")
    piv_e = ev2.pivot_table(index="type", columns="param_str", values="reentry_within_20", aggfunc="mean")
    for nm, piv in [("복귀율", piv_r), ("재진입률", piv_e)]:
        L.append(f"**{nm}**")
        rows = [dict(type=t, **{c: (float(piv.loc[t, c]) if not pd.isna(piv.loc[t, c]) else "") for c in piv.columns})
                for t in piv.index]
        L += [md_table(rows, fmt="{:.2f}"), ""]

    # 4 복귀 시점 ŷ_clean 분포
    L += ["## 4. 복귀 시점 ŷ_clean 분포", ""]
    rows = []
    for nm, sub in [("전체", ev), (f"말기 (pos>{LATE_LIFE})", ev[ev["pos_in_life"] > LATE_LIFE]),
                    (f"중반 (pos≤{LATE_LIFE})", ev[ev["pos_in_life"] <= LATE_LIFE])]:
        y = sub["yhat_clean_at_exit"]
        rows.append({"구간": nm, "n": len(sub), "p10": _q(y, 0.10), "p50": _q(y, 0.50), "p90": _q(y, 0.90),
                     f"ŷ<θ({theta_primary:.2f}) 비율": float((y < theta_primary).mean()) if len(sub) else float("nan")})
    L += [md_table(rows, fmt="{:.3f}"), ""]

    # 5 패턴 분류
    L += ["## 5. 복귀 패턴 분류", "",
          f"- **A flicker**: 재진입 {REENTRY_WINDOW} cycle 내 **또는** 직전 저하 구간 < {SHORT_RUN} cycle",
          f"- **B 말기 수렴**: A 아니고 (ŷ_clean(t_exit) < θ_primary **또는** pos_in_life > {LATE_LIFE})",
          "- **C 진짜 중반 복귀**: A 도 B 도 아님", "",
          md_table([{"pattern": p, "n": int((ev["pattern"] == p).sum()), "비율": shares[p]} for p in "ABC"],
                   fmt="{:.3f}"), ""]
    rows = []
    for t in sorted(ev["type"].unique()):
        e_t = ev[ev["type"] == t]
        rows.append({"type": t, "n": len(e_t),
                     **{p: float((e_t["pattern"] == p).mean()) for p in "ABC"}})
    L += ["**유형별 A/B/C 비율**", md_table(rows, fmt="{:.3f}"), ""]

    # 5-1. 분류 규칙 자체의 건전성 — 지시서 규칙을 그대로 적용한 뒤 사후 점검한다
    nonA = ev[ev["pattern"] != "A"]
    c_y = nonA["yhat_clean_at_exit"] < theta_primary
    c_p = nonA["pos_in_life"] > LATE_LIFE
    only_y, only_p, both = int((c_y & ~c_p).sum()), int((~c_y & c_p).sum()), int((c_y & c_p).sum())
    L += ["### 5-1. 분류 규칙 점검", "",
          "**(a) B 규칙의 `ŷ_clean < θ_primary` 조건은 단독으로 한 번도 발동하지 않는다.**", "",
          md_table([{"조건": "ŷ<θ 만", "n": only_y}, {"조건": "pos>0.9 만", "n": only_p},
                    {"조건": "둘 다", "n": both}], fmt="{:.0f}"),
          "",
          f"비-A 이벤트 {len(nonA)} 개 중 `ŷ<θ` 만으로 B 가 되는 경우는 {only_y} 건이다. "
          f"§4 에서 보듯 중반(pos≤{LATE_LIFE}) 이벤트의 `ŷ<θ` 비율이 정확히 0 이므로, "
          f"B 규칙은 실질적으로 `pos_in_life > {LATE_LIFE}` 단독 조건과 같다. "
          "따라서 A/B/C 분해는 사실상 이 임계 하나가 좌우한다.", "",
          "**(b) 그 임계를 바꾸면 B 와 C 가 크게 뒤집힌다.**", ""]
    rows = []
    for thr in (0.90, 0.85, 0.80, 0.75, 0.70, 0.60):
        b = (nonA["yhat_clean_at_exit"] < theta_primary) | (nonA["pos_in_life"] > thr)
        rows.append({"pos 임계": thr, "A": shares["A"], "B": int(b.sum()) / max(1, len(ev)),
                     "C": int((~b).sum()) / max(1, len(ev)),
                     "판정": ("B 우세" if int(b.sum()) / max(1, len(ev)) >= 0.5 else "") +
                             (" / C 존재" if int((~b).sum()) / max(1, len(ev)) >= 0.2 else "")})
    L += [md_table(rows, fmt="{:.3f}"), ""]
    Cev = ev[ev["pattern"] == "C"]
    if len(Cev):
        L += [f"**(c) C 이벤트는 중반에 고르게 퍼져 있지 않고 임계 바로 아래에 몰려 있다.** "
              f"C 의 pos_in_life 는 median {Cev['pos_in_life'].median():.2f}, "
              f"p25 {Cev['pos_in_life'].quantile(.25):.2f}, p75 {Cev['pos_in_life'].quantile(.75):.2f} 이고 "
              f"{float((Cev['pos_in_life'] > 0.7).mean()):.1%} 가 pos>0.7 이다. "
              f"또한 {float(Cev['is_final_exit'].mean()):.1%} 가 재진입 없는 최종 복귀이며 "
              f"직전 저하 구간 median 은 {Cev['degraded_len_before'].median():.0f} cycle 이다.", "",
              "> 종합하면 C 로 분류된 이벤트의 상당수는 §7 사례에서 보듯 δ 가 RUL→0 과 함께 "
              "단조 감소해 소멸하는 **말기 수렴의 연장**이며, `pos>0.9` 라는 컷오프가 이 현상의 "
              "시작점보다 늦게 잡혀 있어 B 가 아닌 C 로 새어 들어온 것이다. "
              "아래 §9 판정은 지시서 규칙을 그대로 적용한 결과이고, 이 한계를 함께 읽어야 한다.", ""]

    # 6 (k, m) 비교
    L += ["## 6. (k, m) 대안 비교", "",
          "기존 state parquet 을 건드리지 않고 delta 로부터 메모리에서 다시 라벨링해 비교한다.", "",
          md_table(km_table.to_dict("records"), fmt="{:.3f}"), ""]

    # 7 C 사례
    L += ["## 7. C 패턴 사례", ""]
    C = ev[ev["pattern"] == "C"]
    if len(C):
        pick = C.sort_values("degraded_len_before", ascending=False).head(5)
        rows = []
        for i, (_, e) in enumerate(pick.iterrows(), 1):
            ok = case_plot(paths, cache, e, fig_dir / f"D_reversion_case_{i}.png", theta_primary)
            rows.append({"#": i, "type": e.type, "param": "na" if pd.isna(e.param) else f"{e.param:g}",
                         "timing_p": e.timing_p, "unit": int(e.unit), "t_exit": int(e.t_exit),
                         "pos_in_life": e.pos_in_life, "직전저하": int(e.degraded_len_before),
                         "ŷ_clean": e.yhat_clean_at_exit, "δ(t_exit)": e.delta_at_exit,
                         "그림": f"figures/D_reversion_case_{i}.png" if ok else "-"})
        L += [md_table(rows, fmt="{:.2f}"), ""]
        for i in range(1, len(pick) + 1):
            L.append(f"![case {i}](figures/D_reversion_case_{i}.png)")
        L.append("")
    else:
        L += ["C 패턴 이벤트 없음.", ""]

    # 8 그림
    L += ["## 8. 그림", ""]
    if P.hist({t: g["pos_in_life"].to_numpy() for t, g in ev.groupby("type")},
              fig_dir / "D_reversion_pos_in_life.png", "복귀 시점 / T_u (유형별)", "pos_in_life",
              bins=40, log_y=False):
        L.append("![pos_in_life](figures/D_reversion_pos_in_life.png)")
    if P.box({t: g["yhat_clean_at_exit"].to_numpy() for t, g in ev.groupby("type")},
             fig_dir / "D_reversion_yhat_at_exit.png", "복귀 시점의 ŷ_clean (유형별)", "ŷ_clean(t_exit)",
             hline=theta_primary, hline_label=f"θ_primary {theta_primary:.2f}"):
        L.append("![yhat](figures/D_reversion_yhat_at_exit.png)")
    L.append("")

    # 판정
    verd, acts = verdict(shares)
    L += ["## 9. 판정", ""]
    for v in verd:
        L.append(f"- {v}")
    L += ["", "**조치**", ""]
    for a in acts:
        L.append(f"- {a}")
    L.append("")

    out = paths.reports_dir / "D_reversion_diagnostics.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    return out, shares, verd, acts
