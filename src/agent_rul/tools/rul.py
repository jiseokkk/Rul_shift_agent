"""RUL Tool — frozen LSTM 래퍼 (설계서 6).

    RULTool(cfg)                     # models/frozen_rul/ 의 weight + scaler 로드. 학습하지 않는다
      .end_cycle(cycle, seq)         # 착륙: cycle 전체 시계열 → RUL 점추정, 이력에 추가
      .context(cycle)                # 판정용: 현재 예측 + 최근 궤적 + 변화량
      .rows()                        # 기록용 표

아키텍처와 cycle 예측 규칙은 reference_code/prev_project/rul_model.py 와 동일하게 재정의했다
(다른 프로젝트를 import 하지 않기 위해). cycle 예측 = cycle 전체를 비중첩 50-step window 로
잘라 window 별 점추정의 **median** (이착륙 구간에서 튀는 window 에 강건).

Tool 은 RUL 이 맞았는지 판단하지 않고 true RUL 도 읽지 않는다.
torch 가 없는 환경(테스트)에서는 RULTool 만 못 쓰고 rul_context 는 쓸 수 있다.
"""
from __future__ import annotations

import numpy as np

try:
    import torch
    import torch.nn as nn
except ImportError:                 # pragma: no cover
    torch = None
    nn = None


# --------------------------------------------------------------------------- #
# Agent 입력 (순수 numpy — torch 불필요)
# --------------------------------------------------------------------------- #
def rul_context(preds: dict[int, dict], cycle: int, L_c: int) -> dict:
    """{cycle: {rul, ...}} 이력 → Agent 입력용 RUL 블록: 현재 예측 + 최근 궤적 + 변화량."""
    order = sorted(c for c in preds if c <= cycle)
    recent = order[-(L_c + 1):]
    traj = [preds[c]["rul"] for c in recent]
    change = (traj[-1] - traj[-2]) if len(traj) >= 2 else float("nan")
    diffs = np.diff(traj) if len(traj) >= 2 else np.array([np.nan])
    return {
        "current": preds[cycle]["rul"],
        "recent_cycles": recent,
        "recent": traj,
        "change": float(change),
        "recent_median_change": float(np.median(diffs)),
    }


def model_windows(dec_seq: np.ndarray, window: int) -> np.ndarray:
    """(L,18) → (N,window,18) 겹침 없는 window. 짧으면 앞쪽을 복제해 패딩."""
    seq = np.asarray(dec_seq, dtype=np.float32)
    L = len(seq)
    if L < window:
        pad = np.repeat(seq[:1], window - L, axis=0)
        return np.concatenate([pad, seq], axis=0)[None, :, :]
    starts = range(0, L - window + 1, window)
    return np.stack([seq[s:s + window] for s in starts]).astype(np.float32)


# --------------------------------------------------------------------------- #
# 모델 + Tool (torch)
# --------------------------------------------------------------------------- #
if nn is not None:
    class RULNet(nn.Module):
        """2-layer LSTM (18 → hidden) + linear head. weight 파일과 키가 일치해야 한다."""

        def __init__(self, n_in: int = 18, hidden: int = 64, layers: int = 2,
                     dropout: float = 0.3):
            super().__init__()
            self.lstm = nn.LSTM(n_in, hidden, num_layers=layers, batch_first=True,
                                dropout=dropout)
            self.drop = nn.Dropout(dropout)
            self.head = nn.Linear(hidden, 1)

        def forward(self, x):
            out, _ = self.lstm(x)
            return self.head(self.drop(out[:, -1, :])).squeeze(-1)


class RULTool:
    def __init__(self, cfg, device: str | None = None):
        if torch is None:
            raise ImportError("RULTool 은 torch 가 필요하다 (rul_context 는 torch 없이 사용 가능)")
        m = cfg.exp.rul_model
        self.window = int(m["window"])
        self.rul_cap = float(m["rul_cap"])
        self.L_c = cfg.L_c
        dev = device or str(m.get("device", "auto"))
        self.device = ("cuda" if torch.cuda.is_available() else "cpu") if dev == "auto" else dev

        z = np.load(cfg.frozen_rul_path("scaler.npz"))
        self.mean = z["mean"].astype(np.float32)
        self.std = np.where(z["std"] > 0, z["std"], 1e-8).astype(np.float32)

        self.net = RULNet(n_in=int(m["n_input"]), hidden=int(m["hidden"]),
                          layers=int(m["layers"]), dropout=float(m["dropout"]))
        sd = torch.load(cfg.frozen_rul_path("rul_lstm.pt"), map_location=self.device)
        self.net.load_state_dict(sd)
        self.net.to(self.device).eval()
        self.reset()

    def reset(self) -> None:
        self.preds: dict[int, dict] = {}

    # ------------------------------------------------------------------ 추론
    def _predict_windows(self, wins: np.ndarray) -> np.ndarray:
        with torch.no_grad():
            x = (np.asarray(wins, dtype=np.float32) - self.mean) / self.std
            t = torch.tensor(x, dtype=torch.float32, device=self.device)
            return self.net(t).cpu().numpy()

    def predict_cycle(self, dec_seq: np.ndarray) -> dict:
        """한 cycle → {rul, window_spread, n_model_windows}."""
        preds = self._predict_windows(model_windows(dec_seq, self.window))
        return {"rul": float(np.median(preds)),
                "window_spread": float(preds.std()),
                "n_model_windows": int(len(preds))}

    # ------------------------------------------------------------------ 스트림
    def end_cycle(self, cycle: int, seq: np.ndarray) -> dict:
        """착륙: 이 cycle 의 RUL 예측을 이력에 추가."""
        r = self.predict_cycle(seq)
        self.preds[int(cycle)] = r
        return r

    def context(self, cycle: int) -> dict:
        return rul_context(self.preds, int(cycle), self.L_c)

    def rows(self) -> list[dict]:
        return [{"cycle": c, **self.preds[c]} for c in sorted(self.preds)]
