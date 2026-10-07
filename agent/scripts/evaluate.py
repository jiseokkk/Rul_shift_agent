"""run 채점 (시나리오 단위 v2, docs/eval_v2_scenario.md).

  python agent/scripts/evaluate.py --run-id <id>        (또는 --latest)
  python agent/scripts/evaluate.py --latest --theta theta_alt1 --n-boot 0     # θ 대안, CI 생략
  python agent/scripts/evaluate.py --latest --v1                              # v1 cycle 단위 채점도 → eval_v1/
"""
from __future__ import annotations

import argparse
import json

from _bootstrap import AGENT, load_cfg
from src.eval.report import evaluate_run


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--latest", action="store_true")
    ap.add_argument("--theta", default=None)
    ap.add_argument("--n-boot", type=int, default=None, help="unit bootstrap 횟수 (0 = 생략). 기본 configs/agent.yaml eval.n_boot")
    ap.add_argument("--v1", action="store_true", help="legacy v1 (cycle + unit 단위) 채점도 실행")
    a = ap.parse_args()
    acfg = load_cfg("agent")
    runs = AGENT / "runs"
    if a.latest or not a.run_id:
        cands = sorted([p for p in runs.iterdir() if (p / "decisions.csv").exists()], key=lambda p: p.stat().st_mtime)
        run_dir = cands[-1]
    else:
        run_dir = runs / a.run_id
    res = evaluate_run(run_dir, acfg, a.theta, a.n_boot)
    print(json.dumps({"config": res["config"], "metrics": res["metrics"]}, indent=1, default=str, ensure_ascii=False))
    print(f"→ {res['report']}")
    if a.v1:
        from src.eval.legacy_v1 import evaluate_run_v1
        r1 = evaluate_run_v1(run_dir, acfg, a.theta or acfg.get("theta_name", "theta_primary"))
        print(f"→ v1: {r1['report']}")


if __name__ == "__main__":
    main()
