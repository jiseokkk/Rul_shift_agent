# N-CMAPSS Sensor Shift Detection 베이스라인 계획 (0729 v3 확정)

> **개정 이력**: v1(MC-TIRE/ADWIN/KL-CPD 로드맵) → v2(CUSUM/PCA ×Raw·Regime + OC-MLP +
> GDN + RIV/RIF pilot) → **v3(본 문서)**: 선정 기준에 "공개 구현 존재"를 추가하고
> ContextMMD·D3-Regime을 편입, RIV/RIF·USAD/TranAD 제외, Raw 변형은 ablation 전용으로
> 격리, fusion baseline은 현행 스코프에서 제외(설계만 §16.3에 보존).
> 데이터셋 구현 설계와 확정 결정 로그는 §17–18에 유지하며, 충돌 시 §18.3 결정이 우선한다.

## 1. 연구 방향 정의

본 연구는 일반 anomaly detection이나 범용 domain-shift detection 자체가 목적이 아니다.

> **N-CMAPSS의 가변 운항조건과 자연 열화가 존재하는 환경에서, 고정된 RUL 예측 모델의
> 신뢰성을 훼손할 수 있는 비정상 센서 shift를 탐지하고, 서로 다른 탐지 도구가 생성한
> 증거를 LLM Agent가 통합하여 최종 판단하는 연구**

연구는 세 단계로 구성한다.

1. **Sensor Shift Detection** — 운항조건과 자연 열화로 설명되지 않는 센서 변화가
   발생했는지 판단한다.
2. **RUL Harmfulness Assessment** — 탐지된 shift가 고정 RUL 모델의 예측 오차 또는
   정비 의사결정을 실제로 위협하는지 판단한다 (채점 기준은 §18.3 결정 9).
3. **Decision** — 증거를 통합하여 보정·정비 결정을 생성한다 (llmshift 에이전트 축).

## 2. Shift Detection 실험의 라벨 정의

Detection 벤치마크(Table A)에서는 다음 질문만 평가한다: **센서 shift가 발생했는가?**

\[
y_t^{\mathrm{shift}}=\begin{cases}0,&t<t_{\mathrm{onset}}\\1,&t\ge t_{\mathrm{onset}}\end{cases}
\]

| 상황 | 라벨 |
|---|---:|
| Flight Class 변화, 상승·순항·하강 전환, 정상 운항조건 변화 | 0 |
| 자연적인 엔진 열화 | 0 |
| 모든 주입 fault (bias/ramp/gain/noise/stuck/lag/coordinated) | 1 |

RUL 영향의 크고 작음은 이 단계에서 구분하지 않는다. **harmful/benign 구분(§18.3
결정 9의 |ΔRUL| 기준·ignore 셀)은 Harmfulness Assessment 단계에서만 적용한다** —
두 채점은 상충이 아니라 단계 분담이다.

## 3. N-CMAPSS 문제 구조

\[
X_t = g(W_t, H_t) + \epsilon_t,\qquad W_t=[alt_t,\ Mach_t,\ TRA_t,\ T2_t]
\]

- \(W_t\): 운항조건, \(H_t\): 건강상태·자연 열화, \(\epsilon_t\): 정상 노이즈
- shift \(\delta_t\) 주입 시 \(\tilde X_t = g(W_t,H_t)+\delta_t+\epsilon_t\)

Raw sensor에 detector를 직접 적용하면 Flight Class·고도·Mach·출력·비행 phase·자연
열화 등 정상 변화를 shift로 오인한다 (raw-KL 실패의 근본 원인 — §12의 ablation이
이를 실증한다). 따라서 탐지 대상은:

> **운항조건과 자연 열화로 설명되지 않는 센서 분포·관계·시간 패턴의 변화**

기본 구조는 운항조건으로 설명되는 변화를 먼저 제거하고 남은 residual 위에서
탐지하는 것이다:

\[
\hat X_t=f_{\mathrm{OC}}(W_t),\qquad R_t=X_t-\hat X_t
\]

## 4. Baseline 선정 기준

1. N-CMAPSS 운항조건 문제를 처리할 수 있는가
2. 서로 다른 shift 탐지 원리를 대표하는가
3. **공개 구현이 있거나 현실적으로 재현 가능한가**
4. LLM Agent가 통합할 서로 다른 종류의 증거를 제공하는가

같은 계열 모델을 여럿 넣기보다 원리별 대표 하나씩: 순차 통계 / 다변량 통계 /
운항조건→센서 관계 위반 / 조건부 분포 변화 / 학습 기반 domain shift /
temporal·sensor relation anomaly.

## 5. 최종 Core Baseline

| 우선순위 | 방법 | 탐지 원리 | 구현 |
|---:|---|---|---|
| 1 | **OC-MLP Residual** | 운항조건→센서 관계 위반 | 단순 구조, 직접 재현 |
| 2 | **ContextMMD** | 조건부 분포 변화 \(P(X\mid W)\) | SeldonIO/alibi-detect |
| 3 | **D3-Regime** | 학습 기반 domain shift (classifier AUC) | ogozuacik/d3 공식 레포 |
| 4 | **GDN-Regime** | 센서 관계·시간 패턴 이상 | d-ailin/GDN 공식 레포 |
| 5 | **CUSUM-Regime** | 순차 평균 변화 | 직접 구현 (기존) |
| 6 | **PCA-T²/SPE-Regime** | 다변량 선형 공간 변화 | scikit-learn (기존) |

- 본 표의 모든 detector는 regime(운항조건 처리) 버전이 기본이다. Raw 변형은
  baseline이 아니라 **conditioning ablation 전용**(§12).
- 실험 우선순위: **1순위 = 본 표(Table A) 개별 detector 벤치마크**, 2순위 = §12
  ablation(비용 낮음, 1순위와 병행 가능), 이연 = §16.3 fusion.

## 6. OC-MLP Residual

**탐지 질문**: 현재 센서값이 주어진 운항조건으로 정상적으로 설명되는가?

```text
[alt, Mach, TRA, T2] → MLP → 14개 정상 센서값 예측
→ 실제 − 예측 = sensor-wise residual → cycle score
```

- **강점**: step/ramp bias, gain, 단일·다중 센서 shift, 센서별 localization.
  현행 regime_z(polynomial)의 비선형 확장이라 기존 증거와 직접 연결.
- **약점**: lag, noise-only, 정상 관계 유지 coordinated shift, 운항조건으로
  설명 안 되는 자연 열화.
- **학습 프로토콜(필수)**: clean train unit으로만 학습 → 모델 고정 → clean
  validation unit(u20)에서 threshold → injection test에 그대로 적용.
  injection 데이터를 학습에 넣으면 shift까지 정상 관계로 흡수된다.
- **명명·인용 방침**: "OC-MLP"는 특정 논문이 아니라 본 연구의 명명 — 표준 원리
  (analytical redundancy / model-based sensor validation, 예: NASA Kobayashi–Simon
  계열의 터보팬 센서 FDI; C-MAPSS regime normalization 관행)의 최소 MLP 구현이다.
  논문에는 "our instantiation of the standard operating-condition regression
  residual baseline (denoted OC-MLP)"로 표기하고 원리의 계보 문헌을 인용한다.
  CUSUM/PCA와 같은 "교과서 원리의 자체 구현" 범주이므로 발표된 방법의 재현으로
  서술하지 않는다.

## 7. ContextMMD

**탐지 질문**: 운항조건 변화를 허용했을 때도 센서의 조건부 분포가 달라졌는가?

\[
H_0:\ P_{\mathrm{ref}}(X\mid W)=P_{\mathrm{recent}}(X\mid W)
\]

- 문제 정의(§3)와 가장 직접적으로 일치하는 detector. raw 분포 검정(KL/MMD)이
  실패했던 원인을 조건화로 정면 해결한다.
- **강점**: additive bias, gain, noise 증가(분포 형상), 다중 센서·coordinated
  distribution shift. 고정 reference와 비교하므로 지속 shift에 적응하지 않는다.
- **약점**: lag 등 시간 순서 변화(→ GDN 담당), 센서 localization 약함.
- **구현 규정**:
  - `alibi_detect.cd.ContextMMDDrift` 사용.
  - **표본 단위 = timestep** (cycle 아님): 최근 buffer 9–15 cycle × 50 timestep
    = 450–750 표본, context = timestep별 \(W_t\). cycle을 표본으로 쓰면 n≈10이라
    검정력이 없다.
  - **reference set은 train unit의 전체 수명 clean 데이터에서 구성** (§18.3
    결정 15) — 초기 healthy만 쓰면 수명 후반 clean이 전부 drift로 잡힌다.
  - buffer 길이만큼의 고유 latency가 있으므로 latency 보고 시 buffer 크기를 병기.

## 8. D3-Regime

**탐지 질문**: 학습된 domain classifier가 reference 구간과 최근 구간을 구분할 수
있는가? (구분 가능 = 분포가 다름)

```text
Reference windows → Domain 0 / Recent windows → Domain 1
→ classifier 학습 → held-out AUC > threshold ⇒ shift
```

- **강점**: 평균·분산·비선형 domain 차이, 다중 센서 shift. ContextMMD와 다른
  원리(학습 기반)의 분포 변화 증거 제공.
- **약점**: 작은 recent window에서 overfit, temporal 순서 미사용(lag 약함).
- **구현 규정**:
  - 공식 레포 `ogozuacik/d3-discriminative-drift-detector-concept-drift` 기반
    (구조가 단순해 필요시 LR-AUC로 직접 재현 가능).
  - 입력 = OC residual cycle feature: cycle당 50×14 residual → 센서별
    mean/std/slope/min/max = 70차원.
  - classifier 학습은 **결정 케이던스(3 cycle)당 1회**로 묶어 비용 제한.
  - reference domain도 전체 수명 clean에서 구성 (결정 15).
  - threshold: u20 clean-vs-clean AUC 분포의 분위수로 캘리브레이션 (결정 1과 동일
    원칙).

## 9. GDN-Regime

**탐지 질문**: 운항조건 효과 제거 후에도 센서 간 관계와 시간적 예측 구조가 깨졌는가?

\[
R_{t-L:t-1}\rightarrow\hat R_t,\qquad A_t=|R_t-\hat R_t|
\]

### 9.1 입력과 cycle 경계

- 입력 = OC residual (cycle당 50×14). **비행 간 시계열을 연결하지 않는다** — cycle
  내부에서만 temporal window 생성, cycle 종료 시 history reset. (연결 시계열이
  비행 간 자연 변동으로 fault를 덮는 것은 KL-CPD 실측으로 확인, §18.3 결정 10.)
- ⚠ canonical 50-step 압축에서 timestep 하나 ≈ 실제 수십 초 — **lag 주입 τ가
  downsampling 후에도 보이는 스케일인지 사전 확인** (아니면 GDN의 lag 강점을
  평가할 수 없는 데이터가 된다).

### 9.2 지속 bias와 latch

과거값으로 현재를 예측하므로 지속 bias에는 적응해 score가 감소할 수 있다.
→ 공통 hysteresis 위에 event latch(한 번 확정된 shift 상태 유지)를 둔다.

### 9.3 강점/약점

- **강점**: lag, stuck, noise 증가, intermittent, 센서 관계 붕괴, 비선형
  multivariate 패턴 — 분포 기반 detector가 놓치는 temporal 축 담당.
- **약점**: 지속 step bias 적응(→latch), slow ramp 지연, 관계 유지 coordinated
  shift.
- 구현: 공식 `d-ailin/GDN` (PyTorch). 레포 환경이 오래되어 현재 PyTorch/PyG에
  맞춰 모델 부분 이식 권장.

## 10. CUSUM-Regime

**탐지 질문**: 특정 센서 residual의 작은 평균 변화가 지속 누적되는가?

\[
S_t^+=\max(0,S_{t-1}^++z_t-k),\qquad S_t^-=\max(0,S_{t-1}^--z_t-k)
\]

- **강점**: step bias, mean shift, slow ramp, 지속적 단일 센서 변화. 복잡한 모델의
  필요성을 검증하는 최소 sanity-check 기준.
- **약점**: noise-only, lag, stuck, 비선형 다중 센서 변화, 관계 유지 coordinated.
- 구현: NumPy 직접 구현 (기존 `baselines/cusum.py`), 입력만 regime 신호로 교체
  (§18.4의 CUSUM-regime).
- **문헌 계보 (인용 앵커)**: Page (1954, Biometrika) — 순차 변화점 탐지의 원조;
  Moustakides (1986, Ann. Stat.) — 지속 평균 shift에 대한 minimax 최적성 증명;
  Basseville & Nikiforov (1993, *Detection of Abrupt Changes*) — 정본 교과서;
  Gama et al. (2014, ACM Comput. Surv.) — concept drift 서베이에서 표준 drift
  detector로 등재. SPC 계보와 ML drift 계보 양쪽에서 baseline 자격 공인.

## 11. PCA-T²/SPE-Regime

**탐지 질문**: 현재 residual이 정상 다변량 선형 공간에서 벗어났는가?

- \(T^2=t^\top\Lambda^{-1}t\): 정상 주성분 공간 **내부**의 과도한 이동
  (관계 유지 coordinated shift 담당).
- \(SPE=\|R-PP^\top R\|^2\): 정상 부분공간으로 설명되지 않는 **밖**의 변화
  (관계 붕괴, 단일 센서 bias 담당).
- T²와 SPE는 별도 모델이 아니라 하나의 PCA에서 나오는 상호보완 통계량.
- **약점**: 비선형 관계, lag, 아주 작은 drift.
- 구현: scikit-learn PCA + 직접 계산 (기존 구현 유지).
- **문헌 계보 (인용 앵커)**: Hotelling (1947) — 다변량 품질관리의 T²;
  Jackson & Mudholkar (1979, Technometrics) — PCA 잔차 SPE/Q 통계량 정식화;
  Kresta–MacGregor–Marlin (1991) — 다변량 공정 모니터링(MSPC) 확립;
  Qin (2003, J. Chemometrics) / Chiang–Russell–Braatz (2001) — 표준 서베이·교과서.
  Tennessee Eastman 벤치마크의 수십 년 표준 fault-detection baseline이 T²+SPE 조합.

## 12. Conditioning Ablation (Raw vs Regime)

운항조건 처리의 효과를 실증하는 축. **본 비교표(Table A)와 분리해 보고한다** —
Raw 변형은 baseline이 아니라 conditioning 필요성의 증거물이다.

| 비교쌍 | 확인 내용 |
|---|---|
| CUSUM-Raw ↔ CUSUM-Regime | 기존 구현, 비용 0 |
| PCA-T²/SPE-Raw ↔ -Regime | 기존 구현, 비용 0 |
| **MMD-Raw → MMD-Regime → ContextMMD** | raw 분포검정 실패 → residual화 효과 → 직접 조건화 효과의 3단 분해. "KL이 안 됐던 이유는 conditioning 부재"를 실증하는 핵심 ablation |
| D3-Raw ↔ D3-Regime | 학습 기반 detector도 raw에서는 Flight Class를 학습함을 실증 |
| GDN-Raw ↔ GDN-Regime | deep 계열에서의 conditioning 효과 |

기대 결과: Regime 계열에서 natural unit(u14/15) FPR 감소 + injection recall 유지.
(근거가 되는 기존 실측: raw 기반 CUSUM/PCA는 u14에서 FA 22–25회로 사용 불가,
regime 신호는 benign ~0.5–1.2σ vs fault ~15–62σ.)

## 13. 제외 항목과 사유

| 방법 | 사유 |
|---|---|
| RIV/RIF (MI 기반 model drift) | N-CMAPSS 적합성은 높으나 공개 코드 부재 + MI 추정 재현 비용. 그 역할(입출력 관계 변화)은 OC-MLP·D3·ContextMMD가 분담 |
| USAD / TranAD | **ContextMMD·D3가 지속 off-manifold 분포 변화를 커버**하므로 비선형 reconstruction 슬롯이 불필요해짐 (단순 "GDN과 중복"이 아님 — forecasting과 reconstruction은 다른 원리이나, 고정 reference 비교 계열이 그 역할을 대체). TranAD는 50-step cycle에 과한 복잡도 |
| KL-CPD / MC-TIRE | 연결 시계열에서 비행 간 자연 변동이 fault 신호를 덮음 — 실측 확인 (§18.3 결정 10) |
| ADWIN / Page-Hinkley | CUSUM과 역할 중복 (v1에서 이월된 후보, 미채택) |
| Rule 게이트 | 고정 게이트가 공통 FA 캘리브레이션 밖 — detection 벤치마크 제외 (§18.3 결정 6) |
| **Fusion baseline (Max/Weighted/XGBoost)** | **현행 스코프 제외** (§16.3, §18.3 결정 14) |

## 14. 공통 평가 프로토콜

### 14.1 데이터 분할

```text
Train:      Units 2, 5, 10, 16, 18 (clean)
Validation: Unit 20 (clean, threshold 캘리브레이션 전용)
Test:       Units 11, 14, 15 (clean + corrupted)
```

- OC 모델은 Stage 1에서 clean train unit으로 학습 후 **고정** — 모든 split에 동일
  모델로 residual 생성.
- detector의 reference/학습 데이터는 **전체 수명** clean residual 포함 (결정 15).

### 14.2 Threshold와 케이던스

- 캘리브레이션: 전 detector 공통, u20 clean에서 FA ≤ 1회/100 cycles의 분위수
  (§18.3 결정 1). Test label로 threshold 선택 금지.
- 케이던스: cycle별 score → 3 cycle마다 평가 → 2회 연속 초과 → confirmed
  (raw / hysteresis 병행 보고). 감지 크레딧은 off→on 전이 + SAT 표기
  (§18.3 결정 7).
- **모든 detector는 결정 포인트마다 정규화 score를 공통 스키마로 저장한다**
  (§18.3 결정 14) — 이연된 fusion과 LLM evidence 확장을 무비용으로 만드는 조건.

### 14.3 평가 지표

- Event-level Precision / Recall / F1, AUPRC
- Detection latency (ContextMMD는 buffer 크기 병기, 느린 ramp는 §18.5-7 이중 보고)
- FPR, FA/100 cycles, **Flight Class별 clean FPR**
- **수명 전반부 FPR / 수명 후반부 FPR** (자연 열화 confound 검증)
- Shift 유형별 F1, Sensor localization accuracy (지원 detector만: CUSUM/OC-MLP/GDN)

## 15. Shift 유형별 예상 강자 (blind spot 매트릭스)

| Shift 유형 | 유력 detector |
|---|---|
| Step bias | CUSUM, OC-MLP, ContextMMD |
| Slow ramp | CUSUM, OC-MLP |
| Gain | OC-MLP, ContextMMD, PCA |
| Noise 증가 | ContextMMD, D3, GDN |
| Stuck | GDN, D3, PCA-SPE |
| Lag | GDN (단독 — §9.1 τ 확인 필수) |
| Intermittent | GDN, D3 |
| Coordinated (관계 유지) | PCA-T², ContextMMD, D3 |
| 관계 붕괴 | GDN, PCA-SPE |

주입 fault mode 전부에 담당 detector가 존재하며(blind spot 없는 설계), 동시에
**어떤 단일 detector도 전 유형을 커버하지 못한다** — 이 매트릭스가 "다중 증거
통합이 필요하다"는 문제의식의 실증 근거가 된다.

## 16. 연구 질문과 주장 구조

### 16.1 연구 질문

> 기존 detector가 개별 변화 신호를 탐지하더라도, 정상 운항조건 변화·자연 열화와
> RUL 입력을 훼손하는 sensor shift를 구분하는 데 한계가 있는가?

> Tier-1 신호(regime_z, consistency_z, RUL history)를 입력으로 받는 LLM Agent
> (시스템)는 개별 detector 대비 동등 이상으로 안정적인 shift 판별 성능을 보이는가?

> 탐지하기 어려운 낮은 magnitude·관계 보존형 shift가 고정 RUL 모델에 큰 영향을
> 주는 dangerous silent shift를 형성하는가?

### 16.2 주장 구조

**시스템 대 시스템 성능 주장**이다 — "통합 자체가 원인"이라는 인과 주장이 아니다
(§18.3 결정 12·14). 원인 귀속은 consistency ablation(제거 시 adverse F1→0)과
§18.4 통제 실험(CUSUM/PCA-regime)이 담당한다. detection에서 우위가 제한적일
경우의 후퇴선은 detector가 원리적으로 못 하는 축: 방향(adverse/favorable) 판정,
benign/harmful 원인 구분, RUL 보정, 정비 결정, 애매구간 recall·latency
(기존 실측: rule 0.64→LLM 1.00, latency 13→1).

### 16.3 Fusion baseline (현행 스코프 제외, 설계 보존)

추후 필요시(리뷰어 요구 등) 실행할 설계: 모든 detector score \(E_t\)를 공통
입력으로 Best-individual / Max-OR / Weighted / XGBoost fusion vs LLM. 실행 조건:
① §14.2의 score 로깅이 있으면 저장된 score 위에서 재실행 없이 가능, ② 학습형
fusion(Weighted/XGBoost)의 가중치는 개발용 시나리오에서만 학습(dev/final 분리),
③ LLM 입력도 detector score 기반으로 재설계(§18.3 결정 17의 이연 항목)하여 동일
evidence 조건 충족, ④ LLM-비교는 결정 8의 21-시리즈 부분집합 원칙 동일 적용.

---

# [0729 구현] 데이터셋 생성 설계 & 실험 준비물

> shift detection 성능에만 집중하는 1차 실험 기준. decision/correction 축은 이번 단계에서 보고하지 않고,
> RUL impact는 spec.json 메타데이터로만 기록해 둔다 (dangerous silent shift 셀 판별용).

## 17. 데이터셋 생성 설계

### 17.1 생성 방식: 윈도우 레벨 주입 + npz 영속화

- 전체 h5 복제는 시나리오당 ~188MB × 27개 ≈ 5GB로 낭비. 파이프라인이 실제로 소비하는 것은
  per-cycle canonical window 텐서 `(수명 cycles, 50, 18)`이므로 **이것만 저장**한다
  — 시나리오당 ~2MB (float32).
- 저장 스키마 (0729 계층화): `dataset/corrupted_grid/<category>/<block>/<scenario_id>__u<unit>/`
  - category = `natural` | `adversarial`, block = `case1_single_T48` / `case2_temp4mix` /
    `case3_pc1_coordinated` / `case4_fault_on_natural` / `mode_sweep` / `profile_sweep` /
    `all14_uniform`
  - `windows.npz` — corrupted windows, cycles, true_rul
  - `spec.json` — 메타데이터 전부: category/block, fault_mode/seed, fault_channels/
    pattern/profile(+길이, lag_tau), onset, direction, σ배율, delta 물리 단위(°R/psia),
    realised cons/regime (+plateau_def: 미포화 프로파일은 last5), RUL 피해(ΔRUL·RMSE 변화),
    clean/corrupted RUL 예측 시퀀스, 결정 포인트
- clean control (u11/u14/u15)은 원본 h5에서 그대로 로드 — 저장 불필요.
- 주입 엔진은 이미 있음: `grid_experiment.py`의 `make_grid()` + `inject_windows()`
  (additive, step/ramp15, σ·ch_std 단위). **현재는 in-memory로만 돌므로 npz 저장 단계만 추가하면 됨.**

### 17.2 데이터셋 구성 — 조합 축, 현실성 검토, 최종 인벤토리

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
| `lag` | x̃_t = 1차 저역필터(x, τ↑) | 값은 맞는데 **느려짐** | 압력 배관 막힘, 열전대 열질량 증가 | 레벨 불변·동역학만 변화 — 시간 패턴 감지기 비교에 필수 **(신규, 구현 반영 예정; τ의 downsampling 가시성 확인 §9.1)** |

spike(순간 튐)는 range check로 잡히는 point anomaly라 제외. 다중 센서 독립 동시 고장은 후속.

**축 2. 시간 프로파일 — 거짓말이 커지는 속도, b(c)∈[0,1]**

| 값 | 직관 | 현실 대응 | 감지 관점 |
|---|---|---|---|
| `step` | 어느 날 갑자기 전량 | 충격·파손 | 가장 쉬움 (명확한 단절점) |
| `ramp15` | 15 cycle 선형 증가 | **빠른** 열화 | 기본 앵커. 현실 에이징 대비 빠른 편임을 명시 |
| `ramp-slow (L=40)` | 수명 끝까지 미포화 | **현실적 열전대/서미스터 에이징 속도** | 전 감지기의 절벽 예상 — 현실적 최악 셀 **(신규, 구현 반영 예정)** |
| `exp15` | 초반 급증 후 포화 | 초기 진행 빠른 열화 | step/ramp 중간 |

> `intermittent`(간헐 발현)은 **0729 검토에서 삭제** — u11 수명 구조상(onset 27 + 잠복 30cyc,
> 수명 59) 상시 발현 구간이 ~2 cycle뿐이라 산술적으로 불성립, 측정 의미 없음.
> 재도입한다면 cycle 단위 랜덤이 아니라 비행 내(intra-flight) 버스트 방식으로.

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

#### (3) 최종 인벤토리 — 주입 49개 + clean 3개 (`dataset/corrupted_grid/`)

**자연 고장형 (열화 물리에 대응):**

| 블록 | 수 | 변경 축 | 조합 명세 | 답하려는 질문 |
|---|---|---|---|---|
| Case 0 controls | 3 | — | u11 / u14 / u15 clean | 오탐 기준선, benign-vs-harmful |
| Case 1 σ 스윕 | 18 | 크기·프로파일 | add × {step, ramp15} × {0.5,1,2}σ × ± + ramp15 × {0.15,0.25,0.35}σ × ± | 감지기별 절벽 위치 (0.15~0.5σ = 물리적 현실 구간) |
| Case 2 상관 붕괴 | 6 | scope | add × ramp15 × temp4-mix × {0.5,1,2}σ × ± | 다변량 감지기의 강점 축 |
| Case 4 natural+fault | 4 | 유닛 | add × ramp15 × T48 × 1σ × ± @ u14, u15 | benign 위 fault 구분 |
| M 모드 스윕 | 5 | 모드 | gain 1σ ± / noise 1σ / stuck(flatline) / **lag(τ↑)** @ 앵커 | 모드별로 이기는 감지기가 달라지나 |
| P 프로파일 스윕 | 4 | 프로파일 | exp15 ± / **ramp-slow(L=40) ±** @ 앵커 1σ | 발현 속도 vs latency, 현실적 느린 drift |

**적대적 (FDIA/stealth — 자연 고장 아님, 별도 카테고리로 보고):**

| 블록 | 수 | 조합 명세 | 답하려는 질문 |
|---|---|---|---|
| Case 3 PC1-coordinated | 10 | add × ramp15 × PC1 × {0.5,1,2,3,4}σ × ± | on-manifold 공격 — SPE 사각지대 (예비 실행으로 확인) |
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

- onset {30,45,60}% × 시드 3개(noise 등 확률 모드) 반복 — 갈리는 시나리오에만, mean±std 보고
- 비행 내(intra-flight) intermittent 버스트, 압력 채널 lag 변형, 다중 센서 독립 동시 고장

### 17.3 detector별 입력 표현

| detector | 입력 | 상태 |
|---|---|---|
| CUSUM / PCA-SPE·T² (raw·regime) / LLM | 결정 포인트(3 cycle 간격) 18차원 z_global 또는 regime 신호 시퀀스 — 기존 packets와 동일 | 그대로 사용 |
| OC-MLP Residual | canonical window의 per-timestep (W_t → 14센서) 예측 잔차 → cycle score | **신규** |
| ContextMMD | 최근 buffer 9–15 cycle의 timestep 표본 (X_t, W_t) vs 전체 수명 clean reference | **신규 (v3)** |
| D3-Regime | cycle당 70차원 residual feature (센서별 mean/std/slope/min/max) | **신규 (v3)** |
| GDN-Regime | cycle별 canonical window의 regime residual (50×14), 비연결(§9.1) | **신규** |
| ~~RIV/RIF~~ | ~~결정 포인트 window 내 (X_{-j}, e_j) MI~~ | **제외 — §18.3 결정 13** |
| ~~MC-TIRE~~ | ~~canonical window 연결 시계열~~ | **제외 — §18.3 결정 10** |

## 18. 베이스라인 실험 준비물 체크리스트

### 18.1 이미 있는 것

- 주입 엔진 + 그리드 빌더 + **CUSUM** + **PCA-SPE/T²**(1차 구현) + **rule 게이트** +
  공통 hysteresis(2연속) + 블라인드스팟 매트릭스: `grid_experiment.py` (예비 실행 완료,
  결과 `results/grid_experiment.{json,md}`)
- zero-FAR 캘리브레이션 절차 (u20, CUSUM·PCA 공통)
- LLM 에이전트 실행 경로 (`agent.run_llm`, vLLM + Qwen2.5-32B-AWQ)

### 18.2 필요한 작업 (난이도 순)

1. **지표 확장** (낮음) — 현재 event/latency/point-recall/FA만 산출 →
   §14.3 전체: precision, F1, AUPRC, FPR, FA/100cycles, Flight Class별·수명 전/후반부
   FPR, **raw vs hysteresis 병행 보고**.
2. **데이터셋 npz 영속화** (낮음, §17.1) — 재현성 + 딥·분포 detector 학습/reference
   입력으로 필수.
3. **공통 score 로깅 스키마** (낮음, §18.3 결정 14) — 결정 포인트마다 정규화
   detector score 벡터 저장. 이후 fusion/LLM evidence 확장의 전제조건이므로
   **러너 개발 초기에 반영**.
4. **PCA 캘리브레이션 보정** (낮음) — 예비 실행에서 margin 1.0이 no_shift에 FA 1 발생
   → margin {1.2, 1.5} 스윕 또는 분위수 기준 전환 검토.
5. **u14/15 corrupted 시나리오** (낮음, §17.2 Case 4).
6. **OC-MLP Residual 구현** (중간) — clean units(u2/5/10/16/18)로 W→14센서 MLP 학습
   → u20 캘리브레이션 → cycle score + 공통 hysteresis. 기존 polynomial regime
   residual과 성능 비교 병기.
7. **ContextMMD 통합** (중간) — `alibi-detect` 설치 (⚠ **외부 패키지 — 설치 전 사용자
   확인**), §7 구현 규정(표본=timestep, 전체 수명 reference, buffer latency 병기).
8. **D3-Regime 통합** (중간) — 공식 레포 (⚠ **외부 다운로드 전 사용자 확인**; 구조
   단순해 LR-AUC 직접 재현으로 대체 가능), §8 구현 규정.
9. **GDN-Regime 통합** (높음) — 공식 `d-ailin/GDN` (⚠ **외부 다운로드 전 사용자
   확인**), regime residual 입력·cycle 비연결(§9.1), latch(§9.2), 공통
   캘리브레이션·cadence. lag τ의 downsampling 가시성 사전 확인.
10. **LLM 그리드 실행 스크립트** (중간) — 실행 범위는 §18.3 결정 8의 21 시리즈
    (≈ 2,100콜). vLLM 배치 처리, GPU 점유 확인 후 실행.
11. ~~MC-TIRE 통합~~ — 폐기 (결정 10). ~~RIV/RIF pilot~~ — 폐기 (결정 13).

### 18.3 결정 사항 (0729 확정)

1. 공통 캘리브레이션 기준 → **FA ≤ 1/100 cycles (분위수)** 채택.
   u20 결정 포인트 통계량의 q-분위수(q = 1 − DECISION_EVERY/100 = 0.97)를 임계값으로.
   FAR 0%(max) 버전은 부록 병행 보고 가능. 한계: u20 결정 포인트가 ~25개라 97% 분위수는
   상위 1~2번째 값 근처 — max보다는 덜 brittle하지만 여전히 얇은 표본임을 명시.
2. ~~MC-TIRE 입력 표현~~ — **결정 10으로 폐기**.
3. 세분 σ 그리드 → **확정**: Case 1 ramp +{0.15, 0.25, 0.35}σ×±, Case 3 +{3, 4}σ×± (+10개).
4. LLM 실행 범위 → **성능 갈리는 부분집합만** → 결정 8로 구체화.
5. **intermittent 프로파일 삭제** — 산술적 불성립 (§17.2 축 2 주석).
6. **rule 감지기를 detection 벤치마크에서 제외** — rule의 고정 게이트(cons>3 등)는
   공통 FA 캘리브레이션 프로토콜 밖에 있어 운영점 비교가 성립하지 않음(순환 의심 포함).
   rule 에이전트 자체는 llmshift의 에이전트 실험(패밀리 A, 보정/결정 축)에서만 사용.
7. **감지 크레딧 = 알람 전이(off→on) + SAT 표기** — 감지 성공은 onset 이후
   첫 off→on 전이에만 부여. pre-onset부터 hysteresis 확정 알람이 지속 중인 시리즈는
   **SAT(포화, 판정 불능)**로 표기: recall/latency 집계에서 제외, 해당 오탐은 FPR에 계상.
   근거: c4 파일럿에서 natural 유닛의 상시 오탐이 "L0 즉시 감지"로 잘못 집계됨 —
   항상 울리는 알람은 fault에 대한 정보량이 0.
8. **LLM 실행 부분집합 — 입력(σ) 기반 사전 박제, 21 시리즈.**
   선정 기준은 베이스라인 결과·우리 신호(cons) 모두 불사용, 데이터셋 속성만 사용:
   "컨트롤 전부 + natural+fault + 물리적 현실 크기(0.15~0.35σ) 구간 + 결함 모드 + 적대적 대표."

   | 그룹 | 시리즈 |
   |---|---|
   | 컨트롤 | no_shift(u11), natural(u14), natural(u15) |
   | natural+fault | c4_natural_fault_u14_{neg,pos}, c4_natural_fault_u15_{neg,pos} |
   | 현실 크기 구간 | c1_T48_ramp_{0.15,0.25,0.35}s_{neg,pos} (6) |
   | 결함 모드 | m_gain_T48_ramp_1s_{neg,pos}, m_noise_T48_ramp_1s, m_stuck_T48 |
   | 적대적 대표 | c3_coord_pc1_ramp_{1,2}s_{neg,pos} (4) |

   각 시리즈는 유닛 수명 **전체**(pre-onset clean 구간 포함, 결정 포인트 ~20개 × 5샘플)를
   온전한 시계열로 실행 — pre-onset은 FPR 측정 구간이고, RUL 히스토리 축적과 hysteresis에
   연속 시퀀스가 필요. ≈ 2,100콜. **모든 LLM-베이스라인 비교표는 이 21개 부분집합 내
   수치끼리만 구성** (전체 그리드 pooled와 혼합 금지).
9. **harmful 라벨 — Harmfulness Assessment 단계 전용 채점** (detection 벤치마크는
   §2의 주입=1 라벨 사용 — 역할 분담, 결정 16 참조).

   **컨셉 재확인**: 본 연구의 목표는 정상 엔진 열화의 감지가 아니라, **비정상적인 센서
   고장 등으로 인해 LSTM이 잘못된 예측을 내는 상황을 감지·보정**하는 것.
   따라서 harm의 정의 = **배치된 LSTM의 예측 왜곡**(모델 종속적 정의 — 목적이 해당 모델의
   보호이므로 원리적. 모델 무관 심각도는 주입 크기 σ 축이 담당).

   **채점 규칙** (컨셉의 직접 번역):

   | 상황 | 컨셉상 성격 | 채점 |
   |---|---|---|
   | 정상 엔진 열화 (RUL 실제 감소) | 정상 — 모델이 맞게 예측 중 | 울리면 오탐 |
   | 자연 운용 변화 (flight class 등) | 정상 — 센서는 진실을 말함 | 울리면 오탐 |
   | 센서 고장 → LSTM 예측 왜곡 (post-onset 평균 \|ΔRUL\| > 5cyc) | **잡을 대상** | 놓치면 미탐 |
   | 센서 고장이지만 예측 무왜곡 (\|ΔRUL\| ≤ 5cyc) | 잡을 이유 없음 | **채점 제외 (ignore)** |

   임계 5cyc = REPLACE 임계(10)의 절반; {3, 5, 10} 민감도 표 병기로 임계 선택 자의성 방어.

   **근거 — "센서가 망가지면 예측도 틀어진다"는 직관은 성립하지 않음** (파일럿 실측):
   c1 T48 단독 1σ → ΔRUL 36cyc / c3 PC1 방향 **4σ·14채널** → ΔRUL **5.2cyc**.
   LSTM은 민감한 방향이 따로 있고(단일 채널 이탈엔 크게, 정상 상관 방향 이동엔 거의 무반응),
   noise는 윈도우 평균에서 상쇄, stuck은 초기엔 참값과 동일. 따라서 감지 난이도와 RUL 피해는
   **독립된 두 축**이며 2×2 셀이 전부 실재:

   | | 예측 틀어짐 | 예측 무왜곡 |
   |---|---|---|
   | 잡기 쉬움 | 보통의 fault | 시끄럽지만 무해 |
   | 잡기 어려움 | ★ **dangerous silent shift** (핵심 타깃) | 무해+안 보임 → ignore |

   이 두 축을 분리 기록하는 것(spec.json의 σ·실현cons ↔ ΔRUL)이 §17.1 메타데이터 설계의 이유.
10. **딥 CPD 계열(MC-TIRE, KL-CPD) 제외 — 코드 삭제.**
   근거: ① KL-CPD를 BSD-3 공식 코드 포팅으로 실제 통합·실행한 결과, 윈도우 연결
   시계열에서 **clean 데이터의 비행 간 자연 변동(배경 cycle 점수 평균 2.0, max 4.4)이
   fault 신호(2σ step에서 2.5)를 완전히 덮음** — 연결 시계열 CPD가 이 데이터 구조에
   부적합함을 실측 확인. ② MC-TIRE도 동일 입력을 쓰므로 같은 문제 예상 + 인용수 우려.
   딥 슬롯은 GDN-Regime으로 재선정 (§9 — point-wise 이상 감지라 결정 케이던스와 정합).
11. **입력 그룹 분류 정정** — 그룹 기준 = "운항조건 W 사용 여부". OC-MLP·RIV/RIF는
   정의상 regime 측 (v2에서 정정). v3에서는 본 표 전체가 regime 기본이 되어 Raw
   변형은 ablation 전용으로 격리 (§12).
12. **score-fusion baseline 미채택** — 연구 질문을 시스템 대 시스템 성능 주장으로
   한정. 원인 귀속은 consistency ablation + §18.4 통제 실험 담당. (결정 14에서 재확인)
13. **(v3) 라인업 개편** — ContextMMD·D3-Regime 편입 / RIV/RIF 제외(공개 코드 부재,
   MI 재현 비용) / USAD·TranAD 제외(**ContextMMD·D3가 고정 reference 비교로 지속
   off-manifold 분포 변화를 커버** — "GDN 중복"이 아니라 역할 대체가 사유) /
   선정 기준에 "공개 구현 존재" 명문화 (§4–5, §13).
14. **(v3) fusion baseline 현행 스코프 제외 (결정 12 재확인)** — 설계는 §16.3에 보존.
   단, **러너는 결정 포인트마다 정규화 detector score 벡터를 공통 스키마로 저장**
   (§18.2 항목 3) — 이연 비용을 0으로 만드는 유일한 조건.
15. **(v3) 전체 수명 reference 원칙** — ContextMMD reference set·D3 reference
   domain·딥 detector 학습 데이터는 train unit의 **전체 수명** clean residual로 구성.
   초기 healthy만 사용 시 수명 후반 clean 구간 오탐 (트레이드오프: 열화와 닮은
   ramp-slow의 recall 하락은 문제 정의상 필연 — ramp-slow 셀이 이 경계를 측정).
   검증 지표 = 수명 전/후반부 FPR (§14.3).
16. **(v3) 라벨 역할 분담** — detection 벤치마크(Table A) = §2 라벨(주입=1, RUL 영향
   무관) / harmful 채점(결정 9) = Harmfulness Assessment 단계 전용. 상충 아님.
17. **(v3) LLM 입력은 현행 Tier-1 신호 유지** (regime_z, consistency_z, RUL history)
   — detector score 벡터를 evidence로 받는 재설계는 fusion 단계와 함께 이연 (§16.3).
   fusion baseline 없이 LLM에만 detector score를 주면 입력 공정성 비판이 재발하고
   packets/prompt 재작업 비용이 크다.

### 18.4 입력 공정성 프레이밍과 통제 실험 (0729 확정)

**주장 구조**: 본 논문의 기본 주장은 시스템 대 시스템 — "Tier-1 신호 + LLM 추론으로 구성된
에이전트가 기존 통계/모델 기반 shift 감지기보다 낫다." 에이전트가 더 풍부한 입력을 받는 것은
시스템 설계의 일부이므로 핸디캡을 주지 않는다 (LLM은 방향·원인·보정·결정까지 전부 수행).

**단, 승인의 원인 귀속(피처 vs 추론)을 위해 통제 실험 1개를 ablation으로 추가:**

```
베이스라인(raw z) < 베이스라인(+우리 피처) < rule(피처+게이트) < LLM(피처+추론)
                    └── CUSUM-regime / PCA-regime (§5) ──┘
```

- **CUSUM-Regime / PCA-Regime**: 동일 러너에서 입력만 z_global → regime-조건부 신호
  (regime_z, consistency_z 벡터)로 교체. 비용 ≈ 0.
- 해석 (어느 쪽이든 유리):
  - 피처를 받아도 지면 → "이득은 피처가 아니라 추론 로직" 입증, 주장 강화
  - 피처를 받아 감지가 비슷해지면 → 감지는 commodity로 재프레이밍하고, LLM 고유 가치는
    감지기가 원리적으로 못 하는 축으로: 방향(adverse/favorable) 판정, 원인 구분
    (benign vs harmful), RUL 보정, 결정, 애매구간(cons 3~4) recall·latency 우위
    (기존 실측: rule 0.64→LLM 1.00, latency 13→1)
- 근거가 되는 자체 데이터: consistency ablation 시 adverse F1→0 (피처 지배력),
  rule 에이전트 P=1.00/FPR=0.00 (같은 피처 + 손코딩 게이트) — "피처만으로 충분한가"라는
  질문은 우리 결과에서 자연히 제기되므로 선제 대응 필수.

### 18.5 보완 검토 목록 (제안 — 미확정, 채택 시 개별 승인)

1. generic(natural도 positive) 기준과 harmful(결정 9) 기준을 별도 표로 병행 보고.
2. **베이스라인 하이퍼파라미터 튜닝**: u20에 주입한 튜닝 전용 fault로 CUSUM k, PCA 성분수,
   ContextMMD kernel/버퍼, D3 window, GDN L/top-k 등 소규모 그리드서치 — strawman 비판
   방지 (테스트 유닛 불사용 명시).
3. **FA-budget 스윕**: q ∈ {0.5, 1, 2, 5회/100cyc}로 recall-vs-FA 곡선 — 단일 운영점 비판 방지.
4. **반복 실험**: 갈리는 시나리오에 onset {30/45/60%} × 확률 모드 시드 3개 → mean±std.
5. **캘리브레이션 표본 확충**: 임계값 산정만 per-cycle(u20 ~75점) 사용, 부트스트랩 CI 병기.
6. **dangerous silent shift 구성적 탐색**: LSTM 입력 민감도(∂RUL/∂x)를 저-consistency
   부분공간에 사영한 방향으로 주입 (Case 3b) — PC1은 RUL 피해 최대 10.5로 부족 확인됨.
7. **latency 이중 보고**: onset 기준 + "신호 0.5σ 도달 시점" 기준 (느린 ramp 왜곡 보정).
8. **채널 귀속 로깅**: CUSUM 발화 채널·PCA contribution·OC-MLP/GDN sensor score 저장
   → 추후 fault isolation 비교 (§14.3 localization 지표의 근거 데이터).
9. **재현성 스탬프**: spec.json/결과에 git hash 기록. 통계 감지기 per-cycle 케이던스 민감도 각주.
