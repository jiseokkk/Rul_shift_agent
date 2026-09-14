# 사전 준비 최종 계획서 (Phase A–D)

버전: 2026-09-15 v2 (리뷰 반영 통합본)
대체하는 문서: `preparation_plan.md` v1, `folder_structure.md` v1
참조: `research_design.md`, `two_phase_rul_execution_guide.md`
범위: LLM 에이전트 실험 이전에 끝나야 하는 분할 → clean 학습 → shift 주입 → 추론 → 성능 저하 라벨링

상태 표기: ✅ 확정 · 🔶 파일럿(Phase D-2) 후 확정 · ❓ 에이전트 단계에서 결정

---

## 0. 한 장 요약

```
Phase A  분할       train_FD001 (100 unit) ─층화─▶ train 80 / holdout 20
Phase B  clean 학습  train 80 ─▶ 사전학습 ─▶ 미세조정 ─▶ f (고정)        ×3 seed
                     f + test_FD001 ─▶ RMSE 재현 확인
                     f + holdout 20 (clean) ─▶ ŷ_clean (cycle 45~T_u)
Phase C  주입·추론   holdout 20 × 시나리오 ─▶ X̃ (원본 스케일 주입) ─▶ f ─▶ ỹ_shift
Phase D  라벨링      δ = |ỹ − ŷ| ─▶ 분포 분석 ─▶ θ·k·m 확정 ─▶ 히스테리시스 라벨
```

**세 원칙**
1. 모델은 clean으로만 학습한다. 주입본은 추론에만 쓴다.
2. 라벨은 정답 RUL이 아니라 같은 모델의 clean 예측과의 차이(counterfactual delta)로 만든다.
3. 라벨은 오프라인 정답이므로 비인과적으로(미래 정보를 써서) 정의해도 된다. 에이전트는 인과적으로 판단한다.

---

## 1. 폴더 구조 ✅

```
agent_RUL/
├── external/RUL/                   # 원본 clone. 수정 금지. commit hash 기록
│
├── src/
│   ├── data/
│   │   ├── cmapss.py               # txt 로드, 컬럼 상수 RAW_COL={'T24':6,'T30':7,'T50':8,...}
│   │   ├── split.py                # 층화 hold-out
│   │   ├── loaders.py              # CMAPSSDataset_pre/ft 복사 → exclude_units, 고정 정규화, test 제외
│   │   └── shift.py                # 6 유형 주입 (원본 스케일)
│   ├── model/
│   │   ├── nets.py                 # Transformer_pre + Transformer_ft 모델 정의 통합
│   │   ├── train_pre.py
│   │   ├── train_ft.py
│   │   ├── evaluate.py             # test_FD001 RMSE/Score
│   │   └── infer_full.py           # 전 cycle 슬라이딩 추론 (clean/shift 공용)
│   ├── label/
│   │   ├── delta.py
│   │   ├── variability.py          # V1 인접 변화량, V2 seed 편차
│   │   ├── hysteresis.py           # k-of-m 상태 머신 + 역방향 채우기
│   │   └── build_labels.py
│   └── analysis/
│       ├── delta_dist.py
│       └── label_summary.py
│
├── configs/
│   ├── paths.yaml                  # raw 데이터 경로 등 (심볼릭 링크 대신)
│   ├── model_FD001.yaml
│   ├── shift_grid.yaml
│   ├── label.yaml                  # θ 3종·k·m·θ_low 비율. D-2 후 확정값 기록
│   └── agent.yaml                  # N=10 (t0 계산에 필요해 여기 둠)
│
├── scripts/                        # 전부 .py (OS 무관)
│   ├── 00_reproduce_original.py    # external/RUL 그대로 실행 → 11.85 확인
│   ├── 01_split.py
│   ├── 02_train_pre.py
│   ├── 03_train_ft.py              # --seed 루프
│   ├── 04_evaluate.py
│   ├── 05_infer_clean.py
│   ├── 06_inject_infer.py          # scenario_index 메타 컬럼 작성
│   ├── 07_delta_analysis.py
│   └── 08_build_labels.py          # scenario_index 결과 컬럼 추가
│
├── tests/
│   ├── test_hysteresis.py          # 진입·복귀 경계, 역방향 채우기
│   ├── test_shift.py               # τ_s 이전 불변, 크기 α·σ_r
│   └── test_infer_determinism.py   # 같은 입력 두 번 → 완전 일치
│
├── data/
│   ├── split/split_FD001.json
│   ├── norm/
│   │   ├── norm_params_pre_FD0013.npy   # 사전학습용 (FD001 80 + FD003 train)
│   │   └── norm_params_ft_FD001.npy     # 미세조정·추론용 (FD001 80)
│   └── shifted/FD001/u{unit}/{scenario_id}.parquet
│
├── models/FD001/
│   ├── pre_FD0013_holdout.pt
│   ├── ft_s529.pt  ft_s530.pt  ft_s531.pt
│   └── reproduce_metrics.json      # seed별 RMSE/Score + external/RUL commit hash + torch 버전
│
├── preds/FD001/
│   ├── clean/s{seed}/u{unit}.parquet            # [time, pred, rul_true]
│   └── shift/s529/u{unit}/{scenario_id}.parquet # [time, pred]
│
├── labels/FD001/
│   ├── meta/clean_variability.json
│   ├── delta/u{unit}/{scenario_id}.parquet      # [time, pred_clean, pred_shift, delta]
│   ├── state/{theta_name}/u{unit}/{scenario_id}.parquet   # [time, delta, label, state]
│   └── scenario_index.csv                       # long format, θ 컬럼 포함
│
├── reports/
│   ├── A_split_summary.md
│   ├── B_reproduction.md
│   ├── D_delta_distribution.md
│   └── D_label_summary.md
│
├── docs/
├── .gitignore
├── requirements.txt                # torch 버전 고정
└── README.md
```

**묶음 설명**
- `external/RUL`: 원본. 재현 확인과 코드 복사 참조용. `reproduce_metrics.json`에 commit hash 기록
- `src/`: `data`(모델 모름) → `model`(shift 모름) → `label`(모델 모름) → `analysis`. 각 폴더는 앞 단계 산출물만 읽음
- `configs/`: 모든 숫자. `label.yaml`은 재현의 핵심. `agent.yaml`의 N이 t0을 결정하므로 준비 단계에서도 읽음
- `scripts/`: 번호 순 실행. `src/` 함수를 인자만 넣어 호출하는 껍데기
- 데이터 흐름: `data/`(입력) → `models/` → `preds/`(출력) → `labels/`(출력 비교). 에이전트 단계는 `preds/shift/`·`data/shifted/`(입력)와 `labels/state/θ_primary/`(채점)만 읽음

**파일 단위**: `data/shifted`, `preds`, `labels/delta`, `labels/state`는 `u{unit}/{scenario_id}.parquet` = 한 (엔진, 시나리오). 시나리오별 재실행·부분 추출 가능

**scenario_id** (5슬롯 고정, 빈 자리 `na`):
```
{type}_{sensor}_{param}_{dir}_p{timing}
bias_T24_a0.2_pos_p0.4
stuck_T30_na_na_p0.6
noise_T50_b1.0_na_p0.2
multiC_T24+T30+T50_a0.2_na_p0.8
```

**Git**: 코드·설정·문서·리포트 + `split_FD001.json`, `norm_params_*.npy`, `label.yaml`, `scenario_index.csv`, `clean_variability.json`, `reproduce_metrics.json` 포함. `external/`, `data/shifted/`, `preds/`, `labels/delta/`, `labels/state/`, `*.pt` 제외. **기준: 포함된 파일만으로 `scripts/`를 순서대로 돌려 같은 라벨을 재생성할 수 있어야 한다.**

---

## 2. Phase A — Hold-out 분할 ✅

**입력** `train_FD001.txt` → **출력** `data/split/split_FD001.json`, `reports/A_split_summary.md`

1. unit별 수명 T_u (FD001: 128~362, 중앙값 199)
2. T_u 오름차순 5분위 → 각 분위에서 4개 무작위 (seed 529) → hold-out 20
3. 나머지 80 = train
4. 기록: hold-out unit별 T_u, 시점별 τ_s (§4-2 공식), 포화 여부 예상(T_u − τ_s > 125)

**분할은 unit 단위.** hold-out unit은 1 cycle부터 고장까지 전체 궤적이 통째로 hold-out. 층화는 어느 unit을 뽑을지에만 관여.

**체크**: hold-out 20의 T_u 분포가 전체와 유사 (히스토그램 병기)

---

## 3. Phase B — Clean 학습 및 clean 예측 ✅

### B-0. 사전 확인 (코드 착수 전)
- `external/RUL`에서 원본 그대로 실행 → FD001 RMSE 11.85 / Score 214 근처 확인 (`scripts/00`). 안 나오면 여기서 멈춤
- `CMAPSSDataset_ft.py`의 17개 입력 구성 확인: op1~op3 + 14 센서(원본 컬럼 6,7,8,11,12,13,15,16,17,18,19,21,24,25). 내부 이름 `s1`~`s14`는 실제 s2~s21에 대응 (`s1`=T24)
- std=0 컬럼 확인: FD001에서 **op3가 상수(100.0)**. `z_score_normalization`은 `if standard != 0`로 나눗셈을 건너뜀. 체크리스트는 "std=0 컬럼이 op3뿐인지"

### B-1. 사전학습
- 데이터: FD001 train 80 unit + FD003 train 전체. **test 제외** (원본은 정규화 통계에 test 포함)
- FD003 id offset: 원본 `train_df.iloc[-1,0]` → `train_df[0].max()`로 수정 (hold-out에 unit 100이 있으면 원본 방식이 틀림)
- 정규화 통계 → `norm_params_pre_FD0013.npy`
- 20 epoch, seed 529 → `pre_FD0013_holdout.pt`

### B-2. 미세조정
- 데이터: FD001 train 80 unit. 정규화 통계 → `norm_params_ft_FD001.npy` **(이후 모든 추론의 기준)**
- encoder freeze, 200 epoch
- seed ∈ {529, 530, 531} → `ft_s{seed}.pt`. **라벨 생성 기준 모델 = seed 529**, 나머지는 변동성 추정용

### B-3. 재현 확인
- `test_FD001.txt` 원본 방식(마지막 window) 평가 → RMSE, Score, 3 seed 모두
- 기대 12~13 (학습 unit 20% 감소 + 정규화 변경). **15 초과 시 중단·원인 확인**
- `reproduce_metrics.json`에 seed별 수치 + `external/RUL` commit hash + torch 버전

### B-4. Hold-out clean 추론 + 검증
- `infer_full.py`: hold-out 20 × 3 seed, cycle 45~T_u 슬라이딩 → `preds/clean/s{seed}/u{unit}.parquet` [time, pred, rul_true]
- **결정성 검증**: 같은 입력 두 번 추론 → 완전 일치 (`model.eval()`, `torch.use_deterministic_algorithms(True)`). 실패 시 Phase D의 assert가 무의미하므로 반드시 통과
- **정합성 검증 1**: hold-out unit당 무작위 절단점 1개 → test와 같은 방식(마지막 window, RUL clip)으로 RMSE → test RMSE와 비교
- **정합성 검증 2**: 전 cycle RMSE를 RUL 구간별(0–25, 25–75, 75–125)로 보고

---

## 4. Phase C — Shift 주입 및 추론

### C-1. 주입 규격 ✅ (`src/data/shift.py`)

원본 스케일에서, τ_s 이후 cycle에만. 정규화는 `infer_full.py`가 `norm_params_ft_FD001.npy`로 처리.

| 유형 | 구현 | 파라미터 |
|---|---|---|
| bias | x(t) ← x(t) + d·α·σ_r | α, d∈{+1,−1} |
| stuck | x(t) ← x(τ_s) | — |
| noise | x(t) ← x(t) + ε_t, ε~N(0,(β·σ_r)²) | β, rng seed |
| gain | x(t) ← μ_r + (x(t) − μ_r)·(1 + d·α) | α, d∈{+1,−1} |
| multi_C | 센서 집합 S 각각 + sign_deg(s)·α·σ_r(s) | S, α |
| multi_I | 센서 집합 S 각각 + sign(s)·α·σ_r(s), sign 무작위 (rng seed) | S, α |

- **σ_r, μ_r**: `norm_params_ft_FD001.npy`의 std, mean과 동일값 (일관성)
- **gain 평균 중심**: 원식 x·(1+α)는 T24≈642K에서 α=0.1이 64K 이동 → bias와 구분 불가. 편차만 확대/축소해야 "변화폭 오차"의 의도에 맞음. 논문에 명시
- **sign_deg(s)**: train 80 unit에서 각 센서의 (수명 마지막 10% 평균 − 처음 10% 평균) 부호. 열화 시 증가하면 +
- **multi_I 부호 제약**: 무작위 부호 조합 중 **sign_deg와 −sign_deg는 제외** (전자는 열화, 후자는 회복처럼 보이는 일관 변화이므로 둘 다 multi_C 성격)
- **rng seed**: noise·multi_I는 시나리오별 seed를 parquet 메타와 index에 기록

### C-2. 주입 시점 ✅

```
τ_s = t0 + p · (T_u − t0),   p ∈ {0.2, 0.4, 0.6, 0.8}
t0  = 45 + N = 55            (N = 에이전트 window, configs/agent.yaml)
```

| T_u | 20% | 40% | 60% | 80% |
|---|---|---|---|---|
| 128 | 70 | 84 | 99 | 113 |
| 199 | 84 | 113 | 141 | 170 |
| 362 | 116 | 178 | 239 | 301 |

- 모든 unit에서 τ_s ≥ 55 → 에이전트는 최소 N=10 cycle의 clean 예측을 본 뒤 shift를 만남
- 라벨 k-of-m 판정(49부터 가능)도 τ_s 전에 정상 상태 확립
- "배포 첫날부터 고장" 시나리오는 범위 밖 (초기 상태 진단은 다른 문제). 논문에 한 줄 명시
- 포화 negative는 유지: T_u=362의 20% 지점 true RUL=246 (완전 포화), T_u=128은 58 (비포화). 20% 케이스 안에서 unit 길이별로 저하/비저하가 갈림
- N을 바꾸면 t0이 바뀌어 라벨 재생성 필요 → `configs/`에서 t0 = 45 + N 자동 계산

### C-3. 시나리오 grid 🔶 (`configs/shift_grid.yaml` 파일럿 초안)

```yaml
units: holdout 20
timing_p: [0.2, 0.4, 0.6, 0.8]
sensors_single: [T24, T30, T50]        # 원본 컬럼 6, 7, 8. 모두 모델 입력
types:
  bias:    {alpha: [0.1, 0.2, 0.3, 0.5], dir: [pos, neg]}
  gain:    {alpha: [0.1, 0.2, 0.3, 0.5], dir: [pos, neg]}
  noise:   {beta:  [0.5, 1.0, 2.0]}
  stuck:   {}
  multi_C: {sets: [[T24, T30, T50]], alpha: [0.2, 0.3]}
  multi_I: {sets: [[T24, T30, T50]], alpha: [0.2, 0.3]}
```

시나리오 수/unit: bias 24 + gain 24 + noise 9 + stuck 3 + multi 4 = **64 × 시점 4 = 256** → 20 unit = **5,120 추론**. GPU 수 분.

**미사용 센서 대조군은 제거.** FD001에서 모델 제외 7개 센서는 전부 상수/준상수(σ_r=0)이고, 에이전트 입력을 모델 입력 14개로 고정했으므로 에이전트가 볼 수 없어 대조군으로 성립하지 않음. negative 역할은 포화 구간·저강도 케이스가 담당. (21개 센서 입력 확장 실험 시 재도입 가능)

### C-4. 저장·추론·검증
- `data/shifted/FD001/u{unit}/{scenario_id}.parquet`: 원본 26컬럼 + 메타(τ_s, type, sensor, param, dir, rng_seed)
- `scripts/06`이 `scenario_index.csv`에 **메타 컬럼** 작성: unit, T_u, type, sensor, param, dir, timing_p, tau_s, rng_seed
- `infer_full.py`(seed 529) → `preds/shift/s529/u{unit}/{scenario_id}.parquet`
- **검증**: `tests/test_shift.py` — τ_s 이전 완전 불변, bias 크기 = α·σ_r, stuck 값 = x(τ_s). 추가로 임의 3개 시나리오 플롯 육안 확인

---

## 5. Phase D — 성능 저하 라벨링

### D-1. delta ✅
- δ(t) = |ỹ(t) − ŷ(t)|, t ∈ [45, T_u] → `labels/delta/...`
- **assert: τ_s 이전 δ == 0 (전 cycle).** 위반 시 중단. 원인은 (a) 주입이 τ_s 앞으로 샘 (b) 추론 비결정성. 강제로 0을 덮지 않음

### D-2. θ 후보 산출 🔶 (`labels/meta/clean_variability.json`)

| 수치 | 계산 | 용도 |
|---|---|---|
| V1 | \|ŷ(t) − ŷ(t−1)\| 분포 (seed 529, hold-out 20) | θ_primary |
| V2 | 3 seed 예측의 cycle별 표준편차 분포 | V1 교차 검증 |
| V3 | test RMSE (B-3) | θ_alt2 |

| 이름 | 정의 | 비고 |
|---|---|---|
| **θ_primary** | V1 95 percentile (V2 95p와 비교해 큰 쪽) | 주 결과 |
| θ_alt1 | **max(0.2·ŷ_clean(t), θ_primary)** | α-λ ±20% 치환. 바닥 없으면 말기(ŷ→0)에 전부 저하로 잡힘 |
| θ_alt2 | test RMSE (≈12) | 전역 성능 척도 연동 |

**결정 규칙**
1. clean-only 대조(seed 530 예측 vs 529 예측의 δ)에서 θ_primary 기준 저하 진입율 ≤ 5% → 초과하면 99p로 상향
2. bias α=0.1에서 저하 unit 비율이 거의 0이면 α 하한을 내리거나 θ 하향 검토
3. 세 θ 모두로 라벨 생성. `label.yaml`에 세 값과 근거 기록

### D-3. 히스테리시스 라벨 ✅ (`src/label/hysteresis.py`)

```
state = NORMAL; τ_d = None; label[:] = 0
for t in 45 .. T_u:
    lo = max(45, t − m + 1)              # 초기 구간은 있는 만큼만 (안전장치)
    recent = δ[lo .. t]
    if state == NORMAL and count(recent > θ_high) >= k:
        t_enter = first index in [lo..t] with δ > θ_high
        label[t_enter .. t] = 1          # 역방향 채우기
        state = DEGRADED
        if τ_d is None: τ_d = t_enter
    elif state == DEGRADED and count(recent <= θ_low) >= k:
        t_exit = first index in [lo..t] with δ <= θ_low
        label[t_exit .. t] = 0           # 역방향 채우기 (대칭)
        state = NORMAL
    else:
        label[t] = 1 if state == DEGRADED else 0
```

- 기본 k=5, m=7, θ_low = 0.5·θ_high 🔶
- 민감도: k∈{3,5,7}, m∈{5,7,10}
- **역방향 채우기 이유**: 판정 확정 시점(t)과 실제 초과 시작(t_enter) 사이가 "τ_d 이후인데 라벨 0"이 되는 모순 제거. 라벨은 오프라인 정답이므로 비인과적 정의 허용. τ_d가 앞으로 당겨져 unit 단위 평가에서 에이전트의 첫 반응이 FP로 잡히는 문제도 완화
- **정상 복귀 허용 이유**: 에이전트에게 묻는 질문이 "이 cycle에서 성능 저하가 존재하는가"이므로 정답도 그 cycle의 실제 상태를 따라야 함. 수명 말기에 두 예측이 모두 0 근처로 수렴하면 그 구간은 0이 맞음
- τ_s 이전 구간: D-1 assert 통과 시 자동으로 0
- 초기 구간(45~44+m): τ_s ≥ 55이므로 실전에서 걸릴 일은 없지만 안전장치로 유지
- 출력: `labels/state/{theta_name}/u{unit}/{scenario_id}.parquet` [time, delta, label, state]
- `tests/test_hysteresis.py`: 진입·복귀 경계, 역방향 채우기, 초기 구간

### D-4. scenario_index.csv ✅ (long format)

`scripts/06` 메타 컬럼 + `scripts/08` 결과 컬럼. **한 (unit, scenario)당 θ 3행.**

```
# 06이 쓰는 메타
unit, T_u, type, sensor, param, dir, timing_p, tau_s, rng_seed
# 08이 덧붙이는 결과
theta_name, theta_value, k, m,
degraded, tau_d, delay(tau_d − tau_s),
n_degraded_cycles, n_transitions, frac_degraded_after_tau_s,
saturated_at_tau_s (T_u − tau_s > 125)
```

### D-5. 리포트 (`reports/D_label_summary.md`) ✅

1. 유형 × 강도별 저하 unit 비율 heatmap
2. 유형별 지연 τ_d − τ_s 분포 (bias 즉시, noise 지연 예상)
3. 시점별(20/40/60/80) 저하율 — 20%에서 unit 길이(포화 여부)별 분리
4. 복귀(1→0) 발생 비율과 위치 (수명 말기 집중 여부)
5. θ 세 후보 간 라벨 일치율
6. clean-only 대조의 저하 진입율 (θ 검증)

---

## 6. 산출물 체크리스트

| Phase | 산출물 | 검증 |
|---|---|---|
| B-0 | 원본 재현 수치 | RMSE ≈ 11.85 |
| A | `split_FD001.json` | T_u 분포 유사 |
| B | `norm_params_pre_FD0013.npy`, `norm_params_ft_FD001.npy` | shape (17,2), std=0은 op3만 |
| B | `pre_FD0013_holdout.pt`, `ft_s{529,530,531}.pt` | 로드 가능 |
| B | `reproduce_metrics.json` | RMSE 12~13, commit hash, torch 버전 |
| B | `preds/clean/` 60 파일 (rul_true 포함) | 결정성 통과, 절단점 RMSE ≈ test RMSE |
| C | `data/shifted/` 5,120 파일 | `test_shift.py` 통과, 플롯 3개 |
| C | `preds/shift/` 5,120 파일 | 파일 수 일치 |
| C | `scenario_index.csv` 메타 컬럼 | 5,120행 |
| D | `clean_variability.json` | V1, V2, V3 |
| D | `label.yaml` | θ 3종·k·m 확정값 + 근거 |
| D | `labels/state/{3 θ}/` 15,360 파일 | `test_hysteresis.py` 통과, τ_s 이전 δ assert 통과 |
| D | `scenario_index.csv` 결과 컬럼 | 15,360행 (long) |
| D | `D_label_summary.md` | 6개 항목 |

---

## 7. 결정 현황

**✅ 이 문서로 확정**
분할 방식, 모델·seed, 정규화 정책, 주입 6종 정의(gain 평균 중심, multi 부호 규칙), τ_s 공식(t0=55), 미사용 센서 대조군 제거, 에이전트 입력 = 모델 입력 14센서, 라벨 정의(counterfactual delta + 히스테리시스 + 역방향 채우기 + 복귀 허용), θ 3종 구조(θ_alt1 바닥), τ_s 이전 assert, 폴더·파일·scenario_id·git 규칙, 재현성 기록 항목

**🔶 Phase D-2 후 확정**
θ_primary 수치, k, m, θ_low 비율, α grid 최종 범위, N 상향 여부(→ t0 재계산·라벨 재생성)

**❓ 에이전트 단계**
입력 표현 형식, 프롬프트, 도구 사용, 판정 stride s, 이력 사용 ablation, w(허용 범위), baseline 구체 정의, FD002~004 확장

---

## 8. 실행 순서와 예상 소요

| 순서 | 작업 | 소요 | 중단 조건 |
|---|---|---|---|
| B-0 | 원본 재현 + 코드 확인 | 반나절 | RMSE ≠ 11.85 근처 |
| A | 분할 | 반나절 | — |
| B-1~3 | 재학습 3 seed + 재현 | 1~2일 | RMSE > 15 |
| B-4 | 추론 루틴 + 결정성·정합성 | 반나일 | 결정성 실패 |
| C (병렬 가능) | 주입 함수 + grid + 테스트 | 1일 | `test_shift.py` 실패 |
| C 추론 | 5,120 실행 | 수 시간 | — |
| D-1 | delta + assert | 반나절 | τ_s 이전 δ ≠ 0 |
| D-2 | 분포 분석 → θ 결정 (사람 판단) | 1일 | — |
| D-3~5 | 라벨 생성 + 리포트 | 1일 | 테스트 실패 |

총 **5~7일**. A와 C-1은 B와 병렬. C 추론과 D는 B와 C-1 완료 후.
