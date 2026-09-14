"""시나리오 진단 그림: 정답 RUL · clean/shift 예측 · 주입 위치 · 저하 라벨 구간.

산출물만 읽으므로 06~08 을 돌린 뒤 언제든 실행할 수 있다 (재학습·재추론 없음).
결과 → reports/figures/scenarios/

  # 유형별 대표 사례 + T30 음성 대조군 자동 선택 (가장 먼저 이걸 써 보면 된다)
  python scripts/10_plot_scenario.py --examples

  # 특정 시나리오 지정
  python scripts/10_plot_scenario.py --unit 1 --scenario bias_T24_a0.5_pos_p0.2

  # 조건으로 찾기 (맞는 것 중 --limit 개)
  python scripts/10_plot_scenario.py --type bias --sensor T24 --param 1.0 --timing 0.2 --limit 4
  python scripts/10_plot_scenario.py --unit 1 --type noise --degraded

  # 다른 θ 정의로 (theta_primary | theta_alt1 | theta_alt2)
  python scripts/10_plot_scenario.py --examples --theta theta_alt1

  # 후보 목록만 보고 그리지는 않기
  python scripts/10_plot_scenario.py --type gain --degraded --list
"""
from __future__ import annotations

import argparse

import pandas as pd

from _bootstrap import setup
from src.analysis.scenario_fig import pick_examples, scenario_figure


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--unit", type=int, default=None)
    ap.add_argument("--scenario", default=None, help="scenario_id 직접 지정")
    ap.add_argument("--type", default=None, help="bias|gain|noise|stuck|multi_C|multi_I")
    ap.add_argument("--sensor", default=None, help="T24|T30|T50|T24+T30+T50")
    ap.add_argument("--param", type=float, default=None, help="alpha 또는 beta 값")
    ap.add_argument("--timing", type=float, default=None, help="timing_p")
    ap.add_argument("--degraded", action="store_true", help="저하 판정된 것만")
    ap.add_argument("--not-degraded", action="store_true", help="저하 아닌 것만")
    ap.add_argument("--theta", default="theta_primary",
                    choices=["theta_primary", "theta_alt1", "theta_alt2"])
    ap.add_argument("--examples", action="store_true", help="유형별 대표 + T30 대조군 자동 선택")
    ap.add_argument("--limit", type=int, default=6, help="조건 검색 시 최대 장수")
    ap.add_argument("--list", action="store_true", help="후보만 출력하고 그리지 않음")
    ap.add_argument("--outdir", default=None)
    a = ap.parse_args()

    paths, cfg = setup()
    outdir = paths.reports_dir / "figures" / "scenarios" if a.outdir is None else __import__("pathlib").Path(a.outdir)

    if a.examples:
        targets = [(u, s, note) for u, s, note in pick_examples(paths, a.theta)]
    elif a.scenario:
        if a.unit is None:
            raise SystemExit("--scenario 를 쓰면 --unit 도 필요하다")
        targets = [(a.unit, a.scenario, "")]
    else:
        idx = pd.read_csv(paths.scenario_index)
        idx = idx[idx.theta_name == a.theta]
        if a.unit is not None:
            idx = idx[idx.unit == a.unit]
        if a.type:
            idx = idx[idx.type == a.type]
        if a.sensor:
            idx = idx[idx.sensor == a.sensor]
        if a.param is not None:
            idx = idx[idx.param == a.param]
        if a.timing is not None:
            idx = idx[idx.timing_p == a.timing]
        if a.degraded:
            idx = idx[idx.degraded]
        if a.not_degraded:
            idx = idx[~idx.degraded]
        if idx.empty:
            raise SystemExit("조건에 맞는 시나리오가 없다. --list 로 범위를 넓혀 확인할 것")
        print(f"조건에 맞는 (unit, scenario) {len(idx)} 개 중 앞 {min(a.limit, len(idx))} 개")
        targets = [(int(r.unit), r.scenario_id,
                    f"{'저하 O' if r.degraded else '저하 X'}"
                    + (f" 지연 {int(r.delay)}" if pd.notna(r.delay) else ""))
                   for r in idx.head(a.limit).itertuples()]

    if a.list:
        for u, s, note in targets:
            print(f"  unit {u:>3}  {s:<34} {note}")
        return

    for u, s, note in targets:
        p = scenario_figure(paths, cfg, u, s, outdir / f"u{u}_{s}__{a.theta}.png", theta_name=a.theta)
        print(f"→ {p.relative_to(paths.root)}" + (f"   ({note})" if note else ""))


if __name__ == "__main__":
    main()
