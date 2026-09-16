"""Phase A: 층화 hold-out 분할 (unit 단위)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.common import md_table


def stratified_holdout(lengths: pd.Series, n_holdout: int = 20, n_strata: int = 5, seed: int = 529) -> dict:
    """T_u 오름차순으로 n_strata 분위로 나눠 각 분위에서 같은 수를 무작위 추출.

    lengths: unit id → T_u
    """
    assert n_holdout % n_strata == 0, "n_holdout 은 n_strata 의 배수"
    per = n_holdout // n_strata
    order = lengths.sort_values(kind="mergesort")  # 동률은 id 순 유지
    ids = order.index.to_numpy()
    strata = np.array_split(ids, n_strata)
    rng = np.random.default_rng(seed)
    holdout = []
    for s in strata:
        holdout.extend(rng.choice(s, size=per, replace=False).tolist())
    holdout = sorted(int(u) for u in holdout)
    train = sorted(int(u) for u in ids if int(u) not in set(holdout))
    return {
        "seed": seed,
        "n_strata": n_strata,
        "holdout_units": holdout,
        "train_units": train,
        "unit_lengths": {int(u): int(lengths[u]) for u in lengths.index},
    }


def tau_s_of(T_u: int, p: float, t0: int) -> int:
    """τ_s = round(t0 + p·(T_u − t0)). 파이썬 round 의 짝수 반올림을 피하려 floor(x+0.5)."""
    return int(np.floor(t0 + p * (T_u - t0) + 0.5))


def split_report(split: dict, timing_p: list[float], t0: int, max_rul: int, seq_len: int) -> str:
    lengths = pd.Series(split["unit_lengths"]).astype(int)
    lengths.index = lengths.index.astype(int)
    ho = lengths[split["holdout_units"]]
    tr = lengths[split["train_units"]]

    def stats(s: pd.Series) -> dict:
        return {"n": int(len(s)), "min": int(s.min()), "q25": float(s.quantile(0.25)),
                "median": float(s.median()), "q75": float(s.quantile(0.75)), "max": int(s.max()),
                "mean": float(s.mean())}

    lines = ["# Phase A — Hold-out 분할 요약", ""]
    lines.append(f"- seed: {split['seed']}, strata: {split['n_strata']}, hold-out {len(ho)} / train {len(tr)}")
    lines.append(f"- t0 = seq_len({seq_len}) + N = {t0}, timing_p = {timing_p}")
    lines.append("")
    lines.append("## T_u 분포 비교")
    rows = [dict(group="all", **stats(lengths)), dict(group="train", **stats(tr)), dict(group="holdout", **stats(ho))]
    lines.append(md_table(rows, fmt="{:.1f}"))

    # 히스토그램 (텍스트)
    bins = np.arange(120, 380, 20)
    h_all, _ = np.histogram(lengths, bins=bins)
    h_ho, _ = np.histogram(ho, bins=bins)
    lines.append("## 히스토그램 (bin=20)")
    rows = [{"bin": f"{int(b)}-{int(b + 20)}", "all": int(a), "holdout": int(h)} for b, a, h in zip(bins[:-1], h_all, h_ho)]
    lines.append(md_table(rows))

    lines.append("## Hold-out unit 별 τ_s 와 포화 예상 (T_u − τ_s > max_rul)")
    rows = []
    for u in split["holdout_units"]:
        T = int(lengths[u])
        r = {"unit": u, "T_u": T}
        for p in timing_p:
            ts = tau_s_of(T, p, t0)
            r[f"tau_s p{p}"] = ts
            r[f"sat p{p}"] = (T - ts) > max_rul
        rows.append(r)
    lines.append(md_table(rows))
    return "\n".join(lines) + "\n"
