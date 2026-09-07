# Agent 사양 (1차 실험)

대상 모델: Qwen2.5-32B-Instruct (quantized), LangChain/LangGraph 고정 DAG.
LLM은 reasoning 노드 1회 호출. Tool 호출 여부를 LLM이 결정하지 않는다.

```
EDA Tool ──┐
           ├── build_input() ── LLM (structured output) ── post_check() ── Decision
RUL Tool ──┘
```

---

## 1. System Prompt

원칙만 담고 숫자는 넣지 않는다. 32B 양자화 모델을 고려해 짧고 지시문형으로 작성한다.

```text
You are a sensor-fault detection agent monitoring a turbofan engine. A frozen machine-learning
model predicts the engine's Remaining Useful Life (RUL) from sensor data. Your job is to judge,
once per flight cycle, whether the sensor inputs feeding that model look NORMAL or show evidence
of a SENSOR FAULT, and to flag the RUL prediction accordingly.

## What you receive
All statistics are precomputed. Do not recompute anything; interpret what is given.

CALIBRATION — how much each statistic normally fluctuates on clean validation data.
  z_w        : residual mean of a 5-minute window divided by its clean-data std. |z_w| around 1 is
               ordinary; q95 is the value exceeded by only 5% of clean windows.
  std_ratio  : window residual std divided by its clean-data median. 1.0 is ordinary.
  T2         : Hotelling T² of the residual vector across all sensors. median and q95 on clean data
               are given.
These are calibration references, NOT thresholds. Do not invent numeric cutoffs.

MULTIVARIATE — T² per cycle and each sensor's contribution to T² in the current cycle.
  Contribution concentrated in one sensor → single-sensor behaviour.
  Contribution spread across many sensors → system-level change (degradation or unmodelled
  operating condition), which is NOT a sensor fault.

PER SENSOR
  Previous cycles (aggregated): z_w median/max, exceedance (windows beyond q95 / total),
  std_ratio median, step contrast Δμ (change in z_w median vs previous cycles),
  spread contrast Δσ (change in std_ratio vs previous cycles).
  Current cycle (window series): z_w and std_ratio for every window, in flight order,
  plus exceedance and the first window beyond q95.

RUL — current prediction, recent trajectory, and change. Auxiliary context only.

## How to reason (in this order)
1. Look at T² first. Is the current cycle unusual overall? Is the contribution concentrated or spread?
2. For sensors with high contribution or large |Δμ|/|Δσ|, read the current-cycle window series.
   Is the shift present in all windows (persistent), from some window onward (onset mid-flight),
   or in a few windows only (transient)?
3. Compare with the previous cycles. A step from an ordinary level to a sustained new level is
   bias-like. Ordinary z_w with elevated std_ratio is noise-like. Values inside the normal
   fluctuation of previous cycles are not evidence.
4. Check consistency: mean-type and spread-type statistics should tell a coherent story.
5. Use RUL only as supporting context. RUL always drifts downward; a drop alone is never a fault.

## Confidence calibration
confidence reflects how much the evidence converges, not how large any single number is (there
are no fixed thresholds). Judge agreement among: (a) T2 clearly outside its clean range, not
borderline; (b) contribution concentrated in the suspected sensor(s) for FAULT, or spread evenly
for NORMAL; (c) the window-level shift is persistent or has a clear onset, not a transient blip;
(d) the current cycle falls outside the previous cycles' fluctuation; (e) mean-type and
spread-type statistics agree.
  0.85-1.00 : (a)-(e) agree cleanly, no competing explanation.
  0.60-0.85 : most agree; one is weaker or partly explained by operating condition.
  0.35-0.60 : evidence is mixed or borderline; often pairs with fault_pattern = UNCLEAR.
  0.00-0.35 : the input itself is thin (e.g. short flight, n/a stats) rather than just ambiguous.
A clean, unremarkable NORMAL call belongs at 0.85-1.00 too — confidence measures certainty in
either direction, not just how sure you are about FAULT.

## Rules
- A shift explained by many sensors moving together is degradation, not a sensor fault.
- Never declare FAULT from RUL evidence alone.
- FAULT means the sensor input is untrustworthy. It does NOT mean the RUL value is wrong.
- rul_reliability is WARNING if and only if sensor_status is FAULT.
- Cite specific statistics in your rationale (sensor name, cycle, value). Keep it under 120 words.
- Respond only with the JSON object defined by the schema. No prose outside it.
```

---

## 2. Output Schema

```python
from typing import Literal
from pydantic import BaseModel, Field


class Decision(BaseModel):
    sensor_status: Literal["NORMAL", "FAULT"]
    rul_reliability: Literal["RELIABLE", "WARNING"]

    # FAULT일 때 의심 센서. NORMAL이면 빈 리스트. 1차 실험은 single-sensor라 보통 1개.
    suspected_sensors: list[str] = Field(default_factory=list)

    # 관측된 패턴. 1차는 abrupt bias만 주입하지만 진단용으로 기록.
    fault_pattern: Literal["NONE", "BIAS_LIKE", "NOISE_LIKE", "UNCLEAR"] = "NONE"

    # 0~1. 근거 수렴도 기준 (System Prompt "Confidence calibration" 참조).
    # 평가에는 쓰지 않고 threshold sweep / 분석용.
    confidence: float = Field(ge=0.0, le=1.0)

    # 판정을 이끈 핵심 수치 2~4개. 예: ["S7 z_w median 99..102 ≈ 0.1 → cycle 103 = 2.9",
    #                                    "T² 61.4 vs clean q95 19.7, S7 contribution 0.86"]
    key_evidence: list[str] = Field(min_length=1, max_length=4)

    # 120 단어 이내.
    rationale: str
```

### post_check (코드에서 강제)

LLM 출력 후 다음을 코드로 보정·검증한다. 위반은 로그에 남기고 보정한다.

| 검사 | 처리 |
|---|---|
| `sensor_status == FAULT` ↔ `rul_reliability == WARNING` 불일치 | reliability를 status에 맞춰 덮어씀, 불일치 카운트 기록 |
| `NORMAL`인데 `suspected_sensors` 비어 있지 않음 | 리스트 비움 |
| `FAULT`인데 `suspected_sensors` 비어 있음 | 유지, `isolation_missing` 플래그 기록 |
| `suspected_sensors`에 실제 센서 이름이 아닌 값 | 제거 |
| 파싱 실패 | 재시도 최대 2회 → `ERROR` |

### 저장 레코드 (decisions.csv 한 행)

`unit, cycle, sensor_status, rul_reliability, suspected_sensors, fault_pattern, confidence, key_evidence, rationale, n_retries, post_check_flags, latency_ms, prompt_tokens, true_rul, life_fraction`

`true_rul`, `life_fraction`은 Agent에게 주지 않고 평가 시 열화 구간 FP 분석용으로만 저장한다.

---

## 3. Runtime Input 구조

### 3.1 설계 원칙

- 정규화된 값(z_w, std_ratio, T², contribution)만 제공한다. raw mean/median/std/IQR은 LLM 입력에서 제외한다 (window 테이블에는 저장). 32B 모델에 raw 단위가 다른 수치를 섞어 주면 해석 오류가 늘고 토큰만 소비한다.
- 순서: 캘리브레이션 → 다변량(T²) → 센서별 → RUL. 가장 판별력 높은 정보가 먼저 온다.
- 센서별 블록은 T² contribution 내림차순으로 정렬한다. 순서 자체가 힌트가 되지만, 모든 센서를 빠짐없이 제공하므로 "Top-K 선택 금지" 원칙에 어긋나지 않는다.
- 소수 1자리, 부호 명시. 현재 cycle window 시계열은 z_w와 std_ratio 두 줄만.
- 총 길이: 센서 14개 × (이전 4 cycle × 6개 + window 24개 × 2) ≈ 1,000개 숫자 → 5~6k 토큰.

### 3.2 템플릿

```text
=== EVALUATION ===
unit: {unit}    cycle: {cycle}    windows_in_cycle: {n_windows} (L_w = 5 min)

=== CALIBRATION (clean validation) ===
z_w: |z_w| q95 = {q95_z}      std_ratio: clean median = 1.00      T2: median = {t2_med}, q95 = {t2_q95}

=== MULTIVARIATE ===
cycle              : {c-4}   {c-3}   {c-2}   {c-1}   {c}
T2 median          : {..}    {..}    {..}    {..}    {..}
T2 max             : {..}    {..}    {..}    {..}    {..}
contribution @{c}  : {S_a} {p_a}, {S_b} {p_b}, {S_c} {p_c}, ... (all sensors, descending)

=== SENSORS (ordered by contribution @{c}) ===

--- {S_a}  (contribution {p_a}) ---
previous cycles    : {c-4}   {c-3}   {c-2}   {c-1}
  z_w median       : {..}    {..}    {..}    {..}
  z_w max          : {..}    {..}    {..}    {..}
  exceedance       : {k/n}   {k/n}   {k/n}   {k/n}
  std_ratio median : {..}    {..}    {..}    {..}
current cycle {c}  : n_windows = {n}, exceedance = {k/n}, first exceed = {w or -}
  Δμ = {..}   Δσ = {..}
  z_w        : {w1} {w2} {w3} ... {wn}
  std_ratio  : {w1} {w2} {w3} ... {wn}

--- {S_b}  (contribution {p_b}) ---
...

=== RUL (auxiliary) ===
current            : {rul}
recent             : {r-4} → {r-3} → {r-2} → {r-1} → {rul}
change             : {Δ}  (recent median change {Δ_med})

=== TASK ===
Determine sensor_status and rul_reliability. Return the JSON object only.
```

### 3.3 채워진 예시 (unit 12, cycle 103, S7에 bias 주입)

```text
=== EVALUATION ===
unit: 12    cycle: 103    windows_in_cycle: 24 (L_w = 5 min)

=== CALIBRATION (clean validation) ===
z_w: |z_w| q95 = 1.9      std_ratio: clean median = 1.00      T2: median = 10.4, q95 = 19.7

=== MULTIVARIATE ===
cycle              :  99     100    101    102    103
T2 median          :  9.8    11.2   10.1   10.6   61.4
T2 max             : 15.3    17.0   14.8   16.1   68.2
contribution @103  : S7 0.86, S12 0.04, S2 0.03, S11 0.02, S9 0.01, S3 0.01, S4 0.01, S8 0.01, S13 0.00, S14 0.00, S1 0.00, S6 0.00, S10 0.00, S5 0.00

=== SENSORS (ordered by contribution @103) ===

--- S7  (contribution 0.86) ---
previous cycles    :  99     100    101    102
  z_w median       : +0.1   -0.2   +0.0   +0.1
  z_w max          : +0.6   +0.4   +0.5   +0.7
  exceedance       : 0/22   1/24   0/23   0/24
  std_ratio median : 1.0    1.1    0.9    1.0
current cycle 103  : n_windows = 24, exceedance = 24/24, first exceed = #1
  Δμ = +2.9   Δσ = +0.0
  z_w        : +2.9 +3.1 +2.8 +3.0 +2.9 +2.7 +3.0 +2.8 +2.9 +3.1 +2.8 +2.9 +3.0 +2.8 +2.9 +2.7 +3.0 +2.9 +2.8 +3.0 +2.9 +2.8 +3.1 +2.8
  std_ratio  :  1.0  1.0  0.9  1.1  1.0  1.0  1.0  1.0  0.9  1.0  1.1  1.0  1.0  1.0  0.9  1.0  1.0  1.1  1.0  1.0  1.0  0.9  1.0  1.0

--- S12  (contribution 0.04) ---
previous cycles    :  99     100    101    102
  z_w median       : -0.1   +0.0   +0.1   -0.1
  z_w max          : +0.5   +0.6   +0.4   +0.5
  exceedance       : 0/22   0/24   0/23   0/24
  std_ratio median : 1.0    1.0    1.0    1.0
current cycle 103  : n_windows = 24, exceedance = 0/24, first exceed = -
  Δμ = +0.1   Δσ = +0.0
  z_w        : +0.1 -0.2 +0.0 +0.1 +0.2 -0.1 ... (24 values)
  std_ratio  :  1.0  1.0  1.1  1.0  0.9  1.0 ...

... (S2 ~ S5, 나머지 12개 센서 동일 형식)

=== RUL (auxiliary) ===
current            : 47.3
recent             : 55.2 → 53.7 → 51.8 → 50.4 → 47.3
change             : -3.1  (recent median change -1.4)

=== TASK ===
Determine sensor_status and rul_reliability. Return the JSON object only.
```

기대 출력:

```json
{
  "sensor_status": "FAULT",
  "rul_reliability": "WARNING",
  "suspected_sensors": ["S7"],
  "fault_pattern": "BIAS_LIKE",
  "confidence": 0.92,
  "key_evidence": [
    "T2 median 61.4 at cycle 103 vs clean q95 19.7; S7 contribution 0.86",
    "S7 z_w median +0.1..-0.2 in cycles 99-102, +2.9 at cycle 103; exceedance 24/24 from window #1",
    "S7 std_ratio unchanged (1.0); all other sensors within previous range"
  ],
  "rationale": "The current cycle is far outside the clean T2 range and the excess is almost entirely attributable to S7. S7 shows a sustained positive residual shift across all 24 windows from the first window, while its spread is unchanged, which is a bias-like pattern. No other sensor departs from its previous-cycle behaviour, so a system-level change is unlikely. The RUL drop is larger than recent changes but is not needed for this judgement."
}
```

### 3.4 Warm-up 및 예외

- cycle 1~4: Agent 미호출. `previous cycles` 블록이 4개 확보되는 cycle 5부터 호출.
- 비행이 짧아 window 수 < 6이면 `n_windows` 값을 그대로 주고 프롬프트에 별도 처리 없음. 결과 분석 시 short-flight 플래그로 분리.
- 센서 하나의 σ_w나 Σ_r 추정이 불안정하면(조건수 초과) 해당 값을 `n/a`로 표기하고 이유를 한 줄로 넣는다. 1차에서는 발생하지 않을 것으로 예상.

---

## 4. 1차 실험에서 확인할 프롬프트 리스크

| 리스크 | 확인 방법 | 대응 |
|---|---|---|
| 32B 모델이 T²/contribution을 무시하고 z_w만 봄 | rationale의 T² 언급 비율 | Step 1 지시를 더 강하게 |
| 열화 구간에서 여러 센서 z_w가 동시에 1~2로 올라갈 때 FAULT 남발 | life_fraction별 FP 분포 | "spread contribution → not fault" 규칙 강조, 예시 추가 |
| 정렬 순서에 과의존 (첫 센서를 무조건 의심) | clean cycle에서 첫 센서가 suspected에 오르는 비율 | 정렬 제거 ablation |
| JSON 파싱 실패 | FailRate | vLLM tool-call parser 또는 JSON 스키마 강제 |
| confidence가 근거 수렴도가 아니라 \|z_w\| 크기에 비례해서 매겨짐 | confidence vs. \|z_w\| median 상관 / confidence vs. (a)~(e) 충족 개수 상관 비교 | 앵커 문구 구체화 또는 예시 1개 추가 |
