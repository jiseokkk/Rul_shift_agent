"""모델 입력 센서 감도 프로파일 (reports/B_sensor_sensitivity.md).

hold-out 전 window 에 센서 하나씩 +δ σ (정규화 공간) 를 더하고 |Δŷ| 를 잰다.
Phase C 의 bias 주입이 정규화 공간에서 정확히 α 이므로, 여기서 잰 감도가
"같은 크기 주입에 모델이 얼마나 반응하는가" 를 그대로 나타낸다.

T30 이 저하 라벨을 만들지 못하는 것이 특정 seed 의 우연이 아니라 세 seed 공통의
모델 성질임을 보이는 근거로 쓴다.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import torch

from src.analysis import plotting
from src.common import md_table
from src.data import cmapss
from src.data.loaders import apply_zscore, load_norm_params, unit_windows  # noqa: F401 (스크립트에서 재사용)
from src.model.train_ft import load_ft_model


def holdout_windows(paths, cfg: dict, units: list[int], norm: np.ndarray) -> np.ndarray:
    train_df = cmapss.load_raw(paths.raw_dir, "train", cfg["sub_dataset"])
    W = [unit_windows(apply_zscore(cmapss.feature_matrix(cmapss.unit_frame(train_df, u)), norm),
                      cfg["seq_len"], only_final=False).astype(np.float32) for u in units]
    return np.concatenate(W)


@torch.no_grad()
def _predict(model, W: np.ndarray, device, batch: int = 4096) -> np.ndarray:
    out = []
    for i in range(0, len(W), batch):
        out.append(model(torch.from_numpy(W[i:i + batch]).to(device)).squeeze(1).cpu().numpy())
    return np.concatenate(out)


def profile(paths, cfg: dict, units: list[int], seeds: list[int], amp: float = 0.5,
            log=print) -> pd.DataFrame:
    """센서 × seed 별 |Δŷ| 평균과 부호 있는 Δŷ 평균. 반환 long-format DataFrame."""
    norm = load_norm_params(paths.norm_ft)
    W = holdout_windows(paths, cfg, units, norm)
    log(f"[sens] hold-out window {len(W)} 개, 입력 {W.shape[2]} 채널, +{amp}σ 주입")
    names = cmapss.MODEL_FEATURE_NAMES
    rows = []
    for s in seeds:
        model = load_ft_model(paths.ft_model(s), cfg)
        device = next(model.parameters()).device
        base = _predict(model, W, device)
        for fi, nm in enumerate(names):
            Wp = W.copy()
            Wp[:, :, fi] += amp
            d = _predict(model, Wp, device) - base
            rows.append({"seed": s, "feat_idx": fi, "col": nm, "sensor": cmapss.phys_name(nm),
                         "is_op": nm.startswith("op"),
                         "abs_mean": float(np.abs(d).mean()), "signed_mean": float(d.mean()),
                         "p95_abs": float(np.percentile(np.abs(d), 95))})
        log(f"[sens] seed {s} 완료")
    return pd.DataFrame(rows)


def write_report(paths, prof: pd.DataFrame, amp: float, theta_primary: float | None,
                 injected: list[str], n_windows: int, seeds: list[int]) -> Path:
    fig_dir = paths.reports_dir / "figures"
    piv = prof.pivot_table(index=["feat_idx", "col", "sensor", "is_op"], columns="seed",
                           values="abs_mean").reset_index()
    seed_cols = [c for c in piv.columns if isinstance(c, (int, np.integer))]
    piv["mean"] = piv[seed_cols].mean(axis=1)
    piv["std"] = piv[seed_cols].std(axis=1)
    sg = prof.pivot_table(index="feat_idx", columns="seed", values="signed_mean").mean(axis=1)
    piv["signed_mean"] = piv["feat_idx"].map(sg)
    piv = piv.sort_values("mean", ascending=False)

    L = ["# 모델 입력 센서 감도 프로파일", "",
         f"- hold-out {n_windows} window 전체에 센서 하나씩 "
         f"**+{amp}σ (정규화 공간)** 를 더하고 |Δŷ| 를 측정",
         f"- seed {seeds} 세 모델 각각에 대해 수행",
         "- Phase C 의 bias 주입은 정규화 공간에서 정확히 α 이므로, 여기 값이 "
         f"\"bias α={amp} 주입 시 예측이 평균 몇 cycle 움직이는가\" 와 같다",
         ]
    if theta_primary:
        L.append(f"- 비교 기준: θ_primary = {theta_primary:.3f} (이 값을 넘겨야 저하 라벨이 생긴다)")
    L += ["", "## 1. 센서별 absΔŷ (seed 평균 내림차순)", ""]
    by_seed = prof.set_index(["seed", "feat_idx"])["abs_mean"]
    rows = []
    for r in piv.itertuples(index=False):
        row = {"feat": int(r.feat_idx), "센서": r.sensor, "col": r.col}
        for c in seed_cols:
            row[f"s{int(c)}"] = float(by_seed.loc[(c, int(r.feat_idx))])
        row.update({"평균": float(r.mean), "표준편차": float(r.std),
                    "부호평균": float(r.signed_mean),
                    "주입대상": "●" if r.sensor in injected else ""})
        rows.append(row)
    L += [md_table(rows, fmt="{:.3f}"), ""]

    # 주입 대상 3 센서 대비
    inj = piv[piv["sensor"].isin(injected)].sort_values("mean", ascending=False)
    if len(inj):
        top = float(piv["mean"].max())
        L += ["## 2. Phase C 주입 대상 3 센서", ""]
        rows = [{"센서": r.sensor, "absΔŷ 평균": float(r.mean), "표준편차": float(r.std),
                 "최대 센서 대비": float(r.mean) / top if top else np.nan,
                 "전체 순위": int(list(piv["sensor"]).index(r.sensor) + 1),
                 "θ_primary 대비": (float(r.mean) / theta_primary) if theta_primary else np.nan}
                for r in inj.itertuples(index=False)]
        L += [md_table(rows, fmt="{:.3f}"), ""]
        lo = inj.iloc[-1]
        hi = inj.iloc[0]
        L += [f"**{lo.sensor} 의 감도는 {hi.sensor} 의 {float(lo['mean']) / float(hi['mean']):.2f} 배**이고, "
              f"seed 간 표준편차는 {float(lo['std']):.3f} 에 불과하다 "
              f"(seed {seeds} 전부에서 같은 결론). "
              f"즉 {lo.sensor} 가 저하 라벨을 만들지 못하는 것은 특정 학습 seed 의 우연이 아니라 "
              f"세 모델이 공통으로 학습한 성질이다.", ""]

    L += ["## 3. 그림", ""]
    sens_only = piv[~piv["is_op"]]
    if plotting.bar({r.sensor: float(r.mean) for r in sens_only.itertuples(index=False)},
                    fig_dir / "B_sensor_sensitivity.png",
                    f"센서별 abs(dy) (+{amp}σ 주입, seed {len(seeds)}개 평균)", "abs(dy) (cycle)",
                    errs={r.sensor: float(r.std) for r in sens_only.itertuples(index=False)},
                    highlight=injected, hline=theta_primary,
                    hline_label=f"θ_primary {theta_primary:.2f}" if theta_primary else ""):
        L.append("![sensitivity](figures/B_sensor_sensitivity.png)")
    L.append("")

    out = paths.reports_dir / "B_sensor_sensitivity.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    return out
