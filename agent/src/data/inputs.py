"""에이전트가 볼 수 있는 입력만 읽는 로더.

시나리오 하나 = (unit, scenario_id). 반환하는 것은 배포 환경에서 관측 가능한 것뿐이다:
  센서 14개 (cycle 1~T_u), 결정적 RUL 예측 ỹ (cycle 45~T_u), MC dropout 50 pass (cycle 45~T_u).
τ_s, τ_d, 라벨, clean 예측, 시나리오 유형은 여기서 절대 읽지 않는다 (그건 data/truth.py, eval/ 전용).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

AGENT_ROOT = Path(__file__).resolve().parents[2]

# raw 컬럼 → 물리 이름. 모델 입력 14 센서. op1~3 은 단일 운전조건이라 제외.
SENSOR_COLS = {"s2": "T24", "s3": "T30", "s4": "T50", "s7": "P30", "s8": "Nf", "s9": "Nc", "s11": "Ps30",
               "s12": "phi", "s13": "NRf", "s14": "NRc", "s15": "BPR", "s17": "htBleed", "s20": "W31", "s21": "W32"}
SENSORS = list(SENSOR_COLS.values())


def load_paths() -> dict:
    with open(AGENT_ROOT / "configs" / "paths.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return {k: (AGENT_ROOT / v).resolve() if isinstance(v, str) and (v.startswith(".") or v in ("runs", "reports")) else v
            for k, v in cfg.items()}


@dataclass
class ScenarioInputs:
    unit: int
    scenario_id: str
    T_u: int
    sensors: pd.DataFrame     # index=time (1..T_u), columns=SENSORS
    y_hat: pd.Series          # index=time (45..T_u)
    mc: pd.DataFrame          # index=time (45..T_u), columns=pass_00..pass_49

    def cycles(self) -> np.ndarray:
        return self.sensors.index.to_numpy()


def load_scenario(unit: int, scenario_id: str, paths: dict | None = None) -> ScenarioInputs:
    p = paths or load_paths()
    sh = pd.read_parquet(Path(p["shifted_dir"]) / f"u{unit}" / f"{scenario_id}.parquet").sort_values("time")
    sensors = sh.set_index("time")[list(SENSOR_COLS)].rename(columns=SENSOR_COLS)
    sensors.index = sensors.index.astype(int)
    y = pd.read_parquet(Path(p["pred_shift_dir"]) / f"u{unit}" / f"{scenario_id}.parquet").sort_values("time")
    y_hat = y.set_index("time")["pred"].astype(float)
    y_hat.index = y_hat.index.astype(int)
    mc_path = AGENT_ROOT / "artifacts" / "mc_dropout" / "shift" / f"u{unit}" / f"{scenario_id}.parquet"
    mc = pd.read_parquet(mc_path).sort_values("time").set_index("time")
    mc.index = mc.index.astype(int)
    T_u = int(sensors.index.max())
    assert len(sensors) == T_u and sensors.index.min() == 1, "센서 궤적은 cycle 1~T_u 연속이어야 한다"
    assert y_hat.index.min() == 45 and y_hat.index.max() == T_u, "예측은 45~T_u"
    assert mc.index.equals(y_hat.index), "MC 캐시와 예측의 cycle 축이 다르다"
    return ScenarioInputs(unit=int(unit), scenario_id=scenario_id, T_u=T_u, sensors=sensors, y_hat=y_hat, mc=mc)


def load_scenario_list(name_or_path: str) -> pd.DataFrame:
    """configs/{name}.csv 또는 경로. 필요한 컬럼: unit, scenario_id. 다른 컬럼(desc 등)은 무시."""
    p = Path(name_or_path)
    if not p.exists():
        p = AGENT_ROOT / "configs" / f"{name_or_path}.csv"
    df = pd.read_csv(p)
    return df[["unit", "scenario_id"]].drop_duplicates().reset_index(drop=True)
