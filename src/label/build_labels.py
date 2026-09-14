"""Phase D-3/D-4: θ 3종 라벨 생성 + scenario_index.csv long format."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.common import load_json, read_parquet, write_parquet
from src.label.hysteresis import hysteresis_label, summarize

META_COLS = ["unit", "T_u", "scenario_id", "type", "sensor", "param_name", "param", "dir",
             "timing_p", "tau_s", "rng_seed", "signs"]
RESULT_COLS = ["theta_name", "theta_value", "k", "m", "theta_low_ratio", "degraded", "tau_d", "delay",
               "n_degraded_cycles", "n_transitions", "n_reversions", "frac_degraded_after_tau_s",
               "saturated_at_tau_s"]


def read_index_meta(path) -> pd.DataFrame:
    """scenario_index.csv 에서 메타 컬럼만 (long format 이어도 (unit, scenario_id) 유일하게)."""
    df = pd.read_csv(path)
    cols = [c for c in META_COLS if c in df.columns]
    return df[cols].drop_duplicates(subset=["unit", "scenario_id"]).reset_index(drop=True)


def resolve_thetas(label_cfg: dict, clean_var: dict | None, reproduce: dict | None, base_seed: int) -> dict:
    """label.yaml 의 thetas → {name: {'kind','value'|('ratio','floor')}} 확정값."""
    out = {}
    rec = (clean_var or {}).get("recommended", {})
    for name, spec in label_cfg["thetas"].items():
        kind = spec["kind"]
        if kind == "fixed":
            v = spec.get("value")
            if v is None:
                if spec.get("source") == "test_rmse":
                    v = (reproduce or {}).get("finetune", {}).get(str(base_seed), {}).get("rmse")
                    if v is None:
                        v = rec.get("theta_alt2")
                else:
                    v = rec.get("theta_primary")
            if v is None:
                raise ValueError(f"{name}: 값을 결정할 수 없음 (label.yaml value 또는 clean_variability/reproduce_metrics 필요)")
            out[name] = {"kind": "fixed", "value": float(v)}
        elif kind == "adaptive":
            out[name] = {"kind": "adaptive", "ratio": float(spec["ratio"]), "floor_name": spec.get("floor")}
        else:
            raise ValueError(kind)
    for name, spec in out.items():
        if spec["kind"] == "adaptive":
            fl = spec["floor_name"]
            spec["floor"] = float(out[fl]["value"]) if fl in out else float(fl)
    return out


def theta_series(spec: dict, pred_clean: np.ndarray) -> np.ndarray | float:
    if spec["kind"] == "fixed":
        return spec["value"]
    return np.maximum(spec["ratio"] * pred_clean, spec["floor"])


def label_one(delta_df: pd.DataFrame, spec: dict, k: int, m: int, ratio: float) -> tuple[pd.DataFrame, dict]:
    d = delta_df.sort_values("time").reset_index(drop=True)
    th = theta_series(spec, d["pred_clean"].to_numpy())
    res = hysteresis_label(d["delta"].to_numpy(), th, k, m, ratio)
    out = pd.DataFrame({"time": d["time"].astype(int), "delta": d["delta"], "label": res["label"],
                        "state": res["state"], "theta_high": res["theta_high"], "theta_low": res["theta_low"]})
    return out, res


def build_labels(paths, index_meta: pd.DataFrame, thetas: dict, k: int, m: int, ratio: float,
                 max_rul: int, overwrite: bool = True, log=print) -> pd.DataFrame:
    """모든 (unit, scenario) × θ 라벨 생성 → state parquet 저장, long-format index 반환."""
    rows = []
    n = len(index_meta)
    for i, r in enumerate(index_meta.itertuples(index=False)):
        unit, sid, tau_s, T_u = int(r.unit), r.scenario_id, int(r.tau_s), int(r.T_u)
        dpath = paths.delta(unit, sid)
        if not dpath.exists():
            raise FileNotFoundError(f"delta 없음: {dpath} (07_delta_analysis 먼저)")
        d = read_parquet(dpath)
        meta = {c: getattr(r, c) for c in index_meta.columns}
        for name, spec in thetas.items():
            out_path = paths.state(name, unit, sid)
            df, res = label_one(d, spec, k, m, ratio)
            if overwrite or not out_path.exists():
                write_parquet(df, out_path, meta={"unit": unit, "scenario_id": sid, "tau_s": tau_s,
                                                  "theta_name": name, "theta": spec, "k": k, "m": m,
                                                  "theta_low_ratio": ratio})
            s = summarize(res, df["time"].to_numpy(), tau_s)
            row = dict(meta)
            row.update({"theta_name": name,
                        "theta_value": spec["value"] if spec["kind"] == "fixed" else f"max({spec['ratio']}*yhat,{spec['floor']:.4g})",
                        "k": k, "m": m, "theta_low_ratio": ratio})
            row.update(s)
            row["saturated_at_tau_s"] = bool((T_u - tau_s) > max_rul)
            rows.append(row)
        if (i + 1) % 500 == 0:
            log(f"[labels] {i + 1}/{n}")
    cols = [c for c in META_COLS if c in index_meta.columns] + RESULT_COLS
    return pd.DataFrame(rows)[cols]


def sensitivity(paths, index_meta: pd.DataFrame, spec: dict, ks: list[int], ms: list[int], ratio: float,
                log=print) -> pd.DataFrame:
    """θ_primary 고정, (k, m) grid 별 저하율·지연 중앙값·복귀 비율."""
    deltas = {(int(r.unit), r.scenario_id): (read_parquet(paths.delta(int(r.unit), r.scenario_id)), int(r.tau_s))
              for r in index_meta.itertuples(index=False)}
    rows = []
    for k in ks:
        for m in ms:
            if k > m:
                continue
            deg, delays, rev = 0, [], 0
            for (u, sid), (d, tau_s) in deltas.items():
                df, res = label_one(d, spec, k, m, ratio)
                s = summarize(res, df["time"].to_numpy(), tau_s)
                deg += int(s["degraded"])
                rev += int(s["n_reversions"] > 0)
                if s["degraded"]:
                    delays.append(s["delay"])
            rows.append({"k": k, "m": m, "degraded_rate": deg / len(deltas),
                         "delay_median": float(np.median(delays)) if delays else None,
                         "reversion_rate": rev / len(deltas)})
            log(f"[sens] k={k} m={m} degraded={deg / len(deltas):.3f}")
    return pd.DataFrame(rows)
