"""Phase B-3/B-4: test_FD001 재현 평가와 hold-out 정합성 검증."""
from __future__ import annotations

import numpy as np
import torch
from torch.utils.data import DataLoader

from src.common import get_device
from src.model.nets import my_score


@torch.no_grad()
def evaluate_test(model, test_ds, batch_size: int = 256) -> dict:
    """원본 testing 블록: 마지막 window 예측, 음수 0 clip, RMSE vs rul(clip max_rul), Score."""
    device = get_device()
    model.eval()
    loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False)
    preds, ys = [], []
    for X, Y in loader:
        p = model(X.to(device))
        p[p < 0] = 0
        preds.append(p.cpu())
        ys.append(Y)
    P = torch.cat(preds).squeeze(1).numpy()
    Y = torch.cat(ys).squeeze(1).numpy()
    rmse = float(np.sqrt(np.mean((P - Y) ** 2)))
    return {"rmse": rmse, "score": float(my_score(Y, P)), "n": int(len(Y)),
            "pred": P.tolist(), "true": Y.tolist()}


def holdout_cutpoint_check(pred_frames: dict, max_rul: int, seed: int = 529) -> dict:
    """정합성 검증 1: hold-out unit 당 무작위 절단점 1개 → 그 시점 예측 vs true RUL(clip) RMSE/Score.

    pred_frames: unit → DataFrame[time, pred, rul_true]  (clean 예측, 기준 seed)
    절단점은 test set 처럼 45 ≤ t ≤ T_u 에서 균등 추출.
    """
    rng = np.random.default_rng(seed)
    P, Y, cuts = [], [], {}
    for u, df in pred_frames.items():
        t = int(rng.choice(df["time"].to_numpy()))
        row = df[df["time"] == t].iloc[0]
        P.append(float(row["pred"]))
        Y.append(float(min(row["rul_true"], max_rul)))
        cuts[int(u)] = t
    P, Y = np.asarray(P), np.asarray(Y)
    return {"rmse": float(np.sqrt(np.mean((P - Y) ** 2))), "score": float(my_score(Y, P)),
            "n": int(len(P)), "cut_points": cuts}


def holdout_range_rmse(pred_frames: dict, max_rul: int, edges=(0, 25, 75, 125)) -> list[dict]:
    """정합성 검증 2: 전 cycle 예측을 true RUL(clip) 구간별 RMSE 로."""
    allp, ally = [], []
    for df in pred_frames.values():
        allp.append(df["pred"].to_numpy())
        ally.append(np.minimum(df["rul_true"].to_numpy(), max_rul))
    P, Y = np.concatenate(allp), np.concatenate(ally)
    rows = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (Y >= lo) & (Y < hi) if hi < max_rul else (Y >= lo) & (Y <= hi)
        if m.sum() == 0:
            continue
        rows.append({"rul_range": f"{lo}-{hi}", "n": int(m.sum()),
                     "rmse": float(np.sqrt(np.mean((P[m] - Y[m]) ** 2))),
                     "bias": float(np.mean(P[m] - Y[m]))})
    rows.append({"rul_range": "all", "n": int(len(Y)), "rmse": float(np.sqrt(np.mean((P - Y) ** 2))),
                 "bias": float(np.mean(P - Y))})
    return rows
