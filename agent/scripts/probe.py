"""속도·토큰 probe: 실제 프롬프트 n개를 동시 실행 수별로 보내 호출당 시간, 토큰, reasoning 토큰, 비용을 잰다. 캐시를 쓰지 않는다.

  python agent/scripts/probe.py --n 20 --concurrency 1 4
  python agent/scripts/probe.py --n 20 --concurrency 1 4 --llm llm_openrouter     # OpenRouter. reasoning_tokens 가 0 인지 확인
"""
from __future__ import annotations

import argparse
import time
from concurrent.futures import ThreadPoolExecutor

from _bootstrap import AGENT, load_cfg
from src.data.inputs import SENSORS, load_scenario, load_scenario_list
from src.llm.client import LLMClient
from src.llm.prompts import build_input, system_prompt
from src.tools.rul_tool import RULTool
from src.tools.sensor_tool import SensorTool


def make_prompts(n: int, acfg: dict) -> list[tuple[str, str]]:
    scen = load_scenario_list("pilot_scenarios").iloc[0]
    sc = load_scenario(int(scen.unit), scen.scenario_id)
    st = SensorTool(SENSORS, acfg["resolution"], acfg["N"], acfg["short_history"])
    rt = RULTool(acfg["N"], acfg["rul_mad_floor"], acfg["mc_std_floor"])
    system = system_prompt()
    out = []
    for t in range(1, sc.T_u + 1):
        st.observe(t, sc.sensors.loc[t].to_dict())
        if t >= acfg["seq_len"]:
            rt.observe(t, float(sc.y_hat.loc[t]), sc.mc.loc[t].to_numpy())
        if t >= acfg["judge_from"]:
            out.append((system, build_input(int(scen.unit), t, st.summary(), rt.summary(), acfg["seq_len"])))
        if len(out) >= n:
            break
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--concurrency", type=int, nargs="*", default=[1, 4])
    ap.add_argument("--llm", default="llm", help="configs/{name}.yaml")
    a = ap.parse_args()
    acfg, lcfg = load_cfg("agent"), load_cfg(a.llm)
    client = LLMClient(lcfg)
    models = client.list_models()
    print("models:", models if len(models) <= 20 else f"{len(models)}개 (model={lcfg['model']} 포함: {lcfg['model'] in models})")
    prompts = make_prompts(a.n, acfg)
    print(f"prompt chars ≈ {len(prompts[0][0]) + len(prompts[0][1])}")
    for c in a.concurrency:
        t0 = time.time()
        with ThreadPoolExecutor(max_workers=c) as ex:
            outs = list(ex.map(lambda p: client.decide(*p), prompts))
        el = time.time() - t0
        lat = [o["latency_ms"] / 1000 for o in outs]
        err = sum(1 for o in outs if o["error"])
        tok = [o.get("prompt_tokens") for o in outs if o.get("prompt_tokens")]
        comp = [o.get("completion_tokens") or 0 for o in outs]
        reas = [o.get("reasoning_tokens") or 0 for o in outs]
        cost = [o.get("cost") or 0.0 for o in outs]
        print(f"concurrency {c}: {len(prompts)} calls in {el:.0f}s → {el / len(prompts):.1f}s/call wall, "
              f"latency mean {sum(lat) / len(lat):.1f}s, errors {err}, prompt_tokens ≈ {tok[0] if tok else '?'}, "
              f"completion mean {sum(comp) / len(comp):.0f}, reasoning mean {sum(reas) / len(reas):.0f}, "
              f"cost sum ${sum(cost):.4f}" + (" (usage.cost 미반환)" if not any(cost) else ""))
        for o in outs:
            if o["error"]:
                print("  error:", o["error"][:200])
    d = outs[-1]["decision"]
    print("sample decision:", d.model_dump() if d else outs[-1]["error"])


if __name__ == "__main__":
    main()
