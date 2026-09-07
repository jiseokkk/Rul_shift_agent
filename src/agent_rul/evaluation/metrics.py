"""평가 지표 + Sensitivity (설계서 13).

    Precision = TP/(TP+FP), Recall = TP/(TP+FN), F1
    MDD       = TP 들의 평균 지연 d
    LateRate  = Late 수 / faulty trajectory 수
    FailRate  = 판정 실패 cycle / 평가 cycle
    FAR_1000  = FP / clean monitored cycles * 1000

Sensitivity 는 추가 LLM 호출 없이 판정 결과만 재해석한다:
    1) Detection Tolerance D ∈ {3,5,10}
    2) 검사 주기 S ∈ {1,2,3,5} — Agent 입력은 검사 주기와 무관하므로 S=1 판정을 S 간격으로 subsampling
"""
from __future__ import annotations

import numpy as np

from .classify import ScenarioResult, classify_all, clean_monitored_cycles, fail_cycles, to_events


def _f1(p: float, r: float) -> float:
    return 0.0 if (p + r) == 0 else 2 * p * r / (p + r)


def aggregate(results: list[ScenarioResult], clean_monitored: int) -> dict:
    tp = sum(r.tp for r in results)
    fp = sum(r.fp for r in results)
    fn = sum(r.fn for r in results)
    tn = sum(r.tn for r in results)
    n_faulty = sum(1 for r in results if r.is_faulty)
    n_late = sum(1 for r in results if r.late)
    delays = [r.delay for r in results if r.tp and r.delay is not None]
    n_fail = sum(r.n_fail_cycles for r in results)
    n_eval = sum(r.n_eval_cycles for r in results)

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    return {
        "TP": tp, "FP": fp, "FN": fn, "TN": tn,
        "n_scenarios": len(results), "n_faulty": n_faulty,
        "precision": precision, "recall": recall, "f1": _f1(precision, recall),
        "MDD": float(np.mean(delays)) if delays else float("nan"),
        "delays": delays,
        "n_late": n_late,
        "late_rate": (n_late / n_faulty) if n_faulty else float("nan"),
        "n_fail_cycles": n_fail, "n_eval_cycles": n_eval,
        "fail_rate": (n_fail / n_eval) if n_eval else float("nan"),
        "clean_monitored_cycles": clean_monitored,
        "FAR_1000": (fp / clean_monitored * 1000) if clean_monitored else float("nan"),
    }


def by_severity(results: list[ScenarioResult], clean_monitored: int) -> dict:
    """alpha 별 지표. clean 은 alpha=0 그룹. FAR 분모는 전체 clean monitored 를 그대로 쓴다."""
    out = {}
    for a in sorted({r.alpha for r in results}):
        grp = [r for r in results if r.alpha == a]
        out[f"alpha={a:g}"] = aggregate(grp, clean_monitored)
    return out


def per_scenario_rows(results: list[ScenarioResult]) -> list[dict]:
    return [{
        "scenario_id": r.scenario_id, "is_faulty": r.is_faulty, "alpha": r.alpha,
        "t_f": r.t_f, "TP": r.tp, "FP": r.fp, "FN": r.fn, "TN": r.tn,
        "late": r.late, "delay": r.delay, "n_events": r.n_events,
        "n_fail_cycles": r.n_fail_cycles, "n_eval_cycles": r.n_eval_cycles,
        "notes": ";".join(r.notes),
    } for r in results]


def summarize_runs(run_metrics: list[dict],
                   keys=("f1", "precision", "recall", "MDD", "FAR_1000", "fail_rate")) -> dict:
    """반복 3회 평균 ± 표준편차 (설계서 13 '반복 실험')."""
    out = {}
    for k in keys:
        vals = [m[k] for m in run_metrics if m.get(k) is not None
                and not (isinstance(m[k], float) and np.isnan(m[k]))]
        if vals:
            out[k] = {"mean": float(np.mean(vals)), "std": float(np.std(vals)),
                      "n_runs": len(vals), "values": [float(v) for v in vals]}
    return out


# =========================================================================== #
# Sensitivity
# =========================================================================== #
def subsample_decisions(decisions: list[dict], S: int, warm_up: int) -> list[dict]:
    """검사 주기 S 로 판정한 것처럼 cycle 을 골라낸다 (첫 판정 cycle warm_up+1 부터 S 간격)."""
    if S <= 1:
        return list(decisions)
    rows = sorted(decisions, key=lambda r: int(r["cycle"]))
    start = warm_up + 1
    return [r for r in rows if (int(r["cycle"]) - start) % S == 0]


def _run(per_scenario: dict[str, list[dict]], gts: dict[str, dict], D: int,
         warm_up: int, cycle_counts: dict[str, int], S: int = 1) -> dict:
    events, fails, evals = {}, {}, {}
    for sid, rows in per_scenario.items():
        sub = subsample_decisions(rows, S, warm_up)
        events[sid] = to_events(sub)
        fails[sid] = len(fail_cycles(sub))
        evals[sid] = len(sub)
    res = classify_all(events, gts, D, fails, evals)
    clean_mon = clean_monitored_cycles(gts, cycle_counts, warm_up)
    if S > 1:                      # 판정 기회가 1/S 로 줄어든 만큼 분모도 줄인다
        clean_mon = max(1, clean_mon // S)
    return aggregate(res, clean_mon)


def tolerance_sweep(per_scenario, gts, D_list, warm_up: int, cycle_counts) -> dict:
    return {f"D={D}": _run(per_scenario, gts, D, warm_up, cycle_counts, S=1) for D in D_list}


def period_sweep(per_scenario, gts, S_list, D: int, warm_up: int, cycle_counts) -> dict:
    return {f"S={S}": _run(per_scenario, gts, D, warm_up, cycle_counts, S=S) for S in S_list}
