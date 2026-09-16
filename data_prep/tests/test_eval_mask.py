"""평가용 indeterminate 마스크 규칙 검증 (원본 데이터·weight 불필요)."""
import numpy as np
import pandas as pd
import pytest

from src.analysis.reversion import exit_events
from src.common import write_parquet
from src.label.eval_mask import MaskAssertionError, build_mask

SEQ_LEN = 45
THETA = 9.4


class StubPaths:
    """state parquet 만 필요로 하는 build_mask 용 최소 스텁."""

    def __init__(self, root):
        self.root = root

    def state(self, theta_name, unit, scenario_id):
        return self.root / theta_name / f"u{unit}" / f"{scenario_id}.parquet"


def make_index(rows):
    """scenario_index long format 최소 컬럼."""
    return pd.DataFrame([{"unit": u, "scenario_id": s, "type": "bias", "param": 0.5,
                          "timing_p": 0.2, "tau_s": 60, "tau_d": 70, "T_u": T,
                          "theta_name": "theta_primary", "degraded": True}
                         for u, s, T in rows])


def events_from(label, T_u, times=None, delta=None, yhat=None):
    """라벨 시퀀스로부터 이벤트 테이블을 만든다 (unit=1, scenario='s')."""
    label = np.asarray(label)
    n = len(label)
    times = np.arange(SEQ_LEN, SEQ_LEN + n) if times is None else np.asarray(times)
    delta = np.zeros(n) if delta is None else np.asarray(delta)
    yhat = np.full(n, 50.0) if yhat is None else np.asarray(yhat)
    ev = exit_events(times, label, delta, yhat, T_u, THETA)
    for e in ev:
        e["unit"], e["scenario_id"] = 1, "s"
    return pd.DataFrame(ev) if ev else pd.DataFrame(
        columns=["unit", "scenario_id", "t_exit", "is_final_exit", "reentry_within_20"])


def write_state(paths, unit, sid, times, label):
    write_parquet(pd.DataFrame({"time": np.asarray(times).astype(int),
                                "delta": np.zeros(len(label)),
                                "label": np.asarray(label).astype(np.int8)}),
                  paths.state("theta_primary", unit, sid))


# ---------------------------------------------------------------- 규칙
def test_no_reversion_gives_nan():
    """복귀가 없으면 행은 만들되 mask_from_cycle 은 NaN."""
    lab = np.array([0] * 20 + [1] * 30)          # 진입만 하고 끝까지 1
    T_u = SEQ_LEN + len(lab) - 1
    mk = build_mask(None, make_index([(1, "s", T_u)]), events_from(lab, T_u),
                    "theta_primary", SEQ_LEN, verify=False, log=lambda *_: None)
    assert len(mk) == 1
    assert pd.isna(mk["mask_from_cycle"].iloc[0])
    assert mk["n_masked_cycles"].iloc[0] == 0
    assert mk["frac_masked"].iloc[0] == 0.0


def test_reentry_scenario_is_not_masked():
    """복귀 후 다시 진입해 끝까지 1 이면 마스크 대상이 아니다."""
    lab = np.array([0] * 10 + [1] * 15 + [0] * 5 + [1] * 20)
    T_u = SEQ_LEN + len(lab) - 1
    ev = events_from(lab, T_u)
    assert len(ev) == 1 and not bool(ev["is_final_exit"].iloc[0])
    mk = build_mask(None, make_index([(1, "s", T_u)]), ev,
                    "theta_primary", SEQ_LEN, verify=False, log=lambda *_: None)
    assert pd.isna(mk["mask_from_cycle"].iloc[0])


def test_final_exit_is_masked_to_end():
    """최종 복귀 이후 구간이 T_u 까지 마스크된다."""
    lab = np.array([0] * 10 + [1] * 25 + [0] * 15)
    T_u = SEQ_LEN + len(lab) - 1
    t_exit = SEQ_LEN + 35
    mk = build_mask(None, make_index([(1, "s", T_u)]), events_from(lab, T_u),
                    "theta_primary", SEQ_LEN, verify=False, log=lambda *_: None)
    r = mk.iloc[0]
    assert r["mask_from_cycle"] == t_exit
    assert r["mask_to_cycle"] == T_u
    assert r["n_masked_cycles"] == r["mask_to_cycle"] - r["mask_from_cycle"] + 1
    assert r["n_masked_cycles"] == 15
    assert r["frac_masked"] == pytest.approx(15 / (T_u - (SEQ_LEN - 1)))


def test_n_masked_matches_span_for_all_rows():
    """마스크가 있는 모든 행에서 n_masked = to − from + 1."""
    cases = [([0] * 5 + [1] * 20 + [0] * 30, "s1"),
             ([1] * 40 + [0] * 10, "s2"),
             ([0] * 10 + [1] * 12 + [0] * 8 + [1] * 12 + [0] * 25, "s3")]
    rows, evs = [], []
    for lab, sid in cases:
        T_u = SEQ_LEN + len(lab) - 1
        rows.append((1, sid, T_u))
        e = events_from(np.array(lab), T_u)
        e["scenario_id"] = sid
        evs.append(e)
    mk = build_mask(None, make_index(rows), pd.concat(evs, ignore_index=True),
                    "theta_primary", SEQ_LEN, verify=False, log=lambda *_: None)
    has = mk[mk["mask_from_cycle"].notna()]
    assert len(has) == 3          # 셋 다 마지막이 0 으로 끝나 최종 복귀가 있다
    assert (has["n_masked_cycles"] == has["mask_to_cycle"] - has["mask_from_cycle"] + 1).all()


def test_only_last_exit_used_when_multiple():
    """복귀가 여러 번이면 최종 복귀(이후 전부 0)만 마스크 시작점이 된다."""
    lab = np.array([0] * 5 + [1] * 10 + [0] * 6 + [1] * 10 + [0] * 19)
    T_u = SEQ_LEN + len(lab) - 1
    ev = events_from(lab, T_u)
    assert len(ev) == 2 and int(ev["is_final_exit"].sum()) == 1
    mk = build_mask(None, make_index([(1, "s", T_u)]), ev,
                    "theta_primary", SEQ_LEN, verify=False, log=lambda *_: None)
    assert mk["mask_from_cycle"].iloc[0] == SEQ_LEN + 31


# ---------------------------------------------------------------- 검증 경로
def test_verify_passes_on_consistent_labels(tmp_path):
    """마스크 이후 라벨이 전부 0 이면 verify 통과."""
    paths = StubPaths(tmp_path)
    lab = np.array([0] * 10 + [1] * 25 + [0] * 15)
    T_u = SEQ_LEN + len(lab) - 1
    times = np.arange(SEQ_LEN, SEQ_LEN + len(lab))
    write_state(paths, 1, "s", times, lab)
    mk = build_mask(paths, make_index([(1, "s", T_u)]), events_from(lab, T_u),
                    "theta_primary", SEQ_LEN, verify=True, log=lambda *_: None)
    assert mk["mask_from_cycle"].iloc[0] == SEQ_LEN + 35


def test_verify_raises_when_positive_after_mask(tmp_path):
    """마스크 시작 이후 양성이 남아 있으면 예외 (라벨-이벤트 불일치 탐지)."""
    paths = StubPaths(tmp_path)
    lab = np.array([0] * 10 + [1] * 25 + [0] * 15)
    T_u = SEQ_LEN + len(lab) - 1
    times = np.arange(SEQ_LEN, SEQ_LEN + len(lab))
    ev = events_from(lab, T_u)
    corrupted = lab.copy()
    corrupted[-3:] = 1                      # 디스크 라벨만 오염시킨다
    write_state(paths, 1, "s", times, corrupted)
    with pytest.raises(MaskAssertionError):
        build_mask(paths, make_index([(1, "s", T_u)]), ev,
                   "theta_primary", SEQ_LEN, verify=True, log=lambda *_: None)
