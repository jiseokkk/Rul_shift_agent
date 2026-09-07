"""공용 유틸: seed 고정, 로거, csv/json 입출력."""
from __future__ import annotations

import csv
import json
import logging
import os
import random
import sys

import numpy as np

LOGGER_NAME = "agent_rul"


# --------------------------------------------------------------------------- #
# seed
# --------------------------------------------------------------------------- #
def set_seed(seed: int) -> None:
    """numpy / random / torch 시드 고정. LLM 쪽 seed 는 configs/llm.yaml."""
    random.seed(seed)
    np.random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    try:
        import torch
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
    except ImportError:
        pass


# --------------------------------------------------------------------------- #
# logging
# --------------------------------------------------------------------------- #
def setup_logging(level: str = "INFO", log_file: str | None = None) -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(message)s", "%H:%M:%S")

    if not any(isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)
               for h in logger.handlers):
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(fmt)
        logger.addHandler(sh)

    if log_file:
        # 같은 파일 핸들러가 이미 붙어 있으면 중복 추가하지 않는다
        if not any(isinstance(h, logging.FileHandler)
                   and getattr(h, "baseFilename", None) == os.path.abspath(log_file)
                   for h in logger.handlers):
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            fh = logging.FileHandler(log_file, encoding="utf-8")
            fh.setFormatter(fmt)
            logger.addHandler(fh)
    return logger


def get_logger() -> logging.Logger:
    return logging.getLogger(LOGGER_NAME)


# --------------------------------------------------------------------------- #
# csv / json
# --------------------------------------------------------------------------- #
def write_csv(path: str, rows: list[dict], fieldnames: list[str] | None = None) -> str:
    """dict 리스트 → CSV. rows 가 비어 있고 fieldnames 도 없으면 쓰지 않는다."""
    if not rows and not fieldnames:
        return path
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fields = fieldnames or list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    return path


def read_csv(path: str) -> list[dict]:
    """CSV → dict 리스트 (모든 값은 문자열. 형변환은 호출 쪽에서)."""
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_json(path: str, obj, indent: int = 2) -> str:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=indent, ensure_ascii=False, default=str)
    return path


def read_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
