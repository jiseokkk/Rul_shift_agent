# 0804 CUSUM·PCA 베이스라인 실험 — 최종 보고서 (Stage 4)

- 벤치마크: `dataset/corrupted_dataset/` test 50 시나리오 (2026-08-04 잠금,
  engine 0804.1, git aae2134) · detector 9변형 × 2뷰 · 프로토콜 §4 (paired-clean
  유효 탐지, 상태 5분류, hysteresis 2, FA 예산 raw 1/100cyc)
- 원자료: `results/0804_stage3/` (per_scenario.csv 900행, aggregates.json,
  그림 2종, ladder/matched_count 표), per-cycle score 로그 `results/scores/` 50개
- 사전 등록 대조 기준: 계획 §7 예상표 (실험 전 고정)

## 1. 요약 (Executive Summary)

**만능 detector는 없다 — 블록마다 승자가 다르고, 최강 변형도 구조적 대가를
치른다.** 이것이 잠긴 벤치마크의 핵심 결론이며, shift-aware 결정 계층(후속 LLM
에이전트)의 실증적 무대가 된다.

| 축 | 결과 |
|---|---|
| 최고 감도 | spe_regime: Block A–D 사실상 전승 (A 1.00, latency 중앙값 ~5) |
| 그 대가 | spe_regime의 ctrl_u14 confirmed FA **15.8/100cyc** — 전 변형 중 최악, FA 예산을 강화해도 해소 불가 (부록 A) |
| natural 강건 | spe_xs: ctrl_u14 FA 0.0 + Block F 1.00 — 그러나 Block D PC1 **0/6**, 저σ adverse(−) 전멸 |
| 고전 전통 | cusum: A–D 견실 (0.89–1.00), 그러나 Block F **SAT 4/4** + u14 raw FA 97/100cyc |
| 공통 사각 | **noise 0/54** (9변형 × 6시나리오, seed 3개 전부) — 입력 표현의 구조적 사각지대 |
| 케이던스 | 비교 뷰(3-cycle)의 op 저하 **0**, latency +1~2cyc — LLM 비교의 공정성 확보 |

## 2. 본 결과표 (native 뷰, operational detection rate)

| Block | cusum_xs | cusum_xsw | cusum_reg | t2_xs | t2_xsw | t2_reg | spe_xs | spe_xsw | spe_reg |
|---|---|---|---|---|---|---|---|---|---|
| A σ절벽 (18) | 0.89 | 0.89 | 0.94 | 0.22 | 0.17 | 0.22 | 0.83 | 0.83 | **1.00** |
| B ramp40 (2) | 1.00 | 1.00 | 1.00 | 0.00 | 0.00 | 0.00 | 1.00 | 1.00 | 1.00 |
| C temp4 (6) | 1.00 | 1.00 | 1.00 | 0.00 | 0.00 | 0.83 | 1.00 | 1.00 | 1.00 |
| D 부분공간 (8) | 1.00 | 1.00 | 1.00 | 0.50 | 0.50 | 1.00 | **0.25** | 1.00 | 1.00 |
| E 모드 (9) | 0.33 | 0.33 | 0.33 | 0.11 | 0.11 | 0.11 | 0.33 | 0.33 | 0.33 |
| F natural겹침 (4) | **0.00** | **0.00** | 0.50 | 0.00 | 0.00 | 0.25 | **1.00** | **1.00** | 0.50 |

(blind-spot 히트맵: `0804_stage3/blindspot_matrix.png`)

## 3. 사전 등록(§7) 대조 — 적중과 반전

**적중 (예측 = 결과):**
1. noise = 전 변형 recall 0 (예측 "원리적 비가시") — **seed 3개 전부 0**이라
   요행 아님까지 실증. 원인은 detector가 아니라 window-mean 표현.
2. Raw 변형의 natural 파괴 — ctrl_u14 raw FA 97.4/100cyc, Block F SAT 4/4
   (예측 "SAT 예상", "FA 다발" 그대로).
3. **cusum_xs ≡ cusum_xsw 완전 동일** (u14 FA 소수점까지 일치) — 사다리 §3.1의
   사전 등록 예측("W 제거만으로는 부족") 그대로: max-bank에서 W 채널이 지배한
   적이 없고, 센서 자체가 운항조건을 따라 움직인다. **"W를 빼면 되지 않느냐"
   반박은 실측으로 기각.**
4. T²의 단일채널 무능 (A 0.22 — 2σ만 탐지), CUSUM 누적의 ramp40 강점 (1.00 vs
   T² 0.00), SPE-Raw의 PC1 사각 (아래 §6).
5. stuck: 전 변형이 즉시 탐지 (latency 1–3) — §7 단서("동결값이 하강 구간 값이라
   가시적일 수 있음") 방향의 상향이 실제로 발생. flatline 크기 ~180°R.

**반전 (예측 ≠ 결과 — 본 실험의 발견):**
1. **spe_regime이 A 저σ까지 전승** — §7의 "? 핵심 셀"의 답이 ○ (0.15σ ±조차
   latency 16–21). 단, u14 FA 15.8/100의 대가와 함께 (아래 §5).
2. **spe_xs가 Block F를 무결 처리** (op 1.00, u14 FA 0.0; 예측은 SAT) —
   natural flight-class 변화는 센서 상관구조를 **따라** 움직여 SPE 잔차를 거의
   만들지 않는다. natural 강건성이 "regime 조건화" 축만이 아니라 "잔차 통계량"
   축에서도 나온다는 것 — 사다리 해석에 중요한 추가 축.
3. t2_regime의 D 전승 (1.00) — PC1 방향이 vec_regime 공간에서는 주부분공간이
   아니어서 T²-Regime에 그대로 보임 (외부 검토 3.2의 "정렬은 detector-특정적"
   지적의 실증).

## 4. σ 절벽과 방향 비대칭 (Block A, native)

상태(latency): O=clean_detected, x=miss  (`blockA_coverage.png`)

| σ (ramp15) | cusum_xs | cusum_reg | spe_xs | spe_reg |
|---|---|---|---|---|
| 0.15 + / − | O(27) / **x** | O(32) / **x** | O(30) / **x** | O(16) / O(21) |
| 0.25 + / − | O(20) / **x** | O(24) / O(26) | O(28) / **x** | O(9) / O(9) |
| 0.35 + / − | O(17) / O(16) | O(20) / O(19) | O(24) / **x** | O(6) / O(7) |
| 0.5–2.0 | 전부 O (5–13) | 전부 O (7–16) | 전부 O (3–14) | 전부 O (2–5) |

- **절벽 위치**: raw 계열은 0.25~0.35σ 사이(adverse 방향), spe_regime은 0.15σ
  아래(미관측) — 그리드가 절벽을 걸치도록 설계된 목표 달성.
- **방향 비대칭 (신규 발견)**: adverse(−)가 일관되게 어렵다. T48 자연 열화가
  상승 방향이므로 **음의 bias는 자연 추세를 상쇄하며 숨는다** — RUL 과대평가
  방향(위험한 방향)이 정확히 더 안 잡히는 구조. 이 비대칭은 spe_regime만 해소.
- 물리 환산: 0.15σ ≈ 14.8°R ≈ 8.2°C (ch_std 98.42°R 기준), σ_res 단위로는 1.6.

## 5. 감도–natural FA 트레이드오프 (사다리 최종 해석)

| 변형 | A op | F op | ctrl_u14 conf FA/100 | 성격 |
|---|---|---|---|---|
| cusum_xs(=xsw) | 0.89 | 0.00 (SAT) | 1.3 (raw 97) | 전통 강자, natural에서 포화 |
| spe_xs | 0.83 | 1.00 | 0.0 | natural 최강건, PC1·저σ− 사각 |
| spe_regime | 1.00 | 0.50 | **15.8** | 최고 감도, natural 오탐 대가 |

- 부록 A: FA 예산을 0.5~5/100으로 흔들어도 이 순위는 불변 — spe_regime의 u14
  문제는 **threshold 조정으로 해소 불가**(분포 자체가 이동). regime 특징의
  희소-support 구간(u14: train p1–p99 밖 alt 19.8%/T2 24.9%, Stage 0) 외삽과
  연결되는 구조적 비용.
- matched-count 진단(§4.5-6, `matched_count.md`): u14 FPR 초과분이 window 수
  효과를 크게 상회 (cusum +0.68 vs 4win 효과 0.28) → **진짜 분포 변화**. 단
  spe_xs는 초과분 −0.01 → 같은 u14가 통계량에 따라 전혀 문제가 아님 — "natural
  shift의 어려움"은 detector-상대적이다.

## 6. Block D — 부분공간 정렬 shift의 detector-특정성

| 변형 | PC1 (6) | all14 (2) |
|---|---|---|
| spe_xs | **0/6 (사각 실증)** | 2/2 |
| spe_xsw | 6/6 | 2/2 |
| t2_xs | 2/6 (α=4만) | 2/2 |
| t2_regime · cusum 계열 · spe_regime | 6/6 | 2/2 |

PC1은 **vec_xs 공간의** 주부분공간 방향이므로 SPE-Raw-Xs에만 사각이고, W 채널
하나만 더해도(spe_xsw) 정렬이 깨진다. 명명 규칙("subspace-aligned는
PCA-Raw-Xs 대상 white-box")의 타당성이 결과로 확인됨. 주의: cycle-vector PC1은
압력 채널 지배적(T48 loading 0.083)이라 Block D는 사실상 압력 좌표 공격.

## 7. 시간 축: latency·advance·profile

- **step vs ramp15**: step은 즉발(spe 계열 1cyc, cusum 1–6), ramp15는 주입량이
  0.5σ를 넘는 시점부터 잡히는 패턴 (σ 클수록 조기) — 누적/즉발 특성 분리 확인.
- **paired-clean의 가치**: no_effect 5건 검출 — 전부 t2 계열이 natural 열화
  알람(T_clean ≤ T_fault)을 fault로 오크레딧할 뻔한 셀 (예: u15에서
  t_fault=37 = t_clean). 구 정의였으면 "탐지 성공"으로 집계됐을 사례들.
- alarm advance 중앙값 24–31cyc (탐지 성공 셀) — fault 주입이 자연 열화 대비
  알람을 실질적으로 앞당김을 정량화.
- hysteresis 추가 지연: raw 대비 confirmed +1cyc(native)가 로그에서 확인
  (per_scenario.csv의 latency vs latency_raw).

## 8. 이중 케이던스 검증

비교 뷰(3-cycle, q=0.97)에서 **op rate 변화 0** (전 블록·전 변형), latency만
+1~2cyc. → 후속 LLM 비교에서 baseline이 케이던스 핸디캡을 사실상 받지 않음 —
"strawman baseline" 비판 차단 근거.

## 9. 부록

**A. FA 예산 민감도** (native, Block A op | u14 conf FA): budget 0.5→5/100에서
cusum_xs 0.89→0.94|1.3, spe_xs 0.83→0.89|0→2.6, spe_regime 1.00 고정|13~16 —
결론 순위 불변, 트레이드오프는 예산 무관.

**B. CUSUM k 민감도** (dev 전용, u20): k∈{0.25,0.5,1.0} 전부 dev 5개 탐지,
latency 차이 ≤수 cycle — k=0.5 선택 비임계.

**C. Threshold 안정성** (Stage 2 재게): u20 비극단(unit q99 중간대), unit 간
스프레드 ~2.6×, confirmed FA 전 train unit ≤1.3/100. 한계 문구 사전 등록대로.

## 10. 한계 (사전 등록 표현 준수)

1. 단일 held-out unit 캘리브레이션 — 극단 분위수의 정밀도 한계 (안정성 진단
   병기; "nominal marginal exceedance threshold"로 표기).
2. **사례 기반**: u11 반복 주입(공유 clean prefix — pre-onset 판정은
   unit×detector당 1회 실현), Fc당 test unit 1개 (flight-class와 unit 효과
   교락) — 집계는 unit-cluster 단위로 해석하며 모집단 recall 주장 불가.
   "unseen-flight-class units에 대한 사례 기반 분석"이 주장 가능 범위.
3. T48 중심 단독 주입 — 채널 일반화는 추후 계획(압력 채널 Block A 반복 =
   추가 탐색 실험).
4. 사전 등록은 파일럿 정보 반영(informed) — 본 벤치마크는 development
   benchmark이며 confirmatory holdout은 후속 subset으로 이연.
5. noise/stuck에 대한 variance/flatline 전용 baseline 부재 — 본 실험 주장은
   "mean 기반 파이프라인의 사각 문서화"에 한정, LLM 비교 논문 시점에 전용
   baseline 추가 예정.

## 11. 후속 LLM 결정 계층에 주는 시사점

잠긴 벤치마크가 LLM에게 요구하는 것 (규칙 ④: 개발은 devset로만):
1. **중재(arbitration)**: spe_regime의 감도와 spe_xs의 natural 강건성을 상황
   인지적으로 결합 — 어떤 고정 융합 규칙보다 "지금 이 unit이 unseen 운항
   패턴인가"를 판단하는 능력이 관건 (u14 희소-support 진단이 단서 제공).
2. **방향 인지**: adverse(−) 사각 — RUL 과대평가 위험 방향의 보수적 판단.
3. **모드 사각 커버**: noise(전 변형 0)와 같은 분산형 신호 — window std/변동성
   feature를 도구로 노출하면 고전 파이프라인이 못 보는 축을 볼 수 있는가.
4. **비교 조건**: comparison 뷰 (3-cycle, q=0.97) + 동일 FA 예산 + 동일
   paired-clean 프로토콜 — 본 보고서의 표가 그대로 대조군.
