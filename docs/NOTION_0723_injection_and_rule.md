# 0723 — Bias Injection 방식 & Rule Agent 정리

작성일: 2026-07-23. 대상: N-CMAPSS DS02-006, unit 11(Direction A) 중심.
관련: [[NOTION_bias_injection_ko]], [[BIAS_INJECTION_DESIGN_ko]].

---

## Part 1. 이번에 bias를 어떻게 넣었나

### 1.1 한 줄 요약
깨끗한 unit 11의 **관측 센서(X_s)에만** 거짓 왜곡(bias)을 주입하고, RUL 정답(Y)은 그대로 둔다. 왜곡은 `FaultSpec` 레시피로 정의하고, 크기는 **탐지기 신호 cons**가 목표값이 되도록 자동 보정한다. (`inject.py`, `run_experiment.py`)

### 1.2 왜곡을 정의하는 3축 + 크기
| 구성요소 | 이번 실험에서 쓴 값 | 의미 |
|---|---|---|
| **결함 모드** | `drift` | 서서히 커지는 오프셋 (열전대 노후) |
| **시간 프로파일** | `ramp`, 길이 15 cycle | onset부터 15사이클에 걸쳐 서서히 최대치 도달 |
| **채널 범위** | `single(T48)` 또는 `temp4` | 1채널(현실적) vs 4채널(scope 비교) |
| **onset** | 수명의 45% (unit 11 = cycle 27) | 중반부터 결함 시작 |
| **부호** | −(adverse) 또는 +(favorable) | 온도를 낮게(위험) / 높게(과비관) |
| **크기** | cons = 4로 자동 보정 | 아래 1.3 |

### 1.3 크기 보정: cons(탐지기 신호) 기준
- `cons` = `temp_consistency_z_abs` = 온도 4채널이 "서로 얼마나 안 맞나"의 평균. 룰 탐지기가 실제로 보는 값.
- 왜곡 크기를 **이분탐색으로 조절**해, post-onset plateau 구간의 cons가 정확히 목표(4.0)가 되도록 맞춘다. (`inject.calibrate_to_detector`)
- **cons=4**를 쓴 이유: 앞선 스윕 실험에서 recall이 cons 2→3에서 0.00→0.45로 급등, 절벽이 룰 임계값 cons>3에 위치. cons 3~4가 "룰이 반쯤 놓치는 애매 구간".
- σ가 아니라 cons를 쓰는 이유: 같은 σ라도 채널 수에 따라 실효 난이도가 제각각(같은 0.5σ가 recall 0.00~0.73). cons로 맞추면 scope가 달라도 난이도가 정렬됨.
- 보정 결과(예): T48 단독은 −51.3, temp4는 T48 −54.3 등. 4채널은 관계가 보존돼 신호가 희석되므로 더 크게 넣어야 같은 cons가 됨.

### 1.4 원칙
- **관측 센서만 손상, RUL 정답 불변** → "센서는 거짓말하지만 정답은 진짜".
- **train 데이터는 손대지 않음** (오염 시 실험 무의미).
- **원본 스키마 유지** → 기존 로더가 그대로 읽음(드롭인).
- adverse(−)는 열화를 **은폐** → 엔진이 건강해 보임 → RUL 과대평가 → 교체 놓칠 위험(안전 최악).

### 1.5 알아둘 한계 (미해결)
- cons는 **난이도 knob이자 룰 탐지기의 판정 통계량**이라 부분적 순환. 향후 탐지기-독립 지표(Mahalanobis 등)로 분리 검토 중. 이번 실험은 "지금 구조(cons)" 그대로 진행.

### 1.6 이 주입 설계의 근거 논문
"결함 하나를 (모드 × 프로파일 × 크기 × onset)로 파라미터화"하는 방식은 우리가 지어낸 게 아니라 fault-injection 분야의 표준이다. 축별 근거:

| 설계 축 | 근거 논문 | 무엇을 뒷받침 |
|---|---|---|
| **결함 모드** (offset/gain/drift/noise/stuck) | Ni et al., "Sensor Network Data Fault Types," ACM TOSN 2009 | 이 5종이 표준 센서결함 분류. offset/gain/stuck/noise 정의 그대로 |
| 〃 (현실성) | Sharma, Golubchik, Govindan, ACM TOSN 2010 | 실제 배치 데이터에서 이 결함들이 얼마나 흔한지 실증 |
| **파라미터화 전체** (크기·onset·지속시간 랜덤화) | Balaban, Saxena, Goebel et al. (NASA), "Modeling, Detection, and Disambiguation of Sensor Faults for Aerospace Applications," 2009–2011 | 항공우주 센서에 bias/drift/scaling을 랜덤 onset·magnitude로 주입 — 도메인 일치하는 직접 선례 |
| **시간 프로파일** (step=abrupt, ramp=incipient, intermittent) | Koutsoukos et al.(Vanderbilt), "Detection & Estimation of Multiple Fault Profiles," 2012 | abrupt-persistent / abrupt-intermittent / incipient 분류 + 결함 시점·크기 추정 |
| **물리적 근거** (T48=EGT 열전대, 크기) | "Uncertainties in gas-path diagnosis of gas turbines," Aerospace Sci.&Tech. 2021 · Fentaye et al. review, Aerospace 2019 | 가스경로 진단에서 bias/noise 정식화, EGT 열전대가 대표 결함 |
| **adverse/stealth 방향** | Mode & Hoque, "Crafting Adversarial Examples for DL Prognostics," (C-MAPSS) 2020 · Liu-Ning-Reiter, ACM TISSEC 2011 | RUL 모델에 대한 FDIA(계측 조작 공격)의 직접 선행연구 + stealth 공격의 수학적 원형 |

**논문 서사**: "우리는 Balaban et al.(NASA)의 파라미터화된 항공우주 센서결함 주입을, N-CMAPSS RUL 결정 문제로 확장하고, 난이도를 탐지기 신호(cons)로 정규화했다." → 모드 선택·시간 프로파일·물리 정합성·적대적 방향을 모두 인용으로 방어 가능.

---

## Part 2. Rule Agent가 어떻게 되어 있나

### 2.1 한 줄 요약
LLM 없이 **손으로 짠 if-then 규칙**으로 판단하는 기준선. LLM과 **같은 입력**(RUL, cons, regime_z, mc_std, RUL 이력)을 받아 continue/inspect/replace를 결정. 무료·결정론적. "LLM이 이 규칙보다 나은가"의 비교 대상. (`agent.py`)

### 2.2 판정 3단계
**① shift 탐지 게이트** ([agent.py:149](../agent.py))
```python
real_shift = (cons > 3.0 and |regime| > 5.0) or (max_cons > 6.0)
```
- cons(교차채널 불일치) **와** regime(운전조건 보정 후 편차)이 **둘 다** 커야 진짜 결함으로 인정.
- 방향: regime<0 → adverse(온도 낮음, 과낙관), regime>0 → favorable(과비관).

**② RUL 기반 기본 결정**
```
RUL ≤ 10 → replace,  RUL ≤ 20 → inspect,  else → continue
```
- adverse shift가 잡히면 continue를 inspect로 격상.

**③ Tier-2 정책** (LLM에도 동일 적용, `apply_policy`)
- **#5 hysteresis**: shift 기반 격상은 연속 N회 지속돼야 확정 → 일시적 자연 shift 오경보 제거.
- **#6 cost-aware**: adverse 확정 시 부풀린 RUL 불신 → 최소 inspect(짧으면 replace). favorable 확정 시 healthy 자산 조기교체 방지 → inspect로 제한. 저신뢰는 안전한 중간(inspect)으로.

### 2.3 rule의 정체 = "고정 숫자 임계값" (추론 없음)
rule의 본질은 **사람이 정한 고정 컷오프**(`cons>3`, `|regime|>5`, `max_cons>6`, `RUL≤10/20`)를 기계적으로 적용하는 것. 상황에 맞춘 추론이 없다. 이게 실험 해석의 열쇠:
- 게이트 경로 A가 **cons>3 AND |regime|>5** 둘 다 요구 → cons=4 결함은 regime(−1)이 5를 못 넘어 경로 A 실패.
- 경로 B(`max_cons>6`)로만 뒤늦게 부분 탐지 → latency 10~13.
- 옛 ±2σ는 regime을 15~62까지 띄워 쉽게 잡혔지만, 정교화하니 **고정 게이트가 무너짐.**
- LLM은 이 고정 임계값이 없이 "cons=4는 노이즈(~1)의 4배라 이상"으로 **추론** → regime이 작아도 즉시 탐지(latency 1).

### 2.4 세 방법이 무엇을 분리하는가 (비교 구도)
| 방법 | Tier-1 신호(regime_z·consistency_z) | 판단 방식 |
|---|---|---|
| threshold / CUSUM | **안 씀** (RUL 또는 전역 z만) | 고정 규칙 |
| **rule** | **씀** | **고정 임계값** |
| **LLM** | **씀** | **추론으로 통합** |

- **rule vs CUSUM** = "좋은 신호(Tier-1)를 쓰나 안 쓰나"의 차이.
- **rule vs LLM** = "같은 신호를 고정 규칙으로 쓰나 추론으로 쓰나"의 차이.
- → rule이 중간 다리라, LLM 우위가 **"더 좋은 신호" 덕인지 "추론" 덕인지** 구분해 줌. (실험 결과: CUSUM→rule 도약은 신호 덕, rule→LLM 도약은 추론 덕.)

---

## Part 3. 실험 결과 — Rule vs LLM (이번 injection 적용)

cons=4, drift-ramp15, onset 45%. LLM = Qwen32B, 5 samples/point.
`results/experiment_refined_{rule,llm}.json`.

> ⚠️ 초기에 shift recall이 rule/LLM 모두 0.00으로 나왔으나, 이는 `evaluate.shift_detection`이 시나리오명을 `"adverse"`로 하드코딩 필터하는데 우리 시나리오명이 `adverse_single`/`adverse_temp4`라 빈 리스트가 된 **버그**였다. `run_experiment.shift_recall`로 정정.

### 결정 품질 (FNR=결함 놓침, FPR=오경보) + shift 탐지  — 초기 LLM (프롬프트 개선 **전**)
> 아래 LLM FPR(0.55 등)은 프롬프트 Step 3 수정 **전** 값. 수정 후 값은 Part 4 참조. 아래 4-way 표와 Part 4 표는 **개선 후** LLM 기준.

| 시나리오 | rule FNR/FPR | rule recall/lat | LLM FNR/FPR | LLM recall/lat |
|---|---|---|---|---|
| no_shift | 0.22 / **0.00** | — | 0.22 / 0.27 | — |
| adverse_single | 0.11 / 0.00 | 0.73 / 10 | 0.11 / 0.55 | **0.82 / 1** |
| adverse_temp4 | 0.22 / 0.00 | 0.64 / 13 | 0.00 / 0.36 | **1.00 / 1** |
| favorable | 0.00 / 0.09 | — | 0.00 / 0.36 | — |
| natural | 0.06 / **0.00** | — | 0.00 / 0.23 | — |

### 4-way 비교 (baseline 포함) — CUSUM/threshold도 넣음
FNR(결함 놓침) / FPR(오경보):
| 시나리오 | threshold | CUSUM | rule | LLM |
|---|---|---|---|---|
| no_shift | 0.22/0.00 | 0.22/0.00 | 0.22/0.00 | 0.11/0.18 |
| adverse_single | **0.78**/0.00 | **0.78**/0.00 | 0.11/0.00 | 0.11/0.27 |
| adverse_temp4 | **1.00**/0.00 | **0.56**/0.00 | 0.22/0.00 | **0.00**/0.27 |
| favorable | 0.00/0.09 | 0.00/0.09 | 0.00/0.09 | 0.00/0.18 |
| natural | 0.06/0.00 | 0.06/**0.45** | 0.06/0.00 | 0.06/0.16 |

shift 탐지 recall/latency (adverse):
| 시나리오 | CUSUM | rule | LLM |
|---|---|---|---|
| adverse_single | **0.00 / —** | 0.73 / 10 | **0.82 / 1** |
| adverse_temp4 | 0.36 / 22 | 0.64 / 13 | **1.00 / 1** |

**baseline이 정교화된 결함에서 붕괴한다 (이게 injection 정교화의 정당성):**
- **threshold**(RUL만 봄): adverse를 아예 못 잡음(FNR 0.78~1.00) — 센서를 안 보니 당연.
- **CUSUM**(전역 z-score): adverse_single을 **전혀 탐지 못 함**(recall 0.00), temp4도 latency 22로 뒤늦게. 게다가 **natural에서 오경보 폭발(FPR 0.45)** — 비행클래스가 바뀌면 전역 z가 튀어서 benign을 결함으로 오인. "놓치면서 동시에 오경보"하는 최악.
- → 옛 ±2σ는 CUSUM도 쉽게 잡았지만, 정교화(cons=4, regime 보정 회피)하니 **고전 탐지기가 무너짐.** 여기서 Tier-1 신호(regime_z·consistency_z)를 쓰는 rule과, 추론까지 더한 LLM만 살아남음.

### 핵심 결과 (정직하게)
**LLM이 탐지에서 이긴다 — 더 완전하게, 그리고 훨씬 빨리:**
- recall: single 0.73→**0.82**, temp4 0.64→**1.00**
- latency: single **10→1**, temp4 **13→1** (거의 즉시 탐지)

**이유**: LLM은 "cons=4는 노이즈(~1)의 4배라 명백히 이상"으로 추론해 regime이 작아도(−1) adverse로 판정. 반면 rule 게이트는 `cons>3 AND |regime|>5`를 요구 → regime<5라 이 경로로는 못 잡고, `max_cons>6` 경로로만 뒤늦게(latency 10~13) 부분 탐지. **LLM이 룰의 경직된 게이트가 놓치는 걸 유연하게 잡음** = 프로젝트 주장 성립.

**단, 대가가 있다 — LLM은 오경보(FPR)가 높다:**
- 깨끗한 no_shift(0.00→0.27), 자연 shift natural(0.00→0.23)에서 rule은 오경보 0인데 LLM은 올라감.
- 원인(raw 분석): LLM의 Step 3(RUL 이력의 물리적 점프 점검)이 **RUL 이력 노이즈(상향 점프)** 에 반응해 shift가 아닌데도 inspect로 격상. 센서 신호 오독이 아니라 RUL 이력 과민.

### 종합
민감도(빨리·많이 탐지) ↔ 특이도(오경보) 트레이드오프. 프레임워크 비용모델(놓침 > 오경보)에선 **조기 탐지(latency 1)가 큰 가치**지만, **FPR을 잡는 게 다음 과제**.

---

## Part 4. FPR 개선 (프롬프트 Step 3 수정) — 완료

**수정**: Step 3(물리 sanity)을 "보강 증거 전용, 단독 트리거 금지"로 변경. RUL 이력의 작은 점프는 모델 추정 노이즈이며, Step 1이 이미 shift를 찾았을 때 + 크고 지속적 상승일 때만 adverse 보강. benign이면 이력 점프만으로 격상 금지. (user 프롬프트의 "upward jump is impossible" 문구도 완화.)

**결과 — FPR 전반 하락, 탐지 성능은 유지:**
| 시나리오 | LLM FPR 이전 | LLM FPR 이후 | rule FPR |
|---|---|---|---|
| no_shift | 0.27 | **0.18** | 0.00 |
| adverse_single | 0.55 | **0.27** | 0.00 |
| adverse_temp4 | 0.36 | **0.27** | 0.00 |
| favorable | 0.36 | **0.18** | 0.09 |
| natural | 0.23 | **0.16** | 0.00 |

- **탐지는 그대로 우위 유지**: adverse_single recall 0.82/lat 1, adverse_temp4 recall 1.00/lat 1 (rule 0.73/10, 0.64/13 대비).
- FPR이 절반 가까이 하락(특히 adverse_single 0.55→0.27). LLM은 여전히 rule(0.00)보다 오경보가 있지만, rule의 0 FPR은 경직된 게이트가 거의 안 울려서일 뿐 — 그 대가로 탐지가 느림(lat 10~13). **LLM은 조기·완전 탐지 + 수용 가능한 FPR**로 트레이드오프가 크게 개선됨.

## Part 5. LLM은 왜 생각보다 잘하나 — 원인 · 의심 · 한계

정교화된(고전 탐지기가 무너지는) 결함인데도 LLM은 recall 0.82~1.00, latency 1로 잘한다. **왜 잘하는지**와 **그 성적을 얼마나 믿을 수 있는지**를 분리해서 본다.

### 5.1 왜 잘하나 (raw 출력 근거)
LLM 실제 추론을 뜯어보면 (raw jsonl):
- cycle 31 (cons=**1.44**): "둘 다 노이즈(~1) 범위 → shift 없음" — **정확히 억제**. (ramp 초반이라 왜곡이 작음)
- plateau cycle 46 (cons=**4.15**, regime=**−1.08**): "cons가 노이즈의 4배 → 명백히 이상, regime 음수 → adverse" → inspect/replace — **정확히 탐지**.

성적의 실제 원인 4가지:
1. **소프트·연속 임계 vs 경직된 AND 게이트**: 룰은 `cons>3 AND |regime|>5` 둘 다 요구 → cons=4·regime=−1이면 실패. LLM은 cons 하나가 "노이즈 대비 크게" 벗어나면 발화 → **AND 조건에 안 묶임**.
2. **방향을 regime 부호로 읽음**: |regime|이 작아도 부호(−)로 adverse를 정확히 판정.
3. **다신호 통합**: cons + regime + RUL 이력 + mc_std를 한꺼번에 정성적으로 종합.
4. **조기 발화**: cons 하나만 "elevated" 되면 즉시 반응 → ramp가 조금만 자라도 잡음(latency 1). 룰은 `max_cons>6`을 기다려 늦음(latency 10~13).

### 5.2 의심 — 이 성적이 과대평가일 수 있는 이유
"LLM이 추론으로 이겼다"를 곧이곧대로 믿기 전에 걸러야 할 것들:

1. **우리가 스케일을 알려줬다.** 프롬프트에 "표준화 값이라 ±1이 노이즈"라고 명시함. LLM의 "cons=4는 4배라 이상"은 **우리가 준 암묵적 임계값**(~3~4배)을 적용한 것일 수 있음 → "emergent 추론"인지 "힌트 적용"인지 경계 흐림.
2. **프롬프트를 테스트 결과 보고 튜닝함.** 게이트 제거 → 재실행, FPR 높음 확인 → Step 3 수정 → **같은 테스트에 재실행**. 이건 테스트셋 과적합. held-out 검증이 없으면 "능력"인지 "이 테스트에 맞춘 것"인지 불명.
3. **룰을 재튜닝 안 함.** 룰의 `cons>3 AND |regime|>5`는 옛 ±2σ 체제 값. cons=4엔 mismatch. **룰을 `cons>3 OR max_cons>4` 식으로 재튜닝하면 LLM과 비슷해질 수도** 있음 → "LLM>rule"의 일부는 "룰을 안 고쳐서".
4. **난이도를 룰이 실패하는 지점에 놓음.** cons=4는 "cons>3은 넘지만 regime<5"인 지점 — **룰의 AND 게이트 약점을 정확히 찌르는 곳**. 우리가 (의도치 않게) LLM에 유리한 운용점을 고른 셈.
5. **통계적 검정력 없음.** unit 11 하나, post-onset 11점. recall 0.73 vs 0.82 차이는 유의성 검정 불가.
6. **FPR은 여전히 열세.** "좋은 성적"은 LLM이 clean/benign에서 rule(0.00)보다 오경보가 많다는 점(0.16~0.27)을 가림.

### 5.3 종합 판단
현재 상태 = **"정교화된 결함이 고전 탐지기를 무력화하고, LLM이 그것을 조기 탐지할 수 있다"는 유망한 single-unit proof-of-concept.** 단, "LLM이 추론으로 룰보다 낫다"는 일반 주장으로 가기엔 5.2의 1~4번(스케일 힌트·프롬프트 오염·룰 미재튜닝·난이도 위치)이 미해결. **성적 자체는 진짜지만, 그 원인이 "추론"이라는 해석은 아직 증명 안 됨.**

---

## Part 6. 앞으로 어떻게 할 것인가 (우선순위)

### 최우선 — "결과가 설계된 것"이라는 공격 방어
1. **공정한 룰 baseline 재튜닝**: 새 주입(cons 기반)에 맞춰 룰 임계값을 unit 20에서 재보정. 그 뒤에도 LLM이 이기는지 확인 → "룰 안 고쳐서 이긴 것" 반박 차단.
2. **스케일 힌트 절제(ablation)**: 프롬프트에서 "±1이 노이즈" 문구를 뺀 버전과 비교. 여전히 잘하면 → 진짜 추론. 무너지면 → 힌트 덕이었음을 정직히 인정.
3. **held-out 프롬프트 검증**: 프롬프트를 고정한 뒤, **본 적 없는 시나리오**(다른 onset·ramp·mode)에서 평가. 테스트 과적합 분리.

### 그다음 — 일반화·검정력
4. **다중 유닛·seed 확장**: unit 11 외 다른 Fc3 유닛에도 주입, onset 30/45/60%·seed 반복 → 신뢰구간 제시.
5. **난이도 스윕**: cons 2/3/4/6에서 threshold/CUSUM/rule/LLM 4방법 곡선 → "LLM 우위가 어느 난이도에서 최대인지" 정량화(단일 포인트 아님).
6. **학습형 baseline 추가**: 오토인코더/one-class 등 잘 튜닝된 ML 탐지기와 비교 → "CUSUM만 이겼다"는 낮은 허들 극복.

### 구조 개선
7. **난이도 순환 해소**: cons 대신 탐지기-독립 지표(Mahalanobis)로 난이도 재정의 → 평가와 분리.
8. **잔여 FPR**: hysteresis 강화 또는 confidence 보정으로 LLM FPR(0.16~0.27) 추가 하락.
9. **결함 모드 확장**: gain·stealth·degrade 스텁 구현 → "물리적 근거" 주장을 drift 하나가 아니라 여러 모드로 입증.

### 한 줄 로드맵
**(재튜닝 룰 + 힌트 절제 + held-out) 으로 "진짜 추론 우위"를 먼저 방어** → **(다중 유닛 + 난이도 스윕 + 학습형 baseline) 으로 일반화 입증** → **(Mahalanobis + 모드 확장) 으로 프레임워크 완성.**
