"""LLM 출력 → 채점 가능한 레코드. 위반은 고치되 반드시 기록한다. 설계: docs/design_v1.md §6"""
from __future__ import annotations

import json

from pydantic import ValidationError

from src.llm.schema import SENSOR_NAMES, Decision


class ParseError(Exception):
    pass


def parse(text: str) -> Decision:
    """JSON 파싱 + 스키마 검증. 실패 시 ParseError (호출부가 재시도)."""
    s = text.strip()
    if s.startswith("```"):
        s = s.strip("`")
        if s.lower().startswith("json"):
            s = s[4:]
    a, b = s.find("{"), s.rfind("}")
    if a < 0 or b < 0:
        raise ParseError("no JSON object")
    try:
        obj = json.loads(s[a:b + 1])
    except json.JSONDecodeError as e:
        raise ParseError(f"json: {e}") from e
    # 흔한 타입 이탈 보정 (기록은 post_check 에서)
    if isinstance(obj.get("degraded"), str):
        v = obj["degraded"].strip().lower()
        obj["degraded"] = 1 if v in ("1", "true", "yes", "degraded") else 0 if v in ("0", "false", "no", "normal") else obj["degraded"]
    if isinstance(obj.get("degraded"), bool):
        obj["degraded"] = int(obj["degraded"])
    try:
        return Decision(**obj)
    except ValidationError as e:
        raise ParseError(f"schema: {e.errors()[0].get('msg')}") from e


def post_check(d: Decision) -> tuple[Decision, list[str]]:
    flags: list[str] = []
    sensors = []
    for s in d.suspected_sensors:
        if s in SENSOR_NAMES:
            sensors.append(s)
        else:
            flags.append(f"bad_sensor_name:{s}")
    sensors = list(dict.fromkeys(sensors))  # 중복 제거, 순서 유지
    if d.degraded == 0 and sensors:
        flags.append("sensors_on_normal")
        sensors = []
    if d.degraded == 1 and not sensors:
        flags.append("isolation_missing")
    conf = d.confidence
    if not (0.0 <= conf <= 1.0):
        flags.append("confidence_clipped")
        conf = min(1.0, max(0.0, conf))
    rationale = d.rationale
    if len(rationale.split()) > 60:
        flags.append("rationale_long")
    return Decision(degraded=d.degraded, suspected_sensors=sensors, confidence=conf, rationale=rationale), flags
