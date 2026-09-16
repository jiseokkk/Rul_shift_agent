"""Phase D 마감: cycle 단위 평가용 indeterminate 마스크 생성.

시나리오별 '최종 1→0 전이 이후 재진입 없는 구간' 을 채점 대상에서 빼기 위한 표.
θ 3종 각각에 대해 만든다. theta_primary 외에는 09 의 이벤트 추출 함수를 재사용해
해당 θ 라벨에서 이벤트를 다시 뽑는다.

라벨 파일(labels/*/state/) 은 읽기만 한다. 08 재실행 불필요.

산출물
  labels/FD001/meta/eval_mask.csv                 (theta_primary)
  labels/FD001/meta/eval_mask_theta_alt1.csv
  labels/FD001/meta/eval_mask_theta_alt2.csv
  reports/D_eval_mask_summary.md

  python scripts/12_build_eval_mask.py
  python scripts/12_build_eval_mask.py --thetas theta_primary     # 하나만
"""
from __future__ import annotations

import argparse

import pandas as pd

from _bootstrap import setup, load_json, load_yaml
from src.analysis import reversion as R
from src.label import eval_mask as EM
from src.label.build_labels import read_index_meta, resolve_thetas

PRIMARY = "theta_primary"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--thetas", nargs="*", default=["theta_primary", "theta_alt1", "theta_alt2"])
    ap.add_argument("--no-verify", action="store_true", help="마스크 이후 라벨 0 검증 생략")
    ap.add_argument("--no-report", action="store_true")
    a = ap.parse_args()

    paths, cfg = setup()
    lab = load_yaml("label")
    base = cfg["finetune"]["base_seed"]
    k, m, ratio = int(lab["k"]), int(lab["m"]), float(lab["theta_low_ratio"])
    seq_len = int(cfg["seq_len"])

    index_long = pd.read_csv(paths.scenario_index)
    index_meta = read_index_meta(paths.scenario_index)
    clean_var = load_json(paths.clean_variability) if paths.clean_variability.exists() else None
    repro = load_json(paths.reproduce_metrics) if paths.reproduce_metrics.exists() else None
    thetas = resolve_thetas(lab, clean_var, repro, base)
    theta_primary = float(thetas[PRIMARY]["value"])

    ev_csv = paths.labels_dir / "meta" / "reversion_events.csv"
    cache = None
    masks = {}
    for name in a.thetas:
        if name == PRIMARY and ev_csv.exists():
            ev = pd.read_csv(ev_csv)
            print(f"[{name}] 기존 reversion_events.csv 재사용 ({len(ev)} 이벤트)")
        else:
            if cache is None:
                print("[입력] delta/clean 로드 (09 의 이벤트 추출 재사용)")
                cache = R.load_inputs(paths, index_meta, base)
            ev, _ = R.events_for_labels(paths, index_meta, cache, theta_primary,
                                        thetas[name], k, m, ratio,
                                        from_state=True, theta_name=name)
            print(f"[{name}] 이벤트 재추출 ({len(ev)} 건)")
        mk = EM.build_mask(paths, index_long, ev, name, seq_len, verify=not a.no_verify)
        fn = "eval_mask.csv" if name == PRIMARY else f"eval_mask_{name}.csv"
        out = paths.labels_dir / "meta" / fn
        out.parent.mkdir(parents=True, exist_ok=True)
        mk.to_csv(out, index=False)
        masks[name] = mk
        has = mk["mask_from_cycle"].notna()
        n_eval = int((mk["T_u"] - (seq_len - 1)).sum())
        print(f"  → {out.relative_to(paths.root)}  "
              f"마스크 {int(has.sum())}/{len(mk)} 시나리오, "
              f"{int(mk['n_masked_cycles'].sum())}/{n_eval} cycle "
              f"({mk['n_masked_cycles'].sum() / max(1, n_eval):.3f})")

    if a.no_report or PRIMARY not in masks:
        return
    rep = EM.write_report(paths, masks, index_long, seq_len, PRIMARY)
    print(f"→ {rep.relative_to(paths.root)}")


if __name__ == "__main__":
    main()
