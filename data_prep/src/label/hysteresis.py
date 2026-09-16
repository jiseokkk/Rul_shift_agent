"""Phase D-3: k-of-m 히스테리시스 상태 머신 + 역방향 채우기 (계획서 §5 D-3 의사코드 구현).

state = NORMAL; τ_d = None; label[:] = 0
for t in 45 .. T_u:
    lo = max(45, t − m + 1)                    # 초기 구간은 있는 만큼만
    recent = δ[lo .. t]
    if state == NORMAL and count(recent > θ_high) >= k:
        t_enter = first index in [lo..t] with δ > θ_high
        label[t_enter .. t] = 1                # 역방향 채우기
        state = DEGRADED; τ_d = τ_d or t_enter
    elif state == DEGRADED and count(recent <= θ_low) >= k:
        t_exit = first index in [lo..t] with δ <= θ_low
        label[t_exit .. t] = 0                 # 역방향 채우기 (대칭)
        state = NORMAL
    else:
        label[t] = state

θ_high 는 스칼라 또는 δ 와 같은 길이의 배열(θ_alt1 처럼 cycle 별 적응). θ_low = ratio · θ_high.
"""
from __future__ import annotations

import numpy as np

NORMAL, DEGRADED = 0, 1


def hysteresis_label(delta: np.ndarray, theta_high, k: int, m: int, theta_low_ratio: float = 0.5,
                     theta_low=None) -> dict:
    """반환: label(0/1), state(각 t 판정 후 상태), tau_d_idx(첫 진입 index 또는 None), enters, exits.

    index 0 이 첫 예측 cycle(45) 에 대응한다. 시간으로 바꾸려면 start_time 을 더한다.
    """
    delta = np.asarray(delta, dtype=float)
    n = len(delta)
    th_hi = np.broadcast_to(np.asarray(theta_high, dtype=float), (n,)).copy()
    th_lo = th_hi * theta_low_ratio if theta_low is None else np.broadcast_to(np.asarray(theta_low, dtype=float), (n,)).copy()
    assert 1 <= k <= m, (k, m)

    label = np.zeros(n, dtype=np.int8)
    state_arr = np.zeros(n, dtype=np.int8)
    state = NORMAL
    tau_d_idx = None
    enters, exits = [], []
    above = delta > th_hi
    below = delta <= th_lo

    for t in range(n):
        lo = max(0, t - m + 1)
        if state == NORMAL and int(above[lo:t + 1].sum()) >= k:
            t_enter = lo + int(np.argmax(above[lo:t + 1]))
            label[t_enter:t + 1] = 1
            state = DEGRADED
            enters.append(t_enter)
            if tau_d_idx is None:
                tau_d_idx = t_enter
        elif state == DEGRADED and int(below[lo:t + 1].sum()) >= k:
            t_exit = lo + int(np.argmax(below[lo:t + 1]))
            label[t_exit:t + 1] = 0
            state = NORMAL
            exits.append(t_exit)
        else:
            label[t] = 1 if state == DEGRADED else 0
        state_arr[t] = state

    return {"label": label, "state": state_arr, "tau_d_idx": tau_d_idx,
            "enters": enters, "exits": exits, "theta_high": th_hi, "theta_low": th_lo}


def summarize(res: dict, times: np.ndarray, tau_s: int) -> dict:
    """scenario_index 결과 컬럼."""
    label = res["label"]
    times = np.asarray(times)
    degraded = res["tau_d_idx"] is not None
    tau_d = int(times[res["tau_d_idx"]]) if degraded else None
    after = times >= tau_s
    return {
        "degraded": bool(degraded),
        "tau_d": tau_d,
        "delay": (tau_d - tau_s) if degraded else None,
        "n_degraded_cycles": int(label.sum()),
        "n_transitions": int(len(res["enters"]) + len(res["exits"])),
        "n_reversions": int(len(res["exits"])),
        "frac_degraded_after_tau_s": float(label[after].mean()) if after.any() else 0.0,
    }
