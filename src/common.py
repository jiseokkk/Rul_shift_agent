"""공통 유틸: 프로젝트 루트 탐색, YAML/JSON 로드, 경로 해석, seed 고정, parquet 메타."""
from __future__ import annotations

import json
import os
import random
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import yaml


def find_root(start: str | Path | None = None) -> Path:
    p = Path(start or __file__).resolve()
    for parent in [p] + list(p.parents):
        if (parent / "configs" / "paths.yaml").exists():
            return parent
    raise FileNotFoundError("configs/paths.yaml 을 가진 프로젝트 루트를 찾을 수 없음")


ROOT = find_root()


def load_yaml(name_or_path: str | Path) -> dict:
    p = Path(name_or_path)
    if not p.suffix:
        p = ROOT / "configs" / f"{p}.yaml"
    elif not p.is_absolute():
        p = ROOT / p
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_yaml(obj: Any, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(obj, f, allow_unicode=True, sort_keys=False)


def load_json(path: str | Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(obj: Any, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, default=_json_default)


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, Path):
        return str(o)
    raise TypeError(f"not serializable: {type(o)}")


class Paths:
    """configs/paths.yaml 의 항목을 ROOT 기준 절대경로로 해석."""

    def __init__(self, sub_dataset: str = "FD001"):
        cfg = load_yaml("paths")
        self.sub = sub_dataset
        self.root = ROOT
        self.rul_repo = ROOT / cfg["rul_repo"]
        self.raw_dir = ROOT / cfg["raw_dir"]
        self.data_dir = ROOT / cfg["data_dir"]
        self.split_dir = ROOT / cfg["split_dir"]
        self.norm_dir = ROOT / cfg["norm_dir"]
        self.shifted_dir = ROOT / cfg["shifted_dir"] / sub_dataset
        self.models_dir = ROOT / cfg["models_dir"] / sub_dataset
        self.preds_dir = ROOT / cfg["preds_dir"] / sub_dataset
        self.labels_dir = ROOT / cfg["labels_dir"] / sub_dataset
        self.reports_dir = ROOT / cfg["reports_dir"]

    # 자주 쓰는 파일
    @property
    def split_json(self) -> Path:
        return self.split_dir / f"split_{self.sub}.json"

    @property
    def norm_ft(self) -> Path:
        return self.norm_dir / f"norm_params_ft_{self.sub}.npy"

    def norm_pre(self, pre_name: str = "FD0013") -> Path:
        return self.norm_dir / f"norm_params_pre_{pre_name}.npy"

    @property
    def sign_deg_json(self) -> Path:
        return self.norm_dir / f"sign_deg_{self.sub}.json"

    def ft_model(self, seed: int) -> Path:
        return self.models_dir / f"ft_s{seed}.pt"

    @property
    def reproduce_metrics(self) -> Path:
        return self.models_dir / "reproduce_metrics.json"

    def pred_clean(self, seed: int, unit: int) -> Path:
        return self.preds_dir / "clean" / f"s{seed}" / f"u{unit}.parquet"

    def pred_shift(self, seed: int, unit: int, scenario_id: str) -> Path:
        return self.preds_dir / "shift" / f"s{seed}" / f"u{unit}" / f"{scenario_id}.parquet"

    def shifted(self, unit: int, scenario_id: str) -> Path:
        return self.shifted_dir / f"u{unit}" / f"{scenario_id}.parquet"

    def delta(self, unit: int, scenario_id: str) -> Path:
        return self.labels_dir / "delta" / f"u{unit}" / f"{scenario_id}.parquet"

    def state(self, theta_name: str, unit: int, scenario_id: str) -> Path:
        return self.labels_dir / "state" / theta_name / f"u{unit}" / f"{scenario_id}.parquet"

    @property
    def scenario_index(self) -> Path:
        return self.labels_dir / "scenario_index.csv"

    @property
    def clean_variability(self) -> Path:
        return self.labels_dir / "meta" / "clean_variability.json"


def set_seed(seed: int) -> None:
    """원본 스크립트의 seed 고정 블록과 동일."""
    import torch

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def get_device():
    import torch

    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def git_commit_hash(repo: Path) -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()
    except Exception:
        return None


def derive_seed(base_seed: int, *parts) -> int:
    """(base_seed, unit, scenario_id, ...) 로부터 재현 가능한 32bit seed."""
    import zlib

    s = "|".join(str(p) for p in (base_seed, *parts))
    return zlib.crc32(s.encode("utf-8")) & 0x7FFFFFFF


# ---------- parquet with metadata ----------
def write_parquet(df, path: str | Path, meta: dict | None = None) -> None:
    import pyarrow as pa
    import pyarrow.parquet as pq

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(df, preserve_index=False)
    if meta:
        md = dict(table.schema.metadata or {})
        md[b"agent_rul_meta"] = json.dumps(meta, default=_json_default).encode("utf-8")
        table = table.replace_schema_metadata(md)
    pq.write_table(table, path)


def read_parquet(path: str | Path, with_meta: bool = False):
    import pyarrow.parquet as pq

    table = pq.read_table(path)
    df = table.to_pandas()
    if not with_meta:
        return df
    md = table.schema.metadata or {}
    meta = json.loads(md[b"agent_rul_meta"].decode("utf-8")) if b"agent_rul_meta" in md else {}
    return df, meta


def md_table(rows: list[dict], cols: list[str] | None = None, fmt: str = "{:.3f}") -> str:
    """간단한 markdown 표 (tabulate 의존 없이)."""
    if not rows:
        return "(empty)\n"
    cols = cols or list(rows[0].keys())

    def cell(v):
        if isinstance(v, float):
            return fmt.format(v)
        return str(v)

    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in rows:
        out.append("| " + " | ".join(cell(r.get(c, "")) for c in cols) + " |")
    return "\n".join(out) + "\n"
