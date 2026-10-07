"""LLM 호출 유일 지점. vLLM OpenAI 호환 서버 또는 OpenRouter. 설계: docs/design_v1.md §8

decide(system, user) → {'decision', 'flags', 'raw', 'n_retries', 'latency_ms', 'prompt_tokens', 'completion_tokens',
                        'reasoning_tokens', 'cost', 'error'}
temperature 0, seed 고정, JSON 스키마 강제(vLLM guided_json 또는 OpenAI 식 response_format), 파싱 실패 시 재시도.
request_body() 는 배치 제출(scripts/batch_openrouter.py)과 공유해, 동기 호출과 배치가 같은 본문을 보내게 한다.

설정 키 (configs/llm*.yaml)
  base_url, model, max_tokens, timeout_s, retries, concurrency
  api_key            vLLM 은 EMPTY
  api_key_env        환경변수 이름 (저장소 루트 .env 에서 로드). 있으면 api_key 보다 우선
  temperature / send_temperature   GPT-5 계열 reasoning 모델은 temperature 를 받지 않으므로 false
  seed / send_seed                 Anthropic 모델은 seed 미지원 → false
  guided_json: true                vLLM guided decoding (기존 설정과 호환)
  json_mode: response_format       OpenRouter/OpenAI: response_format json_schema strict
  strict, strict_strip             strict 모드가 받지 않는 스키마 키를 뺀다 (기본 maxLength)
  reasoning_effort                 OpenRouter reasoning.effort (none|minimal|low|medium|high). 비우면 보내지 않음
  reasoning_enabled                OpenRouter reasoning.enabled (true/false). effort 'none' 을 모르는 오픈웨이트 모델은 false 로 끈다
  provider                         OpenRouter provider 라우팅 옵션 dict
  usage_include                    OpenRouter usage.cost 반환
"""
from __future__ import annotations

import copy
import os
import time

from openai import OpenAI

from src.llm.post_check import ParseError, parse, post_check
from src.llm.schema import json_schema


def resolve_api_key(cfg: dict) -> str:
    env = cfg.get("api_key_env")
    if not env:
        return cfg.get("api_key", "EMPTY")
    key = os.environ.get(env, "").strip()
    if not key:
        raise RuntimeError(f"환경변수 {env} 가 비어 있다. 저장소 루트 .env 에 '{env}=...' 를 넣는다 (.env.example 참조).")
    return key


def _strip_keys(schema: dict, keys: list[str]) -> dict:
    s = copy.deepcopy(schema)

    def rec(o):
        if isinstance(o, dict):
            for k in list(o):
                if k in keys:
                    del o[k]
                else:
                    rec(o[k])
        elif isinstance(o, list):
            for v in o:
                rec(v)

    rec(s)
    return s


def response_format(cfg: dict) -> dict:
    """OpenAI 식 response_format. strict 가 받지 않는 키는 뺀다. 빠진 제약은 post_check 가 같은 방식으로 기록한다."""
    schema = _strip_keys(json_schema(), list(cfg.get("strict_strip", ["maxLength"])))
    return {"type": "json_schema",
            "json_schema": {"name": "decision", "strict": bool(cfg.get("strict", True)), "schema": schema}}


def request_body(cfg: dict, system: str, user: str, seed: int) -> tuple[dict, dict]:
    """(표준 chat.completions 파라미터, 서버 확장 파라미터). 동기 호출은 extra_body 로, 배치는 둘을 합쳐 보낸다."""
    body: dict = {"model": cfg["model"], "max_tokens": int(cfg.get("max_tokens", 300)),
                  "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    if cfg.get("send_temperature", True):
        body["temperature"] = float(cfg.get("temperature", 0.0))
    if cfg.get("send_seed", True):
        body["seed"] = int(seed)
    mode = cfg.get("json_mode") or ("guided_json" if cfg.get("guided_json", True) else "none")
    extra: dict = {}
    if mode == "guided_json":                     # vLLM
        extra["guided_json"] = json_schema()
    elif mode == "response_format":               # OpenRouter / OpenAI
        body["response_format"] = response_format(cfg)
    elif mode != "none":
        raise ValueError(f"json_mode: {mode}")
    reasoning: dict = {}
    if cfg.get("reasoning_enabled") is not None:  # OpenRouter 공통 스위치. 하이브리드 thinking 모델(Qwen3.x, DeepSeek v4, GLM 등)은 false 로 끈다
        reasoning["enabled"] = bool(cfg["reasoning_enabled"])
    if cfg.get("reasoning_effort"):               # OpenRouter. GPT-5 계열은 기본 off 지만 명시, Claude 는 기본 on
        reasoning["effort"] = str(cfg["reasoning_effort"])
    if reasoning:
        extra["reasoning"] = reasoning
    if cfg.get("provider"):
        extra["provider"] = dict(cfg["provider"])
    if cfg.get("usage_include"):
        extra["usage"] = {"include": True}
    return body, extra


def usage_from_dict(u: dict | None) -> dict:
    u = u or {}
    det = u.get("completion_tokens_details") or {}
    return {"prompt_tokens": u.get("prompt_tokens"), "completion_tokens": u.get("completion_tokens"),
            "reasoning_tokens": det.get("reasoning_tokens"), "cost": u.get("cost")}


def usage_from_obj(usage) -> dict:
    if usage is None:
        return usage_from_dict(None)
    try:
        return usage_from_dict(usage.model_dump())
    except Exception:  # 비 pydantic 객체
        return {"prompt_tokens": getattr(usage, "prompt_tokens", None), "completion_tokens": getattr(usage, "completion_tokens", None),
                "reasoning_tokens": None, "cost": None}


class LLMClient:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.client = OpenAI(base_url=cfg["base_url"], api_key=resolve_api_key(cfg), timeout=cfg.get("timeout_s", 300))
        self.model = cfg["model"]
        self.seed = int(cfg.get("seed", 42))

    def _call(self, system: str, user: str, seed: int) -> tuple[str, dict, str | None]:
        body, extra = request_body(self.cfg, system, user, seed)
        r = self.client.chat.completions.create(**body, extra_body=extra)
        ch = r.choices[0]
        return ch.message.content or "", usage_from_obj(getattr(r, "usage", None)), getattr(ch, "finish_reason", None)

    def decide(self, system: str, user: str) -> dict:
        retries = int(self.cfg.get("retries", 2))
        t0 = time.time()
        raw, err, usage, finish = "", None, usage_from_dict(None), None
        for attempt in range(retries + 1):
            try:
                raw, usage, finish = self._call(system, user, self.seed + attempt)  # 재시도는 seed 를 바꿔 같은 실패 반복 방지
                d = parse(raw)
                d, flags = post_check(d)
                return {"decision": d, "flags": flags, "raw": raw, "n_retries": attempt,
                        "latency_ms": int((time.time() - t0) * 1000), **usage, "error": None}
            except ParseError as e:
                err = f"parse:{e}" + (f" (finish_reason={finish})" if finish and finish != "stop" else "")
            except Exception as e:  # 네트워크·서버 오류. 429 는 분당 한도이므로 길게 기다린다
                err = f"{type(e).__name__}:{e}"
                is_429 = getattr(e, "status_code", None) == 429 or type(e).__name__ == "RateLimitError"
                time.sleep(float(self.cfg.get("rate_limit_wait_s", 20)) if is_429 else 2.0)
        return {"decision": None, "flags": ["ERROR"], "raw": raw, "n_retries": retries,
                "latency_ms": int((time.time() - t0) * 1000), **usage, "error": err}

    def list_models(self) -> list[str]:
        return [m.id for m in self.client.models.list().data]
