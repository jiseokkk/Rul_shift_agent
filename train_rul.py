"""Train the LSTM RUL tool on the 5 flight-class-3 dev units; validate on unit 20.

Reproduces draft §3.2: single flight class establishes a clean in-distribution
regime; target validation RMSE ~5.5 cycles.
"""
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

import han.Rul_shift_agent.rul_shift_agent.config as C
import han.Rul_shift_agent.rul_shift_agent.data_ncmapss as D
from han.Rul_shift_agent.rul_shift_agent.rul_tool import RULModel, fit_scaler, scale, SCALER_PATH, MODEL_PATH


def set_seed(s=C.SEED):
    np.random.seed(s)
    torch.manual_seed(s)
    torch.cuda.manual_seed_all(s)


def rmse(a, b):
    return float(np.sqrt(np.mean((a - b) ** 2)))


def main():
    set_seed()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[train] device={device}")

    Xtr, ytr = D.load_training_windows()
    mean, std = fit_scaler(Xtr)
    print(f"[train] scaler saved -> {SCALER_PATH}")
    Xtr_s = scale(Xtr, mean, std)

    # validation set: one canonical window per cycle of unit 20
    val = D.load_unit_cycles(C.VAL_UNIT)
    Xva_s = scale(val["windows"], mean, std)
    yva = val["rul"]

    ds = TensorDataset(torch.tensor(Xtr_s), torch.tensor(ytr))
    dl = DataLoader(ds, batch_size=C.TRAIN_BATCH, shuffle=True, drop_last=False)

    model = RULModel().to(device)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"[train] LSTM params = {n_params:,}")
    opt = torch.optim.Adam(model.parameters(), lr=C.TRAIN_LR)
    lossf = nn.MSELoss()

    Xva_t = torch.tensor(Xva_s, dtype=torch.float32, device=device)
    best = 1e9
    for ep in range(1, C.TRAIN_EPOCHS + 1):
        model.train()
        tot = 0.0
        for xb, yb in dl:
            xb, yb = xb.to(device), yb.to(device)
            opt.zero_grad()
            loss = lossf(model(xb), yb)
            loss.backward()
            opt.step()
            tot += loss.item() * len(xb)
        model.eval()
        with torch.no_grad():
            pred = model(Xva_t).cpu().numpy()
        vr = rmse(pred, yva)
        if vr < best:
            best = vr
            torch.save(model.state_dict(), MODEL_PATH)
        if ep % 5 == 0 or ep == 1:
            print(f"  epoch {ep:3d}  train_mse={tot/len(ds):7.3f}  val_rmse={vr:6.3f}"
                  f"  (best={best:6.3f})")
    print(f"[train] best val RMSE = {best:.3f}  ->  {MODEL_PATH}")


if __name__ == "__main__":
    main()
