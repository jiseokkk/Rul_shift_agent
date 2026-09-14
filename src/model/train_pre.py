"""Phase B-1: 사전학습 (원본 Transformer_pre.py 의 학습 루프)."""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from src.common import get_device, set_seed
from src.model.nets import build_pre


def train_pretrain(dataset, cfg: dict, out_path: str | Path, seed: int | None = None, log=print) -> Path:
    """encoder state_dict 를 out_path 에 저장 (원본과 동일하게 encoder 만)."""
    p = cfg["pretrain"]
    seed = p["seed"] if seed is None else seed
    set_seed(seed)
    device = get_device()
    loader = DataLoader(dataset, batch_size=cfg["batch_size"], shuffle=cfg.get("shuffle", True),
                        num_workers=cfg.get("num_workers", 0), pin_memory=device.type == "cuda")
    model = build_pre(cfg).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=p["lr"])
    criterion = nn.MSELoss()
    criterion2 = nn.CrossEntropyLoss()

    for epoch in range(p["epochs"]):
        model.train()
        t0 = time.time()
        losses = []
        for X, Y, Y2 in loader:
            X, Y, Y2 = X.to(device), Y.to(device), Y2.to(device)
            optimizer.zero_grad()
            out, classout = model(X)
            loss = torch.sqrt(criterion(out, Y)) + criterion2(classout, Y2.squeeze(1))
            loss.backward()
            optimizer.step()
            losses.append(loss.item())
        log(f"[pre] epoch {epoch + 1}/{p['epochs']} train_loss={np.mean(losses):.3f} ({time.time() - t0:.1f}s)")

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.encoder.state_dict(), out_path)
    return out_path
