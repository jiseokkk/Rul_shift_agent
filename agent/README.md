# agent — 에이전트 설계 및 실험

`data_prep/` 이 만든 산출물을 읽어 LLM 에이전트가 RUL 모델의 출력 신뢰성 상실(오염에 의한 예측 교란)을
탐지하는지 실험한다. `data_prep/` 은 잠긴 상태이며 여기서는 읽기만 한다.

## 폴더

```
agent/
├── configs/
│   ├── paths.yaml      data_prep 산출물 경로. 입력용 / 채점용 구분
│   └── (agent.yaml)    stride, 프롬프트 버전, LLM 모델 등  ← 설계 후 작성
├── src/
│   ├── data/           로더. load_inputs()(센서 + 오염 예측) 와 load_truth()(라벨) 를 분리
│   ├── agent/          프롬프트 · 도구 · 판정 로직
│   ├── baselines/      비교 기준 (임계값, 통계 검정 등)
│   └── eval/           채점 (state 라벨 + eval_mask, unit 단위 / cycle 단위)
├── runs/{run_id}/      실행별 로그 · 판정 · config 스냅샷
├── reports/
└── tests/
```

## 정보 차단 규칙

에이전트는 배포 환경에서 관측 가능한 것만 본다.

| 볼 수 있음 | 볼 수 없음 (채점 전용) |
|---|---|
| `data/shifted/` 센서 궤적 (모델 입력 14 센서) | `preds/clean/` counterfactual 예측 |
| `preds/shift/` RUL 모델 출력 | `labels/state/` 라벨, `labels/meta/eval_mask.csv` |
| `scenario_index.csv` 의 메타 컬럼 (unit, T_u, tau_s 는 실험 설정용) | `scenario_index.csv` 의 결과 컬럼 (degraded, tau_d ...) |

`src/agent/` 는 `src/data` 의 입력 로더만 import 한다. 채점 로더는 `src/eval/` 에서만 쓴다.

## data_prep 과의 계약

- 라벨 버전: grid v3 (2026-09-16), θ_primary 9.399, k=5, m=7, θ_low=0.5θ. `data_prep/configs/label.yaml` `locked: true`
- 규모: hold-out 20 unit × 244 시나리오 = 4,880. 라벨 14,640 행 (θ 3종)
- `data_prep/configs/agent.yaml` 의 N=10 이 τ_s 하한(t0=55)을 결정한다. N 을 바꾸면 data_prep 06 부터 재실행해야 한다.
- 채점 시 `eval_mask.csv` 적용 결과를 주 결과, 미적용을 부록으로 둘 다 보고한다.
