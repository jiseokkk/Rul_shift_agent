"""Phase D-1/D-2: δ 계산(assert 포함) → labels/delta, clean 변동성 → labels/meta/clean_variability.json,
δ 분포 리포트 → reports/D_delta_distribution.md.

여기서 나온 권고 θ_primary 를 보고 configs/label.yaml 을 확정한다 (사람 판단).
"""
from __future__ import annotations

import argparse

from _bootstrap import setup, load_json, load_yaml, save_json
from src.analysis.delta_dist import collect_delta_stats, write_report
from src.common import read_parquet
from src.label.build_labels import read_index_meta
from src.label.delta import build_all_deltas
from src.label.variability import build_clean_variability


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--no-strict", action="store_true", help="τ_s 이전 δ≠0 을 예외 대신 기록만")
    a = ap.parse_args()

    paths, cfg = setup()
    lab = load_yaml("label")
    base = cfg["finetune"]["base_seed"]
    split = load_json(paths.split_json)
    index_meta = read_index_meta(paths.scenario_index)

    # D-1
    res = build_all_deltas(paths, index_meta, base, overwrite=a.overwrite, strict=not a.no_strict)
    if res["errors"]:
        save_json(res["errors"], paths.labels_dir / "meta" / "delta_errors.json")
        for e in res["errors"][:10]:
            print("  ", e)
        raise SystemExit(f"δ assert 실패 {len(res['errors'])} 건 → labels/meta/delta_errors.json. 중단.")

    # D-2 변동성
    pred_by_seed = {s: {u: read_parquet(paths.pred_clean(s, u)) for u in split["holdout_units"]}
                    for s in cfg["finetune"]["seeds"] if paths.pred_clean(s, split["holdout_units"][0]).exists()}
    metrics = load_json(paths.reproduce_metrics) if paths.reproduce_metrics.exists() else {}
    test_rmse = metrics.get("finetune", {}).get(str(base), {}).get("rmse")
    cv = build_clean_variability(pred_by_seed, base, test_rmse, lab["k"], lab["m"], lab["theta_low_ratio"],
                                 primary_pct=lab.get("primary_percentile", 95))
    save_json(cv, paths.clean_variability)
    th_p = cv["recommended"]["theta_primary"]
    thetas = sorted({round(th_p, 6), *(round(c["theta"], 6) for c in cv["candidates"].values()),
                     *([round(test_rmse, 6)] if test_rmse else [])})
    stats = collect_delta_stats(paths, index_meta, thetas)
    stats.to_csv(paths.labels_dir / "meta" / "delta_stats.csv", index=False)
    out = write_report(paths, stats, cv, thetas, lab, load_yaml("shift_grid"))
    print(f"권고 θ_primary = {th_p:.4g}  ({cv['recommended']['note']})")
    print(f"→ {paths.clean_variability}\n→ {out}")


if __name__ == "__main__":
    main()
