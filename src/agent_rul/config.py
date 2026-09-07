"""configs/*.yaml 로드 → Config. **모든 경로와 파일명은 여기서만 조합한다** (CLAUDE.md 규칙 8).

사용:
    from agent_rul.config import load_config
    cfg = load_config()
    cfg.paths.ncmapss_h5, cfg.exp.knn.K, cfg.llm.base_url
    cfg.paths.decisions_csv(run_id), cfg.paths.stats_dir(run_id, scenario_id)

다른 머신에서 같은 데이터를 다른 마운트 경로로 볼 때는 환경변수로 접두어를 바꾼다:
    AGENT_RUL_PATH_MAP="/home/iai4=X:/home/iai4"
"""
from __future__ import annotations

import datetime
import os
from dataclasses import dataclass, field
from typing import Any

import yaml

# 프로젝트 루트 = 이 파일에서 3단계 위 (src/agent_rul/config.py → agent_rul/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_DIR = os.path.join(PROJECT_ROOT, "configs")
PATH_MAP_ENV = "AGENT_RUL_PATH_MAP"


class _Box(dict):
    """yaml 하위 딕셔너리를 점 접근으로 쓰기 위한 얇은 래퍼."""

    def __getattr__(self, k):
        try:
            v = self[k]
        except KeyError as e:
            raise AttributeError(k) from e
        return _Box(v) if isinstance(v, dict) else v


# --------------------------------------------------------------------------- #
# 경로
# --------------------------------------------------------------------------- #
@dataclass
class Paths:
    ncmapss_h5: str
    corrupted_root: str
    manifest_csv: str
    frozen_rul_dir: str
    artifacts_root: str
    results_root: str

    # ---- artifacts (재계산 가능) -------------------------------------------
    @property
    def reference_dir(self) -> str:
        return os.path.join(self.artifacts_root, "reference")

    @property
    def global_json(self) -> str:
        return os.path.join(self.reference_dir, "global.json")

    @property
    def knn_npz(self) -> str:
        return os.path.join(self.reference_dir, "knn.npz")

    @property
    def calibration_json(self) -> str:
        return os.path.join(self.reference_dir, "calibration.json")

    @property
    def cache_dir(self) -> str:
        return os.path.join(self.artifacts_root, "cache")

    @property
    def decision_cache_dir(self) -> str:
        return os.path.join(self.cache_dir, "decisions")

    # ---- results/{run_id}/ --------------------------------------------------
    def run_dir(self, run_id: str) -> str:
        return os.path.join(self.results_root, run_id)

    def run_log(self, run_id: str) -> str:
        return os.path.join(self.run_dir(run_id), "run.log")

    def config_snapshot(self, run_id: str) -> str:
        return os.path.join(self.run_dir(run_id), "config_snapshot.yaml")

    def decisions_csv(self, run_id: str) -> str:
        return os.path.join(self.run_dir(run_id), "decisions.csv")

    def decisions_labeled_csv(self, run_id: str) -> str:
        return os.path.join(self.run_dir(run_id), "decisions_labeled.csv")

    def prompts_dir(self, run_id: str) -> str:
        return os.path.join(self.run_dir(run_id), "prompts")

    def prompt_txt(self, run_id: str, scenario_id: str, cycle: int) -> str:
        return os.path.join(self.prompts_dir(run_id), f"{scenario_id}_{cycle}.txt")

    def stats_dir(self, run_id: str, scenario_id: str) -> str:
        return os.path.join(self.run_dir(run_id), "stats", scenario_id)

    def dry_run_json(self, run_id: str) -> str:
        return os.path.join(self.run_dir(run_id), "dry_run.json")

    def metrics_json(self, run_id: str) -> str:
        return os.path.join(self.run_dir(run_id), "metrics.json")

    def sensitivity_json(self, run_id: str) -> str:
        return os.path.join(self.run_dir(run_id), "sensitivity.json")

    def per_scenario_csv(self, run_id: str) -> str:
        return os.path.join(self.run_dir(run_id), "per_scenario.csv")

    def report_json(self, tag: str) -> str:
        return os.path.join(self.results_root, f"report_{tag}.json")

    def ensure_dirs(self) -> None:
        for d in (self.reference_dir, self.cache_dir, self.decision_cache_dir,
                  self.results_root):
            os.makedirs(d, exist_ok=True)


# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #
@dataclass
class Config:
    paths: Paths
    exp: _Box
    llm: _Box
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def sensors(self) -> list[str]:
        return list(self.exp.channels["sensors"])

    @property
    def operating(self) -> list[str]:
        return list(self.exp.channels["operating"])

    @property
    def input_vars(self) -> list[str]:
        return self.sensors + self.operating

    @property
    def n_sensors(self) -> int:
        return len(self.sensors)

    @property
    def samples_per_window(self) -> int:
        return int(self.exp.time["samples_per_window"])

    @property
    def min_windows_short_flight(self) -> int:
        return int(self.exp.time["min_windows_short_flight"])

    @property
    def L_c(self) -> int:
        return int(self.exp.cycle["L_c"])

    @property
    def warm_up(self) -> int:
        return int(self.exp.cycle["warm_up"])

    @property
    def scenarios(self) -> list[str]:
        return list(self.exp["scenarios"])

    @property
    def seed(self) -> int:
        return int(self.exp["seed"])

    def frozen_rul_path(self, name: str) -> str:
        return os.path.join(self.paths.frozen_rul_dir, name)


# --------------------------------------------------------------------------- #
# 로드
# --------------------------------------------------------------------------- #
def _read_yaml(name: str) -> dict:
    with open(os.path.join(CONFIG_DIR, name), "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _abs(p: str) -> str:
    """상대경로는 프로젝트 루트 기준으로 절대화."""
    return p if os.path.isabs(p) else os.path.join(PROJECT_ROOT, p)


def _map_external(p: str) -> str:
    """AGENT_RUL_PATH_MAP="src=dst[;src2=dst2]" 로 외부 데이터 경로 접두어를 치환."""
    spec = os.environ.get(PATH_MAP_ENV, "").strip()
    if not spec:
        return p
    for pair in spec.split(";"):
        if "=" not in pair:
            continue
        src, dst = pair.split("=", 1)
        if p.startswith(src):
            return dst + p[len(src):]
    return p


def load_config(validate: bool = True) -> Config:
    p = _read_yaml("paths.yaml")
    exp = _read_yaml("experiment.yaml")
    llm = _read_yaml("llm.yaml")

    paths = Paths(
        ncmapss_h5=_map_external(p["ncmapss_h5"]),
        corrupted_root=_map_external(p["corrupted_root"]),
        manifest_csv=_map_external(p["manifest_csv"]),
        frozen_rul_dir=_abs(p["frozen_rul_dir"]),
        artifacts_root=_abs(p["artifacts_root"]),
        results_root=_abs(p["results_root"]),
    )
    cfg = Config(paths=paths, exp=_Box(exp), llm=_Box(llm),
                 raw={"paths": p, "experiment": exp, "llm": llm})
    if validate:
        _validate(cfg)
    return cfg


def _validate(cfg: Config) -> None:
    t = cfg.exp.time
    expected = t["L_w_sec"] // t["delta_s_sec"]
    if expected != t["samples_per_window"]:
        raise ValueError(
            f"samples_per_window={t['samples_per_window']} 가 "
            f"L_w_sec/delta_s_sec={expected} 와 다르다 (experiment.yaml)")
    if len(cfg.input_vars) != int(cfg.exp.rul_model["n_input"]):
        raise ValueError("channels 개수와 rul_model.n_input 이 다르다")
    if not os.path.exists(cfg.paths.ncmapss_h5):
        raise FileNotFoundError(f"HDF5 없음: {cfg.paths.ncmapss_h5}")
    if not os.path.isdir(cfg.paths.corrupted_root):
        raise FileNotFoundError(f"corrupted_root 없음: {cfg.paths.corrupted_root}")


def make_run_id(cfg: Config, seed: int | None = None, tag: str = "") -> str:
    """run_id = {model}_{tag}_seed{seed}_{timestamp} (설계서: seed·model 포함)."""
    seed = cfg.llm.seed if seed is None else seed
    stamp = datetime.datetime.now().strftime("%m%d_%H%M")
    parts = [os.path.basename(str(cfg.llm.model).rstrip("/")).replace("/", "-")]
    if tag:
        parts.append(tag)
    parts += [f"seed{seed}", stamp]
    return "_".join(parts)
