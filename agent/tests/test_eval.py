"""시나리오 단위 v2 채점 (docs/eval_v2_scenario.md §3)."""
import numpy as np
import pandas as pd
import pytest

from src.eval.baselines import always_one, always_zero, random_alarms
from src.data.inputs import load_scenario_list
from src.eval.scenario_table import classify, end_cycles, first_alarms, scenario_metrics
from src.eval.stats import unit_bootstrap

JF = 55


def _idx():
    return pd.DataFrame([
        {"unit": 1, "scenario_id": "A", "type": "bias", "sensor": "T24", "param": 1.0, "dir": "neg", "timing_p": 0.2, "T_u": 100,
         "tau_s": 60, "tau_d": 70, "degraded": True},
        {"unit": 1, "scenario_id": "B", "type": "bias", "sensor": "T30", "param": 1.0, "dir": "neg", "timing_p": 0.2, "T_u": 100,
         "tau_s": 60, "tau_d": np.nan, "degraded": False},
        {"unit": 2, "scenario_id": "C", "type": "multi_C", "sensor": "T24+T30+T50", "param": 0.5, "dir": "na", "timing_p": 0.4, "T_u": 100,
         "tau_s": 60, "tau_d": 72, "degraded": True},
    ])


def _dec(alarms: dict, err=(), sus='["T24"]'):
    """alarms: sid → 판정 1 로 둘 cycle 집합 (iterable) 또는 None."""
    rows = []
    for u, sid in ((1, "A"), (1, "B"), (2, "C")):
        on = set(alarms.get(sid) or [])
        for t in range(JF, 101):
            d = np.nan if t in err else (1 if t in on else 0)
            rows.append({"unit": u, "scenario_id": sid, "cycle": t, "degraded": d, "confidence": 0.8, "suspected_sensors": sus})
    return pd.DataFrame(rows)


def _res(alarms, Delta=5, w=0, H=40, k=1, **kw):
    S = classify(first_alarms(_dec(alarms, **kw), _idx(), JF, k), Delta, w, H).set_index("scenario_id")
    return S


def test_first_alarm_principle_and_categories():
    S = _res({"A": range(72, 101)})
    assert S.loc["A", "result"] == "TP" and S.loc["A", "delay"] == 2 and S.loc["A", "iso_hit"] == True
    assert S.loc["B", "result"] == "TN" and S.loc["C", "result"] == "Miss"
    S = _res({"A": range(56, 101)})                     # 오염 전부터 켜져 있음 → 창과 겹쳐도 PreContam
    assert S.loc["A", "result"] == "PreContam" and S.loc["A", "t_hat"] == 56
    S = _res({"A": [57, 73, 74, 75]})                   # 꺼졌다 창 안에서 다시 켜져도 첫 경보 기준
    assert S.loc["A", "result"] == "PreContam"
    S = _res({"A": range(65, 101)})                     # 오염 후, 저하 전
    assert S.loc["A", "result"] == "PreDegr"
    S = _res({"A": range(76, 101)})                     # 창(70~75) 이후 → Miss (Late 범주 없음)
    assert S.loc["A", "result"] == "Miss" and pd.isna(S.loc["A", "delay"])
    S = _res({"A": [70]})                               # 창 시작 cycle, 한 번만 → TP (유지 여부 무관)
    assert S.loc["A", "result"] == "TP" and S.loc["A", "delay"] == 0


def test_window_front_margin_and_tau_s_clip():
    S = _res({"A": range(67, 101)}, w=5)                # τ_d − 5 = 65 ≤ 67 → TP, delay −3
    assert S.loc["A", "result"] == "TP" and S.loc["A", "delay"] == -3
    S = _res({"A": range(59, 101)}, w=20)               # w 가 커도 창은 τ_s 에서 잘림 → 59 는 PreContam
    assert S.loc["A", "result"] == "PreContam" and S.loc["A", "window_lo"] == 60


def test_nondegraded_horizon():
    S = _res({"B": [58]})
    assert S.loc["B", "result"] == "FP_clean"
    S = _res({"B": [95]})
    assert S.loc["B", "result"] == "FP_contam"
    S = _res({"B": [95]}, H=30)                         # τ_s + 30 = 90 이후 경보는 안 봄
    assert S.loc["B", "result"] == "TN"


def test_k_consecutive_and_error():
    S = _res({"A": [71, 73, 74, 75]}, k=3)              # 3 연속은 73 부터 → TP delay 3
    assert S.loc["A", "result"] == "TP" and S.loc["A", "t_hat"] == 73
    S = _res({"A": [71, 72]}, k=3)
    assert S.loc["A", "result"] == "Miss"
    S = _res({"A": range(72, 101)}, err=(72,))          # ERROR cycle 은 경보 아님
    assert S.loc["A", "t_hat"] == 73 and S.loc["A", "n_error"] == 1


def test_isolation_multi_and_metrics():
    S = _res({"A": [72], "B": [95], "C": [73]}, sus='["T50", "Nc"]')
    assert S.loc["C", "result"] == "TP" and S.loc["C", "iso_hit"] == True and S.loc["C", "iso_jaccard"] == pytest.approx(1 / 4)
    m = scenario_metrics(S.reset_index())
    assert m["detection_rate"] == 1.0 and m["scenario_FAR"] == 1.0 and m["FAR_contam"] == 1.0 and m["FAR_clean"] == 0
    assert m["isolation_rate"] == 0.5 and m["delay_mean"] == 1.5 and m["pre_contam_all"] == 0


def test_baselines_and_curve():
    FA = first_alarms(_dec({}), _idx(), JF)
    m1 = scenario_metrics(classify(always_one(FA, JF), 5, 0, 40))
    assert m1["pre_contam_rate"] == 1.0 and m1["scenario_FAR"] == 1.0 and m1["detection_rate"] == 0
    m0 = scenario_metrics(classify(always_zero(FA), 5, 0, 40))
    assert m0["miss_rate"] == 1.0 and m0["scenario_FAR"] == 0
    R = random_alarms(FA, 0.5, JF, np.random.default_rng(0))
    assert R["t_hat"].notna().all() and (R["t_hat"] >= JF).all()


def test_end_cycles():
    E = end_cycles(_idx(), 5, 40).set_index("scenario_id")["end_cycle"]
    assert E["A"] == 75 and E["C"] == 77          # 저하: τ_d + Δ
    assert E["B"] == 100                          # 비저하: min(τ_s + H, T_u) = min(100, 100)
    idx = _idx(); idx.loc[idx.scenario_id == "B", "T_u"] = 150
    assert end_cycles(idx, 5, 40).set_index("scenario_id")["end_cycle"]["B"] == 100   # τ_s + 40


def test_unit_bootstrap_shape():
    S = classify(first_alarms(_dec({"A": [72], "C": [73]}), _idx(), JF), 5, 0, 40)
    ci = unit_bootstrap(S, ["detection_rate", "scenario_FAR"], n_boot=50)
    assert list(ci["metric"]) == ["detection_rate", "scenario_FAR"] and (ci["lo"] <= ci["point"]).all() and (ci["point"] <= ci["hi"]).all()


def test_scenario_list_passes_end_cycle(tmp_path):
    p = tmp_path / "s.csv"
    pd.DataFrame({"unit": [1, 1], "scenario_id": ["A", "B"], "tau_s": [60, 60], "end_cycle": [75, 100]}).to_csv(p, index=False)
    df = load_scenario_list(str(p))
    assert list(df.columns) == ["unit", "scenario_id", "end_cycle"] and df.end_cycle.tolist() == [75, 100]
    pd.DataFrame({"unit": [1], "scenario_id": ["A"], "tau_s": [60]}).to_csv(p, index=False)
    assert list(load_scenario_list(str(p)).columns) == ["unit", "scenario_id"]
