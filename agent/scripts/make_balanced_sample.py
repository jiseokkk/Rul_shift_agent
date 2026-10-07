"""유형별 균형 시나리오 표본을 configs/{out}.csv 로 만든다.

6개 오염 유형(bias, gain, noise, stuck, multi_C, multi_I)에 같은 수를 배정하고, 유형 안에서는
unit(20) · 주입 시점(4) · 센서 · 강도 · 방향이 고르게 퍼지도록 탐욕적으로 고른다 (seed 고정, 재현 가능).
출력 컬럼은 sample_tiered_full.csv 와 같다 (degraded 등 메타는 표본 구성·보고용. 에이전트는 unit, scenario_id 만 읽는다).

  python agent/scripts/make_balanced_sample.py --n 500 --out sample_or500
  python agent/scripts/make_balanced_sample.py --n 500 --out sample_or500 --per-type bias=120,gain=120,noise=100,stuck=60,multi_C=50,multi_I=50
"""
from __future__ import annotations

import argparse
from collections import Counter

import numpy as np
import pandas as pd

from _bootstrap import AGENT, load_cfg

TYPES = ["bias", "gain", "noise", "stuck", "multi_C", "multi_I"]
STRATA = ["timing_p", "sensor", "param", "dir"]
COLS = ["unit", "scenario_id", "type", "sensor", "param", "dir", "timing_p", "tau_s", "T_u", "degraded", "calls_post"]


def load_index() -> pd.DataFrame:
    paths, acfg = load_cfg("paths"), load_cfg("agent")
    idx = pd.read_csv(AGENT / paths["scenario_index"])
    idx = idx[idx.theta_name == acfg.get("theta_name", "theta_primary")].copy()
    idx["param"] = idx["param"].fillna(-1)
    idx["calls_post"] = idx["T_u"] - idx["tau_s"] + 1
    return idx.reset_index(drop=True)


def per_type_counts(n: int, spec: str | None) -> dict[str, int]:
    if spec:
        out = {k: int(v) for k, v in (kv.split("=") for kv in spec.split(","))}
        missing = [t for t in TYPES if t not in out]
        assert not missing, f"--per-type 에 없는 유형: {missing}"
        return out
    base, rem = divmod(n, len(TYPES))
    out = {t: base for t in TYPES}
    for t in TYPES[:rem]:  # 나머지는 풀이 큰 유형부터
        out[t] += 1
    return out


def pick_balanced(pool: pd.DataFrame, k: int, rng: np.random.Generator) -> list[int]:
    """unit 을 가장 적게 뽑힌 곳부터, 그 안에서 (timing, sensor, param, dir) 누적 수가 가장 작은 후보를 고른다."""
    assert k <= len(pool), f"요청 {k} > 풀 {len(pool)}"
    pool = pool.copy()
    pool["_r"] = rng.random(len(pool))
    unit_cnt: Counter = Counter()
    strata_cnt = {c: Counter() for c in STRATA}
    picked: list[int] = []
    for _ in range(k):
        avail = pool.loc[~pool.index.isin(picked)]
        min_u = min(unit_cnt[u] for u in avail.unit.unique())
        cand = avail[avail.unit.map(lambda u: unit_cnt[u] == min_u)]
        score = sum(cand[c].map(lambda v, c=c: strata_cnt[c][v]) for c in STRATA) + cand["_r"]
        i = int(score.idxmin())
        picked.append(i)
        unit_cnt[int(pool.at[i, "unit"])] += 1
        for c in STRATA:
            strata_cnt[c][pool.at[i, c]] += 1
    return picked


def fresh_calls(df: pd.DataFrame, judge_from: int) -> int:
    """unit 별 (공유 clean prefix) + 시나리오별 post 호출. 실측은 동시 실행 경쟁으로 약 4% 더 나온다."""
    return int(sum((g.tau_s.max() - judge_from) + (g.T_u - g.tau_s + 1).sum() for _, g in df.groupby("unit")))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=500)
    ap.add_argument("--out", default="sample_or500")
    ap.add_argument("--per-type", default=None, help="예: bias=120,gain=120,noise=100,stuck=60,multi_C=50,multi_I=50")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()

    idx = load_index()
    counts = per_type_counts(a.n, a.per_type)
    rng = np.random.default_rng(a.seed)
    parts = []
    for t in TYPES:
        pool = idx[idx.type == t]
        parts.append(pool.loc[pick_balanced(pool, counts[t], rng)])
    df = pd.concat(parts).sort_values(["unit", "type", "scenario_id"]).reset_index(drop=True)
    df["param"] = df["param"].replace(-1, np.nan)
    out = AGENT / "configs" / f"{a.out}.csv"
    df[COLS].to_csv(out, index=False)

    acfg = load_cfg("agent")
    jf = int(acfg["judge_from"])
    print(f"→ {out}  ({len(df)} 시나리오, seed {a.seed})")
    print("\n유형:", df.type.value_counts().reindex(TYPES).to_dict())
    print("unit 별:", df.groupby("unit").size().min(), "~", df.groupby("unit").size().max())
    print("\n유형 × 주입 시점\n", pd.crosstab(df.type, df.timing_p).reindex(TYPES).to_string())
    print("\n유형 × 센서\n", pd.crosstab(df.type, df.sensor).reindex(TYPES).to_string())
    print("\n유형 × 강도\n", pd.crosstab(df.type, df.param.fillna("na")).reindex(TYPES).to_string())
    print("\n유형 × 방향\n", pd.crosstab(df.type, df.dir).reindex(TYPES).to_string())
    print("\n저하 비율:", round(df.degraded.mean(), 3), "| 유형별", df.groupby("type").degraded.mean().round(2).reindex(TYPES).to_dict())
    dec, calls = int((df.T_u - jf + 1).sum()), fresh_calls(df, jf)
    print(f"\n판정 cycle {dec:,} · 고유 프롬프트(LLM 호출) {calls:,} · 시나리오당 판정 {dec / len(df):.0f}")


if __name__ == "__main__":
    main()
