import pytest

from src.llm.post_check import ParseError, parse, post_check
from src.llm.prompts import build_input, system_prompt
from src.llm.schema import json_schema


def test_parse_and_post_check_normal():
    d = parse('{"degraded": 0, "suspected_sensors": [], "confidence": 0.9, "rationale": "ok"}')
    d, flags = post_check(d)
    assert d.degraded == 0 and flags == []


def test_post_check_fixes_contradictions():
    d = parse('{"degraded": 0, "suspected_sensors": ["T24"], "confidence": 0.7, "rationale": "x"}')
    d, flags = post_check(d)
    assert d.suspected_sensors == [] and "sensors_on_normal" in flags
    d = parse('{"degraded": 1, "suspected_sensors": ["T-24", "T50", "T50"], "confidence": 0.7, "rationale": "x"}')
    d, flags = post_check(d)
    assert d.suspected_sensors == ["T50"] and any(f.startswith("bad_sensor_name") for f in flags)
    d = parse('{"degraded": 1, "suspected_sensors": [], "confidence": 0.7, "rationale": "x"}')
    _, flags = post_check(d)
    assert "isolation_missing" in flags


def test_parse_tolerates_wrapping_and_types():
    d = parse('```json\n{"degraded": "1", "suspected_sensors": ["T24"], "confidence": 0.8, "rationale": "r"}\n```')
    assert d.degraded == 1
    d = parse('Sure: {"degraded": true, "suspected_sensors": [], "confidence": 0.5, "rationale": "r"} done')
    assert d.degraded == 1
    with pytest.raises(ParseError):
        parse("no json here")
    with pytest.raises(ParseError):
        parse('{"degraded": 2, "suspected_sensors": [], "confidence": 0.5, "rationale": "r"}')


def test_build_input_shape():
    sensor = {"columns": ["jump", "noise_ratio", "flat_ratio", "level_shift"], "sort_key": "level_shift", "short_history": True,
              "rows": [{"sensor": s, "jump": 0.1, "noise_ratio": 1.0, "flat_ratio": 0.5, "level_shift": -1.9 + i}
                       for i, s in enumerate(["T24", "T30", "T50"])]}
    rul = {"y_hat": 116.9, "recent": [121.5, 119.2, 120.3, 120.8, 120.7, 122.2, 120.7, 118.5, 116.3, 116.9], "slope": -0.42,
           "jump": 0.3, "mc_ratio": 3.5}
    txt = build_input(1, 110, sensor, rul)
    assert "unit: 1    cycle: 110" in txt and "current RUL       : 116.9" in txt
    assert "sorted by |level_shift|" in txt and "[short_history" in txt
    assert "bias" not in txt and "scenario" not in txt.lower()
    assert "resid" not in system_prompt() and "level_shift" in system_prompt()
    assert json_schema()["required"] == ["degraded", "suspected_sensors", "confidence", "rationale"]
