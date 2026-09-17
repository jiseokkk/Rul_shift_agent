"""LLM 호출 유일 지점. vLLM OpenAI 호환 서버. 설계: docs/design_v1.md §8

decide(system, user) → {'decision', 'flags', 'raw', 'n_retries', 'latency_ms', 'prompt_tokens', 'completion_tokens', 'error'}
temperature 0, seed 고정, guided_json 으로 스키마 강제, 파싱 실패 시 재시도.
"""
from __future__ import annotations

import time

from openai import OpenAI

from src.llm.post_check import ParseError, parse, post_check
from src.llm.schema import json_schema


class LLMClient:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.client = OpenAI(base_url=cfg["base_url"], api_key=cfg.get("api_key", "EMPTY"), timeout=cfg.get("timeout_s", 300))
        self.model = cfg["model"]
        self.extra = {"guided_json": json_schema()} if cfg.get("guided_json", True) else {}
        self.seed = int(cfg.get("seed", 42))

    def _call(self, system: str, user: str, seed: int) -> tuple[str, dict]:
        r = self.client.chat.completions.create(
            model=self.model, temperature=float(self.cfg.get("temperature", 0.0)), seed=seed,
            max_tokens=int(self.cfg.get("max_tokens", 300)),
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            extra_body=self.extra,
        )
        usage = getattr(r, "usage", None)
        return r.choices[0].message.content or "", {
            "prompt_tokens": getattr(usage, "prompt_tokens", None), "completion_tokens": getattr(usage, "completion_tokens", None)}

    def decide(self, system: str, user: str) -> dict:
        retries = int(self.cfg.get("retries", 2))
        t0 = time.time()
        raw, err, usage = "", None, {}
        for attempt in range(retries + 1):
            try:
                raw, usage = self._call(system, user, self.seed + attempt)  # 재시도는 seed 를 바꿔 같은 실패 반복 방지
                d = parse(raw)
                d, flags = post_check(d)
                return {"decision": d, "flags": flags, "raw": raw, "n_retries": attempt,
                        "latency_ms": int((time.time() - t0) * 1000), **usage, "error": None}
            except ParseError as e:
                err = f"parse:{e}"
            except Exception as e:  # 네트워크·서버 오류
                err = f"{type(e).__name__}:{e}"
                time.sleep(2.0)
        return {"decision": None, "flags": ["ERROR"], "raw": raw, "n_retries": retries,
                "latency_ms": int((time.time() - t0) * 1000), **usage, "error": err}

    def list_models(self) -> list[str]:
        return [m.id for m in self.client.models.list().data]
