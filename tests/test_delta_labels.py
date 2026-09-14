import numpy as np
import pandas as pd
import pytest

from src.label.build_labels import label_one, resolve_thetas, theta_series
from src.label.delta import DeltaAssertionError, compute_delta


def frames(T=100, tau_s=60, shift_from=None):
    t = np.arange(45, T + 1)
    clean = pd.DataFrame({"time": t, "pred": np.linspace(125, 0, len(t))})
    sh = clean.copy()
    start = tau_s if shift_from is None else shift_from
    sh.loc[sh["time"] >= start, "pred"] += 10
    return clean, sh


def test_delta_ok_and_values():
    c, s = frames()
    d = compute_delta(c, s, tau_s=60)
    assert (d.loc[d["time"] < 60, "delta"] == 0).all()
    assert np.allclose(d.loc[d["time"] >= 60, "delta"], 10)
    assert list(d.columns) == ["time", "pred_clean", "pred_shift", "delta"]


def test_delta_assert_before_tau_s():
    c, s = frames(shift_from=50)  # τ_s 앞으로 샘
    with pytest.raises(DeltaAssertionError):
        compute_delta(c, s, tau_s=60)
    d = compute_delta(c, s, tau_s=60, strict=False)
    assert (d.loc[d["time"] < 60, "delta"] > 0).any()


def test_resolve_thetas_defaults():
    lab = {"thetas": {"theta_primary": {"kind": "fixed", "value": None},
                      "theta_alt1": {"kind": "adaptive", "ratio": 0.2, "floor": "theta_primary"},
                      "theta_alt2": {"kind": "fixed", "value": None, "source": "test_rmse"}}}
    cv = {"recommended": {"theta_primary": 3.3, "theta_alt2": None}}
    rep = {"finetune": {"529": {"rmse": 12.4}}}
    th = resolve_thetas(lab, cv, rep, 529)
    assert th["theta_primary"]["value"] == 3.3
    assert th["theta_alt2"]["value"] == 12.4
    assert th["theta_alt1"]["floor"] == 3.3
    assert np.allclose(theta_series(th["theta_alt1"], np.array([100.0, 10.0, 0.0])), [20.0, 3.3, 3.3])


def test_label_one_adaptive_floor_prevents_end_of_life_trigger():
    c, s = frames(T=140, tau_s=100)
    d = compute_delta(c, s, tau_s=100)
    d["delta"] = 2.0  # 작은 잡음 수준 δ
    spec = {"kind": "adaptive", "ratio": 0.2, "floor": 5.0}
    out, res = label_one(d, spec, k=5, m=7, ratio=0.5)
    assert res["tau_d_idx"] is None  # 말기 ŷ→0 이어도 바닥 5 때문에 진입 없음
