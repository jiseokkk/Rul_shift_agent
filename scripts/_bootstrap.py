"""scripts/*.py 공통 진입: 프로젝트 루트를 sys.path 에 추가하고 설정을 로드."""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")  # CUDA 결정성 (첫 CUDA 연산 전에 설정)

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.common import Paths, load_json, load_yaml, save_json  # noqa: E402


def setup(sub_dataset: str = "FD001"):
    paths = Paths(sub_dataset)
    cfg = load_yaml(f"model_{sub_dataset}")
    return paths, cfg


def t0_from_configs(cfg: dict) -> int:
    return int(cfg["seq_len"]) + int(load_yaml("agent")["N"])
