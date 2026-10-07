"""시나리오 목록 CSV 에 end_cycle 열을 넣는다 (판정 절단, docs/eval_v2_scenario.md §3.5).

  python agent/scripts/add_end_cycle.py --scenarios sample_or500 pilot_scenarios

end_cycle = 저하 τ_d + Δ, 비저하 τ_s + H (configs/agent.yaml eval), 수명 T_u 안으로. 채점 쪽(truth)에서 계산하고,
runner 는 이 숫자만 읽어 그 cycle 에서 스트림을 끝낸다. 프롬프트·캐시 키는 바뀌지 않는다.
Δ 또는 H 를 바꾸면 다시 돌려야 한다 (기존 열은 덮어쓴다).
"""
from __future__ import annotations

import argparse

import pandas as pd

from _bootstrap import AGENT, load_cfg
from src.data.truth import load_index
from src.eval.scenario_table import end_cycles


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenarios", nargs="+", required=True, help="configs/{name}.csv 이름들")
    a = ap.parse_args()
    acfg = load_cfg("agent")
    e = acfg["eval"]
    idx = load_index(theta_name=acfg.get("theta_name", "theta_primary"))
    E = end_cycles(idx, int(e["Delta"]), int(e["H"]))
    for name in a.scenarios:
        p = AGENT / "configs" / f"{name}.csv"
        df = pd.read_csv(p).drop(columns=["end_cycle"], errors="ignore")
        out = df.merge(E, on=["unit", "scenario_id"], how="left")
        assert out["end_cycle"].notna().all(), f"{name}: scenario_index 에 없는 시나리오가 있다"
        out.to_csv(p, index=False)
        T_u = out["T_u"] if "T_u" in out else None
        saved = f", 판정 cycle {int((out['end_cycle'] - acfg['judge_from'] + 1).clip(lower=0).sum()):,} / {int((T_u - acfg['judge_from'] + 1).sum()):,}" if T_u is not None else ""
        print(f"→ {p}  ({len(out)} 시나리오, Δ={e['Delta']}, H={e['H']}{saved})")


if __name__ == "__main__":
    main()
