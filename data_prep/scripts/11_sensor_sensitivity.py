"""모델 입력 센서 감도 프로파일 → reports/B_sensor_sensitivity.md

hold-out 전 window 에 센서를 하나씩 +0.5σ (정규화 공간) 이동시켜 |Δŷ| 를 잰다.
Phase C 의 bias 주입이 정규화 공간에서 정확히 α 이므로, 이 값이 곧
"bias α=0.5 주입에 모델이 평균 몇 cycle 반응하는가" 이다.

T30 이 저하 라벨을 만들지 못하는 것이 seed 우연이 아님을 보이는 근거.

  python scripts/11_sensor_sensitivity.py
  python scripts/11_sensor_sensitivity.py --amp 1.0 --seeds 529
"""
from __future__ import annotations

import argparse

from _bootstrap import setup, load_json, load_yaml
from src.analysis import sensor_sensitivity as S


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--amp", type=float, default=0.5, help="주입 크기 (σ 단위, 정규화 공간)")
    ap.add_argument("--seeds", type=int, nargs="*", default=None)
    a = ap.parse_args()

    paths, cfg = setup()
    seeds = a.seeds or cfg["finetune"]["seeds"]
    split = load_json(paths.split_json)
    units = split["holdout_units"]

    cv = load_json(paths.clean_variability) if paths.clean_variability.exists() else None
    theta = float(cv["recommended"]["theta_primary"]) if cv else None
    injected = list(load_yaml("shift_grid")["sensors_single"])

    prof = S.profile(paths, cfg, units, seeds, amp=a.amp)
    n_win = int(len(S.holdout_windows(paths, cfg, units, S.load_norm_params(paths.norm_ft))))
    out = S.write_report(paths, prof, a.amp, theta, injected, n_win, seeds)
    prof.to_csv(paths.labels_dir / "meta" / "sensor_sensitivity.csv", index=False)
    print(f"→ {out.relative_to(paths.root)}")
    print(f"→ labels/{cfg['sub_dataset']}/meta/sensor_sensitivity.csv")


if __name__ == "__main__":
    main()
