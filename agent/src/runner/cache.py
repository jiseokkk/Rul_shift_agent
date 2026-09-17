"""판정 캐시. key = sha256(system + user prompt) + 모델 + seed.

시나리오 id 는 키에 없다 → 같은 unit 의 τ_s 이전 cycle 은 프롬프트가 바이트 동일해 자동 공유.
프롬프트 문구를 바꾸면 해시가 달라져 자동 무효.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import uuid
from pathlib import Path


def prompt_hash(system: str, user: str) -> str:
    return hashlib.sha256((system + "\n\x00\n" + user).encode("utf-8")).hexdigest()[:24]


class DecisionCache:
    def __init__(self, root: Path, model: str, seed: int):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        tag = hashlib.sha256(f"{model}|{seed}".encode()).hexdigest()[:8]
        self.dir = self.root / tag
        self.dir.mkdir(exist_ok=True)
        (self.dir / "_meta.json").write_text(json.dumps({"model": model, "seed": seed}))

    def path(self, key: str) -> Path:
        return self.dir / f"{key}.json"

    def get(self, key: str) -> dict | None:
        p = self.path(key)
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None

    def put(self, key: str, rec: dict) -> None:
        p = self.path(key)
        # 같은 키(τ_s 이전 프롬프트는 시나리오 간 동일)를 여러 워커가 동시에 쓸 수 있다.
        # 임시 파일을 워커별로 고유하게 만들고 atomic replace. 내용이 같으므로 마지막 쓰기가 이겨도 무방.
        tmp = p.with_name(f"{p.stem}.{os.getpid()}.{threading.get_ident()}.{uuid.uuid4().hex[:6]}.tmp")
        try:
            tmp.write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, p)
        except OSError:
            if tmp.exists():
                tmp.unlink(missing_ok=True)
            if not p.exists():
                raise
