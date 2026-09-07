"""Decision 스키마 (docs/agent_spec.md §2 와 동일).

필드를 바꿀 때는 agent_spec.md §2, research_plan_v2.md 7.3, 그리고
decisions.csv 컬럼(evaluation 쪽)을 함께 고친다.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Decision(BaseModel):
    sensor_status: Literal["NORMAL", "FAULT"]
    rul_reliability: Literal["RELIABLE", "WARNING"]

    # FAULT일 때 의심 센서. NORMAL이면 빈 리스트. 1차 실험은 single-sensor라 보통 1개.
    suspected_sensors: list[str] = Field(default_factory=list)

    # 관측된 패턴. 1차는 abrupt bias만 주입하지만 진단용으로 기록.
    fault_pattern: Literal["NONE", "BIAS_LIKE", "NOISE_LIKE", "UNCLEAR"] = "NONE"

    # 0~1. 근거 수렴도 기준 (System Prompt "Confidence calibration" 참조).
    # 평가에는 쓰지 않고 threshold sweep / 분석용.
    confidence: float = Field(ge=0.0, le=1.0)

    # 판정을 이끈 핵심 수치 2~4개.
    key_evidence: list[str] = Field(min_length=1, max_length=4)

    # 120 단어 이내.
    rationale: str


# decisions.csv 컬럼 순서 (agent_spec.md §2 "저장 레코드")
DECISION_COLUMNS = [
    "scenario_id", "unit", "cycle",
    "sensor_status", "rul_reliability", "suspected_sensors", "fault_pattern",
    "confidence", "key_evidence", "rationale",
    "n_retries", "post_check_flags", "latency_ms", "prompt_tokens",
    "true_rul", "life_fraction",
]
