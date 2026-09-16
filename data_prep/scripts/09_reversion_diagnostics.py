"""Phase D 마감: 복귀(1→0) 진단 및 (k, m) 확정 근거 생성.

현재 라벨(state parquet)의 1→0 전이를 전부 이벤트로 뽑아 A(flicker)/B(말기 수렴)/C(진짜 복귀)
로 분류하고, (k, m) 대안을 메모리에서 다시 라벨링해 비교한다. 기존 state parquet 은 건드리지 않는다.

산출물
  labels/FD001/meta/reversion_events.csv   이벤트 테이블 (기준 (k,m))
  reports/D_reversion_diagnostics.md       9 개 절 + 판정
  reports/figures/D_reversion_*.png        사례 5 종 + 분포 2 종

  python scripts/09_reversion_diagnostics.py
  python scripts/09_reversion_diagnostics.py --km 5,7 7,10 7,7 5,10     # 비교할 조합
  python scripts/09_reversion_diagnostics.py --theta theta_alt1
"""
from __future__ import annotations

import argparse

import pandas as pd

from _bootstrap import setup, load_json, load_yaml
from src.analysis import reversion as R
from src.label.build_labels import read_index_meta, resolve_thetas


def parse_km(items: list[str]) -> list[tuple[int, int]]:
    out = []
    for it in items:
        k, m = it.split(",")
        k, m = int(k), int(m)
        if k > m:
            raise SystemExit(f"k <= m 이어야 한다: {it}")
        out.append((k, m))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--theta", default="theta_primary")
    ap.add_argument("--km", nargs="*", default=["5,7", "7,10", "7,7", "5,10"],
                    help="비교할 (k,m) 조합. 예: --km 5,7 7,10")
    ap.add_argument("--no-report", action="store_true")
    a = ap.parse_args()

    paths, cfg = setup()
    lab = load_yaml("label")
    base = cfg["finetune"]["base_seed"]
    k, m, ratio = int(lab["k"]), int(lab["m"]), float(lab["theta_low_ratio"])

    index_meta = read_index_meta(paths.scenario_index)
    clean_var = load_json(paths.clean_variability) if paths.clean_variability.exists() else None
    repro = load_json(paths.reproduce_metrics) if paths.reproduce_metrics.exists() else None
    thetas = resolve_thetas(lab, clean_var, repro, base)
    spec = thetas[a.theta]
    theta_primary = float(thetas["theta_primary"]["value"])
    print(f"θ_primary = {theta_primary:.4f}, 기준 (k,m) = ({k},{m}), θ_low_ratio = {ratio}")

    print(f"[1/4] 입력 로드 ({len(index_meta)} 시나리오)")
    cache = R.load_inputs(paths, index_meta, base)

    print("[2/4] 현재 라벨에서 복귀 이벤트 추출")
    ev, sc = R.events_for_labels(paths, index_meta, cache, theta_primary, spec, k, m, ratio,
                                 from_state=True, theta_name=a.theta)
    out_csv = paths.labels_dir / "meta" / "reversion_events.csv"
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    ev.to_csv(out_csv, index=False)
    shares = R.pattern_shares(ev)
    print(f"  이벤트 {len(ev)} 개  A={shares['A']:.3f} B={shares['B']:.3f} C={shares['C']:.3f}")
    print(f"  → {out_csv.relative_to(paths.root)}")

    print("[3/4] (k, m) 대안 비교")
    rows = []
    for kk, mm in parse_km(a.km):
        if (kk, mm) == (k, m):
            e2, s2 = ev, sc
        else:
            e2, s2 = R.events_for_labels(paths, index_meta, cache, theta_primary, spec, kk, mm, ratio)
        sh = R.pattern_shares(e2)
        d2 = s2[s2["degraded"]]
        rows.append({"k": kk, "m": mm, "기준": "←" if (kk, mm) == (k, m) else "",
                     "저하율": float(s2["degraded"].mean()),
                     "복귀율": float((s2["n_reversions"] > 0).mean()),
                     "이벤트 n": len(e2),
                     "재진입률": float(e2["reentry_within_20"].mean()) if len(e2) else float("nan"),
                     "A": sh["A"], "B": sh["B"], "C": sh["C"],
                     "지연 median": float(d2["delay"].dropna().median()) if d2["delay"].notna().any() else None})
        print(f"  (k={kk}, m={mm}) 저하 {rows[-1]['저하율']:.3f}  복귀 {rows[-1]['복귀율']:.3f}  "
              f"A={sh['A']:.3f} B={sh['B']:.3f} C={sh['C']:.3f}")
    km_table = pd.DataFrame(rows)

    if a.no_report:
        return
    print("[4/4] 리포트 작성")
    out, shares, verd, acts = R.write_report(paths, ev, sc, theta_primary, km_table, cache, k, m, ratio)
    print(f"→ {out.relative_to(paths.root)}\n")
    print("=" * 60)
    print("판정")
    for v in verd:
        print("  -", v.replace("**", ""))
    print("조치")
    for x in acts:
        print("  -", x)
    print("=" * 60)


if __name__ == "__main__":
    main()
