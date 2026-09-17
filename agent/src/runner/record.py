"""runs/{run_id}/ 기록: decisions.csv, prompts/, stats/, config_snapshot.yaml, run.log"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import yaml

DECISION_COLS = ["run_id", "unit", "scenario_id", "cycle", "degraded", "suspected_sensors", "confidence", "rationale",
                 "flags", "n_retries", "latency_ms", "prompt_tokens", "completion_tokens", "cache_hit", "prompt_hash", "error"]


def make_run_id(model: str, tag: str, seed: int) -> str:
    m = Path(model).name.replace("/", "_")[:24]
    return f"{m}_{tag}_seed{seed}_{datetime.now().strftime('%Y%m%d-%H%M%S')}"


class RunRecorder:
    def __init__(self, runs_dir: Path, run_id: str, save_prompts: bool = True):
        self.dir = Path(runs_dir) / run_id
        (self.dir / "prompts").mkdir(parents=True, exist_ok=True)
        (self.dir / "stats").mkdir(exist_ok=True)
        self.run_id = run_id
        self.save_prompts = save_prompts
        self.log_path = self.dir / "run.log"

    def snapshot(self, **cfgs) -> None:
        (self.dir / "config_snapshot.yaml").write_text(yaml.safe_dump(cfgs, allow_unicode=True, sort_keys=False), encoding="utf-8")

    def log(self, msg: str) -> None:
        line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
        print(line, flush=True)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def save_prompt(self, unit: int, sid: str, cycle: int, system: str, user: str) -> None:
        if not self.save_prompts:
            return
        p = self.dir / "prompts" / f"u{unit}__{sid}__c{cycle}.txt"
        if not p.exists():
            p.write_text(f"### SYSTEM\n{system}\n\n### USER\n{user}\n", encoding="utf-8")

    def save_stats(self, unit: int, sid: str, sensor_rows: list[dict], rul_rows: list[dict]) -> None:
        pd.DataFrame(sensor_rows).to_csv(self.dir / "stats" / f"u{unit}__{sid}__sensor.csv", index=False)
        pd.DataFrame(rul_rows).to_csv(self.dir / "stats" / f"u{unit}__{sid}__rul.csv", index=False)

    def save_decisions(self, rows: list[dict]) -> Path:
        df = pd.DataFrame(rows, columns=DECISION_COLS)
        if len(df):
            df = df.sort_values(["unit", "scenario_id", "cycle"]).reset_index(drop=True)
        out = self.dir / "decisions.csv"
        df.to_csv(out, index=False)
        return out

    def save_summary(self, summary: dict) -> None:
        (self.dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
