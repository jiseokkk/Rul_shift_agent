"""데이터 로더 — HDF5(clean unit), 오염 시나리오(series.npz), window 분할.

세 가지가 한 파일에 있는 이유: 전부 "디스크의 시계열을 (cycle, (T,18)) 로 바꾸는" 일이고,
reference / tools / evaluation 이 공통으로 쓴다.

GT 격리 (CLAUDE.md 규칙 2)
    load_scenario 는 series.npz 의 `true_rul` 과 spec.json 의 fault 필드
    (mode, channels, profile, onset_cycle, sigma_mult, direction, delta_raw, category ...)
    를 **의도적으로 버린다**. 통과시키는 spec 키는 _SPEC_ALLOWED 4개뿐이다.
    평가에 필요한 GT 는 evaluation/gt.py 가 따로 읽는다.

채널 순서 (18): 측정 센서 14개 + 운전조건 4개 = configs/experiment.yaml channels.
series.npz 는 이미 10:1 decimated(10s 간격). HDF5 는 읽을 때 decimation 을 적용해 맞춘다.
"""
from __future__ import annotations

import json
import os
from typing import Iterator

import numpy as np

# =========================================================================== #
# window 분할 (설계서 2.2)
# =========================================================================== #
def split_windows(seq: np.ndarray, samples_per_window: int) -> np.ndarray:
    """(T,18) → (n_w, samples_per_window, 18). cycle 내부 비중첩, 꼬리(< 1 window) 버림."""
    seq = np.asarray(seq, dtype=np.float32)
    n_w = len(seq) // samples_per_window
    if n_w == 0:
        return np.empty((0, samples_per_window, seq.shape[1]), dtype=np.float32)
    usable = n_w * samples_per_window
    return seq[:usable].reshape(n_w, samples_per_window, seq.shape[1])


def n_windows(length: int, samples_per_window: int) -> int:
    return int(length) // int(samples_per_window)


def window_index(seq_len: int, samples_per_window: int) -> np.ndarray:
    """각 window 의 시작 샘플 인덱스 (stats 기록 → 원본 추적용)."""
    return np.arange(n_windows(seq_len, samples_per_window), dtype=np.int64) * samples_per_window


# =========================================================================== #
# 오염 시나리오 (corrupted_dataset/<block>/<scenario_id>/series.npz + spec.json)
# =========================================================================== #
_SPEC_ALLOWED = ("scenario_id", "unit", "flight_class", "life_cycles")


def scenario_path(corrupted_root: str, scenario_id: str) -> str:
    """scenario_id 로 폴더를 찾는다. manifest.csv(GT)는 열지 않고 디렉터리를 탐색한다."""
    for block in sorted(os.listdir(corrupted_root)):
        cand = os.path.join(corrupted_root, block, scenario_id)
        if os.path.isdir(cand) and os.path.exists(os.path.join(cand, "series.npz")):
            return cand
    raise FileNotFoundError(f"시나리오 폴더 없음: {scenario_id} (root={corrupted_root})")


def load_scenario(corrupted_root: str, scenario_id: str) -> dict:
    """GT 를 제외한 시나리오 데이터.

    Returns dict:
        scenario_id, unit, fc, life_cycles,
        cycles (Ncyc,) int, series list[(T_c,18) float32]
    """
    path = scenario_path(corrupted_root, scenario_id)
    z = np.load(os.path.join(path, "series.npz"))
    series, bounds, cycles = z["series"], z["cycle_bounds"], z["cycles"].astype(int)
    per_cycle = [series[bounds[i]:bounds[i + 1]].astype(np.float32)
                 for i in range(len(bounds) - 1)]

    with open(os.path.join(path, "spec.json"), "r", encoding="utf-8") as f:
        spec_full = json.load(f)
    spec = {k: spec_full[k] for k in _SPEC_ALLOWED if k in spec_full}

    return {
        "scenario_id": spec.get("scenario_id", scenario_id),
        "unit": int(spec["unit"]),
        "fc": int(spec.get("flight_class", -1)),
        "life_cycles": int(spec.get("life_cycles", len(cycles))),
        "cycles": cycles,
        "series": per_cycle,
    }


def stream(scenario: dict) -> Iterator[tuple[int, np.ndarray]]:
    """시나리오를 cycle 순서대로 (cycle, (T,18)) 로 흘려보낸다.

    runner 는 이 제너레이터에서 한 cycle 씩 받아 Tool 에 넘긴다. Tool 은 도착한
    cycle 까지만 알게 된다.
    """
    for c, s in zip(scenario["cycles"], scenario["series"]):
        yield int(c), s


def list_available(corrupted_root: str) -> list[str]:
    out = []
    for block in sorted(os.listdir(corrupted_root)):
        bdir = os.path.join(corrupted_root, block)
        if not os.path.isdir(bdir):
            continue
        for sid in sorted(os.listdir(bdir)):
            if os.path.exists(os.path.join(bdir, sid, "series.npz")):
                out.append(sid)
    return out


# =========================================================================== #
# N-CMAPSS DS02-006 HDF5 (clean train / calibration unit 전용)
# =========================================================================== #
# HDF5 구조:
#     A_dev   (N,4)  unit, cycle, Fc, hs
#     X_s_dev (N,14) T24 T30 T48 T50 P15 P2 P21 P24 Ps30 P40 P50 Nf Nc Wf
#     W_dev   (N,4)  alt Mach TRA T2
#     Y_dev   (N,1)  RUL (cycles)
#     dev split = unit {2,5,10,16,18,20}, test split = unit {11,14,15}
DEV_UNITS = (2, 5, 10, 16, 18, 20)
TEST_UNITS = (11, 14, 15)


def _split_for_unit(unit: int) -> str:
    if unit in DEV_UNITS:
        return "dev"
    if unit in TEST_UNITS:
        return "test"
    raise ValueError(f"unknown unit {unit}")


def load_unit_series(h5_path: str, unit: int, decimation: int = 10,
                     cache_dir: str | None = None) -> dict:
    """unit 하나의 cycle 별 decimated 시계열. 2.4GB HDF5 를 매번 읽지 않도록 npz 캐시.

    Returns dict: unit, fc, cycles (Ncyc,) int, series list[(T_c,18)], rul (Ncyc,)
    rul 은 reference 구축에서 쓰지 않는다 (inspect 진단용). Agent 경로는 이 함수를
    쓰지 않는다 (test unit 은 load_scenario 로만).
    """
    cache = None
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)
        cache = os.path.join(cache_dir, f"ncmapss_u{unit}_d{decimation}.npz")
        if os.path.exists(cache):
            return _load_unit_cache(cache)

    import h5py
    split = _split_for_unit(unit)
    with h5py.File(h5_path, "r") as f:
        units = f[f"A_{split}"][:, 0].astype(np.int32)
        idx = np.flatnonzero(units == unit)
        if idx.size == 0:
            raise ValueError(f"unit {unit} 없음 (split={split})")
        lo, hi = int(idx[0]), int(idx[-1]) + 1
        A = f[f"A_{split}"][lo:hi]
        Xs = f[f"X_s_{split}"][lo:hi]
        W = f[f"W_{split}"][lo:hi]
        Y = f[f"Y_{split}"][lo:hi].reshape(-1)

    keep = A[:, 0].astype(np.int32) == unit
    A, Xs, W, Y = A[keep], Xs[keep], W[keep], Y[keep]
    X = np.concatenate([Xs, W], axis=1).astype(np.float32)
    fc = int(np.unique(A[:, 2])[0])

    cyc_ids = np.unique(A[:, 1]).astype(int)
    cyc_ids.sort()
    series, rul, cycles = [], [], []
    for c in cyc_ids:
        m = A[:, 1].astype(int) == c
        series.append(X[m][::decimation].copy())
        rul.append(float(np.median(Y[m])))
        cycles.append(int(c))

    out = {"unit": unit, "fc": fc, "cycles": np.asarray(cycles, dtype=int),
           "series": series, "rul": np.asarray(rul, dtype=np.float32)}
    if cache:
        _save_unit_cache(cache, out)
    return out


def _save_unit_cache(path: str, d: dict) -> None:
    lens = [len(s) for s in d["series"]]
    bounds = np.concatenate([[0], np.cumsum(lens)]).astype(np.int64)
    np.savez(path, series=np.concatenate(d["series"], axis=0).astype(np.float32),
             cycle_bounds=bounds, cycles=d["cycles"].astype(np.int32),
             rul=d["rul"], unit=np.int32(d["unit"]), fc=np.int32(d["fc"]))


def _load_unit_cache(path: str) -> dict:
    z = np.load(path)
    s, b = z["series"], z["cycle_bounds"]
    return {"unit": int(z["unit"]), "fc": int(z["fc"]),
            "cycles": z["cycles"].astype(int),
            "series": [s[b[i]:b[i + 1]] for i in range(len(b) - 1)],
            "rul": z["rul"].astype(np.float32)}


def pooled_samples(h5_path: str, units, decimation: int = 10,
                   max_rows: int | None = None, cache_dir: str | None = None,
                   ) -> np.ndarray:
    """여러 unit 의 샘플을 이어붙인 (M,18). max_rows 초과 시 결정적 등간격 subsample."""
    rows = []
    for u in units:
        rows.extend(load_unit_series(h5_path, u, decimation, cache_dir)["series"])
    pool = np.concatenate(rows, axis=0).astype(np.float32)
    if max_rows and len(pool) > max_rows:
        idx = np.linspace(0, len(pool) - 1, max_rows).astype(np.int64)
        pool = pool[idx]
    return pool


def iter_unit_cycles(h5_path: str, units, decimation: int = 10,
                     cache_dir: str | None = None):
    """(unit, cycle_id, series (T,18)) 순서대로."""
    for u in units:
        d = load_unit_series(h5_path, u, decimation, cache_dir)
        for c, s in zip(d["cycles"], d["series"]):
            yield int(u), int(c), s


# =========================================================================== #
# 진단 (CLI `inspect`)
# =========================================================================== #
def inspect_h5(cfg) -> None:
    import h5py
    print("=" * 78)
    print(f"HDF5: {cfg.paths.ncmapss_h5}")
    with h5py.File(cfg.paths.ncmapss_h5, "r") as f:
        xs = [v.decode() if isinstance(v, bytes) else str(v)
              for v in np.array(f["X_s_var"]).ravel()]
        w = [v.decode() if isinstance(v, bytes) else str(v)
             for v in np.array(f["W_var"]).ravel()]
        print(f"  X_s_var ({len(xs)}): {xs}")
        print(f"  W_var   ({len(w)}): {w}")
        for split in ("dev", "test"):
            A = f[f"A_{split}"][:, :3]
            units = np.unique(A[:, 0]).astype(int)
            print(f"  {split}: rows={len(A):,} units={list(units)}")
            for u in units:
                m = A[:, 0].astype(int) == u
                ncyc = len(np.unique(A[m, 1]))
                fc = int(np.unique(A[m, 2])[0])
                print(f"      unit {u:2d}  Fc{fc}  cycles={ncyc:3d}  rows={m.sum():,}")
    if xs != cfg.sensors or w != cfg.operating:
        raise SystemExit("[!] configs/experiment.yaml 의 channels 가 HDF5 와 다르다")
    print("  → configs/experiment.yaml channels 일치 확인")


def inspect_scenarios(cfg) -> None:
    print("=" * 78)
    print(f"시나리오 (corrupted_root={cfg.paths.corrupted_root})")
    spw = cfg.samples_per_window
    for sid in cfg.scenarios:
        sc = load_scenario(cfg.paths.corrupted_root, sid)
        lens = np.array([len(s) for s in sc["series"]])
        nw = np.array([n_windows(int(x), spw) for x in lens])
        dur_h = lens * int(cfg.exp.time["delta_s_sec"]) / 3600.0
        n_num = cfg.n_sensors * (cfg.L_c * 4 + 5 + int(nw.max()) * 2)
        short = "  [short_flight 있음]" if nw.min() < cfg.min_windows_short_flight else ""
        print(f"  {sid}")
        print(f"      unit={sc['unit']} Fc{sc['fc']} cycles={len(sc['cycles'])} "
              f"({sc['cycles'][0]}..{sc['cycles'][-1]})")
        print(f"      samples/cycle {lens.min()}~{lens.max()} "
              f"(비행 {dur_h.min():.1f}~{dur_h.max():.1f} h)")
        print(f"      windows/cycle {nw.min()}~{nw.max()} (mean {nw.mean():.0f}){short}")
        print(f"      최대 cycle 프롬프트 수치 개수 ≈ {n_num:,} → 대략 "
              f"{n_num * 5 // 1000}~{n_num * 7 // 1000}k 토큰")
