# reference_code — 이전 단계에서 가져온 코드 (출처 기록용)

이 폴더의 코드는 **실행 경로에서 import 하지 않는다.** 시간 단위 설계가 바뀌기
전 버전이거나 다른 프로젝트의 config 에 묶여 있어서, `src/agent_rul/` 에서 필요한
부분만 다시 구현했다. 여기 두는 이유는 (1) 오염 데이터가 어떤 수식으로 만들어졌는지
검증 가능하게 남기고, (2) frozen RUL 모델의 아키텍처·전처리 규칙 근거를 남기기 위함이다.

복사 시점: 2026-09-03. 원본은 그대로 두었으므로 원본이 갱신되면 여기도 갱신해야 한다.

## data_generation/ — 오염 데이터셋을 실제로 만든 코드

원본: `han/Rul_shift_agent/injection/`, `han/Rul_shift_agent/core/`

| 파일 | 원본 | 역할 |
|---|---|---|
| `build_dataset.py` | `injection/build_dataset.py` | 50 시나리오 + devset 생성, `series.npz`/`spec.json`/`manifest.csv` 기록 |
| `engine.py` | `injection/engine.py` | 주입 수식 (add / gain / noise / stuck × step / ramp15 / ramp40) |
| `core_config.py` | `core/config.py` | 채널 정의, unit split, window/모델 하이퍼파라미터 |
| `core_data_ncmapss.py` | `core/data_ncmapss.py` | HDF5 로더 |

### 1차 실험과 관련해 확인한 사항

`engine.py` 의 `add` + `step` 조합이 설계서 1.3 의 수식과 일치한다:

```python
delta_raw[ch] = direction * sigma_mult * ch_std[j]   # ch_std = clean train 전체 std
b(c) = 1.0 if c >= c0 else 0.0                       # profile == "step"
x[:, j] += delta_raw[ch] * b                         # x' = x + α·σ  (t >= t_f)
```

- `σ` = **clean train 전체 표준편차** (운전조건 변동 포함) → 설계서 1.3 의 정의와 같다.
- `onset_cycle = round(0.45 * life)` → unit 11 은 life 59 → t_f = 27. 설계서 12.1 이
  요구한 "수명 30~80% 구간, warm-up 과 겹치지 않음"을 만족한다.
- 주입은 native 1Hz 에서 하고(`injection_level: "native_1hz"`), 저장은 10:1 decimated.
  따라서 `series.npz` 를 추가 decimation 없이 그대로 쓰는 것이 맞다.
- `stuck` 은 X_s 채널만 허용하고, `gain` 은 |train mean| < 1e-3 채널을 금지한다
  (1차 실험은 `add` 만 쓰므로 해당 없음).

## prev_project/ — 직전 프로젝트(rul_agent_project, 8/24)

원본: `han/rul_agent_project/src/`

| 파일 | 원본 | 이 프로젝트에서 |
|---|---|---|
| `config.py` | `src/config.py` | 채널·unit split·모델 하이퍼파라미터를 `configs/experiment.yaml` 로 옮겼다 |
| `ncmapss_loader.py` | `src/data/ncmapss_loader.py` | `data/ncmapss.py` 로 재작성 (cycle별 decimated series + unit 캐시) |
| `shift_injector.py` | `src/data/shift_injector.py` | 주입은 하지 않는다 (기존 데이터만 사용). 수식 확인용 |
| `rul_model.py` | `src/models/rul_model.py` | `tools/rul_tool.py` 가 같은 아키텍처를 재정의해 weight 를 읽는다 |
| `train_rul.py` | `src/models/train_rul.py` | 학습하지 않는다 (frozen). 재학습이 필요할 때만 참고 |

### frozen RUL 모델

weight: `../models/frozen_rul/rul_lstm.pt` + `scaler.npz`
(원본 `han/rul_agent_project/outputs/checkpoints/`)

- 2-layer LSTM, hidden 64, dropout 0.3, 입력 (50, 18), 출력 스칼라 RUL
- scaler: 채널별 mean/std (학습 window 로 fit)
- **cycle 예측 규칙**: cycle 전체 decimated 시계열을 겹침 없는 50-step window 로 잘라
  window 별 점추정의 **median** (`rul_model.py: predict_cycle`). `tools/rul_tool.py`
  가 이 규칙을 그대로 따른다.
- RUL_CAP = 65 는 학습 target 정의. 평가에서 true RUL 을 자를 때만 쓴다.

이 프로젝트에서 쓰지 않는 것: MC-Dropout(`predict_mc`), latent 추출
(`forward_with_latent`) — 설계서 17장의 후속 확장 항목이다.

## 재사용하지 않은 것

`rul_agent_project/src/agent/`, `src/tools/`, `src/evaluation/` 은 판정 체계
(ACCEPT/CAUTION/REJECT, decision point 3 cycle 간격)가 이 연구의 설계
(NORMAL/FAULT + RELIABLE/WARNING, 매 cycle)와 다르므로 가져오지 않았다.
