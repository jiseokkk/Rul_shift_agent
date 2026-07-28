# [0728] LLM 기반 RUL 보정 — 설계 변경과 구현·디버깅 기록

> **한 줄 요약**: 에이전트를 "shift 감지 시 결정만 보수적으로 바꾸는(trust-gating)" 구조에서
> "**shift를 감지하면 잘못된 RUL 값을 직접 보정(corrected_rul)하고, 보정값에 threshold를 적용해
> decision까지 내리는**" 구조로 리디자인하고, LLM 재실행 + 3라운드 디버깅으로 완성.

---

## 1. 기존의 문제 — 왜 바꿨나

기존 설계에서 에이전트는 shift를 감지해도 **RUL 값 자체는 건드리지 않았다.**
"모델을 못 믿겠으니 결정을 inspect로 올린다" 수준의 간접 대응만 가능했고,

- **얼마나** 잘못됐는지는 정량화하지 못함 → 결정 근거가 임계값이 아니라 "불신"
- adverse shift 시 LSTM은 RUL을 64(cap)로 부풀리는데, true RUL이 10 이하로 떨어져도
  보정 없이는 replace 판단의 근거가 생기지 않음
- 평가도 결정 품질(F1)만 가능하고, "에이전트가 RUL을 얼마나 잘 복원했나"는 측정 불가

→ **요청사항: LLM이 shift 상황을 감지하고, 잘못 예측된 RUL 값을 보정해서 decision하도록 변경.**

---

## 2. 설계 변경: trust-gating → RUL correction

| | 기존 (trust-gating) | 변경 후 (RUL correction) |
|---|---|---|
| LLM 출력 | shift 여부 + 신뢰도 + 결정 | shift 여부 + **corrected_rul (숫자)** + 결정 |
| 결정 방식 | shift 확정 시 결정을 보수적으로 상향 | **보정 RUL에 threshold 그대로 적용** (≤10 replace, ≤25 inspect) |
| 보정 방법 | 없음 | **앵커 방식**: pre-shift 히스토리에서 외삽 (아래 §3) |
| hysteresis (#5) | shift 확정 게이트 | **보정 적용 여부**를 게이트 |
| cost-aware (#6) | 결정 자체를 조정 | 보정 주변 가드레일 (adverse→최소 inspect, favorable→replace 금지) |
| 평가 축 | 결정 F1 + 감지 | **rul_correction RMSE/MAE 축 신설** (evaluate.py) |
| HISTORY_K | 5 (뒤로 12 cycles) | **20 (뒤로 57 cycles)** — §3.1의 핵심 전제조건 |

---

## 3. 보정을 어떻게 하나

### 3.1 히스토리 창 — 무엇을 기준으로 얼마나 보나

- 결정 포인트는 **3 cycle 간격** (`DECISION_EVERY=3`). unit 11이면 cycle 1, 4, 7, …, 58.
- 각 결정 포인트에서 에이전트가 받는 히스토리 = **그 시점까지의 LSTM point 예측값 중 마지막 20개**
  (`HISTORY_K=20`). true RUL이 아니라 **모델의 예측값**이다.
- **한 스텝 = 3 cycles** → 창의 범위는 "현재 ~ 뒤로 19스텝 × 3 = **57 cycles**".
- 창은 고정 시작점이 없는 **슬라이딩 창**: 결정할 때마다 한 칸씩 앞으로 밀린다.
  창의 시작은 shift 시점과 무관하게 "지금이 언제인지"로만 정해진다.

**HISTORY_K를 5→20으로 올린 이유** — onset jump는 과거의 고정된 한 지점인데 창은 계속 밀리므로,
창이 짧으면(K=5, 12 cycles) shift 발생 12 cycles 후부터 jump가 창 밖으로 사라져 앵커를 잃는다.
K=20이면 창(57 cycles)이 unit 11의 수명(59 cycles) 전체를 덮어서 **한 번 잡힌 앵커가 수명이
끝날 때까지 창에 남는다.** (K 변경 후 패킷 재빌드 필수 — 완료함)

```
HISTORY_K=5  : cycle 40에서 창=[28…40] → 창 안이 전부 64,64,64 — jump(23) 안 보임 ✗
HISTORY_K=20 : cycle 58에서도 창=[1…58] → jump 항상 보임 ✓
```

### 3.2 앵커 방식 (1순위, 기본 보정)

핵심 아이디어: **"shift 이전의 예측은 믿을 수 있었다."** 오염된 현재 출력은 버리고,
pre-shift의 마지막 신뢰 가능한 예측에서 물리 법칙(RUL은 1/cycle 감소)으로 외삽한다.

1. 히스토리에서 **10 이상**(`CORR_JUMP`)의 급변(jump)을 찾는다 — 그 직전 값이 앵커.
   (adverse: 40→64 급등, favorable: →0 급락. 정상 구간의 ±수 cycle 지터는 무시)
2. 외삽:

```
corrected_rul = (jump 직전 예측값) − 3 × (jump 이후 경과 스텝 수)     # 3 = 스텝당 cycles
```

3. [0, 65]로 클리핑.

**예시** (unit 11 adverse, onset=cycle 23): cycle 40 시점 히스토리 `… 42 → 40 → 64 → 64 …`
→ 앵커 40, 경과 6스텝 → `40 − 3×6 = 22` (true RUL 19). 모델 출력 64를 그대로 썼다면 45 오차.

잔여 오차 ≈ 앵커 시점에 모델이 원래 갖고 있던 편향(+9 cycles 수준) — 에이전트 입장에서는
줄일 수 없는 하한.

### 3.3 gain 방식 — 왜 실패했고, 앵커 방식과 뭐가 다른가

리디자인 초기에 시도한 방식:

```
corrected = rul_now + gain × regime_z      # regime_z 음수(adverse)면 하향, 양수(favorable)면 상향
```

**"오염된 현재 출력"에서 출발해 신호 크기에 비례해 밀어내는** 방식인데, 전제인
"|regime_z| ∝ 모델이 틀린 정도"가 **LSTM 포화 때문에 깨진다**:

- shift 후 출력은 adverse=64(cap), favorable=0에 **포화** → regime_z가 −15든 −62든
  출발점이 똑같아서 출발점에 정보가 없음
- regime_z는 ±60σ까지 튀는데 실제 오차는 그만큼 안 변함 → 어떤 gain을 골라도
  시점에 따라 과보정/과소보정. 특히 favorable은 `0 + gain × z`가 돼 gain 튜닝 그 자체가 됨

| | gain 방식 | 앵커 방식 |
|---|---|---|
| 보정의 근거 | 오염된 현재 출력 + 신호 크기 | **오염 전의 예측** + 물리 법칙(1/cycle) |
| 전제 | \|regime_z\| ∝ 오차 크기 (포화로 깨짐) | pre-shift 예측은 정확 + 1 cycle에 1씩 노화 |
| favorable에서 | 실패 (출력이 0에 붙음) | 동작 (21.4→13.3) |
| 현재 역할 | **fallback (2순위)** | **기본 (1순위)** |

### 3.4 fallback — 앵커가 안 보일 때 (gain 방식이 남아있는 이유)

앵커 방식의 전제는 "**창 안에 jump가 보인다**"이다. 깨지는 경우 두 가지:

1. **shift 발생 후 57 cycles 초과 경과** → jump가 슬라이딩 창 왼쪽 밖으로 밀려남.
   창 안이 전부 오염된 값(64,64,64…)이라 앵커를 잡을 곳이 없음.
2. **관측 시작부터 shift가 있던 경우** → 깨끗한 예측이 히스토리에 존재한 적이 없어 jump 자체가 없음.

이때만 gain 방식으로 넘어간다 (rule: `rul + gain × regime_z`, LLM: |regime_z|·mc_std가
클수록 모델 추정에서 멀리 떨어진 값을 추론하라고 prompt Step 3(b)에 지시).

**현재 실험 설정에서는 fallback이 발동하지 않는다** — 검증 결과 shift 이후 결정 포인트 24개
전부 앵커가 잡힘 (fallback 0건). 수명 59 cycles vs 창 57 cycles이라 구조적으로 안 생긴다.
남겨둔 이유는 일반성: 수명이 더 긴 유닛, 더 이른 onset에서는 반드시 이 경로를 탄다
(예: 수명 120 / onset 20이면 cycle 77부터 fallback).

> ⚠️ 보고 시 유의: 현재 보고되는 보정 성능은 전부 **앵커 경로**의 성능이다.
> fallback 경로는 이번 실험에서 검증되지 않았다 (검증하려면 onset을 당기거나 K를 줄인 별도 실험 필요).

### 3.5 보정값이 결정에 쓰이기까지 — 3겹 게이트

1. **샘플 median** — LLM 5샘플의 corrected_rul 중앙값 (이상 샘플에 강건)
2. **hysteresis** — shift 감지 2회 연속 확정 후에만 보정 적용. 그 전엔 모델 raw 값 사용
   → 일시적 오탐이 잘못된 보정을 못 일으킴
3. **cost-aware 가드레일** — adverse 확정: 보정 RUL이 길어도 최소 inspect (보정 자체 검증 필요).
   favorable 확정: replace 금지 (비관적 모델 때문에 멀쩡한 자산 폐기 방지)

최종 결정 = effective RUL(확정 시 보정값, 아니면 raw)에 threshold 적용.
shift가 없으면 corrected_rul = raw 그대로 — **노이즈에 "보정"하지 않는 것도 명시적 규칙.**

---

## 4. 오늘의 LLM 실행 — 3라운드 디버깅

| 라운드 | 증상 | 원인 | 조치 |
|---|---|---|---|
| **1차** | ① 수명 말기 정상 노화(RUL→0)를 favorable shift로 오인, RUL을 15~23으로 상향 ② adverse 보정값이 외삽 없이 ~40에 정체 (true 34→1) | prompt가 "수명 말기 ≠ shift"를 구분 안 함 / 산식 결과가 작으면 LLM이 버리고 "그럴듯한" 값으로 회귀 | prompt 수정: END-OF-LIFE IS NOT A SHIFT 명시, favorable은 regime_z 명확한 양수일 때만, **산식 결과를 그대로 쓸 것** |
| **2차** | adverse 감지 recall 0.92→**0.17 붕괴** | prompt 논리가 아니라 **파서 버그**: 산식 명시 → Qwen이 계산을 LaTeX(`\text{corrected_rul}`)로 작성 → "첫 `{`~마지막 `}`" 파서가 LaTeX 중괄호에 걸림 → 545샘플 중 ~100개 파싱 실패 → 실패 샘플이 "no shift"로 집계 | `parse_json`을 **뒤에서부터** 유효한 JSON 객체("decision" 포함)를 찾는 방식으로 교체. raw 로그 전문 저장(기존 1500자 잘림이 버그를 가림). `LLM_MAX_TOKENS` 900→1500 |
| **3차 (최종)** | 파싱 실패 **0/545**, 정상 동작 | — | — |

교훈: 라운드 2의 성능 붕괴는 모델·prompt 문제처럼 보였지만 실제로는 **파이프라인(파싱) 문제**였다.
prompt를 바꾸면 모델의 출력 형식도 바뀐다 — 출력 파서는 형식 변화에 강건해야 한다.

---

## 5. 결과 (Qwen2.5-32B-AWQ, 5 samples/point, majority+median)

### RUL 보정 (post-onset RMSE, vs capped true RUL)

| 시나리오 | 모델 그대로 | rule 에이전트 | **LLM 에이전트** |
|---|---|---|---|
| adverse post-onset | 47.7 | 12.3 | **20.5** |
| favorable post-onset | 21.4 | 13.3 | **16.3** |

### 결정 품질 / 감지

| 축 | 비교 대상 | **LLM 에이전트** |
|---|---|---|
| adverse 결정 | threshold 베이스라인 FNR **1.00** (전부 miss) | FNR **0.00**, F1 0.82 |
| shift 감지 latency | CUSUM 8 cycles / rule 5 cycles | **2 cycles** (recall 1.00, 전 방법 중 최고) |
| natural (Fc1/Fc2) | CUSUM FPR 0.45 | FPR **0.00** (F1 0.97) — cause gate가 benign 변화 구분 |

해석: LLM은 절차를 이해하고 방향은 맞게 보정하지만, **앵커 산수의 정확도에서 rule에 못 미친다**
(rule은 같은 신호·같은 절차를 결정론적으로 수행하는 상한 레퍼런스).

---

## 6. 남은 한계와 다음 단계

**한계** (Qwen2.5-32B 능력 한계로 판단):

1. adverse 보정값이 수명 말기에 위로 표류 — cyc58에서 true 1인데 45 출력
   (앵커에서 경과 스텝을 끝까지 정확히 못 셈)
2. 수명 말기 false favorable 7행 잔존 — 최악: 모델 RUL 0.6을 30으로 "보정"
   (no_shift FNR 0.22→0.33 악화의 원인)

**다음 레버**:

- (a) 정책 레벨 하드 가드: 히스토리에 급락 jump가 없고 raw RUL < replace 임계이면 상향 보정 금지
- (b) thinking 모델로 교체 실험 (draft 원안은 Qwen3-14B; `config.py`의 `LLM_PATH`로 전환)
- (c) fallback 경로 검증 실험 (onset 앞당기기 or HISTORY_K 축소 조건)

**산출물 위치**: 최종 결과 `results/metrics.json`, LLM 결정 `results/agent_decisions_llm.json`
(1차 백업: `agent_decisions_llm_v1.json.bak`), raw CoT `packets/agent_results_qwen.jsonl`
