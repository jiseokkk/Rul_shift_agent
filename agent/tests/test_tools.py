import numpy as np
import pytest

from src.tools.base import mad
from src.tools.rul_tool import RULTool
from src.tools.sensor_tool import SensorTool

S = ["A", "B", "C"]
RES = {"A": 0.01, "B": 0.01, "C": 1.0}


def feed(tool, X):
    for t, row in enumerate(X, start=1):
        tool.observe(t, {s: float(v) for s, v in zip(S, row)})


def synth(T=100, seed=0, drift=0.02, noise=0.1):
    rng = np.random.default_rng(seed)
    base = 100 + drift * np.arange(T)[:, None] + rng.normal(0, noise, (T, 3))
    base[:, 2] = np.round(base[:, 2])  # C 는 정수 센서
    return base


def test_mad_basic():
    assert mad(np.array([1, 2, 3, 4, 100.0])) == 1.0


def test_normal_values_near_zero_and_one():
    X = synth()
    tool = SensorTool(S, RES, N=10)
    feed(tool, X)
    rows = {r["sensor"]: r for r in tool.summary()["rows"]}
    assert abs(rows["A"]["jump"]) < 4
    assert 0.3 < rows["A"]["noise_ratio"] < 3
    assert rows["A"]["flat_ratio"] <= 1.0
    assert abs(rows["A"]["level_shift"]) < 3  # 완만한 drift 는 level_shift 를 크게 만들지 않음


def test_bias_step_shows_in_jump_then_level_shift():
    X = synth(noise=0.05)
    X[70:, 0] += 2.0  # A 에 계단
    tool = SensorTool(S, RES, N=10)
    for t in range(1, 72):  # cycle 71 = 계단이 들어온 첫 cycle
        tool.observe(t, {s: float(v) for s, v in zip(S, X[t - 1])})
    j = {r["sensor"]: r for r in tool.summary()["rows"]}["A"]["jump"]
    assert j > 10  # 시작 cycle 의 jump 는 큼
    for t in range(72, 101):
        tool.observe(t, {s: float(v) for s, v in zip(S, X[t - 1])})
    rows = {r["sensor"]: r for r in tool.summary()["rows"]}
    # drift 가 이력 MAD 를 키워 level_shift 는 계단 크기(2.0 = 40σ_noise)보다 훨씬 작게 나온다. 열화 혼동의 실물.
    assert rows["A"]["level_shift"] > 2 and rows["A"]["level_shift"] > 2 * abs(rows["B"]["level_shift"])
    assert abs(rows["A"]["jump"]) < 4  # 계단 이후 jump 는 정상으로 복귀
    assert tool.summary()["rows"][0]["sensor"] == "A"  # |level_shift| 내림차순


def test_noise_and_stuck():
    X = synth(noise=0.05)
    rng = np.random.default_rng(1)
    X[60:, 0] += rng.normal(0, 1.0, 40)   # A noise
    X[60:, 1] = X[59, 1]                  # B stuck
    tool = SensorTool(S, RES, N=10)
    feed(tool, X)
    rows = {r["sensor"]: r for r in tool.summary()["rows"]}
    assert rows["A"]["noise_ratio"] > 5
    assert rows["B"]["noise_ratio"] < 0.2
    assert rows["B"]["flat_ratio"] > 5


def test_integer_sensor_no_division_blowup():
    X = synth()
    tool = SensorTool(S, RES, N=10)
    feed(tool, X)
    rows = {r["sensor"]: r for r in tool.summary()["rows"]}
    assert np.isfinite(rows["C"]["level_shift"]) and abs(rows["C"]["level_shift"]) < 10
    assert rows["C"]["flat_ratio"] <= 2.0  # 정수 센서의 정상적 연속 동일값은 stuck 으로 보이지 않음


def test_no_future_access_and_order():
    tool = SensorTool(S, RES)
    tool.observe(1, {"A": 1.0, "B": 1.0, "C": 1.0})
    with pytest.raises(ValueError):
        tool.observe(3, {"A": 1.0, "B": 1.0, "C": 1.0})


def test_short_history_flag():
    tool = SensorTool(S, RES, N=10, short_history=65)
    feed(tool, synth(T=60))
    assert tool.summary()["short_history"] is True
    feed_more = synth(T=70)[60:]
    for t, row in enumerate(feed_more, start=61):
        tool.observe(t, {s: float(v) for s, v in zip(S, row)})
    assert tool.summary()["short_history"] is False


def test_rul_tool_healthy_and_jump():
    tool = RULTool(N=10)
    rng = np.random.default_rng(0)
    y = 125 - np.arange(60) * 1.0 + rng.normal(0, 0.3, 60)
    for i, v in enumerate(y):
        tool.observe(45 + i, v, v + rng.normal(0, 0.5, 50))
    s = tool.summary()
    assert -1.5 < s["slope"] < -0.5
    assert abs(s["jump"]) < 4 and 0.3 < s["mc_ratio"] < 3
    tool.observe(45 + 60, y[-1] + 15, y[-1] + rng.normal(0, 3.0, 50))   # 급변 + 불확실성 증가
    s = tool.summary()
    assert s["jump"] > 5 and s["mc_ratio"] > 3
    assert len(s["recent"]) == 10
