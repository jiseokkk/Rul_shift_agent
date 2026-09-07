# agent_rul — LLM Agent 기반 RUL 입력 센서 이상 탐지 (1차 실험)

설계: [docs/research_plan_v2.md](docs/research_plan_v2.md) · Agent 사양: [docs/agent_spec.md](docs/agent_spec.md) · 폴더 구조: [docs/project_structure.md](docs/project_structure.md) · 흐름 그림: [docs/figures/agent_flow.svg](docs/figures/agent_flow.svg)

RUL 모델에 들어가는 센서 입력이 정상인지 **비행(cycle)마다** 판정하고, 이상이면 RUL 예측에
신뢰성 경고를 붙인다. 1차 실험은 single-sensor abrupt bias (T48, α∈{0.5,1,2})만 다룬다.

```
비행 중   window(5분)마다  EDA Tool: z_w · std_ratio · T² · contribution        ↻
착륙      EDA Tool: cycle 집계(Δμ, Δσ, exceedance) · RUL Tool: frozen LSTM 예측
판정      eda.evidence ∥ rul.context → prompt → LLM(structured output) → post_check → Decision
          (LangGraph 고정 DAG. LLM 이 tool 호출을 결정하지 않는다. cycle 5 부터, 1~4 는 warm-up)
```

데이터는 cycle 순서대로 스트림으로 들어가고, Tool 은 도착한 cycle 까지만 안다.

## 실행

```bash
PY=/home/iai4/miniconda3/envs/LLMshift/bin/python
$PY -m pip install -e .                    # 한 번

$PY -m agent_rul inspect                   # 데이터 형식 점검, σ_w/σ_global 비율
$PY -m agent_rul build-reference           # 정상 기준 (clean unit, LLM 없음, 한 번)  ~6s
$PY -m agent_rul run                       # 스트림 판정  ← 유일하게 느림 (판정당 ~40-60s)
$PY -m agent_rul evaluate                  # TP/FP/FN/TN, F1, MDD, FAR
$PY -m agent_rul report                    # 반복 3회 집계, severity 표
```

build-reference 는 한 번. run 은 프롬프트/모델을 바꿀 때마다 재실행하되, 캐시 키에 prompt_hash 가
있어 안 바뀐 cycle 은 LLM 을 다시 부르지 않는다. evaluate 는 run 결과만 읽으므로 평가 규칙을
바꿔도 LLM 재호출이 없다.

**run 전에** vLLM 서버가 떠 있어야 한다:

```bash
$PY -m vllm.entrypoints.openai.api_server \
    --model /home/iai4/Desktop/SDM/Qwen2.5-32B-AWQ \
    --max-model-len 32768 --port 8000
```

`configs/llm.yaml` 의 `model` 은 서버 `/v1/models` 의 `id` 와 정확히 같아야 한다.

### 부분 실행 / 디버깅

```bash
$PY -m agent_rul run --dry-run                          # Tool 만 돌리고 프롬프트·stats 생성 (LLM 없음)
$PY -m agent_rul run --scenarios ctrl_u11 --limit 5     # 시나리오 1개, 판정 5 cycle 만
$PY -m agent_rul run --cycles 26 27 30 --tag smoke      # 특정 cycle 만
$PY -m agent_rul run --seed 43 --tag rep2               # 반복 실행 (seed 만 변경)
$PY -m agent_rul run --rul-device cpu                   # LSTM 을 CPU 에서 (vLLM 과 GPU 분리)
$PY -m agent_rul evaluate --run-id rep2_seed43 --D 10
$PY -m pytest tests -q                                  # 72 tests
AGENT_RUL_STRICT_EQUIV=1 $PY -m pytest tests/test_equivalence.py -q   # 예전 산출물과 바이트 비교
```

다른 머신에서 데이터 마운트 경로가 다르면 `AGENT_RUL_PATH_MAP="/home/iai4=X:/home/iai4"`.

## 데이터

| 용도 | 위치 | unit |
|---|---|---|
| Clean train (Global + KNN DB) | `dataset/data_set/N-CMAPSS_DS02-006.h5` dev split | 2, 5, 10, 18 |
| Clean validation (σ_w, q95, Σ_r, T² calibration) | 같음 | 16, 20 |
| Test 시나리오 (오염 주입) | `dataset/corrupted_dataset/` | 11 |

`series.npz` 는 이미 10:1 decimated(10s 간격)이고 18채널 = 측정 센서 14개
(`T24 T30 T48 T50 P15 P2 P21 P24 Ps30 P40 P50 Nf Nc Wf`) + 운전조건 4개 (`alt Mach TRA T2`).

1차 실험 시나리오 (`configs/experiment.yaml`):

| scenario_id | 성격 | α | t_f |
|---|---|---|---|
| `ctrl_u11` | clean 대조군 | – | – |
| `A_add_T48_step_0p5_pos_u11` | T48 abrupt bias | 0.5σ | 27 |
| `A_add_T48_step_1_pos_u11` | T48 abrupt bias | 1.0σ | 27 |
| `A_add_T48_step_2_pos_u11` | T48 abrupt bias | 2.0σ | 27 |

## 산출물

```
artifacts/                        # 재계산 가능 (git 제외)
├── reference/  global.json · knn.npz · calibration.json
└── cache/      ncmapss unit 캐시 · decisions/{key}.json 판정 캐시
results/{run_id}/                 # git 제외. run_id = {model}_{tag}_seed{seed}_{timestamp}
├── config_snapshot.yaml · run.log
├── decisions.csv                 # 판정 로그
├── prompts/{sid}_{cycle}.txt     # 실제 전송된 입력
├── stats/{sid}/                  # 실험 후 파 볼 때: window_stats.csv (window·센서 한 줄, start_sample 로 원본 추적)
│                                 #   cycle_sensor.csv, cycle.csv, rul.csv
├── decisions_labeled.csv         # + true_rul, life_fraction (evaluate 가 채움)
└── metrics.json · sensitivity.json · per_scenario.csv
```

## 지켜야 하는 규칙

[CLAUDE.md](CLAUDE.md) 참조. 핵심:

1. 데이터셋은 읽기만.
2. **GT 격리** — manifest.csv, true_rul, t_f, fault 센서는 `evaluation/` 만 읽는다. `data.load_scenario` 는
   spec.json 에서 4개 필드만 통과시킨다. 위반은 `tests/test_gt_isolation.py` 가 잡는다.
3. LLM 호출은 `agent/llm.py` 한 곳.
4. EDA Tool 은 threshold 판정 / Top-K / 센서 제거를 하지 않는다 — 전 센서 반환.
5. LLM 입력에는 정규화된 값만. raw 통계는 `stats/` 표에만.
6. 새 통계량은 `tools/eda.py` 와 `agent/prompts.py` 를 함께 수정. `format_input` 출력이 바뀌면 캐시 무효.
7. 평가 규칙 변경은 `evaluation/classify.py` + `docs/research_plan_v2.md` 12.4 동시 수정.
8. 경로·파일명은 `configs/paths.yaml → config.py` 경유.

## 재현성 주의

KNN 이웃 검색의 거리 동률(tie) 처리가 scikit-learn 버전에 따라 달라 z_w 가 최대 0.01, T² 는
(Σ_r 조건수 1e7 때문에) 최대 5~8% 달라질 수 있다. 반복 실험·캐시 재사용은 같은 환경에서만.

## 이전 단계 코드

[reference_code/](reference_code/) 는 참고만 하고 import 하지 않는다. frozen RUL weight 는 [models/frozen_rul/](models/frozen_rul/).
