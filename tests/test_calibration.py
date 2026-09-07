"""calibration 불변식 (설계서 3.5, 4.4): sigma_w > 0, Sigma_r 조건수, T2 분해."""
import numpy as np
import pytest

from agent_rul.reference import calibration

SENSORS = [f"S{i}" for i in range(5)]


def _clean(n=4000, p=5, seed=0):
    rng = np.random.default_rng(seed)
    res_mean = rng.normal(0, 0.3, size=(n, p))
    res_std = np.abs(rng.normal(1.0, 0.05, size=(n, p)))
    return res_mean, res_std


def test_sigma_w_positive_and_q95_near_normal():
    cal = calibration.fit(*_clean(), SENSORS)
    assert all(s > 0 for s in cal["sigma_w"])
    # z_w 는 표준정규에 가까우므로 |z_w| q95 ~ 1.96
    assert 1.7 < cal["q95_pooled"] < 2.2
    assert cal["n_windows"] == 4000


def test_sigma_w_zero_raises():
    res_mean, res_std = _clean()
    res_mean[:, 2] = 0.0                     # 변동 없는 센서
    with pytest.raises(ValueError, match="sigma_w"):
        calibration.fit(res_mean, res_std, SENSORS)


def test_std_ref_is_median_of_window_std():
    res_mean, res_std = _clean()
    cal = calibration.fit(res_mean, res_std, SENSORS)
    assert np.allclose(cal["std_ref"], np.median(res_std, axis=0))


def test_sigma_r_well_conditioned_no_ridge():
    cal = calibration.fit(*_clean(), SENSORS)
    assert cal["ridge"] == 0.0
    assert cal["condition_number"] < calibration.RIDGE_COND_LIMIT


def test_ill_conditioned_gets_ridge():
    """완전 상관 센서를 넣으면 Sigma_r 이 특이해지고 ridge 가 붙는다."""
    res_mean, res_std = _clean()
    res_mean[:, 4] = res_mean[:, 0]          # 중복 열 → rank 결손
    cal = calibration.fit(res_mean, res_std, SENSORS)
    assert cal["ridge"] > 0
    assert np.isfinite(cal["condition_number"])


def test_t2_contributions_sum_to_t2():
    """sum_i c_i = T^2 (설계서 4.4 분해)."""
    res_mean, res_std = _clean(n=500)
    cal = calibration.fit(res_mean, res_std, SENSORS)
    a = calibration.as_arrays(cal)
    t2 = calibration.hotelling_t2(res_mean, a["mu_r"], a["Sigma_r_inv"])
    contrib = calibration.t2_contributions(res_mean, a["mu_r"], a["Sigma_r_inv"])
    assert np.allclose(contrib.sum(axis=1), t2, rtol=1e-9, atol=1e-9)


def test_t2_calibration_quantiles_ordered():
    cal = calibration.fit(*_clean(), SENSORS)
    assert 0 < cal["t2_median"] < cal["t2_q95"]


def test_sigma_ratio_recorded():
    """sigma_w / sigma_global 기록 (설계서 1.3, 17장)."""
    res_mean, res_std = _clean()
    sg = np.full(len(SENSORS), 10.0)
    cal = calibration.fit(res_mean, res_std, SENSORS, sigma_global=sg)
    assert np.allclose(cal["sigma_ratio"], np.asarray(cal["sigma_w"]) / 10.0)


def test_window_residual_stats_shapes():
    r = np.zeros((7, 30, 5))
    m, s = calibration.window_residual_stats(r)
    assert m.shape == (7, 5) and s.shape == (7, 5)
