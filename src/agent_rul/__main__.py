"""CLI 진입점 — `python -m agent_rul <명령>`.

    inspect           데이터 형식 점검, σ_w/σ_global 비율
    build-reference   정상 기준 fit (train 데이터, 한 번) → artifacts/reference/
    run               스트림 판정 (Tool 계산 + LLM) → results/{run_id}/
    evaluate          GT 대조 → metrics.json, sensitivity.json
    report            여러 run 집계 → results/report_{tag}.json

실행 순서: inspect → build-reference → run → evaluate → report.
build-reference 는 LLM 없이 한 번, run 은 프롬프트/모델을 바꿀 때마다, evaluate 는 run 결과만 읽는다.
"""
from __future__ import annotations

import argparse
import os
import sys

from .config import load_config
from .utils import set_seed


def _cmd_inspect(args) -> None:
    from . import data
    from .reference import calibration
    cfg = load_config()
    cfg.paths.ensure_dirs()
    if not args.skip_h5:
        data.inspect_h5(cfg)
    data.inspect_scenarios(cfg)
    print("=" * 78)
    if os.path.exists(cfg.paths.calibration_json):
        print(calibration.sigma_table(calibration.load(cfg.paths.calibration_json)))
    else:
        print("sigma_w / sigma_global 비율: artifacts/reference/calibration.json 없음 "
              "→ `build-reference` 를 먼저 실행하면 이 표가 채워진다")


def _cmd_build_reference(args) -> None:
    from .reference import build
    cfg = load_config()
    cfg.paths.ensure_dirs()
    set_seed(cfg.seed)
    if args.K:
        cfg.exp["knn"]["K"] = args.K
        print(f"[reference] K={args.K} (명령행 덮어쓰기)")
    build.build_all(cfg)


def _cmd_run(args) -> None:
    from .agent import runner
    cfg = load_config()
    runner.run(cfg, args.scenarios, seed=args.seed, run_id=args.run_id, tag=args.tag,
               dry_run=args.dry_run, limit=args.limit, only_cycles=args.cycles,
               use_cache=not args.no_cache, save_prompts=not args.no_prompts,
               save_stats=not args.no_stats, rul_device=args.rul_device)


def _cmd_evaluate(args) -> None:
    from .evaluation import report
    cfg = load_config()
    rid = args.run_id or report.latest_run(cfg)
    report.evaluate_run(cfg, rid, D=args.D)


def _cmd_report(args) -> None:
    from .evaluation import report
    cfg = load_config()
    report.build_report(cfg, args.runs, tag=args.tag)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="python -m agent_rul",
                                 description="LLM Agent 기반 RUL 입력 센서 이상 탐지 (1차 실험)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("inspect", help="데이터 형식 점검 (HDF5, 시나리오, σ_w/σ_global)")
    p.add_argument("--skip-h5", action="store_true", help="HDF5 점검 생략 (느림)")
    p.set_defaults(fn=_cmd_inspect)

    p = sub.add_parser("build-reference", help="정상 기준 fit → artifacts/reference/")
    p.add_argument("--K", type=int, default=None, help="KNN K 덮어쓰기")
    p.set_defaults(fn=_cmd_build_reference)

    p = sub.add_parser("run", help="스트림 판정 → results/{run_id}/")
    p.add_argument("--scenarios", nargs="*", default=None, help="기본값: experiment.yaml 의 scenarios")
    p.add_argument("--limit", type=int, default=None, help="시나리오별 판정 cycle 수 제한")
    p.add_argument("--cycles", nargs="*", type=int, default=None, help="특정 cycle 만 판정 (디버깅)")
    p.add_argument("--seed", type=int, default=None, help="llm.yaml seed 덮어쓰기 (반복 실행)")
    p.add_argument("--run-id", default=None)
    p.add_argument("--tag", default="", help="run_id 에 붙일 태그")
    p.add_argument("--dry-run", action="store_true", help="Tool 만 돌리고 프롬프트만 생성 (LLM 없음)")
    p.add_argument("--no-cache", action="store_true", help="판정 캐시 사용 안 함")
    p.add_argument("--no-prompts", action="store_true", help="prompts/ 저장 안 함")
    p.add_argument("--no-stats", action="store_true", help="stats/ 저장 안 함")
    p.add_argument("--rul-device", default=None, help="cpu | cuda (기본: experiment.yaml rul_model.device)")
    p.set_defaults(fn=_cmd_run)

    p = sub.add_parser("evaluate", help="GT 대조 → metrics.json")
    p.add_argument("--run-id", default=None, help="기본값: 가장 최근 run")
    p.add_argument("--D", type=int, default=None, help="detection tolerance (기본: experiment.yaml)")
    p.set_defaults(fn=_cmd_evaluate)

    p = sub.add_parser("report", help="여러 run 집계 → results/report_{tag}.json")
    p.add_argument("--runs", nargs="*", default=None, help="기본값: metrics.json 이 있는 모든 run")
    p.add_argument("--tag", default="latest")
    p.set_defaults(fn=_cmd_report)
    return ap


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main(sys.argv[1:])
