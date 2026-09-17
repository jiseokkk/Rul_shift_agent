"""run 채점.  python agent/scripts/evaluate.py --run-id <id>   (또는 --latest)"""
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
    a = ap.parse_args()
    acfg = load_cfg("agent")
    runs = AGENT / "runs"
    if a.latest or not a.run_id:
        cands = sorted([p for p in runs.iterdir() if (p / "decisions.csv").exists()], key=lambda p: p.stat().st_mtime)
        run_dir = cands[-1]
    else:
        run_dir = runs / a.run_id
    res = evaluate_run(run_dir, acfg, a.theta or acfg.get("theta_name", "theta_primary"))
    print(json.dumps({"cycle": res["cycle"], "unit": res["unit"]}, indent=1, default=str))
    print(f"→ {res['report']}")


if __name__ == "__main__":
    main()
