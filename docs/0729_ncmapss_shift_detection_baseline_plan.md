# N-CMAPSS Shift Detection 실험 설계 및 최소 베이스라인

## 1. 연구 목적

본 실험의 목적은 N-CMAPSS 기반 RUL 예측 환경에서 센서 bias 및 drift로 인해 발생하는 입력 분포 변화를 탐지하고, 기존 shift detection 방법들이 어떤 유형의 변화를 잘 탐지하거나 놓치는지 분석하는 것이다.

N-CMAPSS는 본래 이상탐지 데이터셋이 아니라 RUL 예측 및 열화 분석용 run-to-failure 데이터셋이다. 따라서 본 연구에서는 탐지 task를 다음과 같이 재정의한다.

- **정상 데이터:** 센서 오염이 없는 원본 N-CMAPSS 데이터
  - 정상적인 비행조건 변화 포함
  - 수명에 따른 자연스러운 열화 포함
  - RUL 감소 포함
- **이상 데이터:** 원본 N-CMAPSS에 인위적으로 bias, drift 등의 센서 오염을 주입한 데이터

즉, 엔진 열화 자체가 아니라 **RUL 모델 입력의 무결성을 훼손하는 센서 shift**를 탐지 대상으로 한다.

---

## 2. 1차 확정 베이스라인

초기 실험에서는 서로 다른 탐지 원리를 대표하는 세 가지 모델만 우선 적용한다.

| 분류 | 모델 | 역할 | 선정 이유 |
|---|---|---|---|
| 통계적 순차 탐지 | CUSUM | 단변량 평균 변화 탐지 | 센서 bias와 drift에 대한 가장 기본적인 기준점 |
| 다변량 통계 | PCA-SPE / Hotelling's T² | 센서 관계 붕괴 및 정상 공간 이탈 탐지 | 선형 다변량 센서 관계를 평가하는 대표적인 고전 기준점 |
| Deep Change-Point Detection | MC-TIRE | 다채널 representation 변화 및 onset 탐지 | 학습 기반 다변량 shift detection에 대한 비교군 |

### 최소 비교 구성

```text
1. CUSUM
2. PCA-SPE / T²
3. MC-TIRE
4. Rule-based 제안 방법
5. LLM-based 제안 방법
```

---

## 3. 베이스라인별 평가 목적

### 3.1 CUSUM

CUSUM은 각 센서의 평균값이 정상 기준에서 지속적으로 벗어나는지를 누적 통계량으로 탐지한다.

#### 잘 탐지할 것으로 예상되는 조건

- 단일 센서 step bias
- 지속적인 offset
- 한 방향으로 누적되는 drift
- 비교적 큰 평균 변화

#### 취약할 것으로 예상되는 조건

- 평균 변화는 작지만 센서 간 관계가 깨지는 경우
- 여러 센서가 서로 보상하며 움직이는 경우
- Flight Class 변화와 같은 정상 이용조건 변화
- 짧게 반복되는 intermittent bias
- 매우 느린 gradual drift

CUSUM은 가장 기본적인 sanity-check baseline이며, 단순 통계적 방법으로도 해결되는 문제인지 확인하는 역할을 한다.

---

### 3.2 PCA-SPE / Hotelling's T²

PCA 기반 공정 모니터링에서는 SPE와 T²를 함께 사용한다.

- **SPE(Q-statistic):** 정상 PCA 부분공간으로 설명되지 않는 잔차 변화
- **Hotelling's T²:** 정상 부분공간 내부에서 정상 범위를 벗어난 이동

#### 잘 탐지할 것으로 예상되는 조건

- 일부 센서만 bias된 경우
- 센서 간 correlation 붕괴
- 정상 manifold 밖으로 벗어나는 변화
- 다변량 센서 조합의 불일치

#### 취약할 것으로 예상되는 조건

- PCA 정상 부분공간 방향으로 발생하는 shift
- 여러 센서가 정상 관계를 유지하며 함께 이동하는 경우
- 비선형 센서 관계
- 새로운 Flight Class로 인한 정상 이용점 영역 이동

PCA-SPE/T²는 현재 연구의 `consistency_z`와 가장 직접적으로 비교되는 고전적 다변량 기준점이다.

---

### 3.3 MC-TIRE

MC-TIRE는 다채널 시계열의 temporal 및 cross-channel representation 변화를 학습하여 change-point score를 출력하는 딥러닝 기반 비지도 CPD 모델이다.

#### 잘 탐지할 것으로 예상되는 조건

- 다채널 평균 변화
- 분산 변화
- temporal pattern 변화
- cross-channel representation 변화
- 명확한 shift onset

#### 취약할 것으로 예상되는 조건

- 매우 느린 gradual drift의 정확한 시작점
- 센서 fault와 정상 Flight Class 변화를 구분하는 문제
- 탐지된 변화가 RUL을 실제로 저해하는지 판단하는 문제
- adverse/favorable 방향 판단

MC-TIRE는 shift onset 자체를 탐지하는 딥러닝 비교군으로 사용한다.

---

## 4. 1차 Bias Injection 데이터셋 구성

초기 데이터셋은 탐지 모델별 실패 특성을 확인할 수 있도록 네 가지 핵심 시나리오로 구성한다.

### 4.1 Case 0: Clean Control

```text
No-shift control:
- Unit 11 clean

Natural-shift control:
- Unit 14 clean
- Unit 15 clean
```

#### 목적

- 정상 데이터에서의 false alarm 확인
- 학습하지 않은 Flight Class 변화에 대한 오탐 확인
- benign operational shift와 harmful sensor shift 구분 가능성 평가

---

### 4.2 Case 1: 단일 센서 Bias

```text
대상 센서: T48
Profile: step / ramp
Direction: negative / positive
Magnitude: 0.5σ / 1.0σ / 2.0σ
```

#### 목적

- CUSUM이 기본적인 평균 shift를 정상적으로 탐지하는지 확인
- PCA와 MC-TIRE의 detection latency 비교
- 전체 pipeline이 정상 동작하는지 확인하는 sanity test

---

### 4.3 Case 2: 다채널 관계 붕괴 Bias

예시:

```text
대상 센서:
- T24
- T30
- T48
- T50

각 센서에 서로 다른 크기 또는 방향의 bias 주입
```

#### 목적

- 센서 간 정상 correlation이 깨지는 상황 생성
- PCA-SPE의 강점 확인
- MC-TIRE가 cross-channel 변화를 탐지하는지 확인
- 향후 GDN을 추가할 필요성 판단

---

### 4.4 Case 3: 관계 보존형 Coordinated Bias

여러 센서를 정상 상관구조와 유사한 방향으로 함께 이동시킨다.

예를 들어 학습 데이터에서 구한 PCA loading 방향을 사용할 수 있다.

x'_t = x_t + α·v_k

- x_t: 원본 센서 벡터
- v_k: PCA loading 방향
- α: shift 크기

#### 목적

- 개별 센서 평균은 변하지만 센서 관계는 일정 부분 유지되는 shift 생성
- PCA-SPE가 정상 부분공간 내부 shift를 놓치는지 확인
- PCA-T²와 CUSUM의 반응 비교
- RUL 모델에는 영향을 주지만 detector가 놓치는 silent harmful shift 탐색

---

## 5. 초기 실험 파라미터

### 5.1 Magnitude

```text
0.5σ
1.0σ
2.0σ
```

2σ만 사용하면 모든 detector가 쉽게 탐지할 가능성이 있으므로, 0.5σ와 1σ를 함께 포함한다.

### 5.2 Temporal Profile

```text
Step
Ramp-15 cycles
```

### 5.3 Injection Onset

```text
전체 수명의 45% 지점
```

### 5.4 Direction

```text
Negative bias:
- RUL 과대추정 방향의 adverse shift

Positive bias:
- RUL 과소추정 방향의 favorable shift
```

### 5.5 초기 조합

| Scope | Profile | Magnitude | Direction |
|---|---|---|---|
| Single T48 | Step | 0.5 / 1.0 / 2.0σ | ± |
| Single T48 | Ramp-15 | 0.5 / 1.0 / 2.0σ | ± |
| Temp4 inconsistent | Ramp-15 | 0.5 / 1.0 / 2.0σ | ± |
| Coordinated | Ramp-15 | 0.5 / 1.0 / 2.0σ | ± |

초기 결과에서 모델별 성능이 갈리는 magnitude 구간을 찾은 뒤, 해당 구간을 세분화한다.

예:

```text
0.5σ에서는 대부분 실패
1.0σ에서는 일부 성공
2.0σ에서는 모두 성공

→ 최종 실험:
0.5 / 0.65 / 0.8 / 1.0σ
```

---

## 6. 데이터셋에 저장해야 할 메타데이터

각 injection scenario에 대해 다음 정보를 저장한다.

```text
unit
flight_class
scenario_id
fault_channels
fault_scope
fault_profile
injection_onset
ramp_length
direction
raw_bias
sigma_normalized_bias
clean_rul_prediction
corrupted_rul_prediction
rul_prediction_difference
rul_absolute_error_change
consistency_score
regime_score
```

특히 다음 두 축은 분리해야 한다.

### Injection Magnitude

```text
센서 값이 정상 데이터에서 얼마나 변했는가?
```

### RUL Impact

```text
센서 변화로 인해 RUL 예측이 얼마나 왜곡되었는가?
```

같은 1σ shift라도 센서와 주입 방향에 따라 RUL 영향이 크게 다를 수 있다.

최종적으로 중요한 시나리오는 다음과 같다.

```text
탐지는 쉽지만 RUL 영향은 없는 shift
탐지는 어렵지만 RUL 영향은 큰 shift
```

두 번째 유형은 **dangerous silent shift**로 정의할 수 있다.

---

## 7. 공정한 학습 및 평가 프로토콜

### 7.1 Training

```text
Clean training units:
- Unit 2
- Unit 5
- Unit 10
- Unit 16
- Unit 18
```

모든 모델은 센서 오염이 없는 clean N-CMAPSS 데이터만 사용한다.

### 7.2 Validation 및 Threshold Calibration

```text
Validation:
- Unit 20 clean
```

모든 모델은 동일한 clean false-alarm 조건을 만족하도록 threshold를 설정한다.

예:

```text
False alarm rate = 0%
또는
False alarm ≤ 1회 / 100 cycles
```

Test label을 이용해 threshold를 최적화하면 안 된다.

### 7.3 Test

```text
Unit 11:
- clean
- corrupted

Unit 14:
- clean natural shift
- corrupted

Unit 15:
- clean natural shift
- corrupted
```

가능하면 Unit 14와 Unit 15에도 동일한 fault injection을 적용하여 unit과 scenario가 결합되지 않도록 한다.

### 7.4 공통 후처리

모든 detector에 동일한 hysteresis를 적용한다.

```text
Detector score > threshold
        ↓
2개 decision point 연속 초과
        ↓
Confirmed shift
```

결과는 두 가지 형태로 모두 보고한다.

```text
Raw detection
Detection + common hysteresis
```

---

## 8. 평가 지표

### 8.1 Shift Detection Performance

```text
Precision
Recall
F1-score
Detection latency
False positive rate
False alarms per 100 cycles
Event-level detection rate
```

### 8.2 Harmful Shift Detection

양성과 음성을 다음과 같이 정의한다.

```text
Positive:
- adverse sensor shift
- favorable sensor shift

Negative:
- no shift
- natural Flight Class shift
```

이는 단순한 분포 변화 탐지가 아니라, RUL 입력을 훼손하는 harmful shift를 탐지하는 평가이다.

### 8.3 Generic Shift Detection

```text
Positive:
- adverse shift
- favorable shift
- natural shift

Negative:
- no shift
```

MC-TIRE와 같은 일반 change-point detector는 이 기준에서도 별도로 평가한다.

### 8.4 RUL Impact

```text
Raw RUL RMSE
Corrected RUL RMSE
RUL MAE
RUL prediction difference
Maintenance decision FNR/FPR
```

Shift detection 결과와 RUL correction 결과는 분리해서 평가한다.

---

## 9. 이후 추가할 베이스라인

### 9.1 1순위 추가: GDN

#### 역할

비선형 센서 관계를 학습하는 anomaly detector가 선형 PCA 및 `consistency_z`보다 우수한지 평가한다.

#### 추가 목적

```text
PCA:
선형 센서 관계

GDN:
비선형 graph 기반 센서 관계
```

#### 권장 입력 버전

```text
GDN-Sensor:
- 14개 측정 센서

GDN-Context:
- 14개 센서 + 4개 이용조건

또는

GDN-Regime:
- 이용조건 효과가 제거된 regime residual
```

GDN은 point-wise anomaly detector이므로 공통 threshold 및 hysteresis를 적용해 shift detector로 변환한다.

---

### 9.2 2순위 추가: ADWIN

#### 역할

adaptive-window 기반 streaming drift detector가 고정 누적 방식인 CUSUM보다 gradual drift를 잘 탐지하는지 평가한다.

#### 추가 이유

- 구현 비용이 낮음
- gradual drift 비교에 적합
- streaming drift 분야의 대표적인 기준점

---

### 9.3 3순위 추가: KL-CPD

#### 역할

MC-TIRE 외에 deep kernel 기반 change-point detection에서도 동일한 결과가 나타나는지 확인한다.

#### 추가 시점

- 최종 논문에서 Deep CPD 계열을 두 개 이상 비교할 필요가 있을 때
- MC-TIRE에 좋았던 결과가 아니라는 점을 보여줄 때

---

### 9.4 4순위 추가: TranAD

#### 역할

Transformer 기반 temporal anomaly detector가 시간적 패턴 변화에 얼마나 강한지 평가한다.

#### 적합한 추가 시나리오

```text
Intermittent fault
Lag
Stuck sensor
Noise injection
Temporal dynamics corruption
```

단순 step bias와 ramp만 사용하는 초기 단계에서는 우선순위가 낮다.

---

### 9.5 선택 추가: Page-Hinkley

CUSUM 및 ADWIN과 역할이 일부 중복되므로 필수는 아니다.

다음 경우 추가한다.

- 온라인 gradual mean shift 비교를 보강할 때
- 리뷰어가 streaming drift baseline 하나를 요구할 때

---

## 10. 최종 실험 로드맵

### Phase 1. 최소 베이스라인 구현

```text
CUSUM
PCA-SPE / T²
MC-TIRE
Rule-based method
LLM-based method
```

### Phase 2. 기본 Bias Dataset 생성

```text
Clean control
Single-sensor step
Single-sensor ramp
Multi-sensor inconsistent bias
Coordinated relation-preserving bias
```

### Phase 3. Blind Spot 분석

모델별로 다음을 확인한다.

```text
CUSUM이 놓치는 shift
PCA가 놓치는 shift
MC-TIRE가 benign과 harmful을 구분하지 못하는 조건
```

### Phase 4. 추가 베이스라인 확장

```text
GDN
ADWIN
KL-CPD
TranAD
Page-Hinkley
```

### Phase 5. 최종 Benchmark 구성

모델들이 쉽게 탐지하는 강한 공격보다 다음 조건을 중심으로 구성한다.

```text
낮은 magnitude
느린 gradual drift
관계를 일부 보존하는 coordinated shift
자연 이용조건 변화와 유사한 shift
RUL 예측에는 큰 영향을 주는 silent shift
```

---

## 11. 최종 정리

### 지금 바로 구현할 모델

```text
1. CUSUM
2. PCA-SPE / Hotelling's T²
3. MC-TIRE
```

### 이후 추가할 모델

```text
4. GDN
5. ADWIN
6. KL-CPD
7. TranAD
8. Page-Hinkley
```

초기 실험의 핵심은 단순히 가장 높은 F1-score를 얻는 모델을 찾는 것이 아니다.

```text
어떤 shift를 CUSUM이 놓치는가?
어떤 관계 변화에서 PCA가 실패하는가?
MC-TIRE는 natural shift와 harmful sensor shift를 구분할 수 있는가?
탐지하기 어렵지만 RUL 예측을 크게 훼손하는 shift는 무엇인가?
```

이 질문에 답할 수 있도록 bias injection dataset을 설계하고, 그 결과를 바탕으로 GDN 및 추가 모델을 단계적으로 확장한다.

---

# [0729 업데이트] 구현 계획 — 데이터셋 생성 설계 & 실험 준비물

> shift detection 성능에만 집중하는 1차 실험 기준. decision/correction 축은 이번 단계에서 보고하지 않고,
> RUL impact는 §6 메타데이터로만 기록해 둔다 (dangerous silent shift 셀 판별용).

## 12. 데이터셋 생성 설계

### 12.1 생성 방식: 윈도우 레벨 주입 + npz 영속화

- 전체 h5 복제는 시나리오당 ~188MB × 27개 ≈ 5GB로 낭비. 파이프라인이 실제로 소비하는 것은
  per-cycle canonical window 텐서 `(수명 cycles, 50, 18)`이므로 **이것만 저장**한다
  — 시나리오당 ~2MB (float32).
- 저장 스키마: `dataset/corrupted_grid/<scenario_id>/`
  - `windows.npz` — corrupted windows, cycles, true_rul
  - `spec.json` — §6 메타데이터 전부: fault_channels/scope/profile, onset, ramp_len, direction,
    raw_bias·σ-normalized bias, realised detector-cons, clean/corrupted RUL 예측,
    rul_prediction_difference, rul_rmse 변화, consistency/regime score, 시드
- clean control (u11/u14/u15)은 원본 h5에서 그대로 로드 — 저장 불필요.
- 주입 엔진은 이미 있음: `grid_experiment.py`의 `make_grid()` + `inject_windows()`
  (additive, step/ramp15, σ·ch_std 단위). **현재는 in-memory로만 돌므로 npz 저장 단계만 추가하면 됨.**

### 12.2 데이터셋 구성 — 조합 축, 현실성 검토, 최종 인벤토리

한 시나리오 = **"센서가 ①어떤 방식으로(모드) ②얼마나 빨리(프로파일) ③어디서(scope)
④얼마나 크게(σ) ⑤어느 쪽으로(방향) ⑥누가·언제부터(유닛/onset) 거짓말하는가"**의 조합.

#### (1) 축 정의 — 각 값의 의미와 현실 대응

**축 1. 결함 모드 — 거짓말의 방식 (수식의 형태)**

| 값 | 수식 | 직관 | 현실 대응 | 데이터에서 보이는 모습 |
|---|---|---|---|---|
| `add` | x̃ = x + δ·b(c) | 저울 영점이 틀어짐 | 압력 트랜스듀서 zero drift | 신호 전체 평행이동 |
| `gain` | x̃ = x·(1+γ·b(c)) | 눈금 간격이 틀어짐 — 값이 클수록 크게 틀림 | **열전대 노화의 전형** (접점 산화→기전력 손실) | 고출력 순간만 왜곡 |
| `noise` | x̃ = x + ε_t | 손 떨림 — 평균은 맞고 분산만 증가 | 커넥터 부식·EMI (완전 고장의 전조) | 평균 불변 → 평균계 감지기(CUSUM) 원리적 약점 |
| `stuck` | x̃_t = **상수** (flatline) | 바늘이 얼어붙음 | ADC/DAQ freeze | 윈도우 내 분산 0으로 붕괴, 타 채널과 서서히 괴리. ⚠ 기존 "onset 윈도우 패턴 반복" 구현은 비물리적 → **상수값으로 수정 (구현 반영 예정)** |
| `lag` | x̃_t = 1차 저역필터(x, τ↑) | 값은 맞는데 **느려짐** | 압력 배관 막힘, 열전대 열질량 증가 | 레벨 불변·동역학만 변화 — 시간 패턴 감지기(TranAD류) 비교에 필수 **(신규, 구현 반영 예정)** |

spike(순간 튐)는 range check로 잡히는 point anomaly라 제외. 다중 센서 독립 동시 고장은 후속.

**축 2. 시간 프로파일 — 거짓말이 커지는 속도, b(c)∈[0,1]**

| 값 | 직관 | 현실 대응 | 감지 관점 |
|---|---|---|---|
| `step` | 어느 날 갑자기 전량 | 충격·파손 | 가장 쉬움 (명확한 단절점) |
| `ramp15` | 15 cycle 선형 증가 | **빠른** 열화 | 기본 앵커. 현실 에이징 대비 빠른 편임을 명시 |
| `ramp-slow (L=40)` | 수명 끝까지 미포화 | **현실적 열전대/서미스터 에이징 속도** | 전 감지기의 절벽 예상 — 현실적 최악 셀 **(신규, 구현 반영 예정)** |
| `exp15` | 초반 급증 후 포화 | 초기 진행 빠른 열화 | step/ramp 중간 |
| `intermittent` | 30% 간헐 → +30cyc 후 상시 | 접촉 불량 | hysteresis(2연속) 스트레스. ⚠ 현실은 비행 중 고출력 구간 버스트 — cycle 단위 랜덤은 근사임을 한계로 명시 |

**축 3. 채널 scope — 어디서, 그리고 "센서들끼리 말이 맞는가"**

| 값 | 직관 | 센서 간 모순 | 분류 |
|---|---|---|---|
| `T48 단독` | EGT 센서 하나만 거짓말 | 발생 — 나머지 13개와 비교로 들킴 | **자연 고장** (실무 최빈: EGT 열전대) |
| `temp4-mix` [+1.0,−0.6,+0.8,−1.2] | 온도 4개가 제각각 | **최대** — 다변량 감지기에 가장 쉬움 | **자연 고장** (독립 다중 열화) |
| `all14-uniform` | 14개 전부 같은 방향·크기 | 없음 — 서로는 말이 맞음 | **적대적(FDIA)** — 자연 고장으로는 비물리적 (독립 센서 14개가 동일하게 틀어질 수 없음) |
| `PC1-coordinated` | 정상 상관방향을 따라 전체 이동 | 없음 + 이동 방향조차 정상스러움 | **적대적(FDIA/stealth)** — on-manifold 계측 조작 공격 |

**축 4. 크기 σ — ch_std(비행조건 변동 포함 전역 표준편차) 배수**

- delta = sign × σ배율 × ch_std × 채널계수. 방법 중립 난이도 축 (cons 비사용 근거는 (5)).
- ⚠ **물리 단위 주의**: ch_std가 운용 변동을 포함해 1σ가 물리적으로 큼
  (실측: cons=4 캘리브레이션 시 T48 delta ≈ −51°R ≈ −28°C — 실제 EGT 정확도 규격(수 °C)보다
  훨씬 큰 심각 고장 수준). → **현실적 센서 오차 크기는 0.15~0.5σ 구간** = 감지기 절벽 구간과 일치.
  "물리적으로 현실적인 크기의 fault는 기존 감지기의 절벽 아래에 있다"가 핵심 논지 후보.
- 보고 시 각 시나리오 delta를 물리 단위(°C, psi)로 병기 + 센서 정확도 규격과 대비 **(반영 예정)**.

**축 5. 방향 — RUL을 어느 쪽으로 속이나**

| 값 | 의미 | 결과 | 현실 빈도 |
|---|---|---|---|
| `−` adverse | 열화 은폐 | RUL 과대 → 교체 시점 놓침 (안전 최악) | **열전대 노화는 거의 항상 이 방향** (기전력 손실 → 저평가) |
| `+` favorable | 멀쩡한데 아픈 척 | RUL 과소 → 조기 폐기 (비용) | 상대적으로 드묾 |

그리드는 ± 대칭 유지(벤치마크 완전성), 물리적 비대칭(− 우세 = 안전 최악과 일치)은 서사에 활용.
noise/stuck/lag은 방향 개념 없음.

**축 6. 유닛 / onset**

- `u11`: 훈련과 같은 비행 클래스 → 결함 효과만 분리되는 실험실 조건
- `u14/u15`: 비행 패턴이 훈련과 다름 → benign 변화와 fault가 겹치는 실전 조건
- onset 수명 45% 고정 (1차). {30/60%} 랜덤화는 최종 벤치마크.

#### (2) 조합 전략: 앵커 + 축별 스윕

전체 곱(5모드 × 5프로파일 × 4scope × 6σ × 2방향 ≈ 1,200)은 불가능·불필요.
**앵커 = (add, ramp15, T48, 1σ, ±) 고정, 한 번에 한 축만 변경** → 시나리오에서 감지기가
무너지면 원인이 방금 바꾼 그 축이라고 귀속 가능. σ 스윕은 Case 1(절벽)·Case 3(silent)에만.

#### (3) 최종 인벤토리 — 주입 51개 + clean 3개 (`dataset/corrupted_grid/`)

**자연 고장형 (열화 물리에 대응):**

| 블록 | 수 | 변경 축 | 조합 명세 | 답하려는 질문 |
|---|---|---|---|---|
| Case 0 controls | 3 | — | u11 / u14 / u15 clean | 오탐 기준선, benign-vs-harmful |
| Case 1 σ 스윕 | 18 | 크기·프로파일 | add × {step, ramp15} × {0.5,1,2}σ × ± + ramp15 × {0.15,0.25,0.35}σ × ± | 감지기별 절벽 위치 (0.15~0.5σ = 물리적 현실 구간) |
| Case 2 상관 붕괴 | 6 | scope | add × ramp15 × temp4-mix × {0.5,1,2}σ × ± | 다변량 감지기의 강점 축 |
| Case 4 natural+fault | 4 | 유닛 | add × ramp15 × T48 × 1σ × ± @ u14, u15 | benign 위 fault 구분 |
| M 모드 스윕 | 5 | 모드 | gain 1σ ± / noise 1σ / stuck(flatline) / **lag(τ↑)** @ 앵커 | 모드별로 이기는 감지기가 달라지나 |
| P 프로파일 스윕 | 6 | 프로파일 | exp15 ± / intermittent ± / **ramp-slow(L=40) ±** @ 앵커 1σ | 발현 속도 vs latency, 현실적 느린 drift |

**적대적 (FDIA/stealth — 자연 고장 아님, 별도 카테고리로 보고):**

| 블록 | 수 | 조합 명세 | 답하려는 질문 |
|---|---|---|---|
| Case 3 PC1-coordinated | 10 | add × ramp15 × PC1 × {0.5,1,2,3,4}σ × ± | on-manifold 공격 — rule/SPE 사각지대 (예비 실행으로 확인) |
| S all14-uniform | 2 | add × ramp15 × all14 × 1σ × ± | 관계 보존 공격의 다른 기전 |

각 폴더: `windows.npz` (오염 윈도우 (수명,50,18) + cycles + 무오염 true RUL) +
`spec.json` (레시피 전체 + fault_mode/seed + 실현 cons/regime + RUL 피해 + 물리 단위 delta +
clean/corrupt 예측 시퀀스). → spec.json만 모아 "감지 난이도 × RUL 피해" 산점도로
**dangerous silent shift 셀** 특정.

#### (4) 패밀리 분리

- **패밀리 D (위 51개)** — detection 벤치마크. 난이도 축 = σ (방법 중립).
- **패밀리 A (기존 `corrupted_NCMAPSS/` cons=4 두 개)** — rule-vs-LLM 부가가치 실험 전용.
  cons는 rule 감지기 자신의 통계량 → 다중 감지기 비교의 난이도 축으로 쓰면 순환.

#### (5) 이번에 만들지 않는 것 (이연 + 한계 명시)

- onset {30,45,60}% × 시드 3개(noise/intermittent) 반복 — 갈리는 시나리오에만, mean±std 보고
- 비행 내(intra-flight) intermittent 버스트, 압력 채널 lag 변형, 다중 센서 독립 동시 고장
- MC-TIRE 학습 입력(윈도우 연결)은 npz에서 파생 — 별도 저장 불필요

### 12.3 detector별 입력 표현 (결정 사항 포함)

| detector | 입력 | 상태 |
|---|---|---|
| CUSUM / PCA-SPE·T² / rule / LLM | 결정 포인트(3 cycle 간격) 18차원 z_global 시퀀스 — 기존 packets와 동일 | 그대로 사용 |
| MC-TIRE | 시계열 원본 필요 — **(a)** per-cycle 요약 시퀀스 (~59 샘플 × 14ch, TIRE 창 대비 짧음) vs **(b)** canonical window 연결 (59×50=2,950 timestep × 14ch, cycle 경계에 shift 반영) | **(b) 권장, 결정 필요** |

## 13. 베이스라인 실험 준비물 체크리스트

### 13.1 이미 있는 것

- 주입 엔진 + 그리드 빌더 + **CUSUM** + **PCA-SPE/T²**(1차 구현) + **rule 게이트** +
  공통 hysteresis(2연속) + 블라인드스팟 매트릭스: `grid_experiment.py` (예비 실행 완료,
  결과 `results/grid_experiment.{json,md}`)
- zero-FAR 캘리브레이션 절차 (u20, CUSUM·PCA 공통)
- LLM 에이전트 실행 경로 (`agent.run_llm`, vLLM + Qwen2.5-32B-AWQ)

### 13.2 필요한 작업 (난이도 순)

1. **지표 확장** (낮음) — 현재 event/latency/point-recall/FA만 산출 →
   §8.1 전체: precision, F1, FPR, FA/100cycles, event-level rate, **raw vs hysteresis 병행 보고**.
2. **데이터셋 npz 영속화** (낮음, §12.1) — 재현성 + MC-TIRE 학습 입력으로 필수.
3. **PCA 캘리브레이션 보정** (낮음) — 예비 실행에서 margin 1.0이 no_shift에 FA 1 발생,
   전 시나리오 L4 균일 검출도 임계 과민 신호 → margin {1.2, 1.5} 스윕 또는
   "FA ≤ 1회/100 cycles" 기준(분위수)으로 전환 검토.
4. **u14/15 corrupted 시나리오** (낮음, §12.2 확장 A).
5. **MC-TIRE 통합** (중간) —
   - 외부 코드: github.com/caozhenxiang/MC-TIRE (다채널 확장판) ⚠ **다운로드 전 확인 필요**
   - 의존성: TF/Keras 계열 → LLMshift env에 설치할지 별도 env 만들지 결정
   - 입력 표현 결정 (§12.3), clean 학습 (u2/5/10/16/18) → u20 캘리브레이션 →
     score→alarm 변환 + 공통 hysteresis
   - §8.3 generic 기준(natural도 positive)으로 별도 평가 축 추가
6. **LLM 그리드 실행 스크립트** (중간) — 27+ 시나리오 × ~20 포인트 × 5 샘플 ≈ **2,700+ 콜**
   (기존 545샘플 실행의 ~5배 시간). vLLM 배치 처리, GPU 점유 확인 후 실행.

### 13.3 결정 사항 (0729 확정)

1. 공통 캘리브레이션 기준 → **FA ≤ 1/100 cycles (분위수)** 채택.
   u20 결정 포인트 통계량의 q-분위수(q = 1 − DECISION_EVERY/100 = 0.97)를 임계값으로.
   FAR 0%(max) 버전은 부록 병행 보고 가능. 한계: u20 결정 포인트가 ~25개라 97% 분위수는
   상위 1~2번째 값 근처 — max보다는 덜 brittle하지만 여전히 얇은 표본임을 명시.
2. MC-TIRE 입력 표현 → **(b) canonical window 연결** (2,950 timestep × 14ch).
3. 세분 σ 그리드 → **확정**: Case 1 ramp +{0.15, 0.25, 0.35}σ×±, Case 3 +{3, 4}σ×± (+10개).
4. LLM 실행 범위 → **성능 갈리는 부분집합만** (controls + 애매 구간 ~10 시나리오 ≈ 1,000콜).

주: rule/LLM 에이전트는 고정 게이트(cons/regime 임계)라 분위수 캘리브레이션 대상이 아님 —
공정성 논의에서 "베이스라인은 clean-FA 기준으로 캘리브레이션, 에이전트는 사전 고정 게이트" 명시.
