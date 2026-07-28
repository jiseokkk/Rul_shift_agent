"""RUL estimation tool (draft §3.2): a deliberately unexceptional LSTM.

2-layer LSTM, 64 hidden units (~54K params), window of 50 decimated steps over
18 channels, scalar RUL output capped at 65 cycles.  The model is intentionally
weak — the framework's value must come from the agent's signal integration, not
from the predictor.

Tier-1 #3: the model exposes MC-Dropout predictive uncertainty.  Dropout is kept
active at inference over `MC_SAMPLES` passes, giving mean + std.  Out-of-
distribution inputs (e.g. the Direction-A sensor bias) tend to inflate this
std, giving the agent a *model-internal* reliability channel independent of the
sensor statistics.
"""
import numpy as np
import torch
import torch.nn as nn

import han.Rul_shift_agent.config as C

SCALER_PATH = C.OUT_DIR + "/scaler.npz"
MODEL_PATH = C.OUT_DIR + "/rul_lstm.pt"


class RULModel(nn.Module):
    def __init__(self, n_in=C.N_INPUT, hidden=C.LSTM_HIDDEN,
                 layers=C.LSTM_LAYERS, dropout=C.LSTM_DROPOUT):
        super().__init__()
        self.lstm = nn.LSTM(n_in, hidden, num_layers=layers,
                            batch_first=True, dropout=dropout)
        self.drop = nn.Dropout(dropout)
        self.head = nn.Linear(hidden, 1)

    def forward(self, x):
        out, _ = self.lstm(x)
        h = self.drop(out[:, -1, :])
        return self.head(h).squeeze(-1)


# --------------------------------------------------------------------------- #
# Scaler (per-channel standardisation, fit on training windows only)
# --------------------------------------------------------------------------- #
def fit_scaler(Xtr):
    flat = Xtr.reshape(-1, Xtr.shape[-1])
    mean, std = flat.mean(0), flat.std(0) + 1e-8
    np.savez(SCALER_PATH, mean=mean, std=std)
    return mean, std


def load_scaler():
    z = np.load(SCALER_PATH)
    return z["mean"], z["std"]


def scale(X, mean, std):
    return (X - mean) / std


# --------------------------------------------------------------------------- #
# Inference helpers
# --------------------------------------------------------------------------- #
class RULTool:
    """Loads a trained model + scaler; gives point estimate and MC-Dropout std."""

    def __init__(self, device=None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.mean, self.std = load_scaler()
        self.model = RULModel().to(self.device)
        self.model.load_state_dict(torch.load(MODEL_PATH, map_location=self.device))
        self.model.eval()

    def _prep(self, windows):
        X = scale(np.asarray(windows, dtype=np.float32), self.mean, self.std)
        if X.ndim == 2:
            X = X[None]
        return torch.tensor(X, dtype=torch.float32, device=self.device)

    @torch.no_grad()
    def predict(self, windows):
        """Point estimate (dropout off). Returns np.array (N,)."""
        x = self._prep(windows)
        return self.model(x).cpu().numpy()

    @torch.no_grad()
    def predict_mc(self, windows, n=C.MC_SAMPLES):
        """MC-Dropout. Returns (mean, std) arrays (N,). Dropout kept ON."""
        x = self._prep(windows)
        self.model.train()                       # enable dropout
        samples = np.stack([self.model(x).cpu().numpy() for _ in range(n)], 0)
        self.model.eval()
        return samples.mean(0), samples.std(0)
