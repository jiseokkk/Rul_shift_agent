"""템플릿 렌더링 + 토큰 수 상한 + post_check 보정.

프롬프트 텍스트는 docs/agent_spec.md §3.2 템플릿 구조를 그대로 따라야 한다.
"""
import os
import re

import numpy as np
import pytest

from agent_rul.agent import graph, prompts
from agent_rul.agent.schema import Decision

DOCS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "docs", "agent_spec.md")
SENSORS = ["T48", "T30", "Nf"]


def _evidence(n_win=24, cycle=103):
    rng = np.random.default_rng(0)
    blocks = []
    for i, s in enumerate(SENSORS):
        bias = 2.9 if i == 0 else 0.0
        blocks.append({
            "sensor": s,
            "contribution": [0.86, 0.04, 0.03][i],
            "prev": {
                "cycles": [99, 100, 101, 102],
                "z_w_median": [0.1, -0.2, 0.0, 0.1],
                "z_w_max": [0.6, 0.4, 0.5, 0.7],
                "exceed_k": [0, 1, 0, 0],
                "exceed_n": [22, 24, 23, 24],
                "std_ratio_median": [1.0, 1.1, 0.9, 1.0],
            },
            "current": {
                "n_windows": n_win, "exceed_k": n_win if bias else 0,
                "first_exceed": 1 if bias else -1,
                "delta_mu": bias, "delta_sigma": 0.0,
                "z_w": (rng.normal(bias, 0.1, n_win)).tolist(),
                "std_ratio": (rng.normal(1.0, 0.05, n_win)).tolist(),
            },
        })
    return {
        "meta": {"scenario_id": "A_add_T48_step_1_pos_u11", "unit": 11,
                 "cycle": cycle, "n_windows": n_win, "short_flight": False, "L_w_sec": 300},
        "calibration": {"q95_pooled": 1.9, "std_ratio_ref": 1.0,
                        "t2_median": 10.4, "t2_q95": 19.7,
                        "q95_per_sensor": {s: 1.9 for s in SENSORS}},
        "multivariate": {"cycles": [99, 100, 101, 102, cycle],
                         "t2_median": [9.8, 11.2, 10.1, 10.6, 61.4],
                         "t2_max": [15.3, 17.0, 14.8, 16.1, 68.2],
                         "contribution": [(b["sensor"], b["contribution"]) for b in blocks]},
        "sensors": blocks,
    }


def _rul():
    return {"current": 47.3, "recent_cycles": [99, 100, 101, 102, 103],
            "recent": [55.2, 53.7, 51.8, 50.4, 47.3],
            "change": -3.1, "recent_median_change": -1.4}


# ------------------------------------------------------------- 템플릿 구조
def test_all_blocks_present_in_order():
    txt = prompts.format_input(_evidence(), _rul())
    order = ["=== EVALUATION ===", "=== CALIBRATION (clean validation) ===",
             "=== MULTIVARIATE ===", "=== SENSORS (ordered by contribution @103) ===",
             "=== RUL (auxiliary) ===", "=== TASK ==="]
    pos = [txt.index(b) for b in order]
    assert pos == sorted(pos)


def test_all_sensors_included_no_topk():
    txt = prompts.format_input(_evidence(), _rul())
    for s in SENSORS:
        assert f"--- {s} " in txt
    assert txt.count("current cycle 103") == len(SENSORS)


def test_sensor_order_follows_contribution():
    txt = prompts.format_input(_evidence(), _rul())
    assert re.findall(r"--- (\w+)\s+\(contribution", txt) == SENSORS


def test_window_series_length_matches_n_windows():
    txt = prompts.format_input(_evidence(n_win=37), _rul())
    line = [l for l in txt.splitlines() if l.strip().startswith("z_w  ")][0]
    assert len(line.split(":")[1].split()) == 37


def test_signed_one_decimal():
    txt = prompts.format_input(_evidence(), _rul())
    zline = [l for l in txt.splitlines() if l.strip().startswith("z_w  ")][0]
    for v in zline.split(":")[1].split():
        assert re.fullmatch(r"[+-]\d+\.\d", v), v


def test_no_raw_statistics_leak():
    """raw mean/median/std/IQR 은 프롬프트에 들어가면 안 된다 (규칙 5)."""
    txt = prompts.format_input(_evidence(), _rul()).lower()
    for banned in ("raw", "iqr", "e[x|w]", "w-conditioned"):
        assert banned not in txt, banned


def test_nan_rendered_as_na():
    ev = _evidence()
    ev["sensors"][0]["current"]["delta_mu"] = float("nan")
    assert f"Δμ = {prompts.NA}" in prompts.format_input(ev, _rul())


def test_first_exceed_dash_when_absent():
    txt = prompts.format_input(_evidence(), _rul())
    assert "first exceed = -" in txt
    assert "first exceed = #1" in txt


@pytest.mark.parametrize("n_win,limit", [(24, 9000), (58, 20000)])
def test_prompt_token_budget(n_win, limit):
    """실제 데이터 최대치(window 58개, 센서 14개)에서도 32k 컨텍스트 안에 들어와야 한다."""
    ev = _evidence(n_win=n_win)
    base = ev["sensors"][0]
    ev["sensors"] = [dict(base, sensor=f"S{i}") for i in range(14)]
    ev["multivariate"]["contribution"] = [(f"S{i}", 0.07) for i in range(14)]
    txt = prompts.format_input(ev, _rul())
    est = prompts.estimate_tokens(txt) + prompts.estimate_tokens(prompts.SYSTEM_PROMPT)
    assert est < limit, est


def test_system_prompt_matches_docs():
    """prompts.py 의 SYSTEM_PROMPT 가 docs/agent_spec.md §1 의 텍스트와 같아야 한다."""
    with open(DOCS, "r", encoding="utf-8") as f:
        doc = f.read()
    block = doc.split("```text", 1)[1].split("```", 1)[0].strip()
    assert block == prompts.SYSTEM_PROMPT.strip()


def test_confidence_calibration_section_present():
    assert "## Confidence calibration" in prompts.SYSTEM_PROMPT
    for band in ("0.85-1.00", "0.60-0.85", "0.35-0.60", "0.00-0.35"):
        assert band in prompts.SYSTEM_PROMPT


# ------------------------------------------------------------- post_check
def _dec(**kw):
    base = dict(sensor_status="FAULT", rul_reliability="WARNING",
                suspected_sensors=["T48"], fault_pattern="BIAS_LIKE",
                confidence=0.9, key_evidence=["e"], rationale="r")
    base.update(kw)
    return Decision(**base)


def test_post_check_forces_warning_on_fault():
    d, flags = graph.post_check(_dec(rul_reliability="RELIABLE"), SENSORS)
    assert d.rul_reliability == "WARNING"
    assert graph.FLAG_RELIABILITY in flags


def test_post_check_forces_reliable_on_normal():
    d, flags = graph.post_check(
        _dec(sensor_status="NORMAL", rul_reliability="WARNING",
             suspected_sensors=[], fault_pattern="NONE"), SENSORS)
    assert d.rul_reliability == "RELIABLE"
    assert graph.FLAG_RELIABILITY in flags


def test_post_check_clears_suspected_on_normal():
    d, flags = graph.post_check(
        _dec(sensor_status="NORMAL", rul_reliability="RELIABLE", fault_pattern="NONE"), SENSORS)
    assert d.suspected_sensors == []
    assert graph.FLAG_SUSPECTED_ON_NORMAL in flags


def test_post_check_keeps_fault_without_isolation():
    d, flags = graph.post_check(_dec(suspected_sensors=[]), SENSORS)
    assert d.sensor_status == "FAULT"
    assert graph.FLAG_ISOLATION_MISSING in flags


def test_post_check_drops_unknown_sensor():
    d, flags = graph.post_check(_dec(suspected_sensors=["T48", "S99"]), SENSORS)
    assert d.suspected_sensors == ["T48"]
    assert any(f.startswith(graph.FLAG_UNKNOWN_SENSOR) for f in flags)


def test_post_check_clean_decision_has_no_flags():
    d, flags = graph.post_check(_dec(), SENSORS)
    assert flags == []
    assert d.sensor_status == "FAULT" and d.rul_reliability == "WARNING"
