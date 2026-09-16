import numpy as np
import pandas as pd
import pytest

from src.data import cmapss
from src.data.shift import (compute_sign_deg, inject, make_scenarios, multi_I_sign_choices,
                            n_scenarios_per_unit, scenario_id)
from src.data.split import tau_s_of

GRID = {
    "base_seed": 529, "timing_p": [0.2, 0.4, 0.6, 0.8], "sensors_single": ["T24", "T30", "T50"],
    "types": {"bias": {"alpha": [0.1, 0.2, 0.3, 0.5], "dir": ["pos", "neg"]},
              "gain": {"alpha": [0.1, 0.2, 0.3, 0.5], "dir": ["pos", "neg"]},
              "noise": {"beta": [0.5, 1.0, 2.0]}, "stuck": {},
              "multi_C": {"sets": [["T24", "T30", "T50"]], "alpha": [0.2, 0.3]},
              "multi_I": {"sets": [["T24", "T30", "T50"]], "alpha": [0.2, 0.3]}},
}


def synth_unit(T=200, unit=7, seed=0):
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({"id": unit, "time": np.arange(1, T + 1)})
    for c in cmapss.RAW_COLUMNS[2:]:
        df[c] = 100.0 + rng.normal(0, 1, T) + np.linspace(0, 3, T)
    df["op3"] = 100.0  # 상수
    return df[cmapss.RAW_COLUMNS]


def synth_norm():
    npar = np.zeros((17, 2))
    npar[:, 0] = 100.0
    npar[:, 1] = 2.0
    npar[2, 1] = 0.0  # op3
    return npar


SIGN = {"sign": {s: 1 for s in cmapss.RAW_COLUMNS[5:]}}


def test_tau_s_table_from_plan():
    assert [tau_s_of(128, p, 55) for p in (0.2, 0.4, 0.6, 0.8)] == [70, 84, 99, 113]
    assert [tau_s_of(199, p, 55) for p in (0.2, 0.4, 0.6, 0.8)] == [84, 113, 141, 170]
    assert [tau_s_of(362, p, 55) for p in (0.2, 0.4, 0.6, 0.8)] == [116, 178, 239, 301]


def test_gain_alpha_by_direction():
    g = {**GRID, "types": {**GRID["types"], "gain": {"alpha": {"pos": [0.5, 1.0], "neg": [0.25, 0.5]}, "dir": ["pos", "neg"]}}}
    ids = [s["scenario_id"] for s in make_scenarios(g, 200, 55) if s["scenario_id"].startswith("gain_")]
    assert len(ids) == 3 * 4 * 4  # 3 sensors × (2 pos + 2 neg) × 4 timings
    assert "gain_T24_a1.0_pos_p0.2" in ids and "gain_T24_a1.0_neg_p0.2" not in ids
    assert "gain_T24_a0.25_neg_p0.2" in ids and "gain_T24_a0.25_pos_p0.2" not in ids


def test_scenario_count_and_ids():
    assert n_scenarios_per_unit(GRID) == 256
    ids = [s["scenario_id"] for s in make_scenarios(GRID, 200, 55)]
    assert "bias_T24_a0.2_pos_p0.4" in ids
    assert "stuck_T30_na_na_p0.6" in ids
    assert "noise_T50_b1.0_na_p0.2" in ids
    assert "multiC_T24+T30+T50_a0.2_na_p0.8" in ids
    assert all(len(i.split("_")) == 5 for i in ids)


def _scen(type_key, sensors, param, d, p, T):
    return dict(type=type_key, sensors=sensors, param_name="alpha", param=param, dir=d, timing_p=p,
                tau_s=tau_s_of(T, p, 55), scenario_id=scenario_id(type_key, sensors, f"a{param}", d, p))


def test_bias_unchanged_before_tau_s_and_magnitude():
    u = synth_unit()
    sc = _scen("bias", ["T24"], 0.2, "pos", 0.4, len(u))
    out, meta = inject(u, sc, synth_norm(), SIGN, 529, 7)
    before, after = out["time"] < sc["tau_s"], out["time"] >= sc["tau_s"]
    pd.testing.assert_frame_equal(out[before].reset_index(drop=True), u[before].reset_index(drop=True))
    diff = (out.loc[after, "s2"] - u.loc[after, "s2"]).to_numpy()
    assert np.allclose(diff, 0.2 * 2.0)
    # 다른 센서는 불변
    assert np.array_equal(out["s3"].to_numpy(), u["s3"].to_numpy())
    assert meta["tau_s"] == sc["tau_s"] and meta["rng_seed"] is None


def test_gain_mean_centered():
    u = synth_unit()
    sc = _scen("gain", ["T30"], 0.5, "neg", 0.6, len(u))
    out, _ = inject(u, sc, synth_norm(), SIGN, 529, 7)
    after = out["time"] >= sc["tau_s"]
    expected = 100.0 + (u.loc[after, "s3"] - 100.0) * 0.5
    assert np.allclose(out.loc[after, "s3"], expected)


def test_stuck_holds_value_at_tau_s():
    u = synth_unit()
    sc = _scen("stuck", ["T50"], float("nan"), "na", 0.2, len(u))
    out, meta = inject(u, sc, synth_norm(), SIGN, 529, 7)
    after = out["time"] >= sc["tau_s"]
    x_tau = float(u.loc[u["time"] == sc["tau_s"], "s4"].iloc[0])
    assert np.all(out.loc[after, "s4"] == x_tau) and meta["stuck_value"] == x_tau


def test_noise_reproducible_with_seed():
    u = synth_unit()
    sc = _scen("noise", ["T24"], 1.0, "na", 0.8, len(u))
    sc["param_name"] = "beta"
    a, ma = inject(u, sc, synth_norm(), SIGN, 529, 7)
    b, mb = inject(u, sc, synth_norm(), SIGN, 529, 7)
    assert ma["rng_seed"] == mb["rng_seed"] and np.array_equal(a["s2"], b["s2"])
    c, mc = inject(u, sc, synth_norm(), SIGN, 529, 8)  # 다른 unit → 다른 seed
    assert mc["rng_seed"] != ma["rng_seed"]
    before = a["time"] < sc["tau_s"]
    assert np.array_equal(a.loc[before, "s2"], u.loc[before, "s2"])


def test_multi_I_excludes_deg_patterns():
    ch = multi_I_sign_choices(3, [1, 1, 1])
    assert len(ch) == 6 and (1, 1, 1) not in ch and (-1, -1, -1) not in ch
    u = synth_unit()
    sc = _scen("multi_I", ["T24", "T30", "T50"], 0.3, "na", 0.4, len(u))
    out, meta = inject(u, sc, synth_norm(), SIGN, 529, 7)
    assert tuple(meta["signs"]) in ch
    after = out["time"] >= sc["tau_s"]
    for s, sg in zip(["s2", "s3", "s4"], meta["signs"]):
        assert np.allclose(out.loc[after, s] - u.loc[after, s], sg * 0.3 * 2.0)


def test_multi_C_follows_sign_deg():
    u = synth_unit()
    sign = {"sign": dict(SIGN["sign"])}
    sign["sign"]["s3"] = -1
    sc = _scen("multi_C", ["T24", "T30", "T50"], 0.2, "na", 0.6, len(u))
    out, meta = inject(u, sc, synth_norm(), sign, 529, 7)
    assert meta["signs"] == [1, -1, 1]
    after = out["time"] >= sc["tau_s"]
    assert np.allclose(out.loc[after, "s3"] - u.loc[after, "s3"], -0.2 * 2.0)


def test_unused_sensor_rejected():
    u = synth_unit()
    sc = _scen("bias", ["s1"], 0.2, "pos", 0.4, len(u))
    with pytest.raises(ValueError):
        inject(u, sc, synth_norm(), SIGN, 529, 7)


def test_sign_deg_direction():
    df = pd.concat([synth_unit(T=150, unit=1, seed=1), synth_unit(T=180, unit=2, seed=2)])
    sd = compute_sign_deg(df)
    assert sd["sign"]["s2"] == 1  # 선형 증가 추세
    assert "diff_mean" in sd
