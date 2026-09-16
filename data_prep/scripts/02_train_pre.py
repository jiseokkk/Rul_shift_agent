"""Phase B-1: 사전학습 (FD001 train 80 + FD003 train) → models/FD001/pre_FD0013_holdout.pt,
data/norm/norm_params_pre_FD0013.npy"""
from __future__ import annotations

import argparse

from _bootstrap import setup, load_json
from src.data.loaders import build_pretrain, save_norm_params, zero_std_columns
from src.model.train_pre import train_pretrain


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=None)
    ap.add_argument("--seed", type=int, default=None)
    a = ap.parse_args()

    paths, cfg = setup()
    if a.epochs:
        cfg["pretrain"]["epochs"] = a.epochs
    split = load_json(paths.split_json)
    ds, norm_pre = build_pretrain(paths, cfg, split)
    pre_name = cfg["pretrain"]["out_name"].replace("pre_", "").replace("_holdout.pt", "")
    save_norm_params(norm_pre, paths.norm_pre(pre_name))
    print(f"pretrain windows={len(ds)}  std=0 컬럼={zero_std_columns(norm_pre)}  → {paths.norm_pre(pre_name)}")
    out = train_pretrain(ds, cfg, paths.models_dir / cfg["pretrain"]["out_name"], seed=a.seed)
    print(f"→ {out}")


if __name__ == "__main__":
    main()
