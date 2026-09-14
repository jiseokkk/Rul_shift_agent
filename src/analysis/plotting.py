"""matplotlib 이 없으면 조용히 건너뛰는 플롯 헬퍼."""
from __future__ import annotations

from pathlib import Path

import numpy as np

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    HAS_MPL = True
except Exception:  # pragma: no cover
    HAS_MPL = False

# 한글 폰트가 없는 환경에서 □ 로 깨지지 않도록. 뒤의 DejaVu 는 CJK 폰트에 없는
# 라틴 확장 글리프(ŷ = U+0177) 폴백용이다 (matplotlib 3.6+ 폰트 폴백).
KO_FONTS = ["Noto Sans CJK KR", "Noto Sans CJK JP", "NanumGothic", "NanumBarunGothic",
            "Malgun Gothic", "AppleGothic", "UnDotum", "Source Han Sans KR"]


def setup_font() -> str:
    """사용 가능한 한글 폰트를 rcParams 에 지정. 없으면 'en' 을 반환해 영문 라벨을 쓰게 한다."""
    if not HAS_MPL:
        return "en"
    from matplotlib import font_manager as fm

    have = {f.name for f in fm.fontManager.ttflist}
    for name in KO_FONTS:
        if name in have:
            plt.rcParams["font.family"] = [name, "DejaVu Sans"]
            plt.rcParams["axes.unicode_minus"] = False
            return "ko"
    return "en"


LANG = setup_font()   # 이 모듈을 쓰는 모든 그림에 한 번만 적용


def hist(arrays: dict, path: Path, title: str, xlabel: str, bins=60, log_y=True) -> bool:
    if not HAS_MPL:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7, 4))
    for name, a in arrays.items():
        a = np.asarray(a, dtype=float)
        if a.size:
            ax.hist(a, bins=bins, alpha=0.5, label=f"{name} (n={a.size})")
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    if log_y:
        ax.set_yscale("log")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return True


def heatmap(matrix: np.ndarray, row_labels, col_labels, path: Path, title: str, fmt="{:.2f}") -> bool:
    if not HAS_MPL:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(1.2 * len(col_labels) + 3, 0.5 * len(row_labels) + 2))
    im = ax.imshow(matrix, cmap="viridis", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(col_labels)))
    ax.set_xticklabels(col_labels, rotation=45, ha="right")
    ax.set_yticks(range(len(row_labels)))
    ax.set_yticklabels(row_labels)
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            v = matrix[i, j]
            if not np.isnan(v):
                ax.text(j, i, fmt.format(v), ha="center", va="center",
                        color="white" if v < 0.5 else "black", fontsize=8)
    ax.set_title(title)
    fig.colorbar(im, ax=ax)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return True


def lines(series: dict, path: Path, title: str, xlabel: str, ylabel: str, vlines: dict | None = None) -> bool:
    if not HAS_MPL:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 4))
    for name, (x, y) in series.items():
        ax.plot(x, y, label=name, lw=1)
    for name, xv in (vlines or {}).items():
        ax.axvline(xv, ls="--", c="gray", lw=1)
        ax.text(xv, ax.get_ylim()[1], name, rotation=90, va="top", fontsize=8)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return True


def box(groups: dict, path: Path, title: str, ylabel: str, hline: float | None = None,
        hline_label: str = "") -> bool:
    """{그룹명: 값 배열} 박스플롯. hline 이 있으면 수평 기준선을 긋는다."""
    if not HAS_MPL:
        return False
    groups = {k: np.asarray(v, dtype=float) for k, v in groups.items()}
    groups = {k: v[np.isfinite(v)] for k, v in groups.items()}
    groups = {k: v for k, v in groups.items() if v.size}
    if not groups:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(1.1 * len(groups) + 3, 4.2))
    ax.boxplot(list(groups.values()), tick_labels=[f"{k}\n(n={v.size})" for k, v in groups.items()],
               showfliers=False, medianprops={"color": "#d62728"})
    if hline is not None:
        ax.axhline(hline, color="#2ca02c", ls="--", lw=1.2, label=hline_label or f"{hline:.3g}")
        ax.legend(fontsize=8)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.grid(alpha=0.25, lw=0.5, axis="y")
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return True


def bar(values: dict, path: Path, title: str, ylabel: str, errs: dict | None = None,
        highlight: list | None = None, hline: float | None = None, hline_label: str = "") -> bool:
    """{이름: 값} 막대그래프 (값 내림차순). highlight 에 든 이름은 색을 달리한다."""
    if not HAS_MPL:
        return False
    if not values:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    items = sorted(values.items(), key=lambda kv: -kv[1])
    names = [k for k, _ in items]
    vals = [v for _, v in items]
    e = [float((errs or {}).get(k, 0.0)) for k in names]
    hl = set(highlight or [])
    colors = ["#d62728" if n in hl else "#7f9fc4" for n in names]
    fig, ax = plt.subplots(figsize=(0.55 * len(names) + 3, 4.4))
    ax.bar(range(len(names)), vals, yerr=e, capsize=3, color=colors, edgecolor="#33475b", lw=0.6)
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, rotation=45, ha="right", fontsize=9)
    if hline is not None:
        ax.axhline(hline, color="#2ca02c", ls="--", lw=1.3, label=hline_label or f"{hline:.3g}")
        ax.legend(fontsize=8)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.grid(alpha=0.25, lw=0.5, axis="y")
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return True
