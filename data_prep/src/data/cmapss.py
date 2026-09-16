"""C-MAPSS 원본 txt 로드와 컬럼 상수.

원본 txt 는 공백 구분 26 컬럼(+ 행 끝 공백으로 read_csv 시 NaN 2컬럼):
  0 id, 1 time, 2~4 op1~op3, 5~25 s1~s21

원본 로더(CMAPSSDataset_ft.py)가 쓰는 17 입력 = raw 컬럼
  [2,3,4, 6,7,8,11,12,13,15,16,17,18,19,21,24,25]
  = op1~3 + s2,s3,s4,s7,s8,s9,s11,s12,s13,s14,s15,s17,s20,s21
원본 내부 이름 's1'~'s14' 는 이 14개 센서를 순서대로 부른 것 (원본 's1' = 실제 s2 = T24).
이 프로젝트는 혼동을 피하기 위해 항상 실제 센서 번호(s2) 또는 물리 이름(T24)만 쓴다.
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd

RAW_COLUMNS = ["id", "time", "op1", "op2", "op3"] + [f"s{i}" for i in range(1, 22)]  # 26

# 실제 센서 번호 → 물리 이름 (Saxena et al. 2008)
SENSOR_PHYS = {
    "s1": "T2", "s2": "T24", "s3": "T30", "s4": "T50", "s5": "P2", "s6": "P15", "s7": "P30",
    "s8": "Nf", "s9": "Nc", "s10": "epr", "s11": "Ps30", "s12": "phi", "s13": "NRf", "s14": "NRc",
    "s15": "BPR", "s16": "farB", "s17": "htBleed", "s18": "Nf_dmd", "s19": "PCNfR_dmd",
    "s20": "W31", "s21": "W32",
}
PHYS_TO_SENSOR = {v: k for k, v in SENSOR_PHYS.items()}

# 물리 이름 → raw 컬럼 인덱스  (T24 → 6, T30 → 7, T50 → 8, ...)
RAW_COL = {phys: RAW_COLUMNS.index(s) for s, phys in SENSOR_PHYS.items()}

# 모델 입력 17개 (원본 iloc 선택 그대로)
MODEL_FEATURE_RAW_COLS = [2, 3, 4, 6, 7, 8, 11, 12, 13, 15, 16, 17, 18, 19, 21, 24, 25]
MODEL_FEATURE_NAMES = [RAW_COLUMNS[i] for i in MODEL_FEATURE_RAW_COLS]  # op1..op3,s2,...,s21
MODEL_SENSOR_NAMES = MODEL_FEATURE_NAMES[3:]
UNUSED_SENSOR_NAMES = [s for s in RAW_COLUMNS[5:] if s not in MODEL_SENSOR_NAMES]  # s1,s5,s6,s10,s16,s18,s19


def resolve_sensor(name: str | int) -> str:
    """'T24' / 's2' / 6 → 'sN' (RAW_COLUMNS 상의 컬럼 이름)."""
    if isinstance(name, (int, np.integer)):
        return RAW_COLUMNS[int(name)]
    if name in PHYS_TO_SENSOR:
        return PHYS_TO_SENSOR[name]
    if name in RAW_COLUMNS:
        return name
    raise KeyError(f"unknown sensor: {name}")


def phys_name(col: str) -> str:
    return SENSOR_PHYS.get(col, col)


def feature_index_of(name: str | int) -> int | None:
    """센서가 모델 입력 17개 중 몇 번째인지. 미사용 센서면 None."""
    col = resolve_sensor(name)
    return MODEL_FEATURE_NAMES.index(col) if col in MODEL_FEATURE_NAMES else None


def load_raw(raw_dir: str | Path, kind: str, sub_dataset: str) -> pd.DataFrame:
    """train/test_FD00X.txt → 26 컬럼 DataFrame (id, time 은 int)."""
    assert kind in ("train", "test")
    path = Path(raw_dir) / f"{kind}_{sub_dataset}.txt"
    df = pd.read_csv(path, sep=r"\s+", header=None)
    df = df.iloc[:, :26].copy()
    df.columns = RAW_COLUMNS
    df["id"] = df["id"].astype(int)
    df["time"] = df["time"].astype(int)
    return df


def load_rul(raw_dir: str | Path, sub_dataset: str) -> np.ndarray:
    """RUL_FD00X.txt → (n_test_units,) : test 각 unit 마지막 cycle 의 true RUL (unit id 순)."""
    path = Path(raw_dir) / f"RUL_{sub_dataset}.txt"
    return pd.read_csv(path, header=None).values.squeeze().astype(float)


def unit_lengths(df: pd.DataFrame) -> pd.Series:
    """unit id → T_u (cycle 수). id 오름차순."""
    return df.groupby("id").size().sort_index()


def feature_matrix(df: pd.DataFrame) -> np.ndarray:
    """26 컬럼 df → (n, 17) float64, 원본 입력 순서."""
    return df[MODEL_FEATURE_NAMES].to_numpy(dtype=np.float64)


def unit_frame(df: pd.DataFrame, unit: int) -> pd.DataFrame:
    """한 unit 의 궤적을 time 오름차순으로."""
    return df[df["id"] == unit].sort_values("time").reset_index(drop=True)
