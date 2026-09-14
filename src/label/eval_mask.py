"""Phase D 마감: cycle 단위 평가용 indeterminate 마스크.

시나리오별 '최종 1→0 전이 이후 재진입이 없는 구간' 을 평가에서 제외한다.
그 구간의 라벨 0 은 정의상 정직하지만, 에이전트는 clean 예측을 볼 수 없어
δ 가 소멸했다는 사실을 관측할 방법이 없다. 따라서 채점 대상에서 뺀다.

라벨 파일(labels/*/state/) 은 바꾸지 않는다. 마스크는 별도 csv 로만 나간다.

규칙
  1. 이벤트 중 is_final_exit & ~reentry_within_20 이 있으면
       mask_from_cycle = t_exit,  mask_to_cycle = T_u
  2. 없으면 행은 만들되 mask_from_cycle = NaN (마스크 없음)
  3. mask_from_cycle 이후 라벨이 전부 0 인지 검증 (최종 복귀 정의상 참이어야 한다)

is_final_exit(= 이후 라벨이 전부 0) 은 논리적으로 재진입이 없음을 함의하므로
규칙 1 의 두 조건은 중복이다. 지시서 문구 그대로 두 조건을 모두 적용한다.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.common import md_table, read_parquet

OUT_COLS = ["unit", "scenario_id", "type", "param", "timing_p", "tau_s", "tau_d", "T_u",
            "mask_from_cycle", "mask_to_cycle", "n_masked_cycles", "frac_masked"]


class MaskAssertionError(AssertionError):
    pass


def build_mask(paths, index_long: pd.DataFrame, events: pd.DataFrame, theta_name: str,
               seq_len: int, verify: bool = True, log=print) -> pd.DataFrame:
    """theta_name 라벨 기준 마스크 테이블. index_long 은 해당 θ 행만 걸러 넣는다."""
    idx = index_long[index_long["theta_name"] == theta_name]
    final = events[events["is_final_exit"] & ~events["reentry_within_20"]]
    # 시나리오당 최대 1 건 (is_final_exit 정의상). 혹시 여럿이면 가장 늦은 것을 쓴다.
    final = final.sort_values("t_exit").drop_duplicates(subset=["unit", "scenario_id"], keep="last")
    fmap = {(int(r.unit), r.scenario_id): int(r.t_exit) for r in final.itertuples(index=False)}

    rows, bad = [], []
    for r in idx.itertuples(index=False):
        unit, sid, T_u = int(r.unit), r.scenario_id, int(r.T_u)
        t_exit = fmap.get((unit, sid))
        n_eval = T_u - (seq_len - 1)          # 평가 대상 cycle 수 (seq_len .. T_u)
        if t_exit is None:
            rows.append({"unit": unit, "scenario_id": sid, "type": r.type, "param": r.param,
                         "timing_p": r.timing_p, "tau_s": int(r.tau_s),
                         "tau_d": r.tau_d if pd.notna(r.tau_d) else np.nan, "T_u": T_u,
                         "mask_from_cycle": np.nan, "mask_to_cycle": np.nan,
                         "n_masked_cycles": 0, "frac_masked": 0.0})
            continue
        n_masked = T_u - t_exit + 1
        if verify:
            st = read_parquet(paths.state(theta_name, unit, sid))
            lab = st["label"].to_numpy()[st["time"].to_numpy() >= t_exit]
            if int(lab.sum()) != 0:
                bad.append({"unit": unit, "scenario_id": sid, "t_exit": t_exit,
                            "n_positive_after": int(lab.sum())})
        rows.append({"unit": unit, "scenario_id": sid, "type": r.type, "param": r.param,
                     "timing_p": r.timing_p, "tau_s": int(r.tau_s),
                     "tau_d": r.tau_d if pd.notna(r.tau_d) else np.nan, "T_u": T_u,
                     "mask_from_cycle": t_exit, "mask_to_cycle": T_u,
                     "n_masked_cycles": n_masked, "frac_masked": n_masked / n_eval})
    if bad:
        raise MaskAssertionError(
            f"마스크 시작 이후 양성 라벨이 남아 있다 ({len(bad)} 건): {bad[:5]}")
    log(f"[eval_mask] {theta_name}: {len(fmap)} / {len(idx)} 시나리오에 마스크")
    return pd.DataFrame(rows, columns=OUT_COLS)


# ---------------------------------------------------------------- 요약
def _q(s, q):
    s = pd.Series(s).dropna()
    return float(s.quantile(q)) if len(s) else float("nan")


def summarize(masks: dict, index_long: pd.DataFrame, seq_len: int, primary: str = "theta_primary") -> list[str]:
    """masks = {theta_name: DataFrame}. 마크다운 라인 목록을 반환."""
    L = ["# Phase D — 평가용 indeterminate 마스크 요약", "",
         "cycle 단위 평가에서 '최종 1→0 전이 이후 재진입 없는 구간' 을 채점에서 제외한다.",
         "그 구간의 라벨 0 은 정직하지만 에이전트는 clean 예측을 볼 수 없어 δ 소멸을 관측할 수 없다.",
         "**라벨 파일은 바꾸지 않는다.** 마스크 적용을 주 결과, 미적용을 부록으로 둘 다 보고할 것.", ""]

    # 1. θ 별 전체 규모
    L += ["## 1. θ 별 마스크 규모", ""]
    rows = []
    for name, mk in masks.items():
        idx = index_long[index_long["theta_name"] == name]
        deg = idx[idx["degraded"].astype(bool)]
        dkeys = set(zip(deg["unit"].astype(int), deg["scenario_id"]))
        mk_d = mk[[(u, s) in dkeys for u, s in zip(mk["unit"], mk["scenario_id"])]]
        has = mk["mask_from_cycle"].notna()
        n_eval_all = int((mk["T_u"] - (seq_len - 1)).sum())
        n_eval_deg = int((mk_d["T_u"] - (seq_len - 1)).sum())
        rows.append({
            "theta": name,
            "마스크 시나리오": int(has.sum()),
            "전체 대비": float(has.mean()),
            "저하 시나리오 n": len(mk_d),
            "저하 대비": float(mk_d["mask_from_cycle"].notna().mean()) if len(mk_d) else np.nan,
            "마스크 cycle": int(mk["n_masked_cycles"].sum()),
            "전체 cycle 대비": mk["n_masked_cycles"].sum() / max(1, n_eval_all),
            "저하 cycle 대비": mk_d["n_masked_cycles"].sum() / max(1, n_eval_deg) if n_eval_deg else np.nan,
        })
    L += [md_table(rows, fmt="{:.4g}"), "",
          f"평가 대상 cycle 은 시나리오당 T_u − {seq_len - 1} (예측이 시작되는 cycle {seq_len} 부터).", ""]

    mk = masks[primary]
    has = mk[mk["mask_from_cycle"].notna()]

    # 2. 유형별
    L += [f"## 2. 유형별 마스크 비율 ({primary})", ""]
    rows = []
    for t in sorted(mk["type"].unique()):
        g = mk[mk["type"] == t]
        gh = g[g["mask_from_cycle"].notna()]
        n_eval = int((g["T_u"] - (seq_len - 1)).sum())
        rows.append({"type": t, "시나리오 n": len(g), "마스크 n": len(gh),
                     "시나리오 비율": len(gh) / max(1, len(g)),
                     "cycle 비율": g["n_masked_cycles"].sum() / max(1, n_eval),
                     "frac_masked median": _q(gh["frac_masked"], 0.5)})
    L += [md_table(rows, fmt="{:.3f}"), ""]

    # 3. 시점별
    L += [f"## 3. 시점(timing_p)별 마스크 비율 ({primary})", ""]
    rows = []
    for p in sorted(mk["timing_p"].unique()):
        g = mk[mk["timing_p"] == p]
        gh = g[g["mask_from_cycle"].notna()]
        n_eval = int((g["T_u"] - (seq_len - 1)).sum())
        rows.append({"timing_p": p, "시나리오 n": len(g), "마스크 n": len(gh),
                     "시나리오 비율": len(gh) / max(1, len(g)),
                     "cycle 비율": g["n_masked_cycles"].sum() / max(1, n_eval)})
    L += [md_table(rows, fmt="{:.3f}"), ""]

    # 4. 시작 위치 분포
    L += [f"## 4. mask_from_cycle / T_u 분포 ({primary})", ""]
    pos = (has["mask_from_cycle"] / has["T_u"]).dropna()
    rows = [{"구간": "전체 마스크", "n": len(pos), "p10": _q(pos, .10), "p50": _q(pos, .50), "p90": _q(pos, .90)}]
    for t in sorted(has["type"].unique()):
        g = has[has["type"] == t]
        pp = (g["mask_from_cycle"] / g["T_u"]).dropna()
        rows.append({"구간": t, "n": len(pp), "p10": _q(pp, .10), "p50": _q(pp, .50), "p90": _q(pp, .90)})
    L += [md_table(rows, fmt="{:.3f}"), ""]

    L += ["## 5. 사용법", "",
          "```python",
          "mask = pd.read_csv('labels/FD001/meta/eval_mask.csv')",
          "m = mask.set_index(['unit', 'scenario_id'])['mask_from_cycle']",
          "start = m.get((unit, scenario_id))",
          "keep = state['time'] < start if pd.notna(start) else slice(None)   # 채점 대상 cycle",
          "```", ""]
    return L


def write_report(paths, masks: dict, index_long: pd.DataFrame, seq_len: int,
                 primary: str = "theta_primary") -> Path:
    out = paths.reports_dir / "D_eval_mask_summary.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(summarize(masks, index_long, seq_len, primary)) + "\n", encoding="utf-8")
    return out
