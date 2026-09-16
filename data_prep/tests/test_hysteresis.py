import numpy as np

from src.label.hysteresis import hysteresis_label, summarize


def test_enter_backfill_and_tau_d():
    # θ=0.5, k=3, m=4: 초과가 idx 2,3,4 → t=4 에서 진입 판정, 역방향 채우기로 idx 2 부터 1
    d = np.array([.1, .2, .8, .9, .7, .9, .8, .3, .2, .1, .2, .9, .8, .9])
    r = hysteresis_label(d, 0.5, k=3, m=4, theta_low_ratio=1.0)  # 대칭 θ
    assert r["tau_d_idx"] == 2
    assert r["label"][:2].tolist() == [0, 0]
    assert r["label"][2:7].tolist() == [1, 1, 1, 1, 1]


def test_exit_backfill_symmetric():
    d = np.array([.1, .2, .8, .9, .7, .9, .8, .3, .2, .1, .2, .9, .8, .9])
    r = hysteresis_label(d, 0.5, k=3, m=4, theta_low_ratio=1.0)
    # 복귀: idx 7,8,9 가 ≤θ → t=9 에서 복귀 판정, idx 7 부터 0
    assert r["label"][7:11].tolist() == [0, 0, 0, 0]
    assert r["exits"] == [7]
    # 재진입: idx 11,12,13 → t=13 판정, idx 11 부터 1
    assert r["label"][11:].tolist() == [1, 1, 1]
    assert r["enters"] == [2, 11]


def test_hysteresis_low_threshold_prevents_exit():
    # θ_low = 0.5·θ_high = 0.25: .3 은 ≤0.25 가 아니므로 복귀 조건에 안 들어감
    d = np.array([.9, .9, .9, .9, .9, .3, .3, .3, .3, .3, .3, .3])
    r = hysteresis_label(d, 0.5, k=3, m=4, theta_low_ratio=0.5)
    assert r["exits"] == []
    assert r["label"].sum() == len(d)


def test_initial_partial_window():
    # 초기 구간: t=2 에서 window 는 [0..2] 3개, k=3 이면 3개 모두 초과 시 진입
    d = np.array([1, 1, 1, 0, 0, 0, 0, 0], dtype=float)
    r = hysteresis_label(d, 0.5, k=3, m=7, theta_low_ratio=0.5)
    assert r["tau_d_idx"] == 0
    assert r["label"][:3].tolist() == [1, 1, 1]


def test_adaptive_theta_array():
    d = np.array([5, 5, 5, 5, 5, 5], dtype=float)
    th = np.array([10, 10, 10, 1, 1, 1], dtype=float)  # 뒤쪽만 θ 가 낮음
    r = hysteresis_label(d, th, k=3, m=3, theta_low_ratio=0.5)
    assert r["tau_d_idx"] == 3
    assert r["label"].tolist() == [0, 0, 0, 1, 1, 1]


def test_no_degradation():
    d = np.zeros(20)
    r = hysteresis_label(d, 1.0, k=5, m=7)
    s = summarize(r, np.arange(45, 65), tau_s=50)
    assert s["degraded"] is False and s["tau_d"] is None and s["n_degraded_cycles"] == 0
    assert s["n_transitions"] == 0


def test_summarize_delay():
    d = np.array([0] * 10 + [9] * 10, dtype=float)
    r = hysteresis_label(d, 1.0, k=5, m=7)
    times = np.arange(45, 65)
    s = summarize(r, times, tau_s=55)
    assert s["degraded"] and s["tau_d"] == 55 and s["delay"] == 0
    assert s["frac_degraded_after_tau_s"] == 1.0
