"""Phase C-1: shift 주입 (원본 스케일, t ≥ τ_s 인 cycle 에만).

σ_r, μ_r 은 norm_params_ft (train 80 unit 통계) 의 std, mean 과 동일값을 쓴다.
따라서 bias α 는 정규화 공간에서 정확히 α 만큼의 이동이다.

유형                       구현
bias     x ← x + d·α·σ_r
stuck    x ← x(τ_s)
noise    x ← x + ε,  ε ~ N(0, (β·σ_r)²)         rng seed 기록
gain     x ← μ_r + (x − μ_r)·(1 + d·α)            (평균 중심)
multi_C  S 각각  x_s ← x_s + sign_deg(s)·α·σ_r(s)
multi_I  S 각각  x_s ← x_s + sign(s)·α·σ_r(s),  sign 무작위(rng seed), sign_deg / −sign_deg 조합 제외
"""
from __future__ import annotations

import itertools

import numpy as np
import pandas as pd

from src.common import derive_seed
from src.data import cmapss
from src.data.split import tau_s_of

TYPE_ID = {"bias": "bias", "gain": "gain", "noise": "noise", "stuck": "stuck",
           "multi_C": "multiC", "multi_I": "multiI"}


# ---------------- sign_deg ----------------
def compute_sign_deg(train_df: pd.DataFrame, frac: float = 0.1) -> dict:
    """train unit 별 (수명 마지막 10% 평균 − 처음 10% 평균) 을 unit 평균 → 부호.

    반환: {'s2': +1, 's3': +1, ..., 'diff_mean': {...}}  (상수 센서는 0)
    """
    diffs = {s: [] for s in cmapss.RAW_COLUMNS[5:]}
    for uid in train_df["id"].unique():
        u = cmapss.unit_frame(train_df, uid)
        n = max(1, int(np.floor(len(u) * frac)))
        head, tail = u.iloc[:n], u.iloc[-n:]
        for s in diffs:
            diffs[s].append(float(tail[s].mean() - head[s].mean()))
    out = {"frac": frac, "diff_mean": {}, "sign": {}}
    for s, v in diffs.items():
        m = float(np.mean(v))
        out["diff_mean"][s] = m
        out["sign"][s] = 0 if abs(m) < 1e-12 else int(np.sign(m))
    return out


# ---------------- 시나리오 ----------------
def _fmt(v: float) -> str:
    return str(float(v))  # 0.2 → '0.2', 1.0 → '1.0'


def scenario_id(type_key: str, sensors: list[str], param: str, direction: str, p: float) -> str:
    """5슬롯 고정: {type}_{sensor}_{param}_{dir}_p{timing}. 빈 자리 na. 물리 이름 사용."""
    sens = "+".join(cmapss.phys_name(cmapss.resolve_sensor(s)) for s in sensors)
    return f"{TYPE_ID[type_key]}_{sens}_{param}_{direction}_p{_fmt(p)}"


def _alphas_for_dir(spec: dict, d: str) -> list[float]:
    """alpha 가 list 면 양방향 공통, dict 면 방향별 {pos: [...], neg: [...]}.

    gain neg 는 배율이 (1 − α) 이므로 α ≥ 1 이면 축소가 아니라 고정(α=1)·반전(α>1) 이 된다.
    그래서 gain 은 방향별로 α 를 따로 준다 (2026-09-16 grid v3)."""
    a = spec["alpha"]
    return list(a[d]) if isinstance(a, dict) else list(a)


def make_scenarios(grid: dict, T_u: int, t0: int) -> list[dict]:
    """grid yaml + unit 길이 → 시나리오 dict 목록 (unit 무관 부분 + τ_s)."""
    out = []
    for p in grid["timing_p"]:
        tau_s = tau_s_of(T_u, p, t0)
        for tkey, spec in grid["types"].items():
            if tkey in ("bias", "gain"):
                for s in grid["sensors_single"]:
                    for d in spec["dir"]:
                        for a in _alphas_for_dir(spec, d):
                            out.append(dict(type=tkey, sensors=[s], param_name="alpha", param=float(a),
                                            dir=d, timing_p=float(p), tau_s=tau_s,
                                            scenario_id=scenario_id(tkey, [s], f"a{_fmt(a)}", d, p)))
            elif tkey == "noise":
                for s in grid["sensors_single"]:
                    for b in spec["beta"]:
                        out.append(dict(type=tkey, sensors=[s], param_name="beta", param=float(b),
                                        dir="na", timing_p=float(p), tau_s=tau_s,
                                        scenario_id=scenario_id(tkey, [s], f"b{_fmt(b)}", "na", p)))
            elif tkey == "stuck":
                for s in grid["sensors_single"]:
                    out.append(dict(type=tkey, sensors=[s], param_name="na", param=float("nan"),
                                    dir="na", timing_p=float(p), tau_s=tau_s,
                                    scenario_id=scenario_id(tkey, [s], "na", "na", p)))
            elif tkey in ("multi_C", "multi_I"):
                for S in spec["sets"]:
                    for a in spec["alpha"]:
                        out.append(dict(type=tkey, sensors=list(S), param_name="alpha", param=float(a),
                                        dir="na", timing_p=float(p), tau_s=tau_s,
                                        scenario_id=scenario_id(tkey, S, f"a{_fmt(a)}", "na", p)))
            else:
                raise ValueError(f"unknown shift type: {tkey}")
    ids = [s["scenario_id"] for s in out]
    assert len(ids) == len(set(ids)), "scenario_id 중복"
    return out


def n_scenarios_per_unit(grid: dict) -> int:
    return len(make_scenarios(grid, T_u=200, t0=55))


# ---------------- 주입 ----------------
def _sigma_mu(sensor: str, norm_params: np.ndarray) -> tuple[float, float]:
    fi = cmapss.feature_index_of(sensor)
    if fi is None:
        raise ValueError(f"{sensor} 는 모델 입력이 아니어서 σ_r 이 정의되지 않음 (계획서 C-3: 미사용 센서 대조군 제거)")
    mu, sigma = norm_params[fi]
    if sigma == 0:
        raise ValueError(f"{sensor} σ_r = 0")
    return float(sigma), float(mu)


def multi_I_sign_choices(n: int, sign_deg_vec: list[int]) -> list[tuple[int, ...]]:
    """{±1}^n 에서 sign_deg 와 −sign_deg 를 제외한 조합."""
    sd = tuple(int(v) for v in sign_deg_vec)
    neg = tuple(-v for v in sd)
    return [c for c in itertools.product((1, -1), repeat=n) if c != sd and c != neg]


def inject(unit_df: pd.DataFrame, scen: dict, norm_params: np.ndarray, sign_deg: dict,
           base_seed: int, unit: int) -> tuple[pd.DataFrame, dict]:
    """한 unit 의 26 컬럼 궤적에 시나리오를 주입한 복사본과 메타를 반환. 원본 df 는 변경하지 않음."""
    df = unit_df.sort_values("time").reset_index(drop=True).copy()
    tau_s = int(scen["tau_s"])
    mask = (df["time"] >= tau_s).to_numpy()
    assert mask.any(), f"τ_s={tau_s} 가 unit {unit} 범위 밖"
    t = scen["type"]
    sensors = [cmapss.resolve_sensor(s) for s in scen["sensors"]]
    d = {"pos": 1.0, "neg": -1.0}.get(scen["dir"], 0.0)
    rng_seed = derive_seed(base_seed, unit, scen["scenario_id"])
    rng = np.random.default_rng(rng_seed)
    meta = {"unit": int(unit), "T_u": int(len(df)), "scenario_id": scen["scenario_id"], "type": t,
            "sensors": [cmapss.phys_name(s) for s in sensors], "sensor_cols": sensors,
            "param_name": scen["param_name"], "param": scen["param"], "dir": scen["dir"],
            "timing_p": scen["timing_p"], "tau_s": tau_s, "rng_seed": None, "signs": None,
            "sigma_r": {}, "mu_r": {}}

    if t == "bias":
        (s,) = sensors
        sigma, mu = _sigma_mu(s, norm_params)
        df.loc[mask, s] = df.loc[mask, s] + d * scen["param"] * sigma
        meta["sigma_r"][s], meta["mu_r"][s] = sigma, mu
    elif t == "gain":
        (s,) = sensors
        sigma, mu = _sigma_mu(s, norm_params)
        x = df.loc[mask, s].to_numpy()
        df.loc[mask, s] = mu + (x - mu) * (1.0 + d * scen["param"])
        meta["sigma_r"][s], meta["mu_r"][s] = sigma, mu
    elif t == "noise":
        (s,) = sensors
        sigma, mu = _sigma_mu(s, norm_params)
        eps = rng.normal(0.0, scen["param"] * sigma, size=int(mask.sum()))
        df.loc[mask, s] = df.loc[mask, s].to_numpy() + eps
        meta["rng_seed"] = rng_seed
        meta["sigma_r"][s], meta["mu_r"][s] = sigma, mu
    elif t == "stuck":
        (s,) = sensors
        x_tau = float(df.loc[df["time"] == tau_s, s].iloc[0])
        df.loc[mask, s] = x_tau
        meta["stuck_value"] = x_tau
    elif t == "multi_C":
        signs = []
        for s in sensors:
            sigma, mu = _sigma_mu(s, norm_params)
            sg = int(sign_deg["sign"][s])
            if sg == 0:
                raise ValueError(f"{s} sign_deg = 0")
            df.loc[mask, s] = df.loc[mask, s] + sg * scen["param"] * sigma
            signs.append(sg)
            meta["sigma_r"][s], meta["mu_r"][s] = sigma, mu
        meta["signs"] = signs
    elif t == "multi_I":
        sd_vec = [int(sign_deg["sign"][s]) for s in sensors]
        choices = multi_I_sign_choices(len(sensors), sd_vec)
        signs = list(choices[int(rng.integers(len(choices)))])
        for s, sg in zip(sensors, signs):
            sigma, mu = _sigma_mu(s, norm_params)
            df.loc[mask, s] = df.loc[mask, s] + sg * scen["param"] * sigma
            meta["sigma_r"][s], meta["mu_r"][s] = sigma, mu
        meta["signs"] = signs
        meta["rng_seed"] = rng_seed
    else:
        raise ValueError(t)
    return df, meta


def index_row_from_meta(meta: dict) -> dict:
    """scenario_index.csv 메타 컬럼 (scripts/06 이 작성)."""
    return {
        "unit": meta["unit"], "T_u": meta["T_u"], "scenario_id": meta["scenario_id"],
        "type": meta["type"], "sensor": "+".join(meta["sensors"]),
        "param_name": meta["param_name"], "param": meta["param"], "dir": meta["dir"],
        "timing_p": meta["timing_p"], "tau_s": meta["tau_s"], "rng_seed": meta["rng_seed"],
        "signs": "" if meta["signs"] is None else "+".join(str(s) for s in meta["signs"]),
    }
