"""Phase C: hold-out 20 × 시나리오 주입 → data/shifted, 기준 seed 추론 → preds/shift,
scenario_index.csv 메타 컬럼 작성. sign_deg 는 train 80 unit 에서 계산해 data/norm/sign_deg_FD001.json.

--units 3 4     일부 unit 만
--limit 10      unit 당 시나리오 앞 10 개만 (파일럿)
--skip-infer    주입만
"""
from __future__ import annotations

import argparse

import pandas as pd

from _bootstrap import setup, load_json, load_yaml, save_json, t0_from_configs
from src.common import read_parquet, write_parquet
from src.data import cmapss
from src.data.loaders import load_norm_params
from src.data.shift import compute_sign_deg, index_row_from_meta, inject, make_scenarios, n_scenarios_per_unit
from src.model.infer_full import enable_determinism, infer_unit
from src.model.train_ft import load_ft_model


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--units", type=int, nargs="*", default=None)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--skip-infer", action="store_true")
    a = ap.parse_args()

    paths, cfg = setup()
    grid = load_yaml("shift_grid")
    t0 = t0_from_configs(cfg)
    base = cfg["finetune"]["base_seed"]
    split = load_json(paths.split_json)
    norm = load_norm_params(paths.norm_ft)
    train_df = cmapss.load_raw(paths.raw_dir, "train", cfg["sub_dataset"])

    if paths.sign_deg_json.exists():
        sign_deg = load_json(paths.sign_deg_json)
    else:
        sign_deg = compute_sign_deg(train_df[train_df["id"].isin(split["train_units"])])
        save_json(sign_deg, paths.sign_deg_json)
    print("sign_deg:", {cmapss.phys_name(s): v for s, v in sign_deg["sign"].items() if s in cmapss.MODEL_SENSOR_NAMES})

    units = a.units or split["holdout_units"]
    model = None
    if not a.skip_infer:
        enable_determinism()
        model = load_ft_model(paths.ft_model(base), cfg)

    n_per = n_scenarios_per_unit(grid)
    print(f"t0={t0}, 시나리오/unit={n_per}, unit={len(units)} → {n_per * len(units)} 파일")
    rows = []
    for u in units:
        udf = cmapss.unit_frame(train_df, u)
        scens = make_scenarios(grid, T_u=len(udf), t0=t0)
        if a.limit:
            scens = scens[:a.limit]
        for sc in scens:
            sp = paths.shifted(u, sc["scenario_id"])
            if sp.exists() and not a.overwrite:
                _, meta = read_parquet(sp, with_meta=True)
            else:
                sdf, meta = inject(udf, sc, norm, sign_deg, grid["base_seed"], u)
                write_parquet(sdf, sp, meta=meta)
            rows.append(index_row_from_meta(meta))
            if model is not None:
                pp = paths.pred_shift(base, u, sc["scenario_id"])
                if pp.exists() and not a.overwrite:
                    continue
                sdf = read_parquet(sp) if sp.exists() else sdf
                pred = infer_unit(model, sdf, norm, cfg["seq_len"])
                write_parquet(pred, pp, meta={"unit": u, "seed": base, "kind": "shift", **{k: meta[k] for k in ("scenario_id", "tau_s", "type")}})
        print(f"unit {u}: {len(scens)} 시나리오 완료")

    idx = pd.DataFrame(rows)
    if paths.scenario_index.exists() and (a.units or a.limit):
        old = pd.read_csv(paths.scenario_index)
        keep_cols = [c for c in idx.columns if c in old.columns]
        old = old[keep_cols].drop_duplicates(subset=["unit", "scenario_id"])
        idx = pd.concat([old, idx]).drop_duplicates(subset=["unit", "scenario_id"], keep="last")
    idx = idx.sort_values(["unit", "scenario_id"]).reset_index(drop=True)
    paths.scenario_index.parent.mkdir(parents=True, exist_ok=True)
    idx.to_csv(paths.scenario_index, index=False)
    print(f"scenario_index 메타 {len(idx)} 행 → {paths.scenario_index}")


if __name__ == "__main__":
    main()
