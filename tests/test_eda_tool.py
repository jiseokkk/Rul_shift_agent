"""EDATool 스트림 == 배치 계산 (합성 데이터). 도착한 cycle 만 알고, 결과는 배치와 같아야 한다."""
from types import SimpleNamespace

import numpy as np
import pytest

from agent_rul import data
from agent_rul.reference import calibration
from agent_rul.reference.knn import KNNReference
from agent_rul.tools import eda

P, W, SPW, L_C, WARM = 14, 4, 30, 4, 4
SENSORS = [f"S{i}" for i in range(P)]


@pytest.fixture(scope="module")
def ref():
    rng = np.random.default_rng(0)
    w = rng.uniform(-1, 1, size=(6000, W))
    xs = w @ rng.normal(size=(W, P)) + rng.normal(0, 0.1, size=(6000, P))
    pool = np.concatenate([xs, w], axis=1).astype(np.float32)
    knn = KNNReference.fit(pool, P, K=20, query_chunk=1000)
    res_mean = rng.normal(0, 0.05, size=(3000, P))
    res_std = np.abs(rng.normal(0.1, 0.01, size=(3000, P)))
    cal = calibration.fit(res_mean, res_std, SENSORS)
    g = calibration.fit_global(pool, SENSORS)
    return {"knn": knn, "calibration": cal, "global": g}


@pytest.fixture(scope="module")
def cfg():
    return SimpleNamespace(sensors=SENSORS, n_sensors=P, samples_per_window=SPW,
                           min_windows_short_flight=6, L_c=L_C, warm_up=WARM,
                           exp=SimpleNamespace(time={"L_w_sec": 300}))


def _scenario(seed=1, n_cycles=9):
    rng = np.random.default_rng(seed)
    lengths = [rng.integers(200, 600) for _ in range(n_cycles)]
    lengths[3] = 12                                   # window 0개 → 건너뛰어야 하는 cycle
    series = []
    for L in lengths:
        w = rng.uniform(-1, 1, size=(L, W))
        xs = w @ np.ones((W, P)) * 0.3 + rng.normal(0, 0.1, size=(L, P))
        series.append(np.concatenate([xs, w], axis=1).astype(np.float32))
    return {"cycles": np.arange(1, n_cycles + 1), "series": series, "unit": 7}


def _batch(sc, ref, cfg):
    cal_arr = calibration.as_arrays(ref["calibration"])
    g_arr = calibration.global_as_arrays(ref["global"])
    used, aggs, wins = [], [], {}
    for c, seq in data.stream(sc):
        win = data.split_windows(seq, SPW)
        if len(win) == 0:
            continue
        ws = eda.compute_window_stats(win, ref["knn"], cal_arr, P, g_arr)
        aggs.append(eda.aggregate_cycle(ws, cal_arr["q95"], cfg.min_windows_short_flight))
        wins[c] = ws
        used.append(c)
    eda.fill_contrasts(aggs, L_C)
    return used, dict(zip(used, aggs)), wins


def test_stream_matches_batch(ref, cfg):
    sc = _scenario()
    tool = eda.EDATool(cfg, ref)
    tool.reset("syn", sc["unit"])
    for c, seq in data.stream(sc):
        for win in data.split_windows(seq, SPW):
            tool.observe_window(c, win)
        tool.end_cycle(c)

    used, b_aggs, b_wins = _batch(sc, ref, cfg)
    assert tool.cycles == used
    assert tool.skipped == [4]
    for c in used:
        for col in eda.SENSOR_COLS:
            np.testing.assert_allclose(tool.aggs[c]["sensor"][col], b_aggs[c]["sensor"][col],
                                       rtol=1e-6, atol=1e-9, err_msg=f"cycle {c} {col}")
        for k in ("z_w", "std_ratio", "t2", "contrib_frac"):
            np.testing.assert_allclose(tool.windows[c][k], b_wins[c][k].astype(np.float32),
                                       rtol=1e-6, err_msg=f"cycle {c} {k}")
        assert tool.aggs[c]["cycle"] == b_aggs[c]["cycle"]


def test_observe_cycle_equals_window_by_window(ref, cfg):
    sc = _scenario(seed=2)
    a, b = eda.EDATool(cfg, ref), eda.EDATool(cfg, ref)
    a.reset("a", 1)
    b.reset("b", 1)
    for c, seq in data.stream(sc):
        a.observe_cycle(c, seq)
        for win in data.split_windows(seq, SPW):
            b.observe_window(c, win)
        b.end_cycle(c)
    assert a.cycles == b.cycles
    for c in a.cycles:
        np.testing.assert_array_equal(a.windows[c]["z_w"], b.windows[c]["z_w"])


def test_decision_cycles_warmup_and_history(ref, cfg):
    """cycle > warm_up 이고 이전 cycle 이 L_c 개 있어야 판정. skip 된 cycle 은 이력에 안 들어간다."""
    sc = _scenario()
    tool = eda.EDATool(cfg, ref)
    tool.reset("syn", 7)
    decided = []
    for c, seq in data.stream(sc):
        if tool.observe_cycle(c, seq) and tool.is_decision_cycle(c):
            decided.append(c)
    # 사용된 cycle = [1,2,3,5,6,7,8,9]; 인덱스 >= 4 이고 cycle > 4 → 6,7,8,9
    assert decided == [6, 7, 8, 9]
    ev = tool.evidence(6)
    assert ev["multivariate"]["cycles"] == [1, 2, 3, 5, 6]     # 4 는 window 0개로 없음
    assert ev["meta"]["unit"] == 7 and ev["meta"]["cycle"] == 6
    assert [b["sensor"] for b in ev["sensors"]] and len(ev["sensors"]) == P    # 전 센서


def test_tool_only_knows_arrived_cycles(ref, cfg):
    sc = _scenario()
    tool = eda.EDATool(cfg, ref)
    tool.reset("syn", 7)
    for c, seq in list(data.stream(sc))[:5]:
        tool.observe_cycle(c, seq)
    assert max(tool.cycles) == 5
    with pytest.raises(ValueError):
        tool.evidence(6)


def test_tables_shapes(ref, cfg):
    sc = _scenario()
    tool = eda.EDATool(cfg, ref)
    tool.reset("syn", 7)
    for c, seq in data.stream(sc):
        tool.observe_cycle(c, seq)
    t = tool.tables()
    n_w = sum(len(tool.windows[c]["z_w"]) for c in tool.cycles)
    assert len(t["cycle"]) == len(tool.cycles)
    assert len(t["cycle_sensor"]) == len(tool.cycles) * P
    assert len(t["window_stats"]) == n_w * P
    assert {"cycle", "window_idx", "start_sample", "sensor", "z_w", "raw_mean"} <= set(t["window_stats"][0])
    assert t["window_stats"][0]["window_idx"] == 1 and t["window_stats"][0]["start_sample"] == 0


def test_evidence_has_no_raw_keys(ref, cfg):
    """LLM 입력 evidence 에는 raw 통계가 없어야 한다 (규칙 5)."""
    sc = _scenario()
    tool = eda.EDATool(cfg, ref)
    tool.reset("syn", 7)
    for c, seq in data.stream(sc):
        tool.observe_cycle(c, seq)
    ev = tool.evidence(9)
    blob = repr(ev).lower()
    assert "raw" not in blob and "res_mean" not in blob
