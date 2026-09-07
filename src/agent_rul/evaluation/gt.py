"""Ground Truth 접근 — **evaluation/ 안에서만 import** (CLAUDE.md 규칙 2).

읽는 것:
    manifest.csv          category, unit, onset_cycle, sigma_mult, mode, profile,
                          channels, life_cycles, split
    series.npz:true_rul   cycle 별 true RUL (life_fraction 계산용)

data.py, reference/, tools/, agent/ 에서 이 모듈을 import 하면 규칙 위반이다
(tests/test_gt_isolation.py 가 검사한다).
"""
from __future__ import annotations

import csv
import os

import numpy as np


def load_manifest(manifest_csv: str) -> dict[str, dict]:
    """{scenario_id: row}. 숫자 컬럼은 형변환한다."""
    out = {}
    with open(manifest_csv, "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            r["unit"] = int(r["unit"])
            r["life_cycles"] = int(r["life_cycles"])
            r["onset_cycle"] = int(r["onset_cycle"]) if r["onset_cycle"] else 0
            r["sigma_mult"] = float(r["sigma_mult"]) if r["sigma_mult"] else 0.0
            r["direction"] = int(r["direction"]) if r["direction"] else 0
            out[r["scenario_id"]] = r
    return out


def scenario_gt(manifest: dict[str, dict], scenario_id: str) -> dict:
    """평가에 필요한 GT 만 뽑아낸다.

    Returns:
        is_faulty : category == 'sensor_fault'
        t_f       : fault onset cycle (clean 이면 None)
        alpha     : severity (sigma_mult)
        channel   : 주입 센서 이름 (clean 이면 None)
        mode, profile, unit, life_cycles
    """
    r = manifest[scenario_id]
    faulty = r["category"] == "sensor_fault"
    return {
        "scenario_id": scenario_id,
        "unit": r["unit"],
        "is_faulty": faulty,
        "t_f": int(r["onset_cycle"]) if faulty else None,
        "alpha": r["sigma_mult"] if faulty else 0.0,
        "channel": (r["primary_channel"] or None) if faulty else None,
        "mode": r["mode"],
        "profile": r["profile"],
        "life_cycles": r["life_cycles"],
        "split": r["split"],
    }


def true_rul(corrupted_root: str, manifest: dict[str, dict], scenario_id: str,
             ) -> dict[int, float]:
    """{cycle: true_rul}. series.npz 의 true_rul 배열을 읽는다 (GT)."""
    path = os.path.join(corrupted_root, manifest[scenario_id]["path"], "series.npz")
    z = np.load(path)
    cycles = z["cycles"].astype(int)
    vals = z["true_rul"].astype(float)
    return {int(c): float(v) for c, v in zip(cycles, vals)}


def life_fraction(cycle: int, life_cycles: int) -> float:
    """수명 진행률 (0~1). 열화 구간별 FP 분포 분석용 (agent_spec §2)."""
    return float(cycle) / float(life_cycles) if life_cycles else float("nan")
