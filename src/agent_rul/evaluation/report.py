"""평가 실행 (CLI `evaluate`) 과 반복 집계 리포트 (CLI `report`) — 설계서 12, 13.

evaluate_run : results/{run_id}/decisions.csv + GT → metrics.json, sensitivity.json,
               per_scenario.csv, decisions_labeled.csv (true_rul / life_fraction 채운 판정 로그)
build_report : 여러 run 의 metrics.json → 평균±표준편차, severity 표, life_fraction 별 FP,
               sensitivity 평균 → results/report_{tag}.json

여기와 gt.py 만 GT 를 읽는다 (CLAUDE.md 규칙 2). 판정 결과만 읽으므로 규칙을 바꿔도 LLM 재호출이 없다.
"""
from __future__ import annotations

import os
from collections import defaultdict

from .. import data
from ..utils import read_csv, read_json, write_csv, write_json
from . import classify, gt as gt_mod, metrics


def latest_run(cfg) -> str:
    root = cfg.paths.results_root
    runs = [d for d in os.listdir(root) if os.path.exists(cfg.paths.decisions_csv(d))]
    if not runs:
        raise SystemExit("decisions.csv 가 있는 run 이 없다 (`run` 을 먼저 실행)")
    return max(runs, key=lambda d: os.path.getmtime(cfg.paths.decisions_csv(d)))


# =========================================================================== #
# evaluate
# =========================================================================== #
def evaluate_run(cfg, run_id: str, D: int | None = None, verbose: bool = True) -> dict:
    D = int(cfg.exp.evaluation["D"]) if D is None else int(D)
    warm = cfg.warm_up
    say = print if verbose else (lambda *a, **k: None)
    say(f"[evaluate] run_id={run_id}  D={D}  warm_up={warm}")

    rows = read_csv(cfg.paths.decisions_csv(run_id))
    per_scenario: dict[str, list[dict]] = {}
    for r in rows:
        r["cycle"] = int(r["cycle"])
        per_scenario.setdefault(r["scenario_id"], []).append(r)

    # ---- GT (여기서 처음 읽는다) --------------------------------------------
    manifest = gt_mod.load_manifest(cfg.paths.manifest_csv)
    gts, cycle_counts, truls = {}, {}, {}
    for sid in per_scenario:
        gts[sid] = gt_mod.scenario_gt(manifest, sid)
        cycle_counts[sid] = len(data.load_scenario(cfg.paths.corrupted_root, sid)["cycles"])
        truls[sid] = gt_mod.true_rul(cfg.paths.corrupted_root, manifest, sid)

    # ---- 분류 & 지표 -------------------------------------------------------
    events = {sid: classify.to_events(rs) for sid, rs in per_scenario.items()}
    fails = {sid: len(classify.fail_cycles(rs)) for sid, rs in per_scenario.items()}
    evals = {sid: len(rs) for sid, rs in per_scenario.items()}
    results = classify.classify_all(events, gts, D, fails, evals)
    clean_mon = classify.clean_monitored_cycles(gts, cycle_counts, warm)

    m = metrics.aggregate(results, clean_mon)
    m_sev = metrics.by_severity(results, clean_mon)
    payload = {"run_id": run_id, "D": D, "warm_up": warm, "overall": m, "by_severity": m_sev,
               "scenarios": {sid: {"n_events": len(ev), "events": [(e.onset, e.end) for e in ev]}
                             for sid, ev in events.items()}}
    write_json(cfg.paths.metrics_json(run_id), payload)

    sens = {
        "tolerance": metrics.tolerance_sweep(per_scenario, gts, list(cfg.exp.evaluation["D_sweep"]),
                                             warm, cycle_counts),
        "period": metrics.period_sweep(per_scenario, gts, list(cfg.exp.evaluation["S_sweep"]),
                                       D, warm, cycle_counts),
    }
    write_json(cfg.paths.sensitivity_json(run_id), sens)
    write_csv(cfg.paths.per_scenario_csv(run_id), metrics.per_scenario_rows(results))

    # ---- 판정 로그에 GT 열 채우기 -----------------------------------------
    for r in rows:
        sid = r["scenario_id"]
        r["true_rul"] = truls[sid].get(r["cycle"], "")
        r["life_fraction"] = round(gt_mod.life_fraction(r["cycle"], gts[sid]["life_cycles"]), 4)
    write_csv(cfg.paths.decisions_labeled_csv(run_id), rows)

    say(f"  TP={m['TP']} FP={m['FP']} FN={m['FN']} TN={m['TN']}  "
        f"P={m['precision']:.3f} R={m['recall']:.3f} F1={m['f1']:.3f}")
    say(f"  MDD={m['MDD']:.2f}  LateRate={m['late_rate']:.3f}  FailRate={m['fail_rate']:.3f}  "
        f"FAR_1000={m['FAR_1000']:.1f} (clean monitored {clean_mon} cycles)")
    for k, v in m_sev.items():
        say(f"  {k:>12s}: TP={v['TP']} FP={v['FP']} FN={v['FN']} F1={v['f1']:.3f} MDD={v['MDD']:.2f}")
    say(f"[evaluate] → {cfg.paths.run_dir(run_id)}/metrics.json, sensitivity.json, per_scenario.csv")
    return payload


# =========================================================================== #
# report
# =========================================================================== #
def _load_runs(cfg, run_ids: list[str] | None) -> list[dict]:
    root = cfg.paths.results_root
    if run_ids is None:
        run_ids = sorted(d for d in os.listdir(root) if os.path.exists(cfg.paths.metrics_json(d)))
    return [{"run_id": rid, **read_json(cfg.paths.metrics_json(rid))} for rid in run_ids]


def fp_by_life_fraction(cfg, run_ids: list[str], bins: int = 5) -> dict:
    """열화 구간별 FAULT 판정 분포 (설계서 4장 리스크: 후기 구간 FP 남발 확인).

    decisions_labeled.csv 에는 t_f 가 없으므로 clean 시나리오(true FP 만 발생)만 집계한다.
    """
    counts = defaultdict(lambda: {"n": 0, "fault": 0})
    for rid in run_ids:
        p = cfg.paths.decisions_labeled_csv(rid)
        if not os.path.exists(p):
            continue
        for r in read_csv(p):
            if not r["scenario_id"].startswith("ctrl"):
                continue
            try:
                lf = float(r["life_fraction"])
            except (TypeError, ValueError):
                continue
            b = min(int(lf * bins), bins - 1)
            label = f"{b / bins:.1f}-{(b + 1) / bins:.1f}"
            counts[label]["n"] += 1
            counts[label]["fault"] += int(r["sensor_status"] == "FAULT")
    return {k: {**v, "fault_rate": (v["fault"] / v["n"] if v["n"] else 0.0)}
            for k, v in sorted(counts.items())}


def build_report(cfg, run_ids: list[str] | None = None, tag: str = "latest",
                 verbose: bool = True) -> dict:
    say = print if verbose else (lambda *a, **k: None)
    runs = _load_runs(cfg, run_ids)
    if not runs:
        raise SystemExit("metrics.json 이 있는 run 이 없다 (`evaluate` 를 먼저 실행)")
    ids = [r["run_id"] for r in runs]
    say(f"[report] runs: {ids}")

    summ = metrics.summarize_runs([r["overall"] for r in runs])
    say(f"\n=== 전체 (평균 ± 표준편차, n={len(runs)}) ===")
    for k, v in summ.items():
        say(f"  {k:>10s}: {v['mean']:.3f} ± {v['std']:.3f}   {v['values']}")

    sev_keys = sorted({k for r in runs for k in r["by_severity"]})
    say("\n=== Severity 별 ===")
    say(f"  {'alpha':>12s} {'TP':>4s} {'FP':>4s} {'FN':>4s} {'F1':>8s} {'MDD':>7s}")
    sev_out = {}
    for sk in sev_keys:
        grp = [r["by_severity"][sk] for r in runs if sk in r["by_severity"]]
        sev_out[sk] = metrics.summarize_runs(grp, keys=("f1", "MDD", "recall"))
        tp = sum(g["TP"] for g in grp) / len(grp)
        fp = sum(g["FP"] for g in grp) / len(grp)
        fn = sum(g["FN"] for g in grp) / len(grp)
        f1 = sev_out[sk].get("f1", {}).get("mean", float("nan"))
        mdd = sev_out[sk].get("MDD", {}).get("mean", float("nan"))
        say(f"  {sk:>12s} {tp:4.1f} {fp:4.1f} {fn:4.1f} {f1:8.3f} {mdd:7.2f}")

    fp_dist = fp_by_life_fraction(cfg, ids)
    if fp_dist:
        say("\n=== clean 시나리오 FAULT 판정률 (life_fraction 구간별) ===")
        for k, v in fp_dist.items():
            say(f"  {k:>10s}: {v['fault']:3d}/{v['n']:3d} = {v['fault_rate']:.3f}")

    sens_avg: dict = {}
    for rid in ids:
        p = cfg.paths.sensitivity_json(rid)
        if not os.path.exists(p):
            continue
        for group, d in read_json(p).items():
            for k, m in d.items():
                sens_avg.setdefault(group, {}).setdefault(k, []).append(m)
    sens_out = {g: {k: metrics.summarize_runs(v, keys=("f1", "recall", "MDD"))
                    for k, v in d.items()} for g, d in sens_avg.items()}
    if sens_out:
        say("\n=== Sensitivity ===")
        for g, d in sens_out.items():
            for k, v in d.items():
                say(f"  {g:>10s} {k:>6s}: F1={v.get('f1', {}).get('mean', float('nan')):.3f} "
                    f"R={v.get('recall', {}).get('mean', float('nan')):.3f} "
                    f"MDD={v.get('MDD', {}).get('mean', float('nan')):.2f}")

    out = {"runs": ids, "overall": summ, "by_severity": sev_out,
           "fp_by_life_fraction": fp_dist, "sensitivity": sens_out}
    path = write_json(cfg.paths.report_json(tag), out)
    say(f"\n[report] → {path}")
    return out
