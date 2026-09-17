"""스트림 판정 실행.

  python agent/scripts/run.py --scenarios pilot_scenarios --dry-run          # LLM 없이 프롬프트·stats 만
  python agent/scripts/run.py --scenarios pilot_scenarios --tag pilot        # 본 실행 (vLLM 서버 필요)
  python agent/scripts/run.py --scenarios pilot_scenarios --units 57 --tag u57   # 일부 unit 만
  python agent/scripts/run.py ... --concurrency 8
"""
from __future__ import annotations

import argparse

from _bootstrap import AGENT, load_cfg
from src.data.inputs import load_scenario_list
from src.runner.record import make_run_id
from src.runner.stream import run


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenarios", default="pilot_scenarios", help="configs/{name}.csv 또는 경로")
    ap.add_argument("--units", type=int, nargs="*", default=None)
    ap.add_argument("--limit", type=int, default=None, help="시나리오 앞 n개만")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--concurrency", type=int, default=None)
    ap.add_argument("--tag", default="run")
    ap.add_argument("--run-id", default=None)
    a = ap.parse_args()

    acfg, lcfg = load_cfg("agent"), load_cfg("llm")
    scen = load_scenario_list(a.scenarios)
    if a.units:
        scen = scen[scen["unit"].isin(a.units)]
    if a.limit:
        scen = scen.head(a.limit)
    run_id = a.run_id or make_run_id(lcfg["model"], a.tag + ("_dry" if a.dry_run else ""), int(lcfg.get("seed", 42)))
    out = run(scen.reset_index(drop=True), acfg, lcfg, run_id, AGENT / "runs", dry_run=a.dry_run,
              concurrency=a.concurrency, tag=a.tag)
    print(f"→ {out}")


if __name__ == "__main__":
    main()
