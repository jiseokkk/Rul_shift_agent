"""Phase B-2: 미세조정 seed 루프 → models/FD001/ft_s{seed}.pt, data/norm/norm_params_ft_FD001.npy

norm_params_ft 는 처음 한 번 계산해 저장하고, 이후에는 파일을 읽어 재사용한다 (모든 추론의 기준).
"""
from __future__ import annotations

import argparse

from _bootstrap import setup, load_json
from src.data.loaders import build_finetune, load_norm_params, save_norm_params, zero_std_columns
from src.model.train_ft import train_finetune


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="*", default=None)
    ap.add_argument("--epochs", type=int, default=None)
    ap.add_argument("--pre", default=None, help="사전학습 encoder .pt (기본 models/FD001/<out_name>)")
    a = ap.parse_args()

    paths, cfg = setup()
    if a.epochs:
        cfg["finetune"]["epochs"] = a.epochs
    seeds = a.seeds or cfg["finetune"]["seeds"]
    split = load_json(paths.split_json)
    pre_path = a.pre or (paths.models_dir / cfg["pretrain"]["out_name"])

    norm = load_norm_params(paths.norm_ft) if paths.norm_ft.exists() else None
    train_ds, _, norm = build_finetune(paths, cfg, split, norm_params=norm)
    if not paths.norm_ft.exists():
        save_norm_params(norm, paths.norm_ft)
    zs = zero_std_columns(norm)
    print(f"train windows={len(train_ds)}  norm_params_ft shape={norm.shape}  std=0 컬럼={zs}")
    if zs != ["op3"]:
        print("경고: std=0 컬럼이 op3 만이 아님 → B-0 사전 확인 항목 재점검")

    for s in seeds:
        out = train_finetune(train_ds, cfg, pre_path, paths.ft_model(s), seed=s)
        print(f"→ {out}")


if __name__ == "__main__":
    main()
