# v2 평가 결과 (시나리오 단위, docs/eval_v2_scenario.md)

2026-10-07 부터. 첫 경보 원칙 (cycle 55 이후 첫 경보, 오염 전 포함), Δ = 5, w = 0, H = 40, k = 1. 기준선(항상 0/1, 무작위) 고정, unit bootstrap CI.
생성: `scripts/compare_scenario_runs.py` (run 별 채점은 `scripts/evaluate.py`).

- `compare_or500.md/.xlsx` — or500 표본 5개 run 비교 (Qwen2.5-32B, DeepSeek V4 Pro, Qwen3.8-27B ± thinking, Qwen3.6-35B-A3B). v1 판정 로그 재채점
- `or500_{label}.md` — run 별 보고서 (유형·센서·시점별, 시나리오 상세)
