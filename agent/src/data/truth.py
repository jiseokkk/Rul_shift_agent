"""채점 전용 로더. eval/ 만 import 한다 (tests/test_isolation.py 가 검사).

라벨(state), τ_s, τ_d, degraded, eval_mask, 시나리오 메타(type, sensor, param, dir, timing_p).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.data.inputs import AGENT_ROOT, load_paths


def load_index(paths: dict | None = None, theta_name: str = "theta_primary") -> pd.DataFrame:
    p = paths or load_paths()
    idx = pd.read_csv(p["scenario_index"])
    idx = idx[idx["theta_name"] == theta_name].copy()
    mk = pd.read_csv(p["eval_mask"])[["unit", "scenario_id", "mask_from_cycle"]]
    idx = idx.merge(mk, on=["unit", "scenario_id"], how="left")
    return idx.reset_index(drop=True)


def load_labels(unit: int, scenario_id: str, paths: dict | None = None, theta_name: str = "theta_primary") -> pd.Series:
    """index=time (45..T_u), value=label 0/1."""
    p = paths or load_paths()
    st = pd.read_parquet(Path(p["state_dir"]) / theta_name / f"u{unit}" / f"{scenario_id}.parquet").sort_values("time")
    s = st.set_index("time")["label"].astype(int)
    s.index = s.index.astype(int)
    return s


def scenario_truth(idx: pd.DataFrame, unit: int, scenario_id: str) -> dict:
    r = idx[(idx["unit"] == unit) & (idx["scenario_id"] == scenario_id)].iloc[0]
    return {
        "unit": int(unit), "scenario_id": scenario_id, "type": r["type"], "sensor": r["sensor"],
        "param": r["param"], "dir": r["dir"], "timing_p": float(r["timing_p"]), "T_u": int(r["T_u"]),
        "tau_s": int(r["tau_s"]), "degraded": bool(r["degraded"]),
        "tau_d": int(r["tau_d"]) if pd.notna(r["tau_d"]) else None,
        "mask_from": int(r["mask_from_cycle"]) if pd.notna(r["mask_from_cycle"]) else None,
        "injected_sensors": [s for s in str(r["sensor"]).split("+")],
    }
