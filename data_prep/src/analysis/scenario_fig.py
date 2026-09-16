"""한 (unit, scenario) 의 진단 그림: 정답 RUL · clean/shift 예측 · 주입 위치 · 저하 라벨 구간.

3단 패널 (x축 = cycle 공유)
  1) RUL      : 정답 RUL, 학습 목표(clip max_rul), clean 예측, shift 예측
  2) δ        : |δ| = |ŷ_shift − ŷ_clean| 와 θ_high / θ_low (θ_alt1 처럼 적응형이면 곡선)
  3) 주입 센서 : 주입 대상 센서의 clean vs shift 궤적 (norm_params_ft 로 z-score → α 와 같은 단위)

세 패널 공통으로 τ_s(주입 시작) · τ_d(저하 판정) 수직선과 label==1 구간 음영을 그린다.

앞 계층 산출물만 읽는다: preds/clean, preds/shift, labels/delta, labels/state,
data/shifted, labels/scenario_index.csv, data/norm/norm_params_ft.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.common import read_parquet
from src.data import cmapss
from src.data.loaders import load_norm_params

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    HAS_MPL = True
except Exception:  # pragma: no cover
    HAS_MPL = False

C_TRUE = "#222222"
C_CLIP = "#888888"
C_CLEAN = "#1f77b4"
C_SHIFT = "#d62728"
C_SPAN = "#d62728"
C_TAUS = "#ff7f0e"
C_TAUD = "#d62728"

# 한글 폰트가 없는 환경에서 □ 로 깨지지 않도록 라벨을 두 벌 둔다.
LAB = {
    "ko": {"true": "정답 RUL", "clip": "학습 목표 (clip {n})", "clean": "clean 예측 $\\hat{{y}}$",
           "shift": "shift 예측 $\\hat{{y}}'$", "rul": "RUL (cycle)", "cycle": "cycle",
           "sensor": "주입 센서 (z-score)", "span": "저하 라벨 (label=1)",
           "adaptive": "적응형", "fixed": "고정", "clean_s": "clean", "shift_s": "shift (주입)",
           "deg_y": "저하 O", "deg_n": "저하 X", "delay": "지연"},
    "en": {"true": "true RUL", "clip": "train target (clip {n})", "clean": "clean pred $\\hat{{y}}$",
           "shift": "shifted pred $\\hat{{y}}'$", "rul": "RUL (cycle)", "cycle": "cycle",
           "sensor": "injected sensor (z-score)", "span": "degraded label (label=1)",
           "adaptive": "adaptive", "fixed": "fixed", "clean_s": "clean", "shift_s": "shift (injected)",
           "deg_y": "DEGRADED", "deg_n": "not degraded", "delay": "delay"},
}


def setup_font() -> str:
    """폰트 설정은 plotting 모듈에 모아 두었다 (import 시 1회 적용). 언어 코드만 돌려준다."""
    from src.analysis import plotting as P

    return P.setup_font()


def label_runs(times: np.ndarray, label: np.ndarray) -> list[tuple[int, int]]:
    """label==1 인 연속 구간을 [(t_start, t_end), ...] 로. 없으면 빈 리스트."""
    runs, start = [], None
    for i, v in enumerate(label):
        if v and start is None:
            start = i
        elif not v and start is not None:
            runs.append((int(times[start]), int(times[i - 1])))
            start = None
    if start is not None:
        runs.append((int(times[start]), int(times[-1])))
    return runs


def index_row(paths, unit: int, scenario_id: str, theta_name: str = "theta_primary") -> pd.Series:
    idx = pd.read_csv(paths.scenario_index)
    m = idx[(idx.unit == unit) & (idx.scenario_id == scenario_id) & (idx.theta_name == theta_name)]
    if m.empty:
        raise SystemExit(f"scenario_index 에 없음: unit={unit} scenario={scenario_id} theta={theta_name}\n"
                         f"  (06~08 을 다시 돌렸다면 scenario_id 가 바뀌었을 수 있다)")
    return m.iloc[0]


def _sensor_list(sensor_field: str) -> list[str]:
    """'T24' 또는 'T24+T30+T50' → ['T24', ...]. stuck/single 도 동일 처리."""
    return [s for s in str(sensor_field).split("+") if s and s != "nan"]


def _mark(ax, tau_s, tau_d, runs, first: bool):
    """세 패널 공통 표시: 저하 구간 음영 + τ_s / τ_d 수직선."""
    for t0, t1 in runs:
        ax.axvspan(t0 - 0.5, t1 + 0.5, color=C_SPAN, alpha=0.11, lw=0, zorder=0)
    ax.axvline(tau_s, color=C_TAUS, ls="--", lw=1.4, zorder=3)
    if tau_d is not None and np.isfinite(tau_d):
        ax.axvline(tau_d, color=C_TAUD, ls=":", lw=1.4, zorder=3)
    if first:
        y = ax.get_ylim()[1]
        ax.text(tau_s, y, r" $\tau_s$", color=C_TAUS, va="top", ha="left", fontsize=9, fontweight="bold")
        if tau_d is not None and np.isfinite(tau_d):
            ax.text(tau_d, y, r" $\tau_d$", color=C_TAUD, va="top", ha="left", fontsize=9, fontweight="bold")


def scenario_figure(paths, cfg: dict, unit: int, scenario_id: str, out_path: Path,
                    theta_name: str = "theta_primary", base_seed: int | None = None) -> Path:
    """한 (unit, scenario) 의 3단 패널 그림을 out_path 에 저장하고 경로를 반환."""
    if not HAS_MPL:
        raise SystemExit("matplotlib 이 없다")
    L = LAB[setup_font()]
    base = base_seed or cfg["finetune"]["base_seed"]
    r = index_row(paths, unit, scenario_id, theta_name)
    tau_s = int(r.tau_s)
    tau_d = float(r.tau_d) if pd.notna(r.tau_d) else None

    clean = read_parquet(paths.pred_clean(base, unit))          # time, pred, rul_true
    dl = read_parquet(paths.delta(unit, scenario_id))           # time, pred_clean, pred_shift, delta
    st = read_parquet(paths.state(theta_name, unit, scenario_id))  # time, delta, label, state, theta_high/low
    runs = label_runs(st["time"].to_numpy(), st["label"].to_numpy().astype(bool))

    fig, axes = plt.subplots(3, 1, figsize=(11, 9), sharex=True,
                             gridspec_kw={"height_ratios": [3, 2, 2], "hspace": 0.12})
    ax1, ax2, ax3 = axes

    # ---------------- 1) RUL ----------------
    t, rul = clean["time"].to_numpy(), clean["rul_true"].to_numpy()
    ax1.plot(t, rul, color=C_TRUE, lw=1.8, label=L["true"])
    ax1.plot(t, np.minimum(rul, cfg["max_rul"]), color=C_CLIP, lw=1.2, ls="--",
             label=L["clip"].format(n=cfg["max_rul"]))
    ax1.plot(dl["time"], dl["pred_clean"], color=C_CLEAN, lw=1.5, label=L["clean"].format())
    ax1.plot(dl["time"], dl["pred_shift"], color=C_SHIFT, lw=1.5, label=L["shift"].format())
    ax1.fill_between(dl["time"], dl["pred_clean"], dl["pred_shift"], color=C_SHIFT, alpha=0.18, lw=0)
    ax1.set_ylabel(L["rul"])
    ax1.set_ylim(bottom=0)

    # ---------------- 2) δ ----------------
    ax2.plot(st["time"], st["delta"], color=C_SHIFT, lw=1.5, label=r"$|\delta| = |\hat{y}' - \hat{y}|$")
    th_hi, th_lo = st["theta_high"].to_numpy(), st["theta_low"].to_numpy()
    kind = L["adaptive"] if np.ptp(th_hi) > 1e-9 else L["fixed"]
    ax2.plot(st["time"], th_hi, color="#2ca02c", lw=1.2, ls="--",
             label=rf"$\theta_{{high}}$ ({kind}, {th_hi.mean():.2f})")
    ax2.plot(st["time"], th_lo, color="#2ca02c", lw=1.0, ls=":", label=r"$\theta_{low}$")
    ax2.set_ylabel(r"$|\delta|$")
    ax2.set_ylim(bottom=0)

    # ---------------- 3) 주입 센서 ----------------
    norm = load_norm_params(paths.norm_ft)
    raw = cmapss.unit_frame(cmapss.load_raw(paths.raw_dir, "train", cfg["sub_dataset"]), unit)
    sh = read_parquet(paths.shifted(unit, scenario_id))
    sens = _sensor_list(r.sensor)
    cmap = plt.get_cmap("tab10")
    for i, phys in enumerate(sens):
        col, fi = cmapss.resolve_sensor(phys), cmapss.feature_index_of(phys)
        if fi is None:
            continue
        mu, sd = norm[fi, 0], norm[fi, 1]
        zc = (raw[col].to_numpy() - mu) / (sd if sd else 1.0)
        zs = (sh[col].to_numpy() - mu) / (sd if sd else 1.0)
        # 단일 센서면 위 패널과 같은 색 규약(clean=파랑, shift=빨강), 다중이면 센서별 색
        cc, cs = (C_CLEAN, C_SHIFT) if len(sens) == 1 else (cmap(i), cmap(i))
        ax3.plot(raw["time"], zc, color=cc, lw=1.0, alpha=0.55 if len(sens) > 1 else 0.9, ls="--",
                 label=f"{phys} clean" if len(sens) > 1 else L["clean_s"])
        ax3.plot(sh["time"], zs, color=cs, lw=1.4,
                 label=f"{phys} shift" if len(sens) > 1 else L["shift_s"])
    ax3.set_ylabel(L["sensor"])
    ax3.set_xlabel(L["cycle"])

    for i, ax in enumerate(axes):
        _mark(ax, tau_s, tau_d, runs, first=(i == 0))
        ax.grid(alpha=0.25, lw=0.5)
        ax.legend(loc="upper right", fontsize=8, framealpha=0.9)

    # 저하 구간 범례는 한 번만
    if runs:
        h, l = ax1.get_legend_handles_labels()
        ax1.legend(h + [Patch(facecolor=C_SPAN, alpha=0.11)], l + [L["span"]],
                   loc="upper right", fontsize=8, framealpha=0.9)

    param = "na" if pd.isna(r.param) else f"{r.param:g}"
    try:
        theta_txt = f"{float(r.theta_value):.3f}"
    except (TypeError, ValueError):
        theta_txt = str(r.theta_value)  # θ_alt1 은 'max(0.2*yhat,9.399)' 같은 식 문자열
    title = (f"unit {unit}  |  {scenario_id}\n"
             f"{r.type} · {r.sensor} · {r.param_name}={param} · dir={r.dir} · "
             f"timing_p={r.timing_p:g} · $T_u$={int(r.T_u)}\n"
             f"{theta_name} θ={theta_txt}  k={int(r.k)} m={int(r.m)}  →  "
             + (f"{L['deg_y']}   $\\tau_s$={tau_s}  $\\tau_d$={int(tau_d)}  "
                f"{L['delay']}={int(tau_d - tau_s)}" if tau_d
                else f"{L['deg_n']}   $\\tau_s$={tau_s}"))
    fig.suptitle(title, fontsize=10.5, y=0.995, va="top")
    # suptitle 3 줄 + gridspec hspace 조합이라 tight_layout 대신 여백을 직접 잡는다
    fig.subplots_adjust(top=0.90, bottom=0.07, left=0.085, right=0.985)

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=130)
    plt.close(fig)
    return out_path


def pick_examples(paths, theta_name: str = "theta_primary") -> list[tuple[int, str, str]]:
    """유형별 대표 사례 + T30 음성 대조군을 고른다. 반환 [(unit, scenario_id, 설명)]."""
    idx = pd.read_csv(paths.scenario_index)
    idx = idx[idx.theta_name == theta_name]
    out = []
    for t in ["bias", "gain", "noise", "stuck", "multi_C", "multi_I"]:
        g = idx[(idx.type == t) & (idx.degraded)]
        if not g.empty:  # 지연이 중앙값에 가까운 = 전형적인 사례
            g = g.assign(d=(g.delay - g.delay.median()).abs()).sort_values("d")
            r = g.iloc[0]
            out.append((int(r.unit), r.scenario_id, f"{t} 저하 사례 (지연 {int(r.delay)})"))
    # T30 음성 대조군 ↔ T24 양성: unit·α·dir·timing 을 모두 맞춘 짝으로 뽑아야 비교가 성립한다.
    b = idx[idx.type == "bias"]
    key = ["unit", "param", "dir", "timing_p"]
    t30 = b[(b.sensor == "T30") & (~b.degraded)]
    t24 = b[(b.sensor == "T24") & (b.degraded)]
    pair = t30.merge(t24[key + ["scenario_id"]], on=key, suffixes=("_30", "_24"))
    if not pair.empty:  # 가장 강한 주입 · 가장 이른 시점 = 대비가 가장 뚜렷
        r = pair.sort_values(["param", "timing_p"], ascending=[False, True]).iloc[0]
        cond = f"α={r.param:g} {r.dir} p={r.timing_p:g}"
        out.append((int(r.unit), r.scenario_id_30, f"T30 음성 대조군 ({cond}, 모델이 둔감 → 저하 X)"))
        out.append((int(r.unit), r.scenario_id_24, f"T24 대비군 (같은 unit·{cond} → 저하 O)"))
    return out
