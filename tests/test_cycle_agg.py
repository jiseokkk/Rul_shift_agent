"""cycle 집계: 합성 bias → Delta_mu ≈ alpha, exceedance = n/n (설계서 4.2, 4.3)."""
import numpy as np

from agent_rul.tools import eda

P = 3
Q95 = np.full(P, 1.9)


def _ws(z_w, std_ratio=None, contrib=None):
    """compute_window_stats 출력의 최소 형태."""
    z = np.asarray(z_w, dtype=float)
    n_w = z.shape[0]
    sr = np.ones_like(z) if std_ratio is None else np.asarray(std_ratio, dtype=float)
    cf = np.full_like(z, 1.0 / P) if contrib is None else np.asarray(contrib, float)
    return {"n_windows": n_w, "z_w": z, "std_ratio": sr, "contrib_frac": cf,
            "t2": np.full(n_w, 10.0)}


def _clean_cycle(n_w=24, level=0.0):
    rng = np.random.default_rng(0)
    return _ws(rng.normal(level, 0.2, size=(n_w, P)))


def test_bias_gives_full_exceedance_and_first_window():
    z = np.zeros((24, P))
    z[:, 1] = 2.9
    s = eda.aggregate_cycle(_ws(z), Q95)["sensor"]
    assert s["exceed_k"][1] == 24 and s["exceed_n"][1] == 24
    assert s["first_exceed"][1] == 1               # 1-based
    assert s["exceed_k"][0] == 0 and s["first_exceed"][0] == -1
    assert np.isclose(s["z_w_median"][1], 2.9)


def test_delta_mu_approximates_injected_step():
    alpha_z = 2.9
    per_cycle = [eda.aggregate_cycle(_clean_cycle(), Q95) for _ in range(4)]
    z = np.zeros((24, P))
    z[:, 1] = alpha_z
    per_cycle.append(eda.aggregate_cycle(_ws(z), Q95))
    eda.fill_contrasts(per_cycle, L_c=4)
    dmu = per_cycle[-1]["sensor"]["delta_mu"]
    assert abs(dmu[1] - alpha_z) < 0.15
    assert abs(dmu[0]) < 0.15


def test_delta_sigma_zero_for_pure_bias():
    per_cycle = [eda.aggregate_cycle(_clean_cycle(), Q95) for _ in range(4)]
    z = np.zeros((24, P))
    z[:, 1] = 2.9
    per_cycle.append(eda.aggregate_cycle(_ws(z), Q95))
    eda.fill_contrasts(per_cycle, L_c=4)
    assert abs(per_cycle[-1]["sensor"]["delta_sigma"][1]) < 1e-9


def test_delta_sigma_catches_noise_increase():
    per_cycle = [eda.aggregate_cycle(_clean_cycle(), Q95) for _ in range(4)]
    sr = np.ones((24, P))
    sr[:, 2] = 2.0
    rng = np.random.default_rng(1)
    per_cycle.append(eda.aggregate_cycle(_ws(rng.normal(0, 0.2, size=sr.shape), std_ratio=sr), Q95))
    eda.fill_contrasts(per_cycle, L_c=4)
    assert per_cycle[-1]["sensor"]["delta_sigma"][2] > 0.9


def test_first_cycle_has_nan_contrasts():
    per_cycle = [eda.aggregate_cycle(_clean_cycle(), Q95)]
    eda.fill_contrasts(per_cycle, L_c=4)
    assert np.all(np.isnan(per_cycle[0]["sensor"]["delta_mu"]))


def test_incremental_contrast_matches_batch():
    """contrast(cur, prev) 를 cycle 하나씩 적용한 결과 == fill_contrasts 배치 결과."""
    rng = np.random.default_rng(3)
    cycles = [eda.aggregate_cycle(_ws(rng.normal(0, 0.3, size=(20, P))), Q95) for _ in range(9)]
    batch = [dict(sensor={k: v.copy() for k, v in c["sensor"].items()}, cycle=dict(c["cycle"]))
             for c in cycles]
    eda.fill_contrasts(batch, L_c=4)
    hist = []
    for c in cycles:
        eda.contrast(c, hist[-4:])
        hist.append(c)
    for a, b in zip(batch, hist):
        np.testing.assert_array_equal(a["sensor"]["delta_mu"], b["sensor"]["delta_mu"])
        np.testing.assert_array_equal(a["sensor"]["delta_sigma"], b["sensor"]["delta_sigma"])


def test_onset_mid_flight_first_exceed():
    z = np.zeros((24, P))
    z[10:, 0] = 3.0
    agg = eda.aggregate_cycle(_ws(z), Q95)
    assert agg["sensor"]["first_exceed"][0] == 11
    assert agg["sensor"]["exceed_k"][0] == 14


def test_short_flight_flag():
    assert eda.aggregate_cycle(_clean_cycle(n_w=4), Q95, min_windows_short=6)["cycle"]["short_flight"] is True
    assert eda.aggregate_cycle(_clean_cycle(n_w=24), Q95, min_windows_short=6)["cycle"]["short_flight"] is False


def test_to_tables_columns():
    per_cycle = [eda.aggregate_cycle(_clean_cycle(), Q95)]
    eda.fill_contrasts(per_cycle, L_c=4)
    cs, c = eda.to_tables([5], per_cycle, ["A", "B", "C"])
    assert len(cs) == 3 and len(c) == 1
    for col in eda.SENSOR_COLS:
        assert col in cs[0]
    assert cs[0]["cycle"] == 5 and cs[0]["sensor"] == "A"
