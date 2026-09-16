"""Phase B-4: hold-out 20 × 3 seed 전 cycle clean 추론 → preds/FD001/clean/s{seed}/u{unit}.parquet
+ 결정성 검증 + 정합성 검증 1·2 → reproduce_metrics.json["holdout_checks"], reports/B_reproduction.md"""
from __future__ import annotations

import argparse

from _bootstrap import setup, load_json, save_json
from src.common import md_table, read_parquet, write_parquet
from src.data import cmapss
from src.data.loaders import load_norm_params
from src.model.evaluate import holdout_cutpoint_check, holdout_range_rmse
from src.model.infer_full import determinism_check, enable_determinism, infer_unit
from src.model.train_ft import load_ft_model


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="*", default=None)
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--skip-determinism", action="store_true")
    a = ap.parse_args()

    paths, cfg = setup()
    seeds = a.seeds or cfg["finetune"]["seeds"]
    base = cfg["finetune"]["base_seed"]
    split = load_json(paths.split_json)
    norm = load_norm_params(paths.norm_ft)
    train_df = cmapss.load_raw(paths.raw_dir, "train", cfg["sub_dataset"])
    det_ok = enable_determinism()

    frames_by_seed = {}
    for s in seeds:
        model = load_ft_model(paths.ft_model(s), cfg)
        frames = {}
        for i, u in enumerate(split["holdout_units"]):
            udf = cmapss.unit_frame(train_df, u)
            if s == base and i == 0 and not a.skip_determinism:
                if not determinism_check(model, udf, norm, cfg["seq_len"]):
                    raise SystemExit("결정성 검증 실패: 같은 입력 두 번 추론 결과가 다름. Phase D assert 가 무의미하므로 중단")
                print("결정성 검증 통과 (unit", u, ")")
            out = paths.pred_clean(s, u)
            if out.exists() and not a.overwrite:
                frames[u] = read_parquet(out)
                continue
            df = infer_unit(model, udf, norm, cfg["seq_len"], with_true=True)
            write_parquet(df, out, meta={"unit": u, "seed": s, "kind": "clean", "T_u": len(udf)})
            frames[u] = df
        frames_by_seed[s] = frames
        print(f"seed {s}: {len(frames)} unit 추론 완료")

    # 정합성 검증 (기준 seed)
    cut = holdout_cutpoint_check(frames_by_seed[base], cfg["max_rul"], seed=base)
    rng_rows = holdout_range_rmse(frames_by_seed[base], cfg["max_rul"])
    metrics = load_json(paths.reproduce_metrics) if paths.reproduce_metrics.exists() else {}
    metrics["holdout_checks"] = {"determinism_api": det_ok, "cutpoint": cut, "rul_range": rng_rows}
    save_json(metrics, paths.reproduce_metrics)
    test_rmse = metrics.get("finetune", {}).get(str(base), {}).get("rmse")

    rep = paths.reports_dir / "B_reproduction.md"
    txt = rep.read_text(encoding="utf-8") if rep.exists() else "# Phase B — 재현 확인\n\n"
    txt += (f"\n## B-4 hold-out clean 추론 검증 (seed {base})\n"
            f"- 결정성: 같은 입력 두 번 → 완전 일치 {'통과' if not a.skip_determinism else '(건너뜀)'}; use_deterministic_algorithms={det_ok}\n"
            f"- 정합성 1 (unit 당 무작위 절단점, test 방식): RMSE {cut['rmse']:.3f}, Score {cut['score']:.1f}, n={cut['n']}"
            f"  vs test RMSE {test_rmse}\n"
            f"- 정합성 2 (전 cycle, true RUL 구간별):\n\n" + md_table(rng_rows, fmt="{:.3f}"))
    rep.write_text(txt, encoding="utf-8")
    print(f"절단점 RMSE={cut['rmse']:.3f} (test RMSE={test_rmse})")


if __name__ == "__main__":
    main()
