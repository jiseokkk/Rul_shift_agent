"""scripts/*.py 공통: agent/ 를 sys.path 에 넣고 설정을 로드."""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

AGENT = Path(__file__).resolve().parents[1]
if str(AGENT) not in sys.path:
    sys.path.insert(0, str(AGENT))


def load_cfg(name: str) -> dict:
    with open(AGENT / "configs" / f"{name}.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)
