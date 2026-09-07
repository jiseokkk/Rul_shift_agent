# agent_rul — Claude Code 작업 컨텍스트

## 목적
docs/research_plan_v2.md(설계서)와 docs/agent_spec.md(Agent 사양)에 따라 1차 실험 파이프라인을 구현한다.
폴더 구조는 docs/project_structure.md, 흐름 그림은 docs/figures/agent_flow.svg.

## 1차 실험 범위
- Fault: 기존에 만들어 둔 single-sensor abrupt bias 데이터셋 (프로젝트 바깥 경로, 수정 금지)
- 시간 단위: sample(10s) → window(5min, cycle 내부 비중첩) → cycle
- 구조: **스트림**. runner 가 cycle 을 순서대로 흘려 넣고, Tool 은 도착한 cycle 까지만 안다.
  비행 중 window 마다 통계(z_w, std_ratio, T², contribution) → 착륙 후 cycle 집계 + RUL 예측 → 판정.
- Agent: LangGraph 고정 DAG (eda_node ∥ rul_node → build_input → reason → post_check). LLM 이 tool 호출을 결정하지 않는다.
- LLM: Qwen2.5-32B-Instruct quantized, temperature 0, seed 고정, Pydantic structured output, 재시도 2회
- 판정: cycle 5부터 매 cycle (cycle 1~4는 warm-up, 이력만 쌓고 평가 제외)
- Baseline 없음. Ablation은 2차.

## 절대 규칙
1. 데이터셋 파일은 읽기만 한다.
2. Ground Truth(manifest.csv, true RUL, t_f, fault sensor)는 `evaluation/` 에서만 읽는다.
   `data.py`, `reference/`, `tools/`, `agent/` 가 evaluation 을 import 하면 tests/test_gt_isolation.py 가 실패한다.
   `data.load_scenario` 는 spec.json 에서 4개 필드(scenario_id, unit, flight_class, life_cycles)만 통과시킨다.
3. LLM 호출은 `agent/llm.py` 한 곳에서만.
4. EDA Tool은 threshold 판정, Top-K 선택, 센서 제거를 하지 않는다. 모든 센서의 evidence를 반환한다.
5. LLM 입력에는 정규화된 값(z_w, std_ratio, T², contribution, Δμ, Δσ)만 넣고 raw 통계는 넣지 않는다.
   raw 통계는 `results/{run_id}/stats/` 표에만 나간다.
6. 새 통계량 추가 시 `tools/eda.py`(compute_window_stats → aggregate_cycle → evidence)와 `agent/prompts.py`(format_input)를 함께 수정한다.
   **prompts.format_input 의 출력 바이트가 바뀌면 판정 캐시가 전부 무효화되어 LLM 을 다시 부른다.**
7. 평가 규칙 변경 시 `evaluation/classify.py`와 docs/research_plan_v2.md 12.4를 함께 수정한다.
8. 모든 경로·파일명은 configs/paths.yaml → `config.py` 를 거친다. 하드코딩 금지.
   다른 마운트 경로에서는 `AGENT_RUL_PATH_MAP="/home/iai4=X:/home/iai4"`.

## 실행
```
PY=/home/iai4/miniconda3/envs/LLMshift/bin/python
$PY -m pip install -e .                 # 한 번
$PY -m agent_rul inspect                # 데이터 점검, σ_w/σ_global
$PY -m agent_rul build-reference        # 정상 기준 (train unit, LLM 없음, 한 번)
$PY -m agent_rul run [--dry-run] [--scenarios ...] [--limit N] [--seed 43 --tag rep2]
$PY -m agent_rul evaluate [--run-id ...]
$PY -m agent_rul report --runs ...
$PY -m pytest tests -q                  # 등가성 검증까지: AGENT_RUL_STRICT_EQUIV=1
```
build-reference 는 한 번. run 은 프롬프트/모델 변경 시 재실행(캐시 키에 prompt_hash 가 있어 안 바뀐 cycle 은 재호출 안 함). evaluate 는 run 결과만 읽는다.
`run --dry-run` 은 Tool 을 전부 돌리고 프롬프트·stats 만 만든다 (LLM 없음). 통계량을 바꿨을 때 여기서 표를 먼저 본다.

## 코드 지도 (src/agent_rul, 19 파일)
- `__main__.py` CLI · `config.py` 경로/설정 · `data.py` 로더(HDF5, series.npz, window 분할, stream) · `utils.py`
- `reference/` knn(E[x|W]) · calibration(σ_w, q95, Σ_r, T², global) · build
- `tools/eda.py` EDATool(observe_window → end_cycle → evidence, tables) · `tools/rul.py` RULTool(end_cycle → context)
- `agent/` schema · prompts(SYSTEM_PROMPT + format_input) · llm · graph(DAG + post_check) · runner(스트림 루프, 캐시, 기록)
- `evaluation/` gt · classify(event + 12.4) · metrics(13 + sensitivity) · report(evaluate / report)

## 재현성 주의
KNN 이웃 검색의 거리 동률(tie) 처리가 scikit-learn 버전에 따라 달라 z_w 가 1e-3 수준으로 달라지고, Σ_r 조건수가 커서 T² 는 더 크게 흔들린다. 반복 실험과 캐시 재사용은 같은 환경(LLMshift env)에서만 보장된다.

## reference_code/
이전 단계 코드. 참고만 하고 import 하지 않는다.
