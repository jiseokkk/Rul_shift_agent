# 0804 CUSUM·PCA 베이스라인 실험 계획 — 데이터셋 재구축 + Shift 감지·Latency 평가

> **범위**: 0729 v3 계획(§5)의 core 중 **CUSUM과 PCA-T²/SPE만** 먼저 실행한다.
> 각각 Raw-Xs / Raw-XsW / Regime 입력 3종 = 총 9개 detector 변형.
> 평가 질문은 두 개로 한정: ① **shift를 감지하는가**, ② **onset으로부터 몇 cycle 뒤에
> 최초 감지하는가(latency)**. (+ 대조군에서의 오탐)
> OC-MLP / ContextMMD / D3 / GDN / LLM은 이 실험이 끝난 뒤 같은 데이터셋 위에서 추가한다.
>
> **진행 규칙**: 아래 §8의 단계마다 결과를 보고하고 **사용자 컨펌 후 다음 단계 진행**.
> 이 문서 자체도 컨펌 전까지는 계획일 뿐이며 어떤 코드도 실행하지 않는다.

---

## 1. 현재 자산 (2026-08-04 레포 실사 결과)

| 자산 | 경로 | 상태 |
|---|---|---|
| N-CMAPSS DS02-006 원본 | `dataset/data_set/N-CMAPSS_DS02-006.h5` | 있음 |
| 데이터 로딩·decimation | `core/data_ncmapss.py` (h5 로드, 10:1 decimation) | 있음 — 단 **구 "cycle당 중앙 window 1개" 로직은 표현 v2(§2.1: 전체 비행 sliding window + cycle 집계)로 대체** — window화 계층 수정 필요 |
| 특징 모델 (z_global/regime_z/consistency_z) | `core/preprocess.py` (코드 잔존) | **아티팩트 `feature_models.npz` 삭제(08-04) → Stage 1 ①에서 clean train units로 재적합.** ch_std가 σ 주입 단위·Raw 표준화의 전제라 모든 작업의 선행 조건. (`outputs/`의 `cusum_h.json`·`train_baseline.json`은 구버전 산물 — 재적합 시 무효/덮어씀) |
| **`baselines/` 폴더 전체** (common.py, cusum/pca core, grid_experiment.py) | — | **삭제됨 (2026-08-04) → 본 계획 §8의 신규 레이아웃으로 재작성.** 구버전 `cusum.py`/`grid_experiment.py`만 git 이력에 잔존 (참고용) |
| **`injection/` 폴더 전체** (inject.py, build_corrupted.py) | — | **삭제됨 (2026-08-04) → §8 Stage 1에서 `injection/engine.py`로 재설계.** 구버전은 git 이력에 잔존 (참고용). §2.2 수식이 신규 엔진의 명세 |
| 구 예비 실행 결과 | `results/grid_experiment.{json,md}`, `snr_experiment.json` | 잔존 — §7 예상표의 실측 근거로만 참조 |
| **corrupted_grid 데이터셋** | — | **삭제됨 → 본 계획으로 재구축** |
| 데이터 분할 | `core/config.py`: Train u2/5/10/16/18(Fc3), Val u20(Fc3), Test u11(Fc3)/u14(Fc1)/u15(Fc2) | 고정 |

---

## 2. 데이터셋 설계

### 2.0 유닛 분할과 역할 (`config.py` 고정, DS02-006 전체 9유닛)

| 유닛 | Fc | 수명 | 역할 | 이번 실험에서의 사용 |
|---:|---:|---:|---|---|
| u2,5,10,16,18 | 3 | — | **Train** (clean만) | 표준화 상수 + regime/consistency 회귀 + PCA 부분공간 적합. 주입·평가 안 함 |
| u20 | 3 | 66 | **Val = 캘리브레이션 전용** (clean) | threshold 분위수 산출만. 적합·평가 불사용. (민감도 스윕 시 튜닝 fault는 여기만) |
| u11 | 3 | 59 | **Test — 실험실 조건** | 훈련과 동일 Fc → fault 효과 순수 분리. Block A–E 주입 본진 + clean FA 기준선 |
| u14 | 1 | 76 | **Test — 실전 조건** | 미학습 Fc1 = natural shift. clean은 benign 오탐 측정(라벨 0), Block F는 fault 중첩 |
| u15 | 2 | 67 | **Test — 실전 조건** | u14와 동일 역할 (Fc2) |

- 누수 규율: Train(적합) → u20(임계값) → Test(평가)의 단방향. test label로 어떤
  선택도 하지 않는다.
- flight-class 설계 의도: train/val이 전부 Fc3이므로 u14/15는 "처음 보는 운항
  분포" — benign natural shift 조건을 데이터 구조로 확보. u11에서 잡고 u14/15
  clean에서 안 울리는지가 Raw vs Regime conditioning 효과의 실증 축.
- onset 45% 근사 주입 시점: u11 ≈ cyc 27, u14 ≈ cyc 34, u15 ≈ cyc 30
  (정확값 Stage 0 산출표에서 확정).

### 2.1 표현 계층 (0804 확정: 문헌 표준 정렬) + 주입 지점 + npz 영속화

**표현 v2 — "cycle당 중앙 window 1개"(구 draft 단순화)를 폐기하고 N-CMAPSS RUL
문헌 표준(다운샘플 전체 비행 + sliding window + cycle 집계)으로 전환한다.**

전환 근거: ① LSTM·에이전트가 아직 고정이 아니고 전 계층이 재구축 중인 지금이
전환 비용이 0인 유일한 시점 (이후 단계마다 전환 비용 복리 증가), ② "비표준 표현"
리뷰 리스크 제거, ③ E[s\|W] regime 모델이 상승·하강 포함 전체 운전 영역을 학습
→ within-flight 운전조건 축 회복.

- **저장 단위**: cycle당 10:1 decimated **전체 비행 시계열** `(L_c, 18)` float32,
  L_c ≈ 100–1,800 (Fc1 ~206, Fc2 ~647, Fc3 ~1,125 평균). 시나리오당 ~5MB 이하.
- **주입 지점 (0804 확정: native 1Hz)**: 주입은 **decimation 이전의 native 1Hz
  원시 시계열**에 적용하고, 그 뒤 10:1 decimation을 거쳐 decimated 결과만 저장한다.
  근거: ① 실제 센서 fault는 원시 스트림에서 발생 — 인과 순서 정합, ② 향후 lag
  mode(τ가 실제 초 단위) 추가 시 native 주입이 필수 — 주입 정의가 표현과 독립,
  ③ 저장·실험 결과는 불변 (add/gain/stuck은 subsampling과 가환이라 수학적 동일,
  noise는 subsampling이 σ를 보존해 통계적 동일 — 비용 0).
  **σ 보존의 전제 확인(0804 2차 검토)**: `data_ncmapss.py`의 decimation은 순수
  subsampling(`seq[::10]`, 무필터)임을 코드로 확인 — 독립 noise의 marginal σ 보존
  성립. 향후 필터/평균 기반 decimation으로 바꿀 경우 유효 noise 분산을 별도 측정해
  기록해야 함(주장이 구현 방식 의존적임을 명시).
- **window화**: 길이 50, 기본 비중첩(stride 50) sliding window → cycle당
  N_c = ⌊L_c/50⌋개 (u11 ~22, u14 ~4, u15 ~13). stride 최종값은 Stage 0에서 확정.
- **detector 입력**: window별 특징 → cycle 집계(기본 mean; §3.1) → **cycle당
  벡터 1개**. 결정 케이던스·hysteresis·지표(§4)는 표현 전환과 무관하게 동일.
- **LSTM 정합**: RUL 모델도 후속 단계에서 동일 표현(전 window 학습 + cycle 집계
  예측, 문헌 표준)으로 재학습한다. 본 0804 detection 실험은 LSTM 불사용이므로
  재학습은 비차단 — `outputs/rul_lstm.pt`(구 표현 학습본)는 그때까지 보류.
- **운전조건(W) 축**: W는 1Hz timestep마다 존재하며, 표현 v2에서는 비행 간
  변동(순항점·flight class 차이)뿐 아니라 **비행 내 변동(상승/순항/하강)도
  window들에 포함**된다. regime 조건화는 window 내 timestep 단위로 수행.
- **생성 원칙: 항상 원본 기준** — 모든 시나리오는 원본 h5(읽기 전용)의 clean
  **native 1Hz** 시계열에서 **독립 생성**한다 (주입 → decimation → 저장).
  오염본 위에 재오염 없음; Block F도 u14/15의 clean 데이터 위에 주입(natural
  shift는 원본의 자연 특성). 주입 크기 기준 ch_std도 clean train unit 통계.
- RUL 라벨(Y)은 건드리지 않는다 — "센서는 거짓말하지만 ground truth는 진짜".
- 저장 스키마 — **`dataset/corrupted_dataset/` 아래 카테고리→블록→시나리오 계층**:

```text
dataset/corrupted_dataset/
  manifest.csv                      # 전체 50개 시나리오 인덱스: id, block,
                                    # category(sensor_fault|adversarial), unit, mode,
                                    # profile, σ, 방향, onset_cycle, 물리 delta
  controls/                         # clean 3개도 동일 포맷으로 저장 (자기완결성)
    ctrl_u11/  ctrl_u14/  ctrl_u15/
  blockA_min_shift/                 # 탐지 가능한 최소 shift 크기 (σ 절벽, 18개)
  blockB_slow_drift/                # 느린 drift와 누적 검출 (2개)
  blockC_relation_break/            # 센서 관계 붕괴와 SPE (6개)
  blockD_subspace_aligned/          # PCA 주부분공간 정렬(white-box) shift (8개)
  blockE_fault_modes/               # fault mode에 따른 사각지대 (9개)
  blockF_natural_overlap/           # 운항조건 변화와 실제 fault의 중첩 (4개, u14/15)
  devset/                           # u20 기반 DEV 시나리오 3~5개 (벤치마크 제외)
                                    # 용도: Stage 2 난이도 사전확인·k 민감도 +
                                    # 후속 본 메소드(LLM) 튜닝 전용 재료
  previews/
    <scenario_id>.png               # 주입 채널 clean vs corrupted 오버레이

각 시나리오 폴더 = series.npz (decimated 전체 비행: series, cycles,
cycle_bounds, true_rul) + spec.json (§2.5 메타데이터 전부)
```

- **폴더 = 블록(연구 질문) 단위** — 데이터셋 구조 자체가 실험 설계를 설명한다.
  category 구분은 폴더 계층 대신 **manifest·spec.json의 `category` 필드**로 기록:
  `sensor_fault`(Block A/B/C/E/F — 합성 주입 fault) / `adversarial`(Block D만).
  구명칭 `natural`은 폐기 — 합성 주입 블록이 "자연 발생 고장"으로 오독될 소지
  (0804 2차 검토). Block F는 배경이 자연 shift임을 spec에 별도 필드로 기록:
  `background_shift: natural_operating_condition`, `fault_source: synthetic_injection`.
  적대적 분리 보고 원칙(§2.4)은 집계 단계에서 category 필드로 유지.

- clean 컨트롤도 동일 포맷으로 저장해 데이터셋을 자기완결적으로 만든다
  (h5 없이 corrupted_dataset/만으로 전체 실험 재현 가능, 총 ~250MB 이하).

### 2.2 주입 수식 (fault mode별)

채널 j, cycle c, 프로파일 스케일 \(b(c)\in[0,1]\), 크기 \(\delta_j = \mathrm{sign}\cdot\sigma_{\mathrm{mult}}\cdot\mathrm{ch\_std}_j\):

| mode | 수식 (native 1Hz 시계열 원소별, 주입 후 decimation) | 비고 |
|---|---|---|
| `add` | \(\tilde x = x + \delta_j\, b(c)\) | zero-offset drift. 기본 모드 |
| `gain` | \(\tilde x = x\,(1 + \gamma_j\, b(c))\), \(\gamma_j = \delta_j/\overline{x_j}\) | 값이 클수록 왜곡 — 열전대 노화 전형. **분모 보호(0804 2차 검토)**: 기준 레벨 \(\overline{x_j}\)(train mean)이 \(|\overline{x_j}|<\varepsilon\)인 채널에는 gain 주입 금지(engine.py 가드 — 절대온도·압력 채널은 해당 없음); spec.json에 `gain_reference_type/value, gamma` 기록(§2.5) |
| `noise` | \(\tilde x = x + \varepsilon,\ \varepsilon\sim N(0, (\delta_j b(c))^2)\) | 평균 보존·분산 증가. seed 고정 |
| `stuck` | \(\tilde x_t = x_{t_0^-}\), \(t \ge t_0\) — **onset 직전 마지막 정상 관측값**(= cycle \(c_0{-}1\)의 마지막 native 1Hz sample)으로 이후 전체 동결 (stuck-at-last-value 표준 정의; onset은 cycle 단위이므로 1Hz 기준 시점을 이렇게 확정) | flatline. 방향 개념 없음. 동결값·소스 인덱스는 spec.json에 기록(§2.5) |

프로파일 \(b(c)\), onset \(c_0=\mathrm{round}(0.45\cdot\mathrm{life})\):

| profile | \(b(c)\), \(c\ge c_0\) | 의미 |
|---|---|---|
| `step` | 1 | 즉시 전량 |
| `ramp15` | \(\min(1, (c-c_0+1)/15)\) | 15 cycle 선형 — 빠른 열화 (기본 앵커) |
| `ramp40` | \(\min(1, (c-c_0+1)/40)\) | 수명 내 미포화 — 현실적 느린 에이징 |

**off-by-one 수정 (0804 3차 검토)**: 구식 \(\min(1,(c-c_0)/L)\)은 \(b(c_0)=0\)이라
ramp의 실효 시작이 \(c_0{+}1\)이 되어, \(c_0\)에서 즉시 발효되는 step 대비 latency에
구조적 +1 cycle 편향이 생긴다. \(+1\) 보정으로 두 profile 모두 \(c_0\)부터 주입
효과 발생(\(b(c_0)=1/L\)) — latency는 계속 \(c_0\) 기준으로 계산.

- `lag`은 이번 범위에서 제외 (담당 detector인 GDN이 없어 평가 불능 — 0729 v3 §9.1).
- `intermittent`는 기존 확정대로 제외 (0729 결정 5 — u11 수명 구조상 산술 불성립).
- PC1-coordinated: clean train unit의 **표준화 `vec_xs` 공간(§3.1)**에서 적합한 PCA
  제1주성분 방향 \(v_1\)(X_s 14열만 사용)으로 전 센서 동시 이동 (구용어 vec_global
  폐기 — 0804 2차 검토). z-공간 방향을 물리 단위로 환산해 시계열에 주입:
  \(\Delta x_j = \alpha\, b(c)\, v_{1,j}\, \mathrm{ch\_std}_j\),
  \(\alpha = \sigma_{\mathrm{mult}}\). **명칭: PCA principal-subspace-aligned shift**
  — "on-manifold"는 물리적 정상 manifold 위임을 보장하지 못하므로 비사용(과잉 주장
  방지); 정확히는 "clean train의 PCA 유지 부분공간 방향에 정렬된 white-box shift".
  (detector 자신의 부분공간 방향을 쓰는 worst-case 설계임을 논문에 명시 — FDIA
  프레이밍과 정합)

### 2.3 난이도 축: σ (방법 중립) + 물리 단위 병기

- \(\mathrm{ch\_std}_j\) = train unit 전역 표준편차(운항 변동 포함, `feature_models.npz`).
- **0.15~0.5σ 구간이 물리적으로 현실적인 센서 오차 크기** — 기존 실측: T48 1σ ≈ 51°R ≈
  28°C로 실제 EGT 정확도 규격(수 °C)보다 훨씬 큰 심각 고장 수준. 따라서 저 σ 구간이
  "현실 크기 fault는 고전 감지기의 절벽 아래인가"를 묻는 핵심 셀이다.
- ⚠ **재적합 후 재확인 필요**: 표현 v2에서 적합 풀이 전체 비행(상승·하강 포함)으로
  확장되면 ch_std가 구(순항 풀) 값보다 커질 수 있음 → 51°R 수치는 구 풀 기준.
  σ 그리드는 유지하되 Stage 0/1의 σ→물리 단위 환산표를 신규 ch_std로 갱신하고,
  "현실 크기 구간"의 σ 좌표가 크게 이동하면 그리드 하한을 조정한다.
- spec.json에 각 시나리오 delta를 물리 단위(°R/psia 등)로 병기.
- cons 기반 캘리브레이션(`calibrate_to_detector`)은 **사용하지 않는다** — cons는 rule
  검출기 자신의 통계량이라 다중 검출기 비교의 난이도 축으로 순환 (0729 §17.2 패밀리 분리).

### 2.4 시나리오 인벤토리 — 컨트롤 3 + 주입 47 (총 50)

**컨트롤 (3)**

| id | 내용 | 역할 |
|---|---|---|
| ctrl_u11 | u11 clean (Fc3, 훈련과 동일 클래스) | FA 기준선 |
| ctrl_u14 | u14 clean (Fc1, natural shift) | benign 오탐 — raw 변형의 예상 파괴 지점 |
| ctrl_u15 | u15 clean (Fc2, natural shift) | 〃 |

**Block A — 탐지 가능한 최소 shift 크기 (`blockA_min_shift/`, 18)** : add × T48 단독 × u11

| profile | σ | 방향 | 수 |
|---|---|---|---:|
| ramp15 | 0.15 / 0.25 / 0.35 / 0.5 / 1.0 / 2.0 | ± | 12 |
| step | 0.5 / 1.0 / 2.0 | ± | 6 |

→ 질문: detector별 detection 절벽이 어느 σ에 있는가. step vs ramp latency 차이.

**Block B — 느린 drift와 누적 검출 (`blockB_slow_drift/`, 2)** : add × ramp40 × T48 × 1.0σ × ± × u11
→ 질문: 미포화 느린 drift에서 CUSUM 누적의 강점이 실증되는가, latency는 얼마나 늘어지는가.

**Block C — 센서 관계 붕괴와 SPE (`blockC_relation_break/`, 6)** : add × ramp15 × temp4-mix
(T24,T30,T48,T50에 각각 +1.0/−0.6/+0.8/−1.2 배율) × {0.5, 1.0, 2.0}σ × ± × u11
→ 질문: PCA-SPE의 강점 축 — 단독 채널 대비 우위가 나오는가.

**Block D — 부분공간 정렬 shift와 PCA 사각지대 (`blockD_subspace_aligned/`, 8, category=adversarial)** : u11
| 종류 | σ | 방향 | 수 |
|---|---|---|---:|
| PC1-coordinated × ramp15 | 1.0 / 2.0 / 4.0 | ± | 6 |
| all14-uniform × ramp15 | 1.0 | ± | 2 |

→ 질문: SPE 사각지대 실증. T²가 잡는 크기는 어디부터인가. (적대적/FDIA 카테고리 —
자연 고장과 분리 보고)

**Block E — fault mode에 따른 사각지대 (`blockE_fault_modes/`, 9)** : ramp15 × T48 × u11
| mode | σ | 수 |
|---|---|---:|
| gain | 1.0 ± | 2 |
| noise | 1.0, 2.0 × seeds {0,1,2} | 6 (방향 없음) |
| stuck | — (onset 직전 last-value 동결, §2.2) | 1 (방향·σ·seed 개념 없음, step 성격) |

→ 질문: gain은 add와 유사하게 잡히는가. **noise는 예상 detection rate 0** — 현행 입력이
window-mean 기반이라 원리적으로 비가시(§7 예상 결과 참조). 사각지대 문서화 셀.
**stuck**은 "동결 채널 vs W를 따라 움직이는 타 채널"의 괴리를 SPE/consistency가
늦게라도 잡는지 확인하는 셀 — mode 축 완결 (0804 검토 반영).

**Block F — 운항조건 변화와 실제 fault의 중첩 (`blockF_natural_overlap/`, 4)** : add × ramp15 × T48 × 1.0σ × ± × {u14, u15}
→ 질문: benign flight-class 변화 위에 fault가 겹칠 때 Regime 변형이 구분하는가
(raw 변형은 SAT 예상).

- **채널 선택**: 단독 주입은 전부 T48(EGT) 고정 — ① 블록 축(크기·속도·관계·모드·
  배경)과 채널 축이 섞이지 않게 하는 변인 통제, ② 물리 논거(열전대 노화, adverse
  방향, σ→°C 환산)가 T48에 앵커, ③ 시나리오 예산. 다채널은 Block C(temp4)/
  D(전 14센서)가 담당. **추후 계획**: 채널 일반화 주장이 필요해지면 대표 압력
  채널(P24 등)로 Block A를 반복 — 잠긴 50개는 불변, "추가 탐색 실험"으로 분리
  (§7 규칙 ③).
- onset은 전 시나리오 수명 45% 고정 (30%/60% 랜덤화는 최종 벤치마크로 이연, 0729 §17.2).
- noise는 **처음부터 seeds {0,1,2} 3개 고정** (σ레벨당 3 시나리오, seed별 결과 병기
  + 평균 보고). 구안("seed 1개 → 갈리면 3개 반복", 0729 §18.5-4)은 결과를 본 뒤
  프로토콜을 바꾸는 사후 선택이라 벤치마크 잠금(§7 규칙 ②)과 충돌 — 폐기 (0804 검토 반영).

### 2.5 spec.json 메타데이터

```text
scenario_id, block, category(sensor_fault|adversarial), unit, flight_class, life_cycles
fault: {mode, channels(이름+인덱스), profile, ramp_len, onset_cycle, onset_frac,
        direction, sigma_mult, delta_raw(물리 단위, 채널별), seed}
pc1: {loading_vector, alpha}                    # Block D만
stuck: {stuck_value(채널별 물리값), stuck_source_index(native 1Hz 전역 인덱스)}  # stuck만
gain: {gain_reference_type("train_mean"), gain_reference_value, gamma}  # gain만
background_shift: "natural_operating_condition", fault_source: "synthetic_injection"  # Block F만
injection_level: "native_1hz"                   # 주입 지점 명시 (§2.1: 주입 후 decimation)
provenance: {git_hash, created, engine_version}
```

(clean/corrupted RUL 예측 시퀀스와 ΔRUL은 이번 detection 실험에는 불필요 —
LSTM을 돌리는 별도 후속 단계에서 spec.json에 **추가 기록**할 수 있게 필드만 예약.)

### 2.6 주입 설계의 문헌 근거 (reference 체크)

| 설계 요소 | 근거 |
|---|---|
| fault mode 분류 (bias/drift/gain/noise/stuck) | Balaban et al. (2009, IEEE Sensors J.) — 항공우주 센서 fault의 표준 분류가 정확히 이 5종 (bias, drift, scaling, stuck, noise 계열) |
| 터보팬 가스패스 센서에 bias 주입해 FDI 평가 | Kobayashi & Simon (NASA, 2003/2005 계열) — 엔진 센서 FDI 연구의 표준 평가 방식이 gas-path 센서 bias 주입 |
| 데이터셋·채널 정의 (X_s 14, W 4, DS02-006) | Arias Chao et al. (2021, *Data* 6(1):5) — N-CMAPSS 원 논문 |
| 관계 보존(on-manifold) shift의 적대적 프레이밍 | Liu et al. (2009/2011, ACM CCS/TISSEC) — false data injection attack: 정상 상관구조를 보존하는 조작은 잔차 기반 탐지를 우회 |
| step/ramp 프로파일, 저 σ의 현실성 | 열전대 노화(기전력 손실→완만한 음의 drift)가 지배적 고장 양상, EGT 정확도 규격은 수 °C 수준 — 0729 §17.2 축 정의와 동일 |
| CUSUM/PCA 방법 자체 | 0729 계획 §10–11의 인용 앵커 (Page 1954; Moustakides 1986; Basseville & Nikiforov 1993; Hotelling 1947; Jackson & Mudholkar 1979; Qin 2003) |

> ✅ 서지 웹 검증 완료 (2026-08-04) → `docs/references_baselines.md` 생성됨.
> 잔여 확인 3건(EGT 규격 정식 인용원, 표현 계층 대표 후속 논문, FDIA 서지
> 페이지)은 논문 작성 전까지 — 해당 파일 말미 참조.

---

## 3. Detector 설계 (9 변형)

### 3.1 입력 표현 (공통, 표현 v2)

cycle당 decimated 전체 시계열 → 길이 50 sliding windows (N_c개)
→ window별 `FeatureExtractor` → **cycle 집계** →

| 입력 | 차원 | 내용 | 사용 detector |
|---|---:|---|---|
| `vec_xs` | 14 | window별 global z-score의 cycle 평균 (**X_s 14만, W 제외**) | *-Raw-Xs |
| `vec_xsw` | 18 | 〃 + W 4채널 포함 | *-Raw-XsW |
| `vec_regime` | 28 | window별 regime_z 14 + consistency_z 14의 cycle 평균 | *-Regime |

**(0804 반영 ③) 입력 사다리** — u14/15의 natural FPR을 3단으로 분해한다:

```text
Raw-XsW → W 채널 자체의 변화만으로 울림 (자명한 실패의 기록)
Raw-Xs  → W를 빼도 센서가 운항조건을 따라 움직여 울리는가? ← 핵심 검증 칸
Regime  → 조건화 후 조용한가?
```

"W를 입력에서 빼면 되지 않냐"는 반박을 Raw-Xs 칸이 직접 검증한다 — Raw-Xs가
여전히 울리면 "W 제거로는 부족, E[s\|W] 조건화 필요"가 빈틈없이 증명된다.

- 집계 규칙 기본 = window 평균 (대안 95-percentile은 Stage 2 synthetic 검증에서
  비교 후 확정 — 국소 fault에는 percentile이 유리할 수 있음).
- **(0804 반영 ②) N_c 교란 인지**: cycle 평균의 분산은 window 수 N_c에 반비례하고
  N_c는 Fc마다 다름(u11 ~22 vs u14 ~4) — u14의 FPR 상승이 분포 변화 때문인지
  표본 수 효과인지 분리 필요. **특징 정의는 왜곡 없이 유지**하고(스칼라 정규화는
  fault 신호까지 축소하므로 비채택), §4.5-6의 matched-count 진단으로 효과 크기를
  직접 측정한다.
- regime 조건화(E[s\|W_t])는 window 내 **timestep 단위**로 계산 후 잔차 평균 —
  상승/하강 window에서도 W가 함께 관측되므로 benign 변동은 잔차에 남지 않는다.
  ⚠ 단, 정적 W→X 맵은 과도 구간(상승/하강의 비정상 상태)에서 잔차가 커지고
  비행 구성이 Fc마다 다르므로(Fc1은 과도 구간 비중이 큼) **regime 잔차의 Fc 의존
  가능성**이 있음 — Stage 4에서 u14/15 regime FPR로 검증하고, 문제 시 완화책
  (W에 변화율 추가 또는 정상 상태 masking)을 후속 검토.
- 특징 모델은 clean TRAIN_UNITS로만 적합 — 기존 아티팩트는 삭제되어 **Stage 1
  ①에서 재적합**하며, 적합 풀을 (구) 중앙 window 표본에서 **전체 비행 decimated
  timestep 풀로 확장**한다 (E[s\|W]의 운전 영역 커버리지 확보 — 표현 v2의 핵심
  이득. `core/preprocess.py`의 pooled 소스 수정 필요).

**입력별 역할 구분 (보고 시 라벨링 필수)**:

- **Raw-Xs = 주 고전 baseline.** 탐지 대상이 센서 corruption이므로 센서만
  감시하는 순수형. `feature_models.npz`에서 ch_mean/ch_std(표준화 상수)만 사용 —
  중립 전처리이며 에이전트 도구와 무관. "기존 방법의 성능" 주장은 이 그룹이 담당.
- **Raw-XsW = 부가 변형.** 모든 측정 변수를 감시하는 전통 MSPC 관행 대표.
  u14/15에서 W 채널만으로 울리는 자명한 실패를 기록하는 사다리 1단.
- **Regime 변형 = our-feature 통제 변형 (0729 §18.4).** 에이전트의 Tier-1 피처
  (regime_z/consistency_z)를 고전 detector에 그대로 주는 통제 실험 — LLM 이득의
  원인 귀속(피처 vs 추론) 담당. 결과표에서 "기존 baseline"이 아니라
  **"+our-features control"로 명시**하고 Raw 그룹과 분리 표기한다.
- **핵심 비교 = Raw-Xs vs Regime** (conditioning 효과의 실증 축).

### 3.2 CUSUM (Page 양방향, per-channel)

\[
S_{t,j}^+=\max(0,\,S_{t-1,j}^+ + z_{t,j}-k),\qquad
S_{t,j}^-=\max(0,\,S_{t-1,j}^- - z_{t,j}-k),\qquad
S_t=\max_j\max(S_{t,j}^+,S_{t,j}^-)
\]

- \(k=0.5\) (σ 단위, `config.CUSUM_K`) — 탐지 목표 shift ≈ 2k=1σ에 해당하는 표준 설정.
- 누적은 유닛 수명 시작 cycle부터, 수명 내 reset 없음.
- 통계량 \(S_t\)가 임계 \(h\) 초과 시 raw alarm. \(h\)는 §4.2 공통 캘리브레이션.
- 발화 채널 argmax를 기록 (fault isolation 분석용, 0729 §18.5-8).

### 3.3 PCA-T²/SPE

- clean TRAIN_UNITS의 per-cycle 입력 벡터로 PCA 적합, 주성분 수 = 누적 분산 90%
  (`ev_target=0.90`; 민감도는 §6에서 95%와 병행 확인).
- \(T^2=t^\top\Lambda^{-1}t\) (부분공간 내부), \(SPE=\|x-PP^\top x\|^2\) (부분공간 밖) —
  하나의 PCA에서 나오는 두 통계량, **별도 alarm 시리즈로 각각 보고** (T²/SPE의 담당
  shift가 다르므로 합치면 blind spot 분석이 흐려짐).
- 채널별 SPE contribution 기록 (isolation 분석용).

### 3.4 구현 공신력과 검증 계획

- 구현은 본 프로젝트의 자체 코드다(`baselines/{cusum,pca}/core.py`). 이는 이 분야의
  표준 관행이다 — **T²/SPE 모니터링·다채널 CUSUM을 제공하는 지배적 파이썬
  라이브러리는 없으며**(sklearn은 PCA까지, river는 PageHinkley/ADWIN까지),
  논문 대부분이 sklearn 위에 T²/SPE를 자체 구현한다. 코드-수식 대응은 확인됨:
  CUSUM은 Page(1954) 양방향 정의식, PCA는 Jackson & Mudholkar(1979) T²/SPE 정식.
- **표준형 확인**: CUSUM 갱신식은 Page(1954) tabular two-sided 표준형 그대로,
  k=0.5는 Montgomery SPC 교과서 기본값(k=δ/2, 1σ shift 탐지 설정). PCA는 표준화
  입력의 상관행렬 PCA + Hotelling T²의 부분공간형 + Jackson–Mudholkar Q 정식.
  주성분 수 90% 누적분산은 MSPC 관행 기준.
- **논문에 공개할 설계 선택 (오류 아님, 표준 변형)**:
  ① 다채널 집계 = per-channel CUSUM 뱅크의 max (정본 다변량형은 MCUSUM,
  Crosier 1988 — 채널 isolation을 위해 뱅크 방식 선택; max 통계량에 분위수
  캘리브레이션을 하므로 다중비교는 자동 처리);
  ② T²/SPE 임계값 = 이론 한계(T²의 F-분포, SPE의 Jackson–Mudholkar/Box 근사)
  대신 u20 경험 분위수 — 공통 FA 예산 프로토콜용 의도적 선택, 이론 한계는
  참고치로 병기;
  ③ 모니터링 단위 = cycle window-mean (SPC의 부분군 평균, x̄-chart 논리);
  ④ 수명 내 alarm 후 무reset — latency 벤치마크 목적, SAT 규칙(§4.3)으로 대체.
- **Stage 2 검증 절차 (구현 신뢰성 확보)**:
  1. *Synthetic sanity test*: 백색잡음 + 알려진 크기·시점의 mean shift 합성 시계열에서
     (a) shift 없을 때 FA율이 설정 분위수와 일치, (b) k=0.5에서 1σ shift 탐지,
     (c) PCA에서 loading 방향 shift는 T²만·직교 방향 shift는 SPE만 발화하는지 확인.
  2. *교차검증*: 동일 입력에 대해 CUSUM 통계량을 R `qcc` 패키지(SPC 표준 구현)
     출력과 대조. PCA T²/SPE는 수식이 닫힌형이라 손계산 소규모 케이스로 대조.
  3. 검증 스크립트를 `baselines/tests/`에 저장해 재현 가능하게 유지.

### 3.5 변형 9종 정리

| detector | 입력 | 통계량 |
|---|---|---|
| CUSUM-Raw-Xs / -Raw-XsW / -Regime | vec_xs 14 / vec_xsw 18 / vec_regime 28 | max two-sided CUSUM |
| PCA-T²-Raw-Xs / -Raw-XsW / -Regime | 〃 (PCA는 입력별 별도 적합) | T² |
| PCA-SPE-Raw-Xs / -Raw-XsW / -Regime | 〃 | SPE |

- threshold는 9변형 × 2뷰 = 18개, 전부 §4.2 동일 규칙.

---

## 4. 공통 평가 프로토콜

### 4.1 케이던스 — 이중 보고 (0804 확정: 베이스라인 핸디캡 방지)

3-cycle 케이던스의 출처는 **LLM의 호출 비용 제약**이며, CUSUM/PCA는 매 cycle
평가가 공짜다(실전 배치 CUSUM의 자연 운용 모드). 베이스라인을 LLM 케이던스에
묶으면 latency가 3-cycle 격자로 뭉개져 향후 "LLM latency 우위" 주장에 strawman
비판이 성립한다. → 통계량은 매 cycle 계산하고 **같은 score에서 두 뷰를 도출**:

```text
[Native 뷰]   매 cycle 평가 → 2 cycle 연속 초과 → confirmed
              = 본 0804 실험의 주 결과 (베이스라인 최상 운용 모드)
[비교 뷰]     3 cycle 결정 포인트 평가 → 2포인트 연속 초과 → confirmed
              = 후속 LLM 비교 전용 (LLM-베이스라인 비교표는 이 뷰만 사용)
두 뷰 모두 raw / hysteresis 병행 보고. hysteresis 추가 지연: 첫 raw exceedance
대비 최소 +1 cycle(Native) / +3 cycles(비교 뷰) — "연속 2회"의 두 번째 평가
포인트에서 확정되므로. 비교 뷰는 onset–결정 grid 위상에 따라 0~2 cycle 추가 변동.
```

### 4.2 Threshold 캘리브레이션 (0729 결정 1의 케이던스별 적용)

- **FA 예산의 정의 (0804 확정): "FA ≤ 1회/100 cycles"는 raw-alarm 기준이다.**
  분위수 캘리브레이션이 통제하는 것은 평가 포인트당 raw alarm 확률(3%/1%)이며,
  hysteresis를 거친 confirmed alarm의 실현 FA는 이보다 훨씬 낮다(독립 근사
  ~0.09%/포인트) — 결과표의 confirmed FA가 예산 수치보다 작게 나오는 것은
  mismatch가 아니라 층위 차이임을 논문에 명시.
  (confirmed 기준 역산 캘리브레이션은 u20 66 cycle에서 confirmed 오탐 이벤트가
  0~1개라 식별 불가 — 의도적으로 채택하지 않음.)
- 동일 FA 예산을 각 뷰의 케이던스로 환산해 **뷰별로 별도 캘리브레이션**:
  Native 뷰 q = 1 − 1/100 = **0.99** (u20 per-cycle 66점),
  비교 뷰 q = 1 − 3/100 = **0.97** (u20 결정 포인트 ~22점).
- **실현 FA 검증**: 캘리브레이션 후 u20을 전체 파이프라인(케이던스→hysteresis→
  전이 계수)에 통과시켜 detector·뷰별 실현 FA를 **raw / confirmed 양쪽으로 측정해
  보고** — "정하는 것은 raw 기준, 확인은 양쪽 다" (Stage 2 제출물에 포함).
- 전 detector 동일 규칙. test label로 threshold 선택 금지.
- 한계 명시: 두 뷰 모두 분위수가 상위 1~2번째 값 근처의 얇은 표본 —
  부트스트랩 CI 병기 (0729 §18.5-5). CI는 point가 아닌 **block bootstrap**
  (CUSUM 통계량은 누적형이라 이웃 포인트 간 자기상관 — 점 단위 재표집은
  CI를 과소평가).
- **threshold 안정성 진단 (0804 2차 검토 — "남은 최대 통계 리스크")**: u20 66점의
  q=0.99는 사실상 최대값 1개로 결정되는 극단 분위수. 공식 캘리브레이션은 u20으로
  유지하되(전체 cross-fitting 공식화는 비채택 — train unit은 특징 적합에 사용되어
  in-sample 점수가 낮게 편향), **안정성 검증을 병행**: u20에서 정한 threshold를
  train unit(u2/5/10/16/18) clean 시퀀스에 적용해 unit별 raw/confirmed FA/100cyc
  표 작성 + u20 분위수가 train unit 분포 대비 극단인지 확인(in-sample 편향은
  주석으로 명시). Stage 2 제출물 포함. 논문 한계 문구: "Threshold calibration
  relied on one held-out unit; threshold stability was additionally examined
  across clean training units."

### 4.3 감지 크레딧과 SAT (0729 결정 7 + 0804 개정: SAT = primary 실패 + paired-clean 유효성)

- **(0804 3차 검토 — paired-clean counterfactual) 유효 탐지 정의**: N-CMAPSS는
  run-to-failure라 clean 궤적 자체도 수명 후반에 자연 열화로 알람을 낼 수 있다 —
  "onset 이후 첫 off→on"만으로는 자연 열화 알람이 fault 탐지로 오크레딧된다
  (저σ·ramp40 등 늦게 잡히는 핵심 셀에서 오염 최대). 따라서 각 corrupted
  시나리오를 **동일 unit clean 궤적(ctrl)과 짝지어** 평가한다:
  \(T_{\mathrm{fault}}\) = corrupted의 첫 confirmed alarm(off→on),
  \(T_{\mathrm{clean}}\) = 동일 detector·동일 뷰의 clean 궤적 첫 confirmed alarm
  (clean이 끝까지 안 울리면 수명 종료 시점으로 censoring).
  **유효 탐지 = \(c_0 \le T_{\mathrm{fault}} < T_{\mathrm{clean}}\)**.
  \(T_{\mathrm{fault}} \ge T_{\mathrm{clean}}\)이면 fault가 아닌 자연 열화를 잡은
  것 → 상태 `no_effect`(실패 계상). 비용: detector가 결정적이고 §5가 ctrl 포함
  전 시나리오의 per-cycle score를 로깅하므로 \(T_{\mathrm{clean}}\)은 재실행 없이
  산출 가능.
- pre-onset부터 confirmed alarm이 지속된 채 onset을 넘는 시리즈는 **SAT** 표기.
  해당 오탐은 FPR에 계상. (natural 유닛 위 raw 변형에서 발생 예상 — 이것 자체가
  결과다.)
- **(0804 개정) SAT의 지표 처리**: SAT를 분모에서 제외하면 "항상 울리는 detector"의
  성적이 미화된다(예: 10개 중 8개 SAT + 2개 탐지 → 제외 방식으로는 감지율 100%).
  → **primary 지표에서는 SAT를 실패로 계상**하고, SAT-제외 지표는 진단용 보조로
  강등한다 (§4.4).
- **(0804 2·3차 검토) 시나리오 상태 5분류**: detected/SAT/miss 3분류는 "pre-onset
  오탐 발생 → off 복귀 → onset 후 재탐지" 케이스와 "자연 열화 알람" 케이스를
  표현하지 못한다. 상태를 `clean_detected / preFA_then_detected / no_effect /
  SAT / miss`로 확정 (유효 탐지 조건은 위 paired 정의 적용):
  `clean_detected` = pre-onset 무알람 + 유효 탐지; `preFA_then_detected` =
  pre-onset 오탐 후 복귀 + 유효 탐지 (operational **실패**, conditional **성공
  포함** — 포화만 아니면 탐지력 있음의 진단 목적); `no_effect` = corrupted 알람이
  clean보다 빠르지 않음(operational·conditional 모두 실패); `SAT` = pre-onset부터
  지속 알람; `miss` = onset 이후 유효 알람 없음. u14/15 기반 시나리오·raw 변형에서
  preFA/SAT 실제 등장 예상(§7 FA 다발 셀).

### 4.4 지표 정의

| 지표 | 정의 |
|---|---|
| **★ Operational detection rate (primary)** | (pre-onset 동안 clean 유지 **그리고** onset 후 **유효 탐지**(paired 조건 \(c_0 \le T_{fault} < T_{clean}\), §4.3) 성공한 시나리오 수) / (**전체** fault 시나리오 수). **SAT·miss·no_effect 모두 실패로 계상.** block×σ별 집계 |
| Conditional detection rate (보조) | SAT 제외 조건부 감지율 (구 event detection) — "포화되지 않았을 때의 탐지력" 진단용. **preFA_then_detected는 성공에 포함**(§4.3 — 정의 명시), SAT율·preFA율은 별도 열 병기 |
| **Detection latency** | (첫 confirmed alarm의 cycle) − (onset cycle). 단위: cycles. raw alarm 기준 latency도 병기 (hysteresis가 더하는 지연 — 첫 raw exceedance 대비 **최소** Native +1 cycle / 비교 뷰 +3 cycles; 두 번째 포인트에서 통계량이 threshold를 하회하면 연속 카운트 리셋으로 더 늘어남 — 을 raw vs confirmed latency 차이로 실측 확인. 비교 뷰는 onset–grid 위상에 따른 0~2 cycle 추가 변동 있음). 뷰별 보고. **conditional latency(성공 시나리오만)임을 명시** — 생존 편향 보정은 아래 penalized delay(0804 2차 검토에서 채택 확정, 구 검토 목록 ⑦) |
| Penalized delay (보조) | \(D_{pen}\) = latency(성공 시) / \(H\)(miss·SAT 시), \(H\) = onset 이후 남은 평가 horizon(= life − onset_cycle, 뷰별 평가 포인트 단위) — miss/SAT 제외로 latency가 좋아 보이는 생존 편향 보정. conditional latency와 병기 |
| **Alarm advance (0804 3차 검토)** | \(T_{clean} - T_{fault}\) (단위: cycles, clean 무알람 시 censoring 표기) — fault 주입이 자연 열화 대비 알람을 얼마나 앞당겼는가. 유효 탐지 시나리오에서 latency와 병기; 보조로 \(\Delta S_t = S_t^{fault} - S_t^{clean}\) score 차이 곡선(§5 로깅에서 사후 산출) |
| **Pre-onset FPR** | 주입 시리즈의 onset 이전 평가 포인트(뷰별: cycle 또는 결정 포인트) 중 alarm 비율 |
| **Clean FA/100 cycles** | ctrl_u11/14/15에서 100 cycle당 confirmed alarm의 **off→on 전이 횟수** (지속 알람을 매 포인트 재계상하지 않음 — §4.3과 동일 원칙) |
| **Natural-unit FPR** | ctrl_u14/15 한정 FPR (benign 오탐 — Raw vs Regime 핵심 비교축) |
| **SAT 표기** | SAT 시리즈 수 / 전체 (detector별) |

latency 보조 지표(선택): ramp 시나리오에서 "주입 크기가 0.5σ에 도달한 시점" 기준
latency 병행 (느린 ramp에서 onset 기준 latency의 왜곡 보정, 0729 §18.5-7).

### 4.5 산출물

1. **per-scenario 결과표** (CSV/MD): scenario × detector → 상태 5분류(§4.3:
   clean_detected/preFA_then_detected/no_effect/SAT/miss), \(T_{fault}\)/\(T_{clean}\)/
   alarm advance, latency(raw/hyst), pre-onset FPR
2. **σ-detection coverage 절벽 그림**: Block A에서 detector별 감지 vs σ (핵심 그림).
   σ당 방향 ± 2개 시나리오뿐이라 값이 {0, 0.5, 1}로 이산적 — population recall
   곡선처럼 보이는 연속 곡선 대신 **방향별 성공/실패 marker + coverage 요약선**으로
   표현 (0804 2차 검토: 용어도 recall 대신 scenario-level detection coverage 사용)
3. **latency 곡선**: σ별·profile별 latency 분포
4. **blind spot 매트릭스**: block × detector 히트맵 (§7 예상표와 대조)
5. **입력 사다리 대비표**: Raw-XsW → Raw-Xs → Regime의 natural-unit FPR +
   Block F 성적 (conditioning 효과 실증 — 핵심 비교는 Raw-Xs vs Regime)
6. **matched-count 진단 (②)**: u11 특징을 cycle당 4개 window만으로 재계산 →
   u11 clean FPR의 변화량 = "window 수 효과"의 크기. u11(4win) vs u14(4win)의
   동등 조건 natural-FPR 로버스트니스 표 병기 — u14 FPR 초과분이 window 수
   효과보다 크면 진짜 분포 변화 증명. **4-window 선택 규칙(0804 2차 검토)**:
   단일 임의 선택은 우연성이 큼 → cycle마다 N_c개 중 4개 **비복원 random
   subsampling을 seed 10개로 반복**, FPR 평균·표준편차·범위 보고

---

## 5. 저장·재현성 규칙

- **매 cycle**마다 9개 detector의 정규화 score 벡터를 공통 스키마로 저장
  (`results/scores/<scenario_id>.npz`) — 0729 결정 14. per-scenario 요약에는
  상태 5분류(§4.3)와 boolean 4필드(`had_pre_onset_alarm, detected_after_onset,
  sat, operational_success`) + `t_fault, t_clean`(paired 평가용, §4.3)을 함께
  저장 (0804 2·3차 검토). per-cycle로 저장해야
  §4.1의 두 케이던스 뷰를 재실행 없이 사후 도출 가능. 이후 OC-MLP/ContextMMD/
  D3/GDN/LLM 단계가 같은 스키마에 append하고, fusion이 필요해지면 재실행 없이 가능.
- spec.json/결과에 git hash 스탬프 (0729 §18.5-9).
- 난수는 전부 seed 고정 (noise 주입, PCA SVD는 결정적).

---

## 6. 하이퍼파라미터 방침

| 항목 | 1차 값 | 민감도 확인 |
|---|---|---|
| CUSUM k | 0.5 | {0.25, 0.5, 1.0} — u20에 주입한 튜닝 전용 fault로만 (test 유닛 불사용) |
| PCA ev_target | 0.90 | {0.90, 0.95} |
| FA budget | 1회/100cyc | 부록: q ∈ {0.5, 1, 2, 5}로 detection-rate-vs-FA 곡선 (0729 §18.5-3) |
| HYST_N | 2 | 고정 (raw 병행 보고로 대체) |

민감도 스윕은 Stage 4의 부록 항목 — 본 결과는 1차 값으로 고정 보고 (사후 튜닝 의심 차단).

---

## 7. 예상 결과 (사전 등록 — 실험 후 이 표와 대조)

| Block | CUSUM-Raw | CUSUM-Reg | T²-Raw | T²-Reg | SPE-Raw | SPE-Reg |
|---|---|---|---|---|---|---|
| A 저σ(0.15–0.35) | ✗ | **?** 핵심 셀 | ✗ | ✗ | ✗ | **?** |
| A 중고σ(0.5–2) | ○ | ○ | △ | △ | ○ | ○ |
| B ramp40 | △ 늦음 | ○ 누적 강점 | ✗ | ✗ | △ | △ |
| C temp4-mix | △ | ○ | △ | △ | **○ 강점 축** | ○ |
| D PC1/all14 | ✗~△ | ✗~△ | **○ 담당** | ○ | **✗ 사각 실증** | ✗ |
| E gain | ○ | ○ | △ | △ | ○ | ○ |
| E noise | **✗ 원리적 비가시** | ✗ | ✗ | ✗ | ✗ | ✗ |
| E stuck | ✗~△ (동결 z가 0 근처면 ✗) | △ (W 변동 시 잔차 발생) | ✗ | ✗ | △ **늦게** (동결 vs 타채널 괴리) | △~○ (consistency 붕괴) |
| F natural+fault | **SAT 예상** | ○ | SAT | △ | SAT | △ |
| ctrl u14/15 | FA 다발 (기존 실측 22–25회) | 낮음 | FA | 낮음 | FA | 낮음 |

- 표의 Raw 열은 Raw-XsW 기준. **Raw-Xs의 예상 (사전 등록)**: Block A–E(u11)에서는
  W 채널 기여가 원래 작아 Raw-XsW와 사실상 동일; ctrl u14/15와 Block F에서는
  W 채널의 자명한 FA는 빠지지만 **센서 자체가 운항조건을 따라 움직이므로 여전히
  FA/SAT 발생 예상** — 이 칸이 그대로 나오면 "W 제거로는 부족, 조건화 필요"가
  실증된다 (§3.1 사다리의 핵심 검증 칸).

- **noise 비가시의 원인**은 detector가 아니라 **입력 표현**(window-mean 기반 z)이다 —
  "mean 기반 고전 파이프라인의 구조적 사각지대"로 문서화하고, 분포·temporal 계열
  (ContextMMD/GDN)의 필요 근거로 사용한다. seeds 3개(§2.4)로 "감지율 0이 seed
  요행이 아님"까지 실증.
- **stuck 예상의 단서**: last-value 정의(§2.2)상 동결값은 직전 cycle **하강/착륙
  구간** 값이라 순항 구간 값과 괴리가 커, flatline이 표의 예상(✗~△)보다 잘 보일
  수 있다 — 상향되어 나오면 "동결 기준 시점의 물리적 위치" 효과로 해석.
- 예상과 다른 셀이 나오면 그것이 발견이다 — 표를 실험 전에 고정해 confirmation bias 차단.
- **난이도 판정 기준 (0804 개정: test-tuning 금지)**: 목표는 절벽을 걸치는 스펙트럼 —
  2σ step은 전원 탐지(sanity), 0.5~1σ는 detector별 분기(변별 구간), 0.15~0.35σ·
  PC1·noise·ramp40은 대부분 실패(추후 LLM 비교의 무대). 근거: 기존 파일럿 실측 —
  절벽 실재(저 cons에서 감지율 0), 1σ ≈ 28°C로 물리 현실 크기(수 °C)는 절벽 아래.
  **난이도 확인·조정 규칙**:
  ① σ 그리드의 적정성 판단은 **dev 쪽 증거로만** — Stage 2의 synthetic 테스트와
  u20 튜닝 전용 fault로 절벽 위치를 사전 확인하고, 필요 시 그리드를 조정한 뒤
  **Stage 3 전에 벤치마크를 잠근다(lock)**.
  ② **Stage 3(test) 결과를 보고 시나리오·σ·onset을 재조정하는 것은 금지** —
  test-set tuning에 해당. 전부 쉽거나 전부 어렵게 나와도 그대로 보고한다
  (그것도 결과다).
  ③ 사후에 시나리오를 추가하고 싶으면 가능하되 **"추가 탐색 실험"으로 분리
  표기**하고, 잠긴 50개 벤치마크의 수치는 수정하지 않는다.
  ④ **(본 메소드 단계 확장 — 사전 등록)**: 후속 LLM 에이전트의 프롬프트·구조·
  하이퍼파라미터 반복은 **devset(u20 주입 시나리오)로만** 수행한다. test 50개에
  대한 per-scenario 튜닝 금지; test 실행 전 메소드 동결 선언 후 **1회 실행**.
  (test 유닛이 잠긴 뒤 메소드가 test로 과적합되는 두 번째 누출 경로 차단 —
  데이터셋 난이도 잠금(①~③)과 별개 축)

---

## 8. 실행 단계 (각 단계 종료 시 보고 → **컨펌 후 다음 단계**)

**Stage 0 — 사전 점검** (실행 없음에 준함: 읽기/검증만)
u11/14/15 수명·onset cycle·timestep 통계 산출표(1Hz 실측: Fc3 평균 ~11,200/cycle,
Fc1 ~2,100, Fc2 ~6,500), ch_std의 물리 단위 표 (σ→°R/psia 환산 — 재적합 후 확정),
**window 기준 W의 cycle 간 분산 실측** (between-flight OC 변동 생존의 수치 증거,
유닛·Fc별), **train–test W support 겹침 진단 (0804 2차 검토)**: W 4변수의
train(Fc3) vs u14(Fc1)/u15(Fc2) min–max·분포 겹침과 train support 밖 test 비율
측정 — regime 모델 \(E[X_s|W]\)의 extrapolation 여부 판정. Stage 4 해석 축:
support 밖+Regime FPR↑ = extrapolation 한계 / support 안+FPR↑ = 모델 구조 문제 /
support 밖+FPR 낮음 = 일반화 근거. 서지 재확인 → `references_baselines.md` 초안.

**Stage 1 — 데이터셋 빌더 신규 작성 + 데이터셋 구축**
`baselines/`·`injection/` 삭제에 따라 **전면 신규 작성** (구 코드는 git 이력과
예비 결과 json으로만 참조). 신규 레이아웃:

```text
injection/
  engine.py          # 순수 주입 수학 (§2.2가 명세): FaultSpec 데이터클래스,
                     # mode add/gain/noise/stuck, profile step/ramp15/ramp40,
                     # PC1 방향 주입, seed 규율. torch·RUL모델 무의존 —
                     # 이후 OC-MLP/GDN/LLM 단계도 같은 엔진 재사용
  build_dataset.py   # §2.4 인벤토리 50개 조립: engine.py 호출 + corrupted_dataset
                     # 저장(npz/spec.json/manifest) + preview 그림  [Stage 1]
baselines/
  common.py          # 공통 프로토콜: 뷰별 threshold 캘리브레이션(Native q=0.99 /
                     # 비교 뷰 q=0.97, §4.2), hysteresis, paired-clean 유효 탐지·
                     # SAT·상태 5분류 판정(§4.3),
                     # off→on 감지 크레딧, score 로깅 스키마(§5)
  cusum/core.py      # §3.2 표준형 CUSUM
  pca/core.py        # §3.3 PCA T²/SPE
  run_experiment.py  # 9변형 실행 + §4 지표 + 결과표            [Stage 2–3]
  tests/             # §3.4 검증 (synthetic sanity + 교차검증)
```

역할 분리 원칙: `injection/`은 데이터셋 생산(주입 수학 + 인벤토리·저장),
`baselines/`는 소비(detector·프로토콜·평가) — 후속 단계(딥 detector·LLM)가 동일
데이터셋 생산 계층 위에서 확장할 수 있게 한다.

Stage 1 작업 순서 (의존성 순):
① **표현 v2 window화 계층** — `core/data_ncmapss.py`에 전체 비행 decimated
   시계열 로드 + sliding window 유틸 반영 (구 중앙-window 로직 대체).
② **특징 통계 재적합** — 삭제된 `feature_models.npz`를 clean train units(u2/5/10/
   16/18)의 **전체 비행 timestep 풀**로 재생성 (`preprocess.py` pooled 소스 확장
   포함). ch_std(σ 주입 단위·Raw 표준화)와 regime/consistency 회귀가 여기서
   나오므로 주입보다 선행. **가중 정책 명시(0804 2차 검토)**: 풀은 timestep-level
   가중(비행이 길거나 cycle이 많은 unit이 비례적으로 더 기여) — unit-balanced
   재가중은 비채택하되 정책을 명시하고, unit별 timestep 수·기여율 표를 재적합
   통계 요약에 포함.
③ `injection/engine.py` 작성 (§2.2 수식, **native 1Hz 시계열 대상** — 주입 후
   decimation은 build_dataset 단계).
④ `injection/build_dataset.py` 작성 → 50개 시나리오 생성
   (`dataset/corrupted_dataset/` 계층 + manifest.csv, §2.1 스키마)
   + **devset 3~5개**(u20, add×T48 중심, 예: 0.5/1.0σ ramp15 ± + step 1개 —
   DEV 라벨, manifest에 `split=dev` 표기, 벤치마크 50개와 분리 집계).
→ **재적합 통계 요약 + preview 그림 + manifest.csv 제출 → 컨펌**.

**Stage 2 — detector·프로토콜 신규 작성 + 검증 + 캘리브레이션 + 벤치마크 잠금**
`common.py`/`cusum/core.py`/`pca/core.py`/`run_experiment.py` 작성 (§3.2–3.3
표준형 그대로) → **§3.4 검증 절차 실행** (synthetic sanity + 교차검증, 결과를
`baselines/tests/`에 보존) → u20 캘리브레이션 + **실현 FA 검증(§4.2)** +
**threshold 안정성 진단(§4.2 — train unit clean FA 표 + u20 극단성 확인)**
→ **난이도 사전 확인(§7 규칙 ①)**: u20 튜닝 fault로 절벽 위치 확인, 필요 시
σ 그리드 조정 → **벤치마크 잠금** (이후 Stage 3 결과 기반 수정 금지)
→ **검증 결과 + threshold 값 + 실현 FA + u20 통계량 분포 그림 + 잠금 선언 제출
→ 컨펌**.

**Stage 3 — 본 실험**
50 시나리오 × 9 detector 실행 → per-scenario 결과표 + §4.5 산출물 1–6 생성.

**Stage 4 — 분석 보고**
§7 예상표와 대조한 blind spot 분석, σ 절벽 위치, latency 요약, Raw-vs-Regime
conditioning 효과 정리 → `results/0804_report.md`. (부록: §6 민감도 스윕)

예상 소요: Stage 1–2가 코드 작업의 대부분, Stage 3은 계산 몇 분 수준 (전부 CPU 통계
연산, LSTM/GPU 불필요).
