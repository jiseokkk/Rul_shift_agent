# 평가 v2 — 성능저하 라벨과 시나리오 단위 평가 규칙

작성 2026-10-07. design_v1.md §7 (cycle 단위 + unit 단위) 을 대체한다. 구현: `src/eval/{scenario_table,baselines,stats,report}.py`,
`scripts/evaluate.py`. v1 채점은 `src/eval/legacy_v1.py` (→ `runs/{run_id}/eval_v1/`) 에 남겨 두었다.

변경 이유: v1 의 "τ_s 이후 첫 판정 1" 은 오염 전부터 켜져 있던 경보를 τ_s 에서 첫 경보로 다시 잡아, 항상-1 판정기가
Detection Rate 0.31 을 받았다 (v1_failure_analysis.md §1.2). cycle 단위 지표는 clean 2.4k 대 무해한 오염 233k 의 불균형 때문에
사실상 "무해한 오염에 얼마나 경보하나" 를 쟀다. 변화점 탐지 관행(순차 탐지의 첫 경보 정지 시간, TCPDBench 의 허용 범위 매칭,
NAB 의 창 안 첫 탐지)에 맞춰 시나리오마다 결과 하나를 매긴다.

## 1. 데이터 구성

| 항목 | 값 |
|---|---|
| 대상 | C-MAPSS FD001 hold-out 20 unit × 오염 시나리오 244개 = 4,880 시나리오 |
| 오염 유형 | bias, gain, noise, stuck, multi_C, multi_I. 센서는 T24·T50, 그리고 음성 대조군 T30 |
| 오염 시작 τ_s | round(55 + p·(T_u − 55)), p ∈ {0.2, 0.4, 0.6, 0.8}. 모든 시나리오에서 τ_s > 55 이고 cycle 1 ~ τ_s−1 은 clean |
| 에이전트가 보는 것 | 오염된 센서, 그 입력에 대한 RUL 예측 ỹ, MC dropout |
| 채점에만 쓰는 것 | clean 예측 ŷ, δ, 라벨, τ_s, τ_d, 시나리오 메타 (`src/data/truth.py`, eval 만 import) |

## 2. 성능저하 라벨 (`data_prep/configs/label.yaml`, locked 2026-09-15)

### 2.1 출력 교란량

```
δ(t) = |ỹ(t) − ŷ(t)|,   t ∈ [45, T_u]
ỹ: 오염 입력에 대한 배포 모델(seed 529) 예측,  ŷ: 같은 모델의 clean 입력 예측
τ_s 이전 δ = 0 (전 시나리오 assert 통과)
```

### 2.2 임계값 θ

| 이름 | 값 | 근거 |
|---|---|---|
| **θ_primary (주)** | 9.399 | clean 예측의 인접 cycle 변화 \|Δŷ\| 의 95 percentile (seed 529, hold-out, n=3,217) |
| θ_alt1 | max(0.2·ŷ(t), 9.399) | 상대 기준 + 하한 |
| θ_alt2 | 13.33 | test RMSE |

### 2.3 k-of-m 히스테리시스 (k=5, m=7, θ_low = 0.5·θ) — `src/label/hysteresis.py`

- **진입:** 최근 7 cycle 중 5개 이상에서 δ > θ 이면 저하 상태. 라벨은 그 7 cycle 안에서 처음 δ > θ 였던 cycle 까지 거슬러 올라가 1 로 채운다.
- **τ_d:** 첫 진입 때 거슬러 올라간 그 cycle. 진입이 확정되는 시점보다 최대 6 cycle 앞 (오프라인 라벨이라 허용).
- **복귀:** 최근 7 중 5개 이상에서 δ ≤ θ_low 이면 같은 방식으로 0 으로 되돌린다.

### 2.4 시나리오 라벨

**저하 시나리오 = τ_d 가 존재하는 시나리오.**

| 집합 | 저하 | 비저하 |
|---|---|---|
| 전량 4,880 | 1,345 (28%) | 3,535 |
| or500 표본 | 159 (32%) | 341 |
| T30 단일 센서 (대조군) | 약 1% | — |

### 2.5 라벨의 뜻

- 라벨 1 = **오염 때문에 모델 출력이 clean 대비 θ 이상 벗어난 상태** (출력 신뢰성 상실). 정답 대비 정확도 저하가 아니다.
  라벨 1 cycle 의 27.6% 는 오히려 정답에 더 가깝다 (clean 모델의 +3~5 낙관 편향을 과소 방향 오염이 상쇄).
- |오염 오차 − clean 오차| ≤ δ 이므로 교란이 없으면 정확도 저하도 없다. 교란은 정확도 저하의 필요조건.

### 2.6 평가에 영향을 주는 라벨 성질

| 성질 | 값 | 평가에 주는 의미 |
|---|---|---|
| τ_d − τ_s | 중앙값 9, ≤5 가 25%, >30 이 13%, 최대 194 | 창이 오염 시작에 붙은 시나리오와 멀리 떨어진 시나리오가 섞임 |
| δ 증가 속도 | τ_s 이후 cycle 당 약 1.6 (45-cycle window 가 오염값으로 채워지는 속도) | τ_d 직전 경보는 "거의 맞은" 경보 → w 민감도 분석 |
| 라벨 잡음 | clean 끼리(seed 530 vs 529)도 cycle 양성 3.5%, unit 진입 30% | τ_d 자체에 몇 cycle 오차 |
| 수명 말기 복귀 | 저하 시나리오의 약 90% 가 말기에 0 으로 복귀 | 첫 진입만 쓰므로 무관. eval_mask 불필요 |

## 3. 평가 규칙

### 3.1 기호와 값 (`configs/agent.yaml` `eval:`)

| 기호 | 뜻 | 값 |
|---|---|---|
| t₀ | 첫 판정 cycle (`judge_from`) | 55 |
| Δ | 허용 지연 | 5 |
| w | 창 앞쪽 여유 | 0 |
| H | 비저하 시나리오를 τ_s 이후 지켜보는 길이 | 40 |
| k | 경보로 인정하는 연속 판정 수 | 1 |
| t̂ | 첫 경보 cycle | — |

### 3.2 경보와 t̂

- **경보:** 판정 1(DEGRADED) 이 나온 cycle. k>1 이면 k 번 연속의 첫 cycle.
- **t̂:** **t₀ 이후 첫 경보.** 오염 전 구간도 포함한다.
- **ERROR cycle:** 경보 아님. 오류율은 따로 보고.
- **첫 경보 원칙:** 시나리오의 결과는 t̂ 하나로 정해진다. 이후 경보가 유지되든, 꺼지든, 다시 켜지든 결과에 쓰지 않는다.

### 3.3 저하 시나리오 — 허용 창 W = [max(τ_s, τ_d − w), min(τ_d + Δ, T_u)]

| 결과 | 조건 | 뜻 |
|---|---|---|
| **PreContam** | t̂ < τ_s | 오염이 없는데 울림 (오경보) |
| **PreDegr** | τ_s ≤ t̂ < max(τ_s, τ_d − w) | 오염은 감지했지만 출력 저하 전에 울림 |
| **TP** | t̂ ∈ W | 허용 범위 안에서 탐지 |
| **Miss** | 창 끝까지 경보 없음 | Late 포함 |

N_D = N_TP + N_PreContam + N_PreDegr + N_Miss. 두 Pre 범주는 모두 실패이지만 고치는 방향이 다르다
(PreContam = clean 데이터 특이도, PreDegr = 무해/유해 오염 구분). PreContam 은 오염 전 구간 길이(29~115 cycle)에 크게 좌우된다.

### 3.4 비저하 시나리오 — 관찰 구간 t₀ ~ min(τ_s + H, T_u)

| 결과 | 조건 | 뜻 |
|---|---|---|
| **FP_clean** | t̂ < τ_s | 오염 전 오경보 |
| **FP_contam** | τ_s ≤ t̂ ≤ τ_s + H | 무해한 오염에 반응 |
| **TN** | τ_s + H 까지 경보 없음 | |

H = 40 은 저하 시나리오가 τ_s 이후 관찰되는 길이(τ_d + Δ − τ_s)의 90% 가 39~44 cycle 인 데 맞춘 값. 수명 끝까지 보면
비저하 쪽만 관찰 기회가 길어져(중앙값 58, 최대 115+ cycle) FAR 이 부풀고 호출 비용의 대부분이 이 꼬리에서 나온다.

### 3.5 판정 종료 (evaluation truncation)

- **종료 시점:** 저하 시나리오 **τ_d + Δ**, 비저하 시나리오 **τ_s + H** (수명 T_u 안으로). 그 뒤 cycle 은 LLM 을 호출하지 않는다.
  전량 4,880 기준 판정 cycle 741k → 527k, LLM 호출(고유 프롬프트) 375k → 162k (43%).
- **구현:** `scripts/add_end_cycle.py` 가 채점 쪽(truth)에서 `end_cycle` 을 계산해 시나리오 목록 CSV 의 열로 넣고, runner(`stream.py`)는
  그 숫자만 읽어 스트림을 끝낸다. 프롬프트·캐시 키는 바뀌지 않고 LLM 은 종료 시점을 모른다. runner 가 truth 모듈을 import 하지
  않으므로 정보 차단 규칙 2 도 유지된다. Δ 나 H 를 바꾸면 스크립트를 다시 돌린다.
- **종료 시점은 정답(τ_s, τ_d)으로 정해지므로 오프라인 벤치마크용 절단이다.** 실제 배포에서 에이전트가 τ_d 를 알고 동작하는 것으로
  해석되어서는 안 된다. 시나리오 간 기억 공유도 금지.
- **eval_mask 는 쓰지 않는다.** 창이 라벨 복귀보다 먼저 끝난다.
- **v1 실행(수명 끝까지 판정)은 재호출 없이 재채점한다.** 채점기는 판정 로그가 창 끝에 못 미치는 시나리오 수(`n_uncovered`)를 보고한다.

### 3.6 지표

**메인**

| 지표 | 정의 |
|---|---|
| Detection Rate ↑ | N_TP / N_D |
| PreContam rate ↓ | N_PreContam / N_D |
| PreDegr rate ↓ | N_PreDegr / N_D |
| Miss Rate ↓ | N_Miss / N_D |
| Detection Delay | TP 시나리오에서만 t̂ − τ_d 의 평균·중앙값 (범위 −w ~ Δ) |
| Scenario FAR ↓ | (N_FP_clean + N_FP_contam) / N_N, 두 항도 나눠서 보고 |
| Isolation ↑ | TP 시나리오 중 t̂ 시점의 suspected_sensors 에 주입 센서가 하나 이상 있는 비율. Jaccard 보조 |

**보조:** 오염 시점별 오염 전 경보율 (저하·비저하 합산) · 유형·센서·시점별 표.

### 3.7 기준선 (모든 표에 고정)

| 기준선 | 정의 | 예상 |
|---|---|---|
| 항상 0 | 경보 없음 | Miss 1.0, FAR 0 |
| 항상 1 | 매 cycle 경보 (t̂ = t₀) | PreContam 1.0, FAR 1.0 |
| 무작위 | 매 cycle 독립 확률 p 로 경보. p = 비교 대상 에이전트의 cycle 당 경보율 (p = 0.05 도 병기). 100회 평균 | 우연 수준 |
| (선택) 통계 검출기 | 도구 통계에 임계값을 건 규칙 | LLM 이 더하는 가치 |

### 3.8 민감도 분석 — 설계 단계라 제외 (2026-10-07)

w·Δ·H·k 스윕과 θ_alt 재채점은 평가에서 뺐다. 절단 시점이 τ_d + Δ / τ_s + H 라 새 실행에서는 Δ·H 를 키우는 방향의 분석은 불가능하고,
줄이는 방향은 `first_alarms.csv` 에 `classify` 를 다시 걸면 된다. 참고로 DeepSeek or500 재채점에서 w=5 면 DR 0.08 → 0.18,
k=3 이면 PreContam 0.50 → 0.13 / Miss 0.16 → 0.51 로 바뀌었다.

### 3.9 통계

- 평가 단위 시나리오, **리샘플링 단위 engine unit** (hold-out 20). unit bootstrap 95% CI (2,000회).
- 방법 간 비교는 같은 시나리오끼리 짝지어 차이를 구하고 그 차이의 unit bootstrap CI 를 보고 (`stats.paired_diff_bootstrap`).
- 같은 unit 의 오염 전 판정은 시나리오 간 동일하므로 unit 내 상관이 크다.

### 3.10 메인 표 양식

| Method | DR ↑ | PreContam ↓ | PreDegr ↓ | Miss ↓ | Delay | FAR clean / contam ↓ | Isolation ↑ |
|---|---:|---:|---:|---:|---:|---:|---:|
| 항상 0 / 항상 1 / 무작위 (p 매칭) | | | | | | | |
| LLM Agent | | | | | | | |

## 4. 실행

```bash
python agent/scripts/add_end_cycle.py --scenarios sample_or500   # 시나리오 CSV 에 end_cycle 열 (Δ·H 바꾸면 재실행)
python agent/scripts/run.py --scenarios sample_or500 --llm llm_openrouter --tag or500   # end_cycle 에서 멈춤
python agent/scripts/evaluate.py --run-id <id>                   # → runs/{id}/eval/{report.md, scenario_table.csv, first_alarms.csv, metrics.json}
python agent/scripts/evaluate.py --latest --v1                   # legacy v1 채점도 → eval_v1/
```
