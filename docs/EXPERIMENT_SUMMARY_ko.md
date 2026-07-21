# 실험 정리 — 분포이동 인식 RUL 결정 에이전트 (N-CMAPSS DS02-006)

> 대상 코드: `/home/iai4/Desktop/han/rul_shift_agent/`
> 실행: `/home/iai4/miniconda3/envs/LLMshift/bin/python run_all.py --agent llm`

---

## 0. 한 줄 요약

약한 LSTM이 RUL(잔여수명)을 예측하고, 그 **위에 얹힌 에이전트가 "지금 데이터가 학습 분포에서 벗어났는가"를 판단해 정비 결정(continue/inspect/replace)을 내린다.** 에이전트는 RUL 예측을 고치지 않고, **얼마나 믿을지**를 결정한다. 핵심 기여는 그 판단을 가능케 하는 **Tier-1 신호 3종**이다.

---

## 1. 왜 이 문제가 어려운가 (Tier-1이 푸는 것)

RUL 모델은 Fc3(비행클래스 3) 엔진으로만 학습됐다. 배포 시 두 종류의 "이동"이 생긴다:

| 이동 | 예시 | 위험한가? | 원하는 행동 |
|---|---|---|---|
| **센서 결함/공격 (adverse)** | 온도센서가 실제보다 낮게 읽힘 | **위험** — 엔진이 건강해 보여 RUL 과대평가(silent over-optimism) | 경보(escalate) |
| **운전조건 변화 (natural)** | 다른 비행클래스(Fc1/Fc2)라 센서값 자체가 다름 | 안전 — 모델이 사실 잘 일반화함 | 그냥 진행(무경보) |

**문제의 핵심:** 순진한 z-score(`z_global` = "이 센서값이 학습 평균에서 몇 σ 떨어졌나")로는 **이 둘을 구분할 수 없다.** 센서 결함도 z_global을 키우고, 다른 비행클래스도 z_global을 키운다. 그래서:
- **threshold** 베이스라인: adverse에서 부풀린 RUL을 그대로 믿어 **전부 놓침 (FNR 1.00)**.
- **CUSUM** 베이스라인: z_global만 보고 둘 다 경보 → natural에서 **오경보 폭발 (FPR 0.45)**.

**단일 방법으로는 adverse를 잡으면서 natural을 조용히 둘 수 없다.** 이걸 푸는 게 Tier-1이다.

---

## 2. Tier-1 상세 — 직관 먼저 (⭐ 여기 집중)

Tier-1은 "이 센서값이 평균에서 멀다"라는 멍청한 질문 대신, **분포이동의 원인을 구분하는 두 개의 똑똑한 질문**을 던진다.

### 2.1 `z_global` (기존/순진한 방식) — 왜 부족한가

> 질문: "이 센서값이 **학습 전체 평균**에서 몇 σ 떨어졌나?"

문제: 엔진을 **다르게 운전하면**(다른 고도·마하) 센서값이 당연히 평균에서 멀어진다. 그게 고장인지 그냥 다른 상황인지 구분 못 함. → CUSUM이 실패하는 이유.

### 2.2 Tier-1 #1 `regime_z` — "지금 **운전 방식**을 고려하면 이 값이 정상인가?"

**자동차 비유:** RPM이 4000이다. 평균 2000의 2배니까 경보? → 멍청하다. **오르막에서 액셀을 밟고 있으면** 4000은 정상이다. 똑똑한 질문은 *"지금 액셀을 밟고 급경사를 오르는 중인데, 그 상황에서 4000 RPM이 정상인가?"* 이다.

- **W = (alt, Mach, TRA=스로틀, T2=흡입온도)** = "지금 엔진을 **어떻게 운전하고 있나**" (= 운전 상황).
- 학습 데이터로 회귀모델을 fit: **"이 운전점에서라면 온도 T48은 대략 X여야 한다"** (`E[센서 | W]`, 다항회귀).
- **regime_z** = 실제 값이 그 **운전점별 기대치**에서 얼마나 벗어났나 (잔차를 정규화).

왜 구분되나:
- **다른 비행클래스**: 운전점(W)이 다를 뿐, "이 운전점이면 X여야 한다"는 물리 규칙은 그대로 성립 → 잔차 작음 → **regime_z 작음**.
- **센서 바이어스**: 운전점과 **무관한** 상수 오프셋이 얹힘 → 기대치에서 벗어남 → **regime_z 폭발**. 게다가 **부호가 방향을 알려줌**(음수=온도 낮게=엔진 건강해 보임=adverse / 양수=favorable).

### 2.3 Tier-1 #2 `consistency_z` — "센서들끼리 **서로 말이 맞는가?**" (이 태스크의 핵심 판별기)

**방 온도계 비유:** 방에 온도계 4개. 하나가 25°C, 나머지 셋이 20°C를 가리킨다. **"진짜 온도가 몇 도인지 몰라도"** — 서로 안 맞는다는 사실만으로 하나가 고장임을 안다. 엔진 물리는 온도·압력·회전수를 일정 비율로 **묶어 놓는다.**

- 학습으로 fit: **"T48은 다른 센서들(압력·회전수)로 예측할 수 있다"** (`E[센서 | 나머지 센서들]`).
- **consistency_z** = T48이 **다른 센서들이 말하는 값**에서 얼마나 벗어났나.

왜 구분되나:
- **온도 4채널에만 바이어스**: 온도는 튀는데 압력·회전수는 멀쩡 → 서로 안 맞음 → **consistency_z 폭발**.
- **다른 비행클래스**: 모든 센서가 물리 곡면을 따라 **함께** 움직임 → 여전히 서로 맞음 → **consistency_z 작음**.

### 2.4 #1과 #2의 차이 (헷갈리기 쉬운 지점)

| | 무엇과 비교? | benign 이동에서 | 센서 결함에서 |
|---|---|---|---|
| **#1 regime_z** | 센서 vs **운전조건(W)** | 작음 | 폭발 (+부호로 방향) |
| **#2 consistency_z** | 센서 vs **다른 센서들** | 작음 | 폭발 |

둘 다 "benign은 통과, 결함은 실패"하는 **독립적 위생검사** 두 개다. 이 태스크(온도 subset 바이어스)에선 **#2가 주력 판별기**, natural 오탐 억제엔 **#1이 직접 기여.**

### 2.5 Tier-1 #3 `mc_std` — 모델의 "나 자신 없어" 신호

LSTM에 dropout을 켠 채 30번 예측 → 표준편차. OOD(바이어스) 입력에선 예측이 더 흔들려 std 상승. 센서통계와 **독립적인** 신뢰도 채널.

### 2.6 실측 — 세 신호가 실제로 갈라지는가 (unit 11, cycle 30)

| 지표 | clean | **adverse(−2σ)** | favorable(+2σ) | **natural(Fc1)** |
|---|---|---|---|---|
| temp z_global (순진) | +0.31 | −1.69 | +2.31 | +0.58 |
| **temp regime_z (#1)** | −0.05 | **−62.5** | **+62.4** | **−0.55** |
| **temp consistency_z (#2)** | 0.40 | **15.6** | 15.9 | **0.52** |
| max consistency_z (#2) | 1.09 | **28.0** | 28.0 | **1.20** |
| RUL 예측 편향 | 0 | **+41.9** | −23.3 | ≈0 |
| MC std (#3) | 1.68 | **4.97** | — | — |

→ **센서 바이어스는 15~62σ로 폭발, 자연 이동은 0.5~1.2σ로 잠잠.** 10배 이상 분리 → 원인 구분 성립. 이게 adverse(잡기)와 natural(무시)을 **동시에** 가능케 한다.

---

## 3. Tier-2 상세 — 결정 정책 (에이전트 출력 다듬기)

Tier-1이 "입력 신호"라면 Tier-2는 "출력 정책"이다. 원래 3개 중 #4는 제거했다.

| | 내용 | 상태 | 어디서 |
|---|---|---|---|
| #4 | CUSUM 통계를 에이전트 입력으로 융합 | ❌ **제거** (Tier-1이 지배해 기여 미미 → CUSUM은 순수 baseline으로 환원) | — |
| #5 | **시간적 hysteresis** | ✅ 사용 | `agent.apply_policy` |
| #6 | **cost-aware abstention** | ✅ 사용 | `agent.apply_policy` |

- **#5 hysteresis:** shift 기반 격상을 **연속 2회(HYSTERESIS_N) 지속돼야 확정.** 건강한 엔진에 뜨는 고립된 단발 오경보를 억제. (ablation: 끄면 adverse FPR 0.18→0.27.)
- **#6 cost-aware:** 확정 adverse → 부풀린 RUL 불신 → **최소 inspect로 floor**; favorable(과비관) → **inspect로 cap**(멀쩡한 자산 조기교체 방지); 저confidence → 안전한 중간(inspect)으로 기권. miss가 false alarm보다 비싸다는 비대칭 반영.

---

## 4. 전체 파이프라인

```
[HDF5 DS02-006]
  │ data_ncmapss.py  유닛·사이클별 500s 윈도우(50×18) + RUL 라벨(cap 65), 분할
  ▼
① preprocess.fit_feature_models()   (Fc3 학습만)
  │  전역 mean/std, regime 모델 E[s|W](#1), consistency 모델 E[s|others](#2) → feature_models.npz
  ▼
② train_rul.py   (Fc3 5유닛 학습 / unit20 검증)  LSTM 54,849 params, val RMSE 5.65, scaler 저장
  ▼
③ build_decisions.py   (시나리오 4종: no_shift/adverse/favorable/natural)
  │  결정포인트(3사이클마다): 바이어스 주입(adverse/favorable) → RUL point+MCstd(#3)
  │  → FeatureExtractor: z_global + regime_z(#1) + consistency_z(#2) → context, gt_label → packets.json
  ▼
④ baselines.py   threshold + CUSUM(unit20 보정) → baseline_decisions.json  (CUSUM은 baseline 전용)
  ▼
⑤ agent.py (--agent llm/rule)   프롬프트 3블록 → 4단계 추론 → 5샘플 다수결 → apply_policy(#5,#6)
  │  Step1 CAUSE GATE: regime_z·consistency_z 작으면 shift 아님(z_global 커도) → RUL만으로 판단  ← natural 오탐 억제
  │  Step2 DIRECTION(부호) → Step3 물리(RUL 상승점프=불가능) → Step4 비용 반영 결정
  ▼
⑥ evaluate.py  FNR/FPR/F1 + shift 감지    ⑦ ablation.py    ⑧ make_figures/make_report
```

---

## 5. 결과

### 5.1 결정 품질 (FNR / FPR / F1) — CUSUM은 baseline

| Method | no_shift | adverse | favorable | natural |
|---|---|---|---|---|
| threshold | 0.22/0.00/0.88 | **1.00/0.00/0.00** | 0.00/0.27/0.86 | 0.06/0.00/0.97 |
| cusum | 0.22/0.00/0.88 | 0.00/0.09/0.95 | 0.00/0.27/0.86 | 0.00/**0.45**/0.72 |
| **agent (LLM)** | 0.22/0.00/0.88 | 0.00/0.27/0.86 | 0.00/0.27/0.86 | 0.06/**0.00**/0.97 |

- shift 감지(Dir A): CUSUM F1 0.91/지연 8, **agent F1 1.00/지연 2**.
- 요지: agent는 **adverse 놓치지 않고(FNR 0)** + **natural 조용(FPR 0)** 을 동시에. 단일 베이스라인 불가.

### 5.2 Ablation (rule 에이전트)

| config | adverse | natural | 의미 |
|---|---|---|---|
| full | 0.00/0.18/0.90 | 0.06/0.00/0.97 | 기준 |
| no_consistency | **1.00/0.00/0.00** | 0.06/0.00/0.97 | #2 제거 → adverse 완전 붕괴 |
| no_tier1 | 0.00/0.18/0.90 | 0.06/**0.65**/0.62 | Tier-1 전부 제거 → natural이 CUSUM처럼 오탐 |
| no_hysteresis | 0.00/**0.27**/0.86 | 0.06/0.00/0.97 | #5 제거 → adverse FPR↑ |

→ **#2가 adverse를 잡고, Tier-1 전체가 natural 오탐을 막고, #5가 오탐을 더 줄인다.**

---

## 6. Bias Injection 정교화 필요성 (⚠️ 중요)

**현재 FNR 0은 상당 부분 "쉬운 주입" 때문이다.** 스트레스 테스트(`stress_difficulty.py`)로 확인:

| 주입 방식 | FNR | shift recall | latency | meanCons |
|---|---|---|---|---|
| temp4 step **0.25σ** | **0.78** | **0.00** | — | 1.98 |
| temp4 step 0.50σ | 0.00 | 0.92 | 5 | 3.82 |
| temp4 step **2.00σ (현 설정)** | 0.00 | 0.92 | 5 | **15.65** |
| temp4 **RAMP→1.0σ** (점진) | **0.22** | 0.58 | **17** | 3.93 |
| **all14** step 0.5σ (전채널) | 0.11 | **0.08** | 14 | 1.14 |

**세 가지 약점:**
1. **크기가 너무 큼.** 탐지 절벽은 ~0.4σ. 2σ는 그 5배(meanCons 15.65) → "공짜" 영역. 0.25σ에선 완전 실패(FNR 0.78).
2. **급격한 스텝이라 쉬움.** 점진 ramp면 latency 5→17, FNR 0→0.22. 실제 센서 열화는 점진적.
3. **채널 subset이라 쉬움.** consistency_z는 "일부만 오염 + 나머지 깨끗한 기준"에 의존. **전채널 바이어스면 관계가 보존돼 recall 0.08로 실패.**

**개선 방향 (정직한 프로토콜):**
- 단일 2σ 점 → **σ 스윕 탐지곡선**을 주 결과로 ("0.4σ에서 절벽"이 훨씬 과학적).
- **점진적 ramp를 기본 주입**으로 (latency가 의미를 가짐).
- **하드 케이스 추가:** 전채널/무작위 subset, 곱셈형 gain 오차, **운전점과 공변하는 calibration 오차**(regime_z도 속임).
- **더 어려운 자연 이동:** 다른 DSxx나 RUL 모델 약화로 실제 예측 붕괴 조건 확보.
- draft §5.3도 "Dir A 주입은 인위적"이라 이미 인정 → 이 스트레스 곡선으로 한계를 정량화하면 논문이 더 단단해짐.

**단, 완전히 무의미하진 않음:** 2σ에서도 **베이스라인은 실패**(threshold FNR 1.00, CUSUM FPR 0.45)하므로 비교는 공정. "다 쉬운 게 아니라 에이전트 특징이 이 섭동에 잘 맞을 뿐". **Dir B(자연 이동)는 주입이 없는 진짜 일반화 테스트**라 더 정직한 결과.

---

## 7. 파일 맵

| 파일 | 역할 |
|---|---|
| `config.py` | 상수·분할·채널·임계 |
| `data_ncmapss.py` | HDF5 → 윈도우 + RUL 라벨 |
| `preprocess.py` | **Tier-1 #1 regime_z, #2 consistency_z** fit/계산 |
| `rul_tool.py` | LSTM + **Tier-1 #3 MC-Dropout** |
| `train_rul.py` | RUL 학습 |
| `build_decisions.py` | 시나리오·바이어스 주입·패킷 생성 |
| `baselines.py` | threshold + CUSUM (baseline 전용) |
| `prompt.py` | LLM 프롬프트(3블록 + CAUSE GATE 추론) |
| `agent.py` | LLM/rule 에이전트 + **Tier-2 #5,#6 정책** |
| `evaluate.py` / `ablation.py` | 지표 / 요소별 절제 |
| `stress_difficulty.py` | **bias 난이도 스윕(§6)** |
| `make_figures.py` / `make_report.py` | 그림 / 리포트 |
