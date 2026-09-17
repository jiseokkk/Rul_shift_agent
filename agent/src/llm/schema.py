"""에이전트 출력 스키마. 채점은 degraded 만. 설계: docs/design_v1.md §6"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

SENSOR_NAMES = ["T24", "T30", "T50", "P30", "Nf", "Nc", "Ps30", "phi", "NRf", "NRc", "BPR", "htBleed", "W31", "W32"]


class Decision(BaseModel):
    degraded: Literal[0, 1]
    suspected_sensors: list[str] = Field(default_factory=list, max_length=14)
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str = Field(max_length=500)


def json_schema() -> dict:
    """vLLM guided_json 용. additionalProperties 를 막아 형식을 고정한다."""
    return {
        "type": "object",
        "properties": {
            "degraded": {"type": "integer", "enum": [0, 1]},
            "suspected_sensors": {"type": "array", "items": {"type": "string", "enum": SENSOR_NAMES}, "maxItems": 14},
            "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "rationale": {"type": "string", "maxLength": 500},
        },
        "required": ["degraded", "suspected_sensors", "confidence", "rationale"],
        "additionalProperties": False,
    }
