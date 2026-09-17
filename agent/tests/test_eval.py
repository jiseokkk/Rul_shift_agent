import numpy as np
import pandas as pd

from src.eval.cycle_table import build_cycle_table, cycle_metrics, dedup_negatives
from src.eval.unit_table import build_unit_table, unit_metrics


def _idx():
    return pd.DataFrame([
        {"unit": 1, "scenario_id": "A", "type": "bias", "sensor": "T24", "param": 1.0, "dir": "neg", "timing_p": 0.2, "T_u": 100,
         "tau_s": 60, "tau_d": 70, "degraded": True, "mask_from_cycle": 90},
        {"unit": 1, "scenario_id": "B", "type": "bias", "sensor": "T30", "param": 1.0, "dir": "neg", "timing_p": 0.2, "T_u": 100,
         "tau_s": 60, "tau_d": np.nan, "degraded": False, "mask_from_cycle": np.nan},
    ])


def _labels():
    a = pd.Series(0, index=range(45, 101)); a.loc[70:89] = 1
    b = pd.Series(0, index=range(45, 101))
    return {(1, "A"): a, (1, "B"): b}


def _dec(alarm_from_A, alarm_from_B=None, err_cycles=()):
    rows = []
    for sid, start in (("A", alarm_from_A), ("B", alarm_from_B)):
        for t in range(55, 101):
            d = np.nan if t in err_cycles else (1 if (start is not None and t >= start) else 0)
            rows.append({"unit": 1, "scenario_id": sid, "cycle": t, "degraded": d, "confidence": 0.8, "suspected_sensors": '["T24"]'})
    return pd.DataFrame(rows)


def test_cycle_table_mask_dedup_error():
    T = build_cycle_table(_dec(72, None, err_cycles=(56,)), _idx(), _labels(), 55)
    assert T[(T.scenario_id == "A")].cycle.max() == 89           # 마스크 90~ 제외
    assert (T[T.cycle == 56].error).all()
    Td = dedup_negatives(T)
    pre = Td[Td.pre_tau_s]
    assert len(pre) == 5 and pre.groupby("cycle").size().max() == 1  # 55~59, 두 시나리오 → 1개씩
    m = cycle_metrics(Td)
    assert m["TP"] == 18 and m["FN"] == 2 and m["FP"] == 0        # A: 72~89 TP, 70~71 FN
    assert m["recall"] == 0.9 and m["FAR"] == 0
    assert m["n_error"] == 1 and cycle_metrics(T)["n_error"] == 2   # 중복 제거로 pre-τ_s 오류 2행 → 1행


def test_unit_table_classification():
    idx, jf, w, D = _idx(), 55, 5, 5
    U = build_unit_table(_dec(72), idx, jf, w, D).set_index("scenario_id")
    assert U.loc["A", "result"] == "TP" and U.loc["A", "delay"] == 2 and U.loc["A", "iso_hit"]
    assert U.loc["B", "result"] == "TN"
    U = build_unit_table(_dec(62), idx, jf, w, D).set_index("scenario_id")
    assert U.loc["A", "result"] == "Early" and U.loc["A", "delay"] == -8
    U = build_unit_table(_dec(66), idx, jf, w, D).set_index("scenario_id")
    assert U.loc["A", "result"] == "TP" and U.loc["A", "delay"] == -4     # w 안
    U = build_unit_table(_dec(80), idx, jf, w, D).set_index("scenario_id")
    assert U.loc["A", "result"] == "Late" and U.loc["A", "delay"] == 10
    U = build_unit_table(_dec(None, 65), idx, jf, w, D).set_index("scenario_id")
    assert U.loc["A", "result"] == "Miss" and U.loc["B", "result"] == "FP"
    U = build_unit_table(_dec(56), idx, jf, w, D).set_index("scenario_id")
    assert U.loc["A", "pre_alarm"] and U.loc["A", "t_hat"] == 60         # τ_s 이전 알람은 t_hat 후보 아님
    m = unit_metrics(build_unit_table(_dec(72, 65), idx, jf, w, D))
    assert m["detection_rate"] == 1.0 and m["scenario_FAR"] == 1.0 and m["MDD_mean"] == 2
