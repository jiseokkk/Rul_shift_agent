"""스트림 판정 런너 (CLI `run`) — 설계서 7, 8.

시나리오 하나를 cycle 순서대로 흘려 넣는다:

    for cycle, series in data.stream(scenario):
        비행 중  : window 마다 eda.observe_window            (z_w, std_ratio, T², contribution)
        착륙     : eda.end_cycle, rul.end_cycle               (cycle 집계, RUL 예측, 이력 추가)
        cycle ≤ warm_up 이거나 이전 cycle 이 L_c 개 미만이면 여기서 끝
        판정     : graph.invoke → Decision → decisions.csv 한 줄

판정 캐시 키 = (scenario, cycle, prompt_hash, seed, model). 프롬프트가 바뀌면 hash 가 바뀌어
자동 재호출되고, 안 바뀌면 LLM 을 부르지 않고 재사용한다.

시나리오가 끝나면 Tool 이력을 results/{run_id}/stats/{scenario}/ 에 표로 남긴다
(window_stats / cycle_sensor / cycle / rul). 나중에 판정을 파 볼 때 prompts/ 와 같이 본다.
true_rul / life_fraction 열은 비워 두고 evaluate 가 채운다 (GT 격리).
"""
from __future__ import annotations

import hashlib
import os

import yaml

from .. import data
from ..config import make_run_id
from ..reference import build
from ..tools.eda import EDATool
from ..tools.rul import RULTool
from ..utils import get_logger, read_json, set_seed, setup_logging, write_csv, write_json
from . import prompts
from .schema import DECISION_COLUMNS


# --------------------------------------------------------------------------- #
# 판정 캐시
# --------------------------------------------------------------------------- #
def prompt_hash(system_prompt: str, runtime_input: str) -> str:
    h = hashlib.sha256()
    h.update(system_prompt.encode("utf-8"))
    h.update(b"\x00")
    h.update(runtime_input.encode("utf-8"))
    return h.hexdigest()[:16]


def cache_key(scenario_id: str, cycle: int, p_hash: str, seed: int, model: str) -> str:
    model_slug = str(model).replace("/", "-")
    return f"{scenario_id}_c{cycle}_{model_slug}_seed{seed}_{p_hash}"


class DecisionCache:
    """artifacts/cache/decisions/{key}.json — 값은 decisions.csv 한 행(dict)."""

    def __init__(self, root: str, enabled: bool = True):
        self.dir = root
        self.enabled = enabled
        if enabled:
            os.makedirs(self.dir, exist_ok=True)

    def _path(self, key: str) -> str:
        return os.path.join(self.dir, f"{key}.json")

    def get(self, key: str) -> dict | None:
        if not self.enabled or not os.path.exists(self._path(key)):
            return None
        return read_json(self._path(key))

    def put(self, key: str, record: dict) -> None:
        if self.enabled:
            write_json(self._path(key), record)


# --------------------------------------------------------------------------- #
# 레코드
# --------------------------------------------------------------------------- #
def _record(sid: str, unit, cycle: int, out: dict, res, p_tokens: int) -> dict:
    """decisions.csv 한 행. true_rul / life_fraction 은 evaluate 가 채운다."""
    d = out.get("decision")
    return {
        "scenario_id": sid, "unit": unit, "cycle": cycle,
        "sensor_status": d.sensor_status if d else "ERROR",
        "rul_reliability": d.rul_reliability if d else "ERROR",
        "suspected_sensors": "|".join(d.suspected_sensors) if d else "",
        "fault_pattern": d.fault_pattern if d else "",
        "confidence": d.confidence if d else "",
        "key_evidence": " || ".join(d.key_evidence) if d else "",
        "rationale": d.rationale.replace("\n", " ") if d else "",
        "n_retries": getattr(res, "n_retries", 0),
        "post_check_flags": ";".join(out.get("flags") or []),
        "latency_ms": getattr(res, "latency_ms", 0),
        "prompt_tokens": getattr(res, "prompt_tokens", 0) or p_tokens,
        "true_rul": "", "life_fraction": "",
    }


def _write_stats(cfg, run_id: str, sid: str, eda: EDATool, rul: RULTool | None) -> str:
    d = cfg.paths.stats_dir(run_id, sid)
    t = eda.tables()
    write_csv(os.path.join(d, "window_stats.csv"), t["window_stats"])
    write_csv(os.path.join(d, "cycle_sensor.csv"), t["cycle_sensor"])
    write_csv(os.path.join(d, "cycle.csv"), t["cycle"])
    if rul is not None:
        write_csv(os.path.join(d, "rul.csv"), rul.rows())
    return d


# --------------------------------------------------------------------------- #
# 실행
# --------------------------------------------------------------------------- #
def run(cfg, scenarios: list[str] | None = None, *, seed: int | None = None,
        run_id: str | None = None, tag: str = "", dry_run: bool = False,
        limit: int | None = None, only_cycles: list[int] | None = None,
        use_cache: bool = True, save_prompts: bool = True, save_stats: bool = True,
        rul_device: str | None = None) -> str:
    """시나리오들을 스트림으로 판정. 반환: results/{run_id}/ 경로.

    dry_run : Tool 은 전부 돌리고 프롬프트만 만든다 (LLM 호출 없음). 토큰 수 점검용.
    limit   : 시나리오별 판정 cycle 수 제한 (이력은 끝까지 쌓는다)
    """
    cfg.paths.ensure_dirs()
    if seed is not None:
        cfg.llm["seed"] = seed
    set_seed(cfg.seed)

    rid = run_id or make_run_id(cfg, tag=tag or ("dry" if dry_run else ""))
    out_dir = cfg.paths.run_dir(rid)
    os.makedirs(cfg.paths.prompts_dir(rid), exist_ok=True)
    log = setup_logging(log_file=cfg.paths.run_log(rid))
    log.info(f"run_id = {rid}{'  (dry-run)' if dry_run else ''}")
    with open(cfg.paths.config_snapshot(rid), "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg.raw, f, allow_unicode=True, sort_keys=False)

    ref = build.load_all(cfg)
    eda = EDATool(cfg, ref)
    rul = RULTool(cfg, device=rul_device)
    log.info(f"RUL tool device = {rul.device}")
    targets = scenarios or cfg.scenarios
    only = set(only_cycles) if only_cycles else None

    app = cache = None
    if dry_run:
        try:
            from .llm import ping
            log.info(f"LLM ping → {ping(cfg)!r}")
        except Exception as e:                       # 서버가 없어도 프롬프트 생성은 계속
            log.warning(f"LLM 서버 연결 실패 (프롬프트 생성만 계속): {e}")
    else:
        from .graph import build_graph
        app = build_graph(cfg, eda, rul)
        cache = DecisionCache(cfg.paths.decision_cache_dir, enabled=use_cache)

    rows, sizes, n_err, n_cached = [], [], 0, 0
    for sid in targets:
        sc = data.load_scenario(cfg.paths.corrupted_root, sid)
        unit = sc["unit"]
        eda.reset(sid, unit)
        rul.reset()
        n_decided = 0

        for cycle, seq in data.stream(sc):
            # ---- 비행 중: window 마다 통계 --------------------------------
            for win in data.split_windows(seq, cfg.samples_per_window):
                eda.observe_window(cycle, win)
            # ---- 착륙: cycle 집계 + RUL 예측 --------------------------------
            has_windows = eda.end_cycle(cycle)
            rul.end_cycle(cycle, seq)
            if not has_windows:
                log.info(f"{sid} cycle {cycle}: window 0개 → 판정 없음 (len={len(seq)})")
                continue
            if not eda.is_decision_cycle(cycle):
                continue                                  # warm-up / 이력 부족
            if only is not None and cycle not in only:
                continue
            if limit is not None and n_decided >= limit:
                continue
            n_decided += 1

            # ---- 판정 -------------------------------------------------------
            rin = prompts.format_input(eda.evidence(cycle), rul.context(cycle))
            if save_prompts or dry_run:
                with open(cfg.paths.prompt_txt(rid, sid, cycle), "w", encoding="utf-8") as f:
                    f.write(rin)
            if dry_run:
                sizes.append({"scenario_id": sid, "cycle": cycle, "chars": len(rin),
                              "est_tokens": prompts.estimate_tokens(rin)})
                continue

            key = cache_key(sid, cycle, prompt_hash(prompts.SYSTEM_PROMPT, rin),
                            int(cfg.llm["seed"]), cfg.llm["model"])
            hit = cache.get(key)
            if hit is not None:
                rows.append(hit)
                n_cached += 1
                n_err += int(hit["sensor_status"] == "ERROR")
                continue

            out = app.invoke({"scenario_id": sid, "cycle": cycle, "unit": unit})
            res = out.get("llm")
            rec = _record(sid, unit, cycle, out, res, prompts.estimate_tokens(rin))
            if rec["sensor_status"] == "ERROR":
                n_err += 1
                log.warning(f"{sid} cycle {cycle}: ERROR {getattr(res, 'errors', [])[:1]}")
            else:
                log.info(f"{sid} cycle {cycle}: {rec['sensor_status']:6s} "
                         f"conf={rec['confidence']} susp={rec['suspected_sensors'] or '-'} "
                         f"({rec['latency_ms']}ms, {rec['prompt_tokens']}tok)")
            cache.put(key, rec)
            rows.append(rec)

        if save_stats:
            _write_stats(cfg, rid, sid, eda, rul)
        log.info(f"{sid}: cycles={len(sc['cycles'])} 판정={n_decided} "
                 f"skipped(window 0)={len(eda.skipped)}")

    # ---- 마무리 ----------------------------------------------------------------
    if dry_run:
        write_json(cfg.paths.dry_run_json(rid), sizes)
        if sizes:
            tok = sorted(s["est_tokens"] for s in sizes)
            log.info(f"[dry-run] 프롬프트 {len(sizes)}개 → {cfg.paths.prompts_dir(rid)}")
            log.info(f"[dry-run] 추정 토큰: min {tok[0]:,} / median {tok[len(tok) // 2]:,} / "
                     f"max {tok[-1]:,}  (system prompt ≈ "
                     f"{prompts.estimate_tokens(prompts.SYSTEM_PROMPT):,})")
        else:
            log.warning("[dry-run] 판정 대상 cycle 이 없다")
        return out_dir

    path = write_csv(cfg.paths.decisions_csv(rid), rows, fieldnames=DECISION_COLUMNS)
    n = len(rows)
    log.info(f"[run] 완료: {n} 판정 (캐시 {n_cached}, ERROR {n_err}, "
             f"FailRate {n_err / n if n else 0:.3f}) → {path}")
    return out_dir
