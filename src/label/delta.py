"""Phase D-1: δ(t) = |ỹ(t) − ŷ(t)|, t ∈ [45, T_u].  τ_s 이전 δ == 0 assert."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.common import read_parquet, write_parquet


class DeltaAssertionError(AssertionError):
    pass


def compute_delta(pred_clean: pd.DataFrame, pred_shift: pd.DataFrame, tau_s: int,
                  strict: bool = True, atol: float = 0.0) -> pd.DataFrame:
    """[time, pred_clean, pred_shift, delta]. τ_s 이전 δ 가 0 이 아니면 예외 (강제로 덮지 않음)."""
    a = pred_clean[["time", "pred"]].rename(columns={"pred": "pred_clean"})
    b = pred_shift[["time", "pred"]].rename(columns={"pred": "pred_shift"})
    df = a.merge(b, on="time", how="inner").sort_values("time").reset_index(drop=True)
    if len(df) != len(a) or len(df) != len(b):
        raise DeltaAssertionError(f"clean/shift 예측 길이 불일치: clean={len(a)} shift={len(b)} merged={len(df)}")
    df["delta"] = (df["pred_shift"] - df["pred_clean"]).abs()
    before = df["time"] < tau_s
    if strict and before.any():
        bad = df.loc[before & (df["delta"] > atol)]
        if len(bad):
            raise DeltaAssertionError(
                f"τ_s={tau_s} 이전 δ≠0 (n={len(bad)}, max={bad['delta'].max():.6g}). "
                "원인: (a) 주입이 τ_s 앞으로 샘 (b) 추론 비결정성")
    return df


def build_all_deltas(paths, index_df: pd.DataFrame, base_seed: int, overwrite: bool = False,
                     strict: bool = True, log=print) -> dict:
    """scenario_index 메타 행마다 delta parquet 생성. 반환: {'n_built', 'n_skipped', 'errors': [...]}"""
    n_built = n_skipped = 0
    errors = []
    clean_cache: dict[int, pd.DataFrame] = {}
    for r in index_df.itertuples(index=False):
        unit, sid, tau_s = int(r.unit), r.scenario_id, int(r.tau_s)
        out = paths.delta(unit, sid)
        if out.exists() and not overwrite:
            n_skipped += 1
            continue
        if unit not in clean_cache:
            clean_cache[unit] = read_parquet(paths.pred_clean(base_seed, unit))
        try:
            shift = read_parquet(paths.pred_shift(base_seed, unit, sid))
            d = compute_delta(clean_cache[unit], shift, tau_s, strict=strict)
        except (DeltaAssertionError, FileNotFoundError) as e:
            errors.append({"unit": unit, "scenario_id": sid, "error": str(e)})
            continue
        write_parquet(d, out, meta={"unit": unit, "scenario_id": sid, "tau_s": tau_s, "base_seed": base_seed})
        n_built += 1
    log(f"[delta] built={n_built} skipped={n_skipped} errors={len(errors)}")
    return {"n_built": n_built, "n_skipped": n_skipped, "errors": errors}
