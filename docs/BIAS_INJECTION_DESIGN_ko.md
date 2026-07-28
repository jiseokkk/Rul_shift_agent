# Bias Injection 정교화 설계 (v2)

작성일: 2026-07-21. 대상: N-CMAPSS DS02-006, Direction-A(센서 결함) 시나리오 재설계.

---

## 1. 현재 설정의 한계 (EXPERIMENT_SUMMARY §6 재확인)

현행: unit 11, 온도 4채널(T24/T30/T48/T50)에 cycle 23부터 **±2σ 상수 스텝**.

| 약점 | 근거 |
|---|---|
| 크기가 너무 큼 | 탐지 절벽 ~0.4σ인데 2σ 주입 → meanCons 15.65, "공짜" 영역 |
| 스텝이라 쉬움 | ramp로 바꾸면 latency 5→17, FNR 0→0.22 |
| 채널 subset이라 쉬움 | 전채널 bias면 consistency 관계 보존 → recall 0.08 |
| 결정론적 | onset=23 고정, 부호 2개뿐 → 단일 포인트 결과, 통계적 신뢰 없음 |
| 물리적 근거 없음 | "4개 온도에 동일 σ배 오프셋"은 실제 어떤 결함 모드에도 대응 안 됨 |

정교화의 목표는 단순히 "더 어렵게"가 아니라:
1. **물리적으로 해석 가능한 결함 모드**(무엇이 고장났는가를 말할 수 있게),
2. **난이도를 연속 파라미터로 제어**(탐지 절벽 주변에서 운용),
3. **랜덤화된 시나리오 행렬**(단일 포인트가 아니라 곡선/분포로 보고),
4. **LLM 에이전트의 부가가치가 드러나는 모호성**(룰 탐지기가 절반쯤 맞고 절반쯤 틀리는 지점).

---

## 2. 설계 공간: 3축 분해

주입 하나를 `(결함 모드) × (시간 프로파일) × (채널 범위)`의 조합으로 정의한다.

### 축 1 — 결함 모드 (fault mode)

센서 결함의 표준 분류를 따른다. `x_t`를 원신호, `x̃_t`를 관측치라 할 때:

| 모드 | 수식 | 물리적 대응 | 비고 |
|---|---|---|---|
| `offset` | `x̃ = x + δ` | 캘리브레이션 오프셋 | 현행 방식 |
| `gain` | `x̃ = x·(1+γ)` | 열전대 감도 열화 (K-type 규격 ±0.75% 수준) | 신호 크기에 비례 → 고출력 구간에서만 크게 나타남. 상수 오프셋 가정을 깨는 핵심 모드 |
| `drift` | `x̃ = x + δ·r(c)` | 서미스터/열전대 에이징 | ramp 프로파일과 결합된 offset |
| `noise` | `x̃ = x + ε_t, ε~N(0,(kσ_ch)²)` | 커넥터 열화, EMI | 평균은 안 움직임 → z_global/consistency 평균 기반 탐지가 원리적으로 약함 |
| `stuck` | `x̃_t = x_{t0}` | 센서/ADC freeze | std→0 시그니처. 기존 C-MAPSS stuck 폴더의 N-CMAPSS 이식 |
| `lag` | `x̃_t = α·x̃_{t-1} + (1-α)·x_t` | 응답 지연(배관 막힘, 필터 오염) | 과도 구간에서만 오차 발생 |
| `stealth` | §4 참조 | FDIA(계측 조작 공격) | consistency 잔차를 0으로 유지하는 on-manifold 주입 |

우선순위: **gain, drift, stealth** 3개가 논문 기여에 직결. noise/stuck/lag는 부록용 확장.

### 축 2 — 시간 프로파일 (temporal profile)

`b(c)`를 cycle `c`에서의 크기 배율(0~1)이라 할 때:

| 프로파일 | 정의 | 파라미터 | 난이도 효과 |
|---|---|---|---|
| `step` | `1[c ≥ c₀]` | onset `c₀` | 기준선 (CUSUM에 최적 매치) |
| `ramp` | `min(1, (c−c₀)/L)` | onset, **ramp 길이 L** | L을 수명 종점과 분리(현행은 EOL 도달 고정). L∈{5,15,30}cycles |
| `exp` | `1−exp(−(c−c₀)/τ)` | 시정수 τ | 초기 빠르고 포화 — 실제 드리프트 형태 |
| `intermittent` | 초기엔 flight당 확률 p로 발현, `c₁` 이후 상시 | p, 잠복 길이 | 간헐 결함 → 상시 결함. CUSUM 리셋을 유발해 latency를 크게 늘림 |
| `in-flight` | flight 내 특정 구간(예: 고고도 순항)에만 적용 | 구간 마스크 | window 평균이 희석됨 → 평균 기반 feature 약화 |

onset `c₀`는 고정하지 말고 **수명의 {30%, 45%, 60%} 3지점 × 부호 ± = 시드당 6개 변형**으로 샘플링.

### 축 3 — 채널 범위 (channel scope)

| 범위 | 구성 | 현실성 | 탐지기와의 관계 |
|---|---|---|---|
| `single` | T48 단독 (EGT 열전대 — 실무에서 가장 흔한 결함) | 최고 | consistency_z에는 잡히지만 temp4 평균 aggregate가 희석 → 현행 rule 임계값 재검토 강제 |
| `temp4` | 현행 4채널 | 낮음 | 기준선 유지(하위 호환) |
| `module` | 물리 모듈 단위: HPT 후단 {T48, T50} 또는 압축단 {T24, Ps30, P24} | 중간 | "한 모듈의 계측 라인 공유 결함" 시나리오 |
| `all14` | 전 측정 채널 | 낮음(우연으로는 비현실적, 공격으로는 현실적) | consistency 무력화 확인용 (이미 recall 0.08 확인) |

---

## 3. 크기 보정: σ가 아니라 "탐지기 신호 cons"로 제어

> **용어**: 이 난이도 지표를 초안에서 "SNR"이라 불렀으나, 탐지기 판정 통계량과 정렬되도록 **`cons`(= `temp_consistency_z_abs`)로 정정·통일**했다(구현·실험에서 확정). 아래는 cons 기준.

핵심 정교화. 채널 원시 σ 단위로 크기를 주면 모드/채널/프로파일마다 실효 난이도가 제각각이 된다.
대신 **실효 난이도를 룰 탐지기의 판정 통계량 cons 기준으로 역산**한다:

```
cons(spec) := E[ temp_consistency_z_abs | post-onset plateau ]  (주입 후 실측)
```

절차:
1. 주입 스펙마다 크기 파라미터를 이분탐색해 `cons`가 목표값이 되도록 보정 (`calibrate_to_detector`).
2. 목표값 표준화: **cons ∈ {1~2 (한계 이하), 3~4 (절벽/애매), 6 (여유 탐지)}**
   — 실험(`snr_experiment.py`)에서 recall이 cons 2→3에서 0.00→0.45로 급등, 절벽이 룰 임계값
   cons>3에 정확히 위치. cons 3~4가 "룰은 흔들리고 LLM 추론이 기여할 수 있는" 운용점.
3. 보고서에는 σ값이 아니라 cons 값으로 시나리오를 명명 (모드·채널 간 공정 비교 가능).

gain 모드의 경우 γ는 채널 평균 대비 비율로도 병기 (예: T48 γ=0.6%) →
물리 규격(열전대 ±0.75%)과 직접 비교 가능해 논문 서사가 강해짐.

---

## 4. Stealth(on-manifold) 주입 — 최고 난이도 티어

consistency 탐지기 `E[s_j | s_others]`(선형, `cons_coef` A, 표준화 공간)를 알고 있다고 가정하는
**model-aware FDIA**. 목표 채널 j에 δ를 넣되 consistency 잔차가 0에 가깝도록 나머지 채널을 공동 섭동:

```
min_d ‖(I − A)d‖²   s.t.  d_j = δ        (d ∈ R^14, 표준화 단위)
```

- 폐형해: 등식 제약 최소자승 (14×14라 즉시 풀림). `(I−A)`의 null-space 방향으로 δ를 전파.
- 효과: consistency_z ≈ 0 유지. 그러나 regime_z(`E[s|W]`)는 모든 채널이 W 기준선에서
  벗어나므로 **자연 shift(Direction B)와 유사한 시그니처**를 만든다.
- **이게 설계 의도다**: 룰 탐지기 관점에서 "flight-class 변화"와 구분 불가능한 증거 패턴이
  생기고, 에이전트는 (flight class 컨텍스트가 변하지 않았다는 사실 + RUL 이력 + 불확실성)을
  종합해야만 정답에 도달한다. LLM 결정 계층의 존재 이유를 정면으로 시험하는 시나리오.
- 변형(위협 모델 완화): 공격자가 A를 모르고 훈련 데이터 통계만 아는 경우 →
  훈련 풀의 후기수명 방향(§5의 `degrade` 방향)으로 주입. "모델 지식 수준" 자체를 축으로 쓸 수 있음.

## 5. 열화 정렬(degradation-aligned) 주입 — 의미론적 adverse

부호 ±의 의미를 물리로 승격시킨다. 훈련 유닛들의 후기수명 구간에서 경험적 열화 방향
`u = E[Δx/Δcycle | RUL<20]` (14차원 단위벡터)를 추출한 뒤:

- `x̃ = x − s·u` (**열화 은폐**): 엔진이 실제보다 건강해 보임 → RUL 과대평가 → 현행 adverse의
  물리적으로 정합적인 버전. "고장을 숨기는 결함/공격"이라는 명확한 서사.
- `x̃ = x + s·u` (**열화 과장**): favorable의 정합 버전.

상수 오프셋과 달리 열화 방향은 manifold 위에 있으므로 consistency가 거의 반응하지 않고,
RUL 모델은 직접 속는다 — stealth와 동일하게 "탐지기-회피 + 모델-기만"을 하나의 스칼라 s로 제어.

---

## 6. 난이도 티어 요약 (논문용 시나리오 행렬)

| Tier | 이름 | 구성 | 시험하는 능력 |
|---|---|---|---|
| L0 | legacy | temp4 · step · 2σ (현행, 하위호환) | sanity check |
| L1 | calibrated-step | single(T48) · step · cons∈{2,3,4,6} | 크기 민감도 곡선 |
| L2 | drift | single(T48) · ramp(L∈{5,15,30}) + exp(τ=10) · cons 4 | 점진 변화 탐지 latency |
| L3 | gain | single(T48) · gain(step/ramp) · γ→cons 4 | 레짐 의존 오차(고출력에서만 발현) |
| L4 | intermittent | single(T48) · intermittent(p=0.3, 잠복 10cyc) · cons 4 | CUSUM 리셋 내성, 증거 누적 추론 |
| L5 | stealth | all14 · step/ramp · on-manifold(δ→T48 환산 cons 4) | Direction A/B 구분 — LLM 부가가치 핵심 |
| L6 | degrade-hide | all14 · ramp · 열화 은폐 −s·u | 안전 최악 시나리오 (RUL 과대평가) |

각 티어 × onset 3지점 × 부호 ± (L5/L6은 부호가 의미 내장) → 시나리오당 3~6개 변형.
보고는 단일 FNR이 아니라 **(cons, FNR)·(ramp L, latency) 곡선 + 변형 간 평균±표준편차**.

권장 "본문 대표 시나리오": **L2 (T48 단독, ramp 15cycles, cons 4)** — 물리적으로 가장 그럴듯한
"EGT 열전대 드리프트"이며 룰/LLM 격차가 벌어질 것으로 예상되는 운용점.
L5/L6은 논문의 차별화 포인트(적대적/은폐 시나리오)로 별도 절 구성.

---

## 7. 구현 스케치

새 모듈 `inject.py` 하나로 집중, `load_unit_cycles`의 기존 인자는 유지(L0 하위호환):

```python
@dataclass
class FaultSpec:
    mode: str          # offset | gain | drift | noise | stuck | lag | stealth | degrade
    channels: list     # 채널 인덱스 (stealth/degrade는 무시하고 전채널 산출)
    target_snr: float  # 3절 cons 난이도 (탐지기 통계량, 이분탐색 보정)
    profile: str       # step | ramp | exp | intermittent
    onset_frac: float  # 수명 대비 onset (0.30/0.45/0.60)
    ramp_len: int = 0
    sign: int = -1
    seed: int = 0      # intermittent 발현, onset jitter 용

def inject(clean: dict, spec: FaultSpec, fx_models) -> dict   # windows만 교체, RUL 라벨 불변
def calibrate_magnitude(spec, clean, fx, tol=0.1) -> float     # cons 역산 (탐지기 통계량 기준) (결과 캐시)
```

- `stealth`: `feature_models.npz`의 `cons_coef`로 `(I−A)` 제약 최소자승 → 표준화 d → 원단위 환산.
- `degrade`: `pooled_training_timesteps` 후기수명 구간에서 u 추출, `outputs/`에 캐시.
- `stress_difficulty.py`는 FaultSpec 그리드 러너로 재작성 (`build_adverse`의 수동 주입 코드 대체).
- `build_decisions.py`의 adverse/favorable은 대표 시나리오(L2)로 교체하되
  `--tier L0` 플래그로 기존 결과 재현 가능하게.

검증 순서: (1) L0 재현으로 파이프라인 무결성 확인 → (2) cons 보정 루틴을 L1으로 검증
(스트레스 테스트의 기존 σ-스윕과 교차 확인) → (3) L2~L6 순차 실행, rule agent로 먼저
난이도 곡선 확보 → (4) 운용점 확정 후 LLM agent 투입 (vLLM 비용 절약).

---

## 8. 평가 프로토콜 변경점

- 지표 추가: **detection latency 분포**(변형별), **cons-FNR 곡선의 AUC**(모드 간 비교용),
  post-onset 구간의 **결정 비용**(REPLACE 지연 비용 vs 조기교체 비용) 가중 합.
- Direction B(자연 shift) 유닛 14/15는 그대로 두고 L5 stealth와 **혼동 행렬**을 별도 보고:
  "A/B 구분 정확도"가 LLM 계층의 헤드라인 지표가 됨.
- 모든 변형은 seed 고정 + FaultSpec JSON을 packet에 동봉 (재현성).
