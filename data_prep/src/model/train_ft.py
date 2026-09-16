"""Phase B-2: 미세조정 (원본 Transformer_ft_serialatten.py 의 학습 루프).

encoder 에 사전학습 weight 로드(strict=False) 후 encoder 파라미터만 freeze.
linear, pos_embedding, out 은 학습. 전체 model.state_dict() 저장.
"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from src.common import get_device, set_seed
from src.model.nets import build_ft


def train_finetune(train_ds, cfg: dict, pre_path: str | Path, out_path: str | Path, seed: int, log=print) -> Path:
    f = cfg["finetune"]
    set_seed(seed)
    device = get_device()
    loader = DataLoader(train_ds, batch_size=cfg["batch_size"], shuffle=cfg.get("shuffle", True),
                        num_workers=cfg.get("num_workers", 0), pin_memory=device.type == "cuda")
    model = build_ft(cfg).to(device)
    state = torch.load(pre_path, map_location=device)
    missing, unexpected = model.encoder.load_state_dict(state, strict=False)
    if missing or unexpected:
        log(f"[ft] encoder load: missing={list(missing)} unexpected={list(unexpected)}")
    for param in model.encoder.parameters():
        param.requires_grad = False

    optimizer = torch.optim.Adam(model.parameters(), lr=f["lr"])  # 원본: 전체 파라미터 전달 (frozen 은 grad None)
    criterion = nn.MSELoss()
    for epoch in range(f["epochs"]):
        model.train()
        t0 = time.time()
        losses = []
        for X, Y in loader:
            X, Y = X.to(device), Y.to(device)
            optimizer.zero_grad()
            out = model(X)
            loss = torch.sqrt(criterion(out, Y))
            loss.backward()
            optimizer.step()
            losses.append(loss.item())
        if (epoch + 1) % 10 == 0 or epoch == 0:
            log(f"[ft s{seed}] epoch {epoch + 1}/{f['epochs']} train_rmse={np.mean(losses):.3f} ({time.time() - t0:.1f}s)")

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), out_path)
    return out_path


def load_ft_model(path: str | Path, cfg: dict, device=None):
    device = device or get_device()
    model = build_ft(cfg).to(device)
    model.load_state_dict(torch.load(path, map_location=device))
    model.eval()
    return model
