"""LLM 호출 — **이 프로젝트에서 LLM 을 호출하는 유일한 곳** (CLAUDE.md 규칙 3).

vLLM 을 OpenAI 호환 서버로 띄워 두고 langchain-openai 로 붙는다. structured output 은
서버측 guided decoding(json_schema)에 의존하고, 실패하면 json_mode 로 낮춰 재시도한다.
configs/llm.yaml 의 max_retries 를 초과하면 LLMResult.status = "ERROR".
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from .prompts import SYSTEM_PROMPT
from .schema import Decision


@dataclass
class LLMResult:
    status: str                       # "OK" | "ERROR"
    decision: Decision | None = None
    n_retries: int = 0
    latency_ms: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    errors: list[str] = field(default_factory=list)


class DecisionLLM:
    def __init__(self, cfg):
        c = cfg.llm
        self.cfg = cfg
        self.max_retries = int(c["max_retries"])
        self.method = str(c.get("structured_output_method", "json_schema"))
        self._base = ChatOpenAI(
            model=str(c["model"]),
            base_url=str(c["base_url"]),
            api_key=str(c["api_key"]),
            temperature=float(c["temperature"]),
            max_tokens=int(c["max_tokens"]),
            top_p=float(c.get("top_p", 1.0)),
            seed=int(c["seed"]),
            timeout=float(c["timeout_s"]),
            max_retries=0,                 # 재시도는 여기서 직접 센다
        )
        self._structured = {
            m: self._base.with_structured_output(Decision, method=m, include_raw=True)
            for m in ("json_schema", "json_mode")
        }

    def decide(self, runtime_input: str) -> LLMResult:
        """system + runtime input → Decision. 실패 시 max_retries 만큼 재시도."""
        msgs = [SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=runtime_input)]
        res = LLMResult(status="ERROR")
        t0 = time.perf_counter()

        for attempt in range(self.max_retries + 1):
            method = self.method if attempt == 0 else "json_mode"
            try:
                raw = self._structured[method].invoke(msgs)
                dec = raw.get("parsed") if isinstance(raw, dict) else raw
                err = raw.get("parsing_error") if isinstance(raw, dict) else None
                if dec is None:
                    raise ValueError(f"parse 실패: {err}")
                res.status = "OK"
                res.decision = dec
                res.n_retries = attempt
                _fill_usage(res, raw)
                break
            except Exception as e:                        # 호출·파싱·검증 실패 전부
                res.errors.append(f"attempt{attempt}({method}): {type(e).__name__}: {e}")
                res.n_retries = attempt

        res.latency_ms = int((time.perf_counter() - t0) * 1000)
        return res


def _fill_usage(res: LLMResult, raw) -> None:
    msg = raw.get("raw") if isinstance(raw, dict) else None
    um = getattr(msg, "usage_metadata", None) or {}
    res.prompt_tokens = int(um.get("input_tokens", 0) or 0)
    res.completion_tokens = int(um.get("output_tokens", 0) or 0)


def ping(cfg) -> str:
    """서버 연결 확인용 (`run --dry-run`)."""
    llm = ChatOpenAI(model=str(cfg.llm["model"]), base_url=str(cfg.llm["base_url"]),
                     api_key=str(cfg.llm["api_key"]), temperature=0.0, max_tokens=8,
                     timeout=30, max_retries=0)
    return llm.invoke([HumanMessage(content="reply with OK")]).content
