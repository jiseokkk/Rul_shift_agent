# Stage 2 보고서 — detector 검증·캘리브레이션·벤치마크 잠금 (2026-08-04)

계획: `docs/0804_cusum_pca_baseline_experiment.md` §3–§4, §8 Stage 2.

## 1. 구현 (신규 작성)

- `baselines/common.py` — cycle-vector 파이프라인(표현 v2), 입력 3종
  (vec_xs 14 / vec_xsw 18 / vec_regime 28), 듀얼 뷰(native q=0.99 / 비교 q=0.97),
  hysteresis(연속 2회), paired-clean 유효 탐지 + 상태 5분류, FA 계수(raw/confirmed).
- `baselines/cusum/core.py` — Page 두측 tabular CUSUM, per-channel bank + max,
  k=0.5, 수명 내 무리셋.
- `baselines/pca/core.py` — PCA T²/SPE (Jackson–Mudholkar 계열), ev_target 0.90.
- **재표준화 공개(§3.1 관련)**: detector 입력은 clean train의 cycle-level
  평균/표준편차로 재표준화 — window-mean 집계로 cycle 분산이 ~1/N_c로 줄기 때문에,
  이 보정 없이는 k=0.5가 "cycle σ의 ~1.1배"를 의미하게 됨. 보정 후 k=0.5 =
  cycle-level 0.5σ (문서 서술과 정합).

## 2. 검증 (§3.4) — `baselines/tests/results_sanity.json`

| 검사 | 결과 |
|---|---|
| ARL₀ 교차검증 (Montgomery 표준값) | h=4: MC 166.4 vs 168 (오차 1.0%) / h=5: 454.3 vs 465 (2.3%) ✅ |
| 1σ step 감지 sanity | delay 24, pre-onset FA 없음, 채널 격리 정확 ✅ |
| PCA 방향성 | loading 방향 shift → T²×5.3·SPE×1.0 / 직교 shift → SPE×63·T²×1.0 ✅ |

(bank 테스트 h=8 사용 — d채널 max-bank는 family-wise ARL₀가 ~1/d로 줄어
h=5로는 pre-onset 오탐이 이론적으로 예상되기 때문. 코드 주석에 명시.)

## 3. 캘리브레이션 — `outputs/thresholds.json` (9변형 × 2뷰 = 18)

u20 clean(ctrl_u20, 66 cycles) 분위수. 대표값(native, block bootstrap 95% CI):

| detector | native h (CI) | comparison h |
|---|---|---|
| cusum_xs | 8.89 (4.8–9.1) | 6.93 |
| cusum_regime | 73.97 (23.2–79.1) | 64.34 |
| t2_xs | 7.93 (6.3–9.3) | 5.56 |
| spe_xs | 3.17 (0.6–3.9) | 2.30 |
| spe_regime | 11.45 (5.0–13.3) | 8.21 |

**실현 FA (u20, 전 detector 동일)**: raw 1.52/100cyc (66cyc 중 1점 — q=0.99의
산술적 결과), **confirmed 0.00/100cyc** (hysteresis가 단발 초과를 제거 —
"정하는 것은 raw, 확인은 양쪽" 원칙의 예상 그대로).

## 4. Threshold 안정성 진단 (0804 2·3차 검토 채택분)

u20 threshold를 train unit clean에 적용 (native, per 100cyc):

| unit | cusum_xs raw/conf | spe_xs | spe_regime | t2_regime |
|---|---|---|---|---|
| u2 | 5.3/1.3 | 0/0 | 0/0 | 0/0 |
| u5 | 4.5/1.1 | 2.2/1.1 | 1.1/0 | 0/0 |
| u10 | 0/0 | 3.7/1.2 | 0/0 | 0/0 |
| u16 | 0/0 | 0/0 | 3.2/0 | 0/0 |
| u18 | 0/0 | 1.4/0 | 0/0 | 0/0 |

- **u20은 극단이 아님**: unit별 q99 분포에서 u20은 중간~중상위
  (cusum_xs: 3.6–9.4 범위에서 u20=8.89; spe_regime: 7.8–13.9에서 11.45).
- **unit 간 변동이 지배적** (cusum q99 스프레드 ~2.6×) — 단일 unit 극단 분위수의
  한계가 실측으로 정량화됨. 다만 **confirmed FA는 전 unit ≤1.3/100cyc**로
  hysteresis가 유효하게 방어.
- 한계 문구(사전 등록): "Threshold calibration relied on one held-out unit;
  threshold stability was additionally examined across clean training units."
  (train unit은 특징 적합의 in-sample이라 점수 하향 편향 — 진단용, 캘리브레이션
  대체 불가.)

## 5. 난이도 사전 확인 (§7 규칙 ① — dev 증거만 사용)

devset(u20) + 메모리상 저σ 주입, native 뷰, paired-clean 판정:

| σ | cusum_xs | cusum_regime | spe_xs | spe_regime | t2_xs |
|---|---|---|---|---|---|
| 0.15 | +만 탐지 (L27) | −만 탐지 (L36) | 혼재 | 탐지 (L15) | miss |
| 0.25 | 탐지 (L19–21) | 탐지 (L22–27) | 혼재 | 탐지 (L10) | miss |
| 0.35 | 탐지 (L15–16) | 탐지 (L17–21) | 혼재 | 탐지 (L7) | miss |
| 0.5 | 탐지 (L12–13) | 탐지 (L14–17) | 탐지 | 탐지 (L4) | miss |

- **절벽이 스펙트럼 내부에 실재**: 0.15σ = 경계(방향·detector별 분기, latency
  15–36), 0.5σ+ = 안정 탐지. u11은 onset 후 잔여 수명이 32cyc라 저σ의 긴
  latency가 miss로 전환될 여지도 있음(의도된 난이도).
- t2 전 구간 miss — §7 사전 등록 예측과 일치.
- **판정: σ 그리드 조정 불필요.**

## 6. 벤치마크 잠금 선언

- **잠금 대상**: `dataset/corrupted_dataset/`의 test 50개 시나리오
  (manifest split=test), spec 전체, threshold 18개(`outputs/thresholds.json`),
  프로토콜(§4: 듀얼 뷰·hysteresis·paired-clean·상태 5분류·지표 정의).
- **이후 Stage 3(test) 결과를 근거로 한 시나리오·σ·onset·threshold 수정 금지**
  (§7 규칙 ②). 사후 추가는 "추가 탐색 실험"으로 분리(규칙 ③).
- 본 메소드(LLM) 단계의 반복은 devset로만(규칙 ④).

**LOCKED — 2026-08-04, engine 0804.1, git aae2134.**
