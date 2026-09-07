"""LangGraph 고정 DAG + post_check (설계서 2.1, 10.2 / agent_spec §2).

    START ──┬── eda_node ──┬── build_input ── reason ── post_check ── END
            └── rul_node ──┘

eda_node / rul_node 는 Tool 의 이력에서 현재 cycle 의 evidence / context 를 꺼낸다.
LLM 은 reason 노드에서 1회만 호출되고, **tool 호출 여부를 LLM 이 결정하지 않는다**.

post_check (agent_spec §2 표):
    FAULT ↔ WARNING 불일치            reliability 를 status 에 맞춰 덮어씀, 플래그
    NORMAL 인데 suspected 비어있지 않음  리스트 비움, 플래그
    FAULT 인데 suspected 비어있음        유지, isolation_missing 플래그
    suspected 에 실제 센서 이름이 아닌 값  제거, 플래그
    파싱 실패                          llm.py 에서 재시도 → ERROR
플래그는 decisions.csv 의 post_check_flags 컬럼에 ';' 로 join 해 남긴다.
"""
from __future__ import annotations

from typing import Annotated, Any, TypedDict

from . import prompts
from .schema import Decision

FLAG_RELIABILITY = "reliability_mismatch"
FLAG_SUSPECTED_ON_NORMAL = "suspected_on_normal"
FLAG_ISOLATION_MISSING = "isolation_missing"
FLAG_UNKNOWN_SENSOR = "unknown_sensor"
FLAG_PATTERN_ON_NORMAL = "pattern_on_normal"


# --------------------------------------------------------------------------- #
# post_check
# --------------------------------------------------------------------------- #
def post_check(dec: Decision, valid_sensors: list[str]) -> tuple[Decision, list[str]]:
    """(보정된 Decision, 플래그 목록). 원본은 수정하지 않는다."""
    d = dec.model_copy(deep=True)
    flags: list[str] = []
    valid = set(valid_sensors)

    unknown = [s for s in d.suspected_sensors if s not in valid]
    if unknown:
        d.suspected_sensors = [s for s in d.suspected_sensors if s in valid]
        flags.append(f"{FLAG_UNKNOWN_SENSOR}:{','.join(unknown)}")

    if d.sensor_status == "NORMAL" and d.suspected_sensors:
        d.suspected_sensors = []
        flags.append(FLAG_SUSPECTED_ON_NORMAL)

    if d.sensor_status == "FAULT" and not d.suspected_sensors:
        flags.append(FLAG_ISOLATION_MISSING)

    want = "WARNING" if d.sensor_status == "FAULT" else "RELIABLE"
    if d.rul_reliability != want:
        d.rul_reliability = want
        flags.append(FLAG_RELIABILITY)

    if d.sensor_status == "NORMAL" and d.fault_pattern != "NONE":
        flags.append(f"{FLAG_PATTERN_ON_NORMAL}:{d.fault_pattern}")

    return d, flags


# --------------------------------------------------------------------------- #
# DAG
# --------------------------------------------------------------------------- #
def _take_last(a, b):
    """병렬 노드가 같은 키를 쓰지 않으므로 마지막 값을 취하는 단순 reducer."""
    return b if b is not None else a


class AgentState(TypedDict, total=False):
    scenario_id: str
    cycle: int
    unit: int
    evidence: Annotated[dict[str, Any], _take_last]
    rul: Annotated[dict[str, Any], _take_last]
    runtime_input: str
    llm: Any
    decision: Any
    flags: list[str]
    status: str


def build_graph(cfg, eda, rul, llm=None):
    """eda: tools.eda.EDATool, rul: tools.rul.RULTool (둘 다 현재 시나리오 이력을 들고 있음)."""
    from langgraph.graph import END, START, StateGraph
    from .llm import DecisionLLM

    llm = llm or DecisionLLM(cfg)

    def eda_node(state: AgentState) -> dict:
        return {"evidence": eda.evidence(state["cycle"])}

    def rul_node(state: AgentState) -> dict:
        return {"rul": rul.context(state["cycle"])}

    def build_input(state: AgentState) -> dict:
        return {"runtime_input": prompts.format_input(state["evidence"], state["rul"])}

    def reason(state: AgentState) -> dict:
        res = llm.decide(state["runtime_input"])
        return {"llm": res, "status": res.status}

    def check(state: AgentState) -> dict:
        res = state["llm"]
        if res.status != "OK" or res.decision is None:
            return {"decision": None, "flags": ["llm_error"], "status": "ERROR"}
        valid = [b["sensor"] for b in state["evidence"]["sensors"]]
        dec, flags = post_check(res.decision, valid)
        return {"decision": dec, "flags": flags, "status": "OK"}

    g = StateGraph(AgentState)
    g.add_node("eda", eda_node)
    g.add_node("rul", rul_node)
    g.add_node("build_input", build_input)
    g.add_node("reason", reason)
    g.add_node("post_check", check)

    g.add_edge(START, "eda")           # fan-out: eda ∥ rul
    g.add_edge(START, "rul")
    g.add_edge("eda", "build_input")   # fan-in: 둘 다 끝나야 실행
    g.add_edge("rul", "build_input")
    g.add_edge("build_input", "reason")
    g.add_edge("reason", "post_check")
    g.add_edge("post_check", END)
    return g.compile()
