"""Phase A: 층화 hold-out 분할 → data/split/split_FD001.json, reports/A_split_summary.md"""
from __future__ import annotations

import argparse

from _bootstrap import setup, load_yaml, save_json, t0_from_configs
from src.data import cmapss
from src.data.split import split_report, stratified_holdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=529)
    ap.add_argument("--n-holdout", type=int, default=20)
    ap.add_argument("--n-strata", type=int, default=5)
    ap.add_argument("--force", action="store_true", help="기존 split 덮어쓰기")
    a = ap.parse_args()

    paths, cfg = setup()
    if paths.split_json.exists() and not a.force:
        raise SystemExit(f"{paths.split_json} 이미 존재. 덮어쓰려면 --force (이후 모든 산출물이 무효화됨)")
    df = cmapss.load_raw(paths.raw_dir, "train", cfg["sub_dataset"])
    lengths = cmapss.unit_lengths(df)
    split = stratified_holdout(lengths, a.n_holdout, a.n_strata, a.seed)
    save_json(split, paths.split_json)

    grid = load_yaml("shift_grid")
    t0 = t0_from_configs(cfg)
    rep = split_report(split, grid["timing_p"], t0, cfg["max_rul"], cfg["seq_len"])
    paths.reports_dir.mkdir(parents=True, exist_ok=True)
    (paths.reports_dir / "A_split_summary.md").write_text(rep, encoding="utf-8")
    print(f"holdout={split['holdout_units']}")
    print(f"→ {paths.split_json}\n→ {paths.reports_dir / 'A_split_summary.md'}")


if __name__ == "__main__":
    main()
