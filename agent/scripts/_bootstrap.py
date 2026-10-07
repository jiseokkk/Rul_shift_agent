"""scripts/*.py 공통: agent/ 를 sys.path 에 넣고 설정을 로드. 저장소 루트 .env 를 환경변수로 올린다."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import yaml

AGENT = Path(__file__).resolve().parents[1]
ROOT = AGENT.parent
if str(AGENT) not in sys.path:
    sys.path.insert(0, str(AGENT))


def load_cfg(name: str) -> dict:
    with open(AGENT / "configs" / f"{name}.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_env(path: Path = ROOT / ".env") -> None:
    """KEY=VALUE 줄을 환경변수로. 이미 있는 변수는 덮어쓰지 않는다. 파일이 없으면 무시 (.env.example 참조)."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


load_env()
