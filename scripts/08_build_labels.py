"""Phase D-3~D-5: θ 3종 라벨 → labels/state/{theta}/..., scenario_index.csv (long, 결과 컬럼 추가),
reports/D_label_summary.md.  --sensitivity 로 (k, m) grid 부록."""
from __future__ import annotations

import argparse

from _bootstrap import setup, load_json, load_yaml
from src.analysis.label_summary import write_report
from src.label.build_labels import build_labels, read_index_meta, resolve_thetas, sensitivity


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sensitivity", action="store_true")
    ap.add_argument("--no-report", action="store_true")
    a = ap.parse_args()

    paths, cfg = setup()
    lab = load_yaml("label")
    base = cfg["finetune"]["base_seed"]
    cv = load_json(paths.clean_variability) if paths.clean_variability.exists() else None
    metrics = load_json(paths.reproduce_metrics) if paths.reproduce_metrics.exists() else None
    thetas = resolve_thetas(lab, cv, metrics, base)
    print("θ:", {k: (v["value"] if v["kind"] == "fixed" else f"max({v['ratio']}·ŷ, {v['floor']:.4g})") for k, v in thetas.items()})

    index_meta = read_index_meta(paths.scenario_index)
    long = build_labels(paths, index_meta, thetas, lab["k"], lab["m"], lab["theta_low_ratio"], cfg["max_rul"])
    long.to_csv(paths.scenario_index, index=False)
    print(f"scenario_index long {len(long)} 행 → {paths.scenario_index}")

    sens = None
    if a.sensitivity:
        sens = sensitivity(paths, index_meta, thetas["theta_primary"], lab["sensitivity"]["k"], lab["sensitivity"]["m"],
                           lab["theta_low_ratio"])
        sens.to_csv(paths.labels_dir / "meta" / "sensitivity_km.csv", index=False)
    if not a.no_report:
        out = write_report(paths, long, cv, sens=sens)
        print(f"→ {out}")


if __name__ == "__main__":
    main()
