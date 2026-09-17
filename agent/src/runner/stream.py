"""스트림 실행: 시나리오 하나를 cycle 순서대로 흘려 넣고 judge_from 부터 매 cycle 판정.

도구는 도착한 cycle 까지만 안다. LLM 은 build_input 결과만 본다. 시나리오 id·τ_s·라벨은 여기서 읽지 않는다.
"""
from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd

from src.data.inputs import AGENT_ROOT, SENSORS, load_scenario
from src.llm.prompts import build_input, system_prompt
from src.runner.cache import DecisionCache, prompt_hash
from src.runner.record import RunRecorder
from src.tools.rul_tool import RULTool
from src.tools.sensor_tool import SensorTool


def run_scenario(unit: int, sid: str, acfg: dict, system: str, client, cache: DecisionCache | None,
                 rec: RunRecorder, run_id: str, dry_run: bool, save_stats: bool = True) -> list[dict]:
    sc = load_scenario(unit, sid)
    st = SensorTool(SENSORS, acfg["resolution"], acfg["N"], acfg["short_history"])
    rt = RULTool(acfg["N"], acfg["rul_mad_floor"], acfg["mc_std_floor"])
    seq_len, judge_from = int(acfg["seq_len"]), int(acfg["judge_from"])
    rows, sensor_stats, rul_stats = [], [], []
    for t in range(1, sc.T_u + 1):
        st.observe(t, sc.sensors.loc[t].to_dict())
        if t >= seq_len:
            rt.observe(t, float(sc.y_hat.loc[t]), sc.mc.loc[t].to_numpy())
        if t < judge_from:
            continue
        ssum, rsum = st.summary(), rt.summary()
        if save_stats:
            sensor_stats.extend(st.stats_row())
            rul_stats.append(rt.stats_row())
        user = build_input(unit, t, ssum, rsum, seq_len)
        key = prompt_hash(system, user)
        rec.save_prompt(unit, sid, t, system, user)
        base = {"run_id": run_id, "unit": unit, "scenario_id": sid, "cycle": t, "prompt_hash": key}
        if dry_run:
            rows.append({**base, "degraded": np.nan, "suspected_sensors": "[]", "confidence": np.nan, "rationale": "", "flags": "[\"DRY\"]",
                         "n_retries": 0, "latency_ms": 0, "prompt_tokens": None, "completion_tokens": None, "cache_hit": False, "error": None})
            continue
        hit = cache.get(key) if cache is not None else None
        if hit is None:
            out = client.decide(system, user)
            d = out["decision"]
            hit = {"degraded": d.degraded if d else None, "suspected_sensors": d.suspected_sensors if d else [],
                   "confidence": d.confidence if d else None, "rationale": d.rationale if d else "", "flags": out["flags"],
                   "n_retries": out["n_retries"], "latency_ms": out["latency_ms"], "prompt_tokens": out.get("prompt_tokens"),
                   "completion_tokens": out.get("completion_tokens"), "error": out["error"], "raw": out["raw"]}
            if cache is not None and hit["error"] is None:
                cache.put(key, hit)
            cache_hit = False
        else:
            cache_hit = True
        rows.append({**base, "degraded": hit["degraded"], "suspected_sensors": json.dumps(hit["suspected_sensors"]),
                     "confidence": hit["confidence"], "rationale": hit["rationale"], "flags": json.dumps(hit["flags"]),
                     "n_retries": hit["n_retries"], "latency_ms": hit["latency_ms"], "prompt_tokens": hit.get("prompt_tokens"),
                     "completion_tokens": hit.get("completion_tokens"), "cache_hit": cache_hit, "error": hit["error"]})
    if save_stats:
        rec.save_stats(unit, sid, sensor_stats, rul_stats)
    return rows


def run(scenarios: pd.DataFrame, acfg: dict, lcfg: dict, run_id: str, runs_dir: Path, dry_run: bool = False,
        concurrency: int | None = None, tag: str = "") -> Path:
    rec = RunRecorder(runs_dir, run_id)
    rec.snapshot(agent=acfg, llm=lcfg, run={"run_id": run_id, "dry_run": dry_run, "tag": tag, "n_scenarios": int(len(scenarios))})
    system = system_prompt()
    client = cache = None
    if not dry_run:
        from src.llm.client import LLMClient
        client = LLMClient(lcfg)
        cache = DecisionCache(AGENT_ROOT / "artifacts" / "cache" / "decisions", lcfg["model"], int(lcfg.get("seed", 42)))
    nconc = int(concurrency or lcfg.get("concurrency", 4)) if not dry_run else 1
    rec.log(f"run {run_id}: {len(scenarios)} scenarios, dry_run={dry_run}, concurrency={nconc}")
    all_rows, t0 = [], time.time()
    todo = list(scenarios.itertuples(index=False))
    with ThreadPoolExecutor(max_workers=nconc) as ex:
        futs = {ex.submit(run_scenario, int(r.unit), r.scenario_id, acfg, system, client, cache, rec, run_id, dry_run): r
                for r in todo}
        for i, f in enumerate(as_completed(futs), 1):
            r = futs[f]
            try:
                rows = f.result()
            except Exception as e:  # 한 시나리오 실패가 전체를 멈추지 않게
                rec.log(f"  FAIL u{r.unit} {r.scenario_id}: {type(e).__name__}: {e}")
                continue
            all_rows.extend(rows)
            n_err = sum(1 for x in rows if x.get("error"))
            n_hit = sum(1 for x in rows if x.get("cache_hit"))
            rec.log(f"  [{i}/{len(todo)}] u{r.unit} {r.scenario_id}: {len(rows)} cycles, cache {n_hit}, error {n_err}, "
                    f"elapsed {(time.time() - t0) / 60:.1f} min")
            if i % 5 == 0:  # 중간에 꺼도 결과가 남게 주기적으로 저장 (완료 시나리오만 포함)
                rec.save_decisions(all_rows)
    out = rec.save_decisions(all_rows)
    df = pd.DataFrame(all_rows)
    summary = {"n_scenarios": int(len(scenarios)), "n_decisions": int(len(df)),
               "n_llm_calls": int((~df["cache_hit"].astype(bool)).sum()) if len(df) and not dry_run else 0,
               "n_errors": int(df["error"].notna().sum()) if len(df) else 0,
               "mean_latency_ms": float(df.loc[~df["cache_hit"].astype(bool), "latency_ms"].mean()) if len(df) and not dry_run else None,
               "elapsed_min": (time.time() - t0) / 60}
    rec.save_summary(summary)
    rec.log(f"done: {summary}")
    return out
