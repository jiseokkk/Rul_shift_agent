# RUL Shift Agent

LLM 에이전트를 **고정된 LSTM RUL 모델 위의 shift 감지·보정·의사결정 레이어**로 쓰는 실험.
N-CMAPSS DS02-006 터보팬 데이터에 센서 bias/drift를 주입하고, 에이전트가

1. 분포 shift(센서 fault vs 자연스러운 운용 변화)를 **감지**하고,
2. 오염된 RUL 예측을 **보정**(`corrected_rul`)한 뒤,
3. 보정값에 threshold(≤10 replace, ≤25 inspect)를 적용해 **정비 결정**을 내린다.

predictor는 재학습하지 않는다 — 감지·보정은 전부 모델 바깥의 에이전트 몫.

## 핵심 아이디어

- **Tier-1 신호**: 운용조건-조건부 z(`regime_z`) + 채널 간 일관성 잔차(`consistency_z`).
  센서 fault는 ~15–62σ, 양성 flight-class shift는 ~0.5–1.2σ → 원인 구분(cause gate)이 가능.
- **앵커 보정**: shift 후 LSTM 출력은 포화(adverse→cap, favorable→0)되므로, pre-shift
  마지막 신뢰 예측을 앵커로 잡아 1 cycle당 −1로 외삽. 앵커가 창 밖이면 gain 방식 fallback.
- **3겹 게이트**: 샘플 median → hysteresis(2회 연속 확정 후 보정 적용) → cost-aware
  가드레일(adverse 확정 시 최소 inspect, favorable 확정 시 replace 금지).

## 실행

```bash
# 환경: conda env LLMshift를 절대 경로로 사용 (conda activate가 안 먹는 머신)
cd /home/iai4/Desktop/han/Rul_shift_agent
PY=/home/iai4/miniconda3/envs/LLMshift/bin/python

# 전체 파이프라인 (rule 에이전트, LLM 없음 — 빠르고 결정론적)
PYTHONPATH=/home/iai4/Desktop $PY -m han.Rul_shift_agent.llmshift.run_all --agent rule --skip_train

# LLM 에이전트 (vLLM + 로컬 Qwen2.5-32B-AWQ, 2×GPU)
PYTHONPATH=/home/iai4/Desktop $PY -m han.Rul_shift_agent.llmshift.run_all --agent llm --skip_train

# 베이스라인 그리드 실험
PYTHONPATH=/home/iai4/Desktop $PY -m han.Rul_shift_agent.baselines.grid_experiment
```

스테이지: `core.preprocess`(Tier-1 피처 fit) → `core.train_rul`(LSTM) →
`core.build_decisions`(패킷) → `baselines.cusum` → `llmshift.agent`(rule/llm) →
`core.evaluate` → `llmshift.ablation` → `llmshift.make_figures`.

## 폴더 구조

| 폴더 | 내용 |
|---|---|
| `core/` | 공용 기반 — config, 데이터 로더, 피처 추출, LSTM RUL 모델, 패킷 빌더, 평가 |
| `llmshift/` | LLM/rule 에이전트 — agent, prompt, ablation, 실험 러너, 리포트 |
| `baselines/` | 감지 베이스라인 — CUSUM, PCA-SPE/T² + 그리드 실험 |
| `injection/` | 데이터셋 조작 — FaultSpec 주입 엔진, corrupted 데이터셋 빌더 |

데이터 `dataset/`(≈28GB)은 git에 올리지 않는다. `config.py`의 `DATA_H5` 경로에
N-CMAPSS DS02-006 h5를 두면 된다. LLM 경로는 `config.py`의 `LLM_PATH`.

## 주요 파일

| 파일 | 역할 |
|---|---|
| `core/config.py` | 전 파라미터 (units, thresholds, `HISTORY_K=20`, `CORR_JUMP` 등) |
| `llmshift/agent.py` | rule/LLM 에이전트: 감지 + 앵커 보정 + hysteresis/가드레일 + parse_json |
| `llmshift/prompt.py` | LLM 프롬프트 (cause gate, END-OF-LIFE≠shift, 보정 산식) |
| `injection/inject.py` / `build_corrupted.py` | FaultSpec 주입, 감지기-정렬 난이도 캘리브레이션 |
| `baselines/cusum.py` | threshold + per-channel CUSUM 베이스라인 |
| `baselines/grid_experiment.py` | 시나리오 그리드 × 감지기(CUSUM/PCA/rule) 벤치마크 러너 |
| `core/evaluate.py` | 결정 F1 / shift 감지 / rul_correction RMSE·MAE |
| `llmshift/run_experiment.py`, `snr_experiment.py` | rule-vs-LLM 실험, σ-vs-cons 난이도 실험 |

## 현재 결과 요약 (Qwen2.5-32B-AWQ, 5 samples)

| 축 | 베이스라인 | LLM 에이전트 |
|---|---|---|
| adverse post-onset RUL RMSE | 모델 그대로 47.7 (rule ref 12.3) | **20.5** |
| favorable post-onset RUL RMSE | 21.4 (rule ref 13.3) | **16.3** |
| adverse 결정 | threshold FNR 1.00 | FNR **0.00**, F1 0.82 |
| 감지 latency | CUSUM 8 / rule 5 cycles | **2 cycles** (recall 1.00) |
| natural FPR | CUSUM 0.45 | **0.00** |

자세한 설계·디버깅 기록과 다음 단계는 `docs/` 참고:
`NOTION_0728_rul_correction_ko.md`(보정 리디자인), `BIAS_INJECTION_DESIGN_ko.md`(주입 설계),
`BASELINES_AND_EVAL_DESIGN_ko.md`(베이스라인·평가 설계, 문헌 조사).
