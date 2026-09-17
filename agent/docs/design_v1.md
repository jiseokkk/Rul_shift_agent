# 에이전트 설계 v1

작성 2026-09-17. 데이터: `../data_prep/` (grid v3, 잠금). 데이터 요약은 `../data_prep/docs/data_prep_summary.md`.

---

## 1. 질문

배포된 RUL 모델을 감시하는 LLM 에이전트가, 매 cycle **"지금 이 모델의 출력이 오염된 입력에 끌려가 신뢰할 수 없는 상태인가"**(0/1)를 판정한다.
정답은 `data_prep`의 cycle 라벨(theta_primary): 오염 때문에 모델 출력이 clean 대비 θ=9.4 이상 벌어진 상태.

에이전트는 배포 환경에서 관측 가능한 것만 본다. clean 예측, 정답 RUL, 오염 시작 시점(τ_s), 시나리오 종류는 끝까지 없다.

---

## 2. 관측 가능한 데이터

| 구분 | 내용 | 출처 |
|---|---|---|
| 센서 | 현재 cycle 값, 이전 cycle 값 (모델 입력 14센서. op1~3은 단일 운전조건이라 제외) | `data_prep/data/shifted/FD001/u{u}/{sid}.parquet` |
| RUL 모델 | 현재 출력 ỹ_t, 이전 출력 (cycle 45~) | `data_prep/preds/FD001/shift/s529/` |
| RUL 모델 | MC dropout 50 pass (현재 + 이력) | `agent/artifacts/mc_dropout/shift/` (사전 계산 캐시, 결정적 seed) |
| 맥락 | unit 번호, 현재 cycle | 실행기 |
| 사전 지식 | clean(train) 정규화 통계 | **v1에서는 사용하지 않음** (v2 후보) |

채점 전용(에이전트 코드에서 import 금지): `preds/clean/`, `labels/state/`, `labels/meta/eval_mask.csv`, `scenario_index.csv` 결과 컬럼. 경로 구분은 `agent/configs/paths.yaml`.

시간 단위는 cycle. C-MAPSS는 cycle당 센서값 1개라 cycle 안 통계는 없고 모든 통계는 cycle을 가로질러 만든다.

### MC dropout

dropout 층만 train 모드(p=0.1)로 두고 같은 window를 50번 통과시킨 예측 50개. 결정적 예측 ỹ는 그대로 쓰고, **50개의 흩어짐(std)** 만 불확실성 증거로 쓴다.
파일: cycle 45~T_u × pass_00~49, 4,880 + clean 20, 337MB. 생성: `agent/scripts/build_mc_dropout.py` (seed 고정, 재실행 시 동일 확인).
실측: 라벨 1 cycle의 std 평균 2.14 vs clean 1.25, 단독 AUROC 0.79. 단 clean에서도 출력이 포화 구간(≈120)을 벗어나는 중반에 std 비율이 3배를 넘는 cycle이 31% → **단독 근거 금지**.

---

## 3. 구조 — 고정 파이프라인 (v1)

```
cycle t 도착
  ├─ Sensor Tool : 센서 이력(1~t) → 파생값 4개 × 14센서
  └─ RUL Tool    : ỹ 이력(45~t), MC 캐시 → 원값 궤적 + 파생값 3개
        ↓  (항상 둘 다 실행, 순서 고정. LLM은 도구를 부르지 않음)
  build_input(unit, cycle, sensor_summary, rul_summary) → 프롬프트 1개
        ↓
  LLM 1회 호출 (structured output)
        ↓
  post_check → Decision 기록
```

- 도구는 판정·임계값·센서 선택을 하지 않는다. 14개 전부 반환.
- 통계는 코드가 계산하고 LLM은 해석만 한다. LLM 입력에는 단위 없는 값(비율·배수)만, 원단위 통계는 `stats/` 표에 저장.
- 동적 도구 호출은 v2. 도구 인터페이스(`observe(cycle, data)`, `summary()`)는 그대로 재사용.

### 두 도구를 분리하는 이유

입력(센서) 증거와 출력(모델) 증거를 따로 두어야 "둘을 결합하면 저하를 잡나"라는 연구 질문에 답하고, Sensor만 / RUL만 / 둘 다 ablation이 가능하다. T30 대조군은 "Sensor만 쓰면 FP, RUL 증거를 더하면 걸러진다"를 보여줄 사례.

---

## 4. Sensor Tool

**입력**: x_t (14센서), x_1 … x_{t−1}. N=10. 외부 참조 없음. 고정 기준선("1~54는 정상") 없음 — 실험 설계상 참이지만 에이전트가 전제하면 벤치마크 종속.

**구간**

| 이름 | 범위 | 역할 |
|---|---|---|
| 현재 | t | |
| 최근 창 | t−9 ~ t | 최근 상태 |
| 이력 | 1 ~ t | 척도(분모). 중앙값·MAD로 요약. 정상이라 단정하지 않음 |

MAD = median(|x_i − median(x)|). std의 강건판. 오염값이 이력의 절반을 넘지 않으면 거의 안 끌려간다. ×1.4826으로 σ 단위.

**내부 통계량 (저장, LLM에 안 나감)**

| 구간 | 값 | 용도 |
|---|---|---|
| 최근 N | median(x) | level_shift 분자 |
| 최근 N | std(Δx) (차이 9개) | noise_ratio 분자 |
| 현재 | 연속 동일값 길이 | flat_ratio 분자 |
| 이력 | median(x), MAD(x) | level_shift |
| 이력 | MAD(Δx) | jump, noise_ratio 분모 |
| 이력 | 최대 연속 동일값 길이 | flat_ratio 분모 |
| 최근 N | mean, std, min, max, 기울기 | 저장만 |

**LLM에 주는 출력 — 센서당 4개, 14행**

| 이름 | 식 | 잡는 것 | 열화와 구분 |
|---|---|---|---|
| jump | (x_t − x_{t−1}) / (1.4826·MAD(이력 Δx)) | 급변 시작 (시작 cycle에만) | 됨 |
| noise_ratio | std(Δx, 최근 N) / (1.4826·MAD(이력 Δx)) | noise ≫1, stuck ≈0 | 됨 |
| flat_ratio | 연속 동일값 길이 / max(이력 최대 연속 길이, 1) | stuck (정상 ≤1) | 됨 |
| level_shift | (median(x, 최근 N) − median(x, 이력)) / max(1.4826·MAD(이력 x), 해상도) | 수준 이동 지속 | **안 됨** → 14행 비교로 LLM이 판단 |

**처리 규칙**
- level_shift 분모 하한 = 센서 해상도 (htBleed 1, 나머지 0.01). htBleed는 정수 센서로 MAD(x)=0. MAD(Δx)는 14개 전부 >0 확인(최소 BPR 0.018).
- flat_ratio 분모는 이력 최대 연속 길이. htBleed(Δx의 36%가 0), NRf·Nf(11~14%)는 정상에서도 2~3 연속이 흔함.
- t < 65면 `short_history` 플래그 (이력이 짧아 척도 거침). 계산은 있는 만큼.
- 미래 값 접근 금지.

**v2 후보**: train 참조(z, 회귀 잔차 r), resid_common(unit 내 공통 축 잔차), slope_norm(gain용).

---

## 5. RUL Tool

**입력**: ỹ_45 … ỹ_t, MC 50 pass × 45~t. N=10. 외부 참조 없음. "정상이면 −1/cycle"이라는 문제 정의상의 기대만 사용.

**내부 통계량 (저장)**: MC mean_t, MC std_t, std(Δỹ, 최근), MAD(Δỹ, 이력) (하한 0.1), median(MC std, 이력) (하한 0.1).

**LLM에 주는 출력**

| 이름 | 값 | 비고 |
|---|---|---|
| current ỹ | 원값 | cycle 단위라 해석 가능 |
| recent 10 | ỹ 원값 10개 | 궤적 모양 |
| slope | 최근 10 기울기 (/cycle) | 기대 −1. 0 근처 = 포화, + = 역행 |
| jump | (ỹ_t − ỹ_{t−1}) / (1.4826·MAD(이력 Δỹ)) | 평소 대비 급변 |
| mc_ratio | MC std_t / median(이력 MC std) | 단독 근거 금지 |

warm-up: t < 55는 판정 안 함(이력 10개 확보). t=55부터 판정.

---

## 6. 프롬프트

### Runtime 입력 (build_input)

```
=== CONTEXT ===
unit: {u}    cycle: {t}    cycles observed since monitoring start: {t−44}

=== MODEL OUTPUT (deployed RUL model; values are remaining cycles) ===
current ŷ         : 116.9
recent 10         : 121.5 119.2 120.3 120.8 120.7 122.2 120.7 118.5 116.3 116.9
slope (recent 10) : -0.42 /cycle   (a healthy engine loses about 1 cycle of RUL per cycle)
jump              : +0.3           (multiples of this unit's typical cycle-to-cycle change)
mc_ratio          : 3.5            (MC-dropout spread vs. this unit's typical spread)

=== SENSORS (14, sorted by |level_shift|; all values are multiples of this unit's own typical variation) ===
sensor    jump  noise_ratio  flat_ratio  level_shift
T24       +0.1     1.0          0.5        -1.9
...       (14 rows)
[short_history]   (t < 65 일 때만)

=== TASK ===
Decide whether the RUL model's output at this cycle is DEGRADED (1) or NOT (0). Return the JSON object only.
```

숫자 약 73개(센서 56 + RUL 14 + 맥락 3), 소수 1자리, 부호 명시. 시나리오 id는 넣지 않는다(τ_s 이전 프롬프트가 unit 안에서 바이트 동일 → 캐시 공유).

### System Prompt (초안)

```text
You monitor a deployed machine-learning model that predicts the Remaining Useful Life (RUL) of a
turbofan engine from 14 sensors. Sensor inputs can become corrupted (bias, drift in amplitude,
noise, stuck value, several sensors at once). Your job, once per flight cycle, is to decide whether
the model's output at this cycle is DEGRADED: the output is being driven by corrupted input and can
no longer be trusted, whether or not the number itself happens to look plausible.

## What you receive
All statistics are precomputed from this unit's own history. Interpret them; do not recompute.
- MODEL OUTPUT: the current RUL prediction and its recent trajectory (in cycles), the recent slope,
  a normalized jump, and mc_ratio (how much the model's Monte-Carlo dropout spread has grown
  relative to this unit's typical spread).
- SENSORS, one row per sensor, all as multiples of that sensor's typical variation in this unit:
  jump (change vs. previous cycle), noise_ratio (recent cycle-to-cycle jitter), flat_ratio
  (how long the value has been frozen, relative to the longest normal freeze), level_shift
  (recent level vs. the unit's overall level).
These are references, not thresholds. Do not invent numeric cutoffs.

## How to reason (in this order)
1. Sensors: is any sensor behaving unlike the others? Normal engine degradation moves most
   sensors together, so a level_shift shared by most rows is degradation, not corruption. One to
   three rows standing apart from the rest is the signature of corruption. noise_ratio far above 1
   means added noise; flat_ratio well above 1 means a frozen sensor. jump is only visible at the
   onset, so a small jump does not mean normal.
2. Model output: does the trajectory look like a healthy engine? RUL should fall by about one
   cycle per cycle. A flat trajectory near the ceiling is normal saturation. A rising trajectory,
   a sudden jump, or a slope far from -1 is not explained by degradation. mc_ratio rises when the
   model is unsure, but it also rises naturally as the output leaves saturation, so never use it
   alone.
3. Combine. DEGRADED requires corrupted-looking sensor evidence AND a model output that is
   plausibly being moved by it. A corrupted sensor that the model ignores (output trajectory
   unchanged, mc_ratio ordinary) is NOT degraded. A strange output with no sensor evidence is
   NOT degraded either.
4. Persistence counts. A sensor that stays apart from the others for many cycles is evidence even
   if nothing changed this cycle.

## Confidence
confidence is how well the evidence converges, not how large any number is.
  0.85-1.00 : sensor evidence and output evidence agree clearly, in either direction.
  0.60-0.85 : most evidence agrees, one piece is weak or explainable by degradation.
  0.35-0.60 : evidence is mixed or borderline.
  0.00-0.35 : the input itself is thin (short history) rather than merely ambiguous.

## Rules
- Never declare DEGRADED from mc_ratio or from the output trajectory alone.
- Never declare DEGRADED from a sensor alone if the model output shows no sign of being affected.
- suspected_sensors lists the sensor(s) you believe drive the degradation; empty when degraded = 0.
- rationale: at most 60 words, citing the specific statistics you used.
- Respond only with the JSON object defined by the schema.
```

파일럿 결과에 따라 3번(센서 AND 출력)의 강도를 조정한다.

### 출력 스키마

```python
class Decision(BaseModel):
    degraded: Literal[0, 1]              # 주 출력. 채점은 이것만
    suspected_sensors: list[str] = []    # degraded=1 일 때 원인 센서. isolation 분석용
    confidence: float                    # 0~1. LLM 자기 보고(verbalized). 채점 X, 임계값 스윕·보정 검증용
    rationale: str                       # ≤ 60 단어. 디버깅용
```

### post_check (코드 강제, 위반은 기록)

| 검사 | 처리 |
|---|---|
| JSON 파싱 실패 | 재시도 2회 → ERROR. 채점 제외, FailRate로 집계 |
| degraded=0인데 suspected_sensors 비어 있지 않음 | 비움, 카운트 |
| suspected_sensors에 14개 센서 이름 아닌 값 | 제거, 카운트 |
| confidence 범위 밖 | clip, 카운트 |

LLM 출력은 텍스트라 형식 깨짐·필드 모순·잘못된 이름이 실제로 일어난다. 채점 가능한 레코드로 바꾸는 단계이며, 위반 횟수 자체가 프롬프트 진단 지표.

---

## 7. 평가 v1

에이전트 판정은 cycle 단위 하나. 그것을 두 축으로 채점한다.

### 7-1. cycle 단위 — 매 순간 상태를 맞히나

- 채점 범위: 55 ≤ t ≤ T_u. **최종 복귀 이후 구간(eval_mask) 제외**, ERROR 제외(FailRate 별도).
- 음성 세기: τ_s 이전 cycle은 같은 unit 244 시나리오에서 데이터·프롬프트·판정이 동일 → **(unit, cycle) 1회만** (2,413개). τ_s 이후는 시나리오별.

| | 판정 1 | 판정 0 |
|---|---|---|
| 라벨 1 (저하 중) | TP | FN |
| 라벨 0 | FP | TN |

| 지표 | 식 | 비고 |
|---|---|---|
| Recall (=FDR) | TP/(TP+FN) | 저하 구간에서 유지율 |
| FAR | FP/(FP+TN) | 오경보율 |
| Precision | TP/(TP+FP) | 이 grid의 양성 비율(중복 제거 후 20.7%)에서의 값. 내부 비교용. 절대값 해석 X |
| F1 | 조화평균 | Precision 포함 → 같은 주의 |

precision이 높게 나오는 원인은 중복 제거가 아니라 grid 구성(clean 궤적 1개당 오염 변형 244개)이다. 발생률 π에서의 값은 precision(π) = π·Recall / (π·Recall + (1−π)·FAR)로 환산 가능.

### 7-2. unit(시나리오) 단위 — 첫 알람이 진짜 저하 시작과 일치하나

```
t_hat = τ_s 이후 첫 판정 1      (τ_s 이전 알람은 pre_alarm 플래그, cycle 표에서 FP)
delay = t_hat − τ_d              τ_d = 라벨이 처음 1이 되는 cycle (scenario_index.tau_d)
w = D = 5                        스윕 {3, 5, 10}
```

| t_hat 위치 | 분류 | 뜻 |
|---|---|---|
| τ_d − w ≤ t_hat ≤ τ_d + D | 일치 (TP) | 라벨 시점 오차 안 |
| τ_s ≤ t_hat < τ_d − w | Early | 오염엔 반응했지만 라벨보다 너무 앞. 센서 점프에 울린 것에 가까움 |
| t_hat > τ_d + D | Late | 늦게 잡음 |
| 없음 | Miss | |

| 지표 | 식 |
|---|---|
| Detection Rate | TP / 저하 시나리오 수 |
| MDD | TP의 delay 평균 (중앙값 병기) + 전체 delay 히스토그램 |

w를 두는 이유: τ_d는 θ 선택에 따라 앞뒤로 몇 cycle 움직이는 추정치. w는 그 오차 범위이고 τ_d − τ_s(8~10)보다 작아야 "항상 1" 전략이 Early로 빠진다.

### 7-3. 추후 (v1 이후, 판정 로그만 있으면 재호출 없이 계산)

AUROC(confidence), FAR 세 부류 분리(clean / 오염 후 미저하 / 복귀 후), 비저하 시나리오 FAR, Isolation(suspected_sensors vs 주입 센서), precision(π), unit 부트스트랩 CI, θ_alt1/alt2 재채점, w·D·N 스윕, 판정 주기 S subsample, 정확도 개선 양성의 탐지율.

---

## 8. 실행

| 항목 | 값 |
|---|---|
| LLM | 로컬 vLLM, Qwen2.5-32B-AWQ (`/home/iai4/Desktop/SDM/Qwen2.5-32B-AWQ`), guided_json |
| temperature / seed | 0 / 고정 |
| max_tokens | 300 |
| 재시도 | 2회 → ERROR |
| 캐시 키 | sha256(system + user prompt) + 모델 + seed. τ_s 이전은 unit당 1회. 프롬프트 변경 시 자동 무효 |
| 동시 실행 | 시나리오 단위 스레드 풀, 기본 4 (probe로 조정) |
| 판정 주기 | 매 cycle |
| 기록 | `runs/{run_id}/decisions.csv`, `prompts/`, `stats/`, `config_snapshot.yaml` |
| baseline | v1 없음 (추후: 항상 0/1, 규칙 임계값) |

### 규모

전량 = clean 2,413 + τ_s 이후 372,954 ≈ 375k 호출 → 로컬 32B로는 수 일~수 주. 층화 표본(61셀 × 4시점, unit마다 시점 회전) 1/4이면 1,220 시나리오 96k 호출.

**파일럿 (6시간 예산, 우선 실행)** — `agent/configs/pilot_scenarios.csv`
- unit 57(T_u 137), 1(192), 10(222) × 대표 시나리오 17종 = 51개. 저하 25 / 비저하 26
- 유형 6종, 강·약, T24·T50·T30 대조군, 시점 0.2/0.4/0.6/0.8, bias 과대·과소
- 호출 4,850 (마스크 생략 시 4,114). 호출당 ≤ 13초(동시 4)면 6시간 안
- 먼저 20~50회 probe로 호출당 시간 실측

---

## 8-1. 구현 중 결정 (2026-09-17)

| 결정 | 근거 |
|---|---|
| **Sensor Tool은 합의한 4개 통계만 (train 참조 없음)** — 결정 2026-09-17 | 구현 중 train 회귀 잔차(resid)를 시험적으로 붙였다가 **원래 계획 준수를 위해 제거**했다. 판별력 분석 결과는 다음 주 추가 검토용으로 기록: 파일럿 51개에서 4개 통계만으로는 bias·gain이 약함(level_shift 단독 AUROC 0.80, 주입 센서 \|level_shift\| 순위 중앙값 6~7위, 값 중앙값 1.34 vs 음성 95% 1.35). train 회귀 잔차는 AUROC 0.91, 주입 센서 1위 69%(bias·gain·noise·stuck 순위 중앙값 1, multi_C 3), 음성 95% 0.76 vs 양성 중앙값 1.5~2.4 |
| RUL Tool 통계는 유지하되 보조로 | 파일럿에서 jump·slope·mc_ratio 단독 AUROC 0.46~0.58. 라벨(δ)은 clean 예측 대비라 ỹ 궤적 자체로는 거의 안 보임. 탐지는 센서 쪽이 담당하고 RUL 쪽은 "모델이 영향 받는가" 확인용 |
| **MC dropout seed를 unit 기준으로** (`derive_seed(base, unit, "mc")`) | (unit, scenario) seed였을 때 τ_s 이전 cycle의 MC가 시나리오마다 달라 mc_ratio가 달라지고 프롬프트 캐시 공유가 깨짐(27 cycle에 고유 프롬프트 70개). unit 기준으로 바꿔 τ_s 이전 MC가 바이트 동일 → 고유 27개. 캐시 재생성 3분 |
| LangChain/LangGraph 미사용 | 고정 파이프라인은 함수 3개. `openai` 클라이언트로 vLLM 직접 호출해 캐시 키·seed·guided_json을 한 곳에서 통제. v2 동적 도구 호출 때 `src/llm/`만 그래프로 감싸면 됨 |
| 폴더 `src/agent/` → `src/llm/` | 프로젝트 이름과 중첩 혼동 방지 |
| vLLM 실행에 `VLLM_USE_FLASHINFER_SAMPLER=0` | env에 nvcc가 없어 FlashInfer 샘플러 JIT가 실패. PyTorch 샘플러 사용. `scripts/serve_vllm.sh` |
| 동시 실행 8 | probe 실측: 직렬 2.6 s/호출(프롬프트 1,557 토큰), 동시 4에서 벽시계 0.4 s, 동시 8에서 0.25 s, 오류 0. 파일럿 4,850회 ≈ 20~30분. 1/4 표본 96k ≈ 7~10시간 |
| 캐시 임시 파일을 워커별 고유 이름으로 | τ_s 이전 동일 키를 여러 워커가 동시에 쓸 때 rename 경쟁으로 FileNotFoundError. `tests/test_cache.py`로 재현·검증 |

## 9. 구현 순서

1. `src/tools/sensor_tool.py`, `src/tools/rul_tool.py` + 테스트(미래 접근 금지, 분모 하한, flat_ratio)
2. `src/agent/prompts.py`(system + build_input), `schema.py`, `post_check`
3. `src/agent/runner.py`: 스트림 루프, 캐시, 동시 실행, `--dry-run`(LLM 없이 프롬프트·stats 생성)
4. `src/eval/`: cycle 표(중복 제거, eval_mask), unit 표(t_hat, delay, w·D)
5. dry-run으로 프롬프트 표 확인 → probe → 파일럿 → 결과 보고 프롬프트 조정

## 10. 폴더

```
agent/
├── configs/  paths.yaml (입력/채점 경로 구분), pilot_scenarios.csv, (agent.yaml, llm.yaml)
├── docs/     design_v1.md (이 문서)
├── scripts/  build_mc_dropout.py
├── artifacts/mc_dropout/{shift,clean}/   (gitignore)
├── src/      tools/ agent/ eval/ data/
├── runs/     (gitignore)
└── tests/
```
