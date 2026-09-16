"""전 cycle 슬라이딩 추론 (clean / shift 공용).

입력: 한 unit 의 26 컬럼 궤적 (원본 스케일; clean 이든 주입본이든 구분하지 않음)
처리: norm_params_ft 로 z-score → 길이 seq_len 슬라이딩 window → 예측, 음수 0 clip
출력: DataFrame[time, pred]  (t = seq_len .. T_u; window 는 cycle t−seq_len+1 .. t)
"""
from __future__ import annotations

import os
import warnings

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")  # 결정성 (torch import 전)

import numpy as np
import pandas as pd
import torch

from src.data import cmapss
from src.data.loaders import apply_zscore, unit_windows


def enable_determinism() -> bool:
    """가능한 결정성 설정. warn_only=True: 비결정 연산이 있어도 예외 대신 경고 (GPU 에서 중단 방지).
    실제 결정성은 determinism_check() 로 같은 입력을 두 번 넣어 확인한다."""
    try:
        torch.use_deterministic_algorithms(True, warn_only=True)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
        return True
    except Exception as e:  # 일부 버전에서 미지원
        warnings.warn(f"use_deterministic_algorithms 실패: {e}")
        return False


@torch.no_grad()
def predict_windows(model, X_norm: np.ndarray, seq_len: int, batch_size: int = 1024) -> np.ndarray:
    """(T, 17) 정규화된 궤적 → (T − seq_len + 1,) 예측. T < seq_len 이면 edge pad 후 1개."""
    device = next(model.parameters()).device  # 모델이 놓인 장치를 따른다
    model.eval()
    W = unit_windows(X_norm, seq_len, only_final=False).astype(np.float32)
    out = []
    for i in range(0, len(W), batch_size):
        p = model(torch.from_numpy(W[i:i + batch_size]).to(device))
        out.append(p.squeeze(1).cpu().numpy())
    P = np.concatenate(out)
    P[P < 0] = 0.0
    return P


def infer_unit(model, unit_df: pd.DataFrame, norm_params: np.ndarray, seq_len: int,
               with_true: bool = False) -> pd.DataFrame:
    """26 컬럼 unit 궤적 → [time, pred(, rul_true)]."""
    df = unit_df.sort_values("time").reset_index(drop=True)
    X = apply_zscore(cmapss.feature_matrix(df), norm_params)
    T = len(df)
    P = predict_windows(model, X, seq_len)
    times = df["time"].to_numpy()
    t_idx = times[seq_len - 1:] if T >= seq_len else times[-1:]
    out = pd.DataFrame({"time": t_idx.astype(int), "pred": P.astype(np.float64)})
    if with_true:
        out["rul_true"] = (T - out["time"]).astype(float)  # real RUL (clip 안 함)
    return out


def determinism_check(model, unit_df: pd.DataFrame, norm_params: np.ndarray, seq_len: int) -> bool:
    a = infer_unit(model, unit_df, norm_params, seq_len)["pred"].to_numpy()
    b = infer_unit(model, unit_df, norm_params, seq_len)["pred"].to_numpy()
    return bool(np.array_equal(a, b))
