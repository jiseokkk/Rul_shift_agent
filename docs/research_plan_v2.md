# LLM Agent 기반 RUL 모델 운영 중 센서 이상 탐지 및 예측 신뢰성 판단 연구 계획

## 1. 연구 목적 및 정의

### 1.1 연구 배경

RUL(Remaining Useful Life) 예측 모델은 학습 과정에서 관측된 정상 센서 및 운전 조건 데이터를 기반으로 설비의 잔여수명을 예측한다. 그러나 실제 운영 환경에서는 센서 bias, calibration error, noise 증가, gradual drift 등의 센서 이상이 발생할 수 있으며, 이러한 이상 입력이 발생하더라도 기존 RUL 모델은 이를 직접 인식하지 못한 채 지속적으로 RUL 값을 출력할 수 있다.

따라서 실제 RUL 모델 운영 환경에서는 예측값 자체뿐 아니라, **현재 RUL 모델에 입력되는 센서 데이터가 정상적인 상태인지 검증하고 이상 입력이 발생한 경우 해당 RUL 예측의 신뢰성에 경고를 제공할 수 있는 별도의 검증 체계**가 필요하다.

본 연구에서는 N-CMAPSS 데이터셋을 기반으로 센서 이상 상황을 구성하고, EDA 기반 통계적 Evidence와 기존 RUL 모델의 출력 정보를 활용하는 LLM Agent를 구축하여 센서 이상을 탐지하고 RUL 예측의 사용 가능성을 판단한다.

---

### 1.2 연구 목표

본 연구의 1차 목표는 다음과 같다.

> **N-CMAPSS 기반 RUL 모델 운영 과정에서 발생하는 센서 이상을 LLM Agent가 탐지하고, 탐지 결과를 기반으로 현재 RUL 예측에 대한 신뢰성 경고를 제공하는 Agent를 개발한다.**

전체 연구 흐름은 다음과 같다.

\[
\text{Sensor Fault}
\rightarrow
\text{Abnormal Sensor Behavior}
\rightarrow
\text{LLM Agent Detection}
\rightarrow
\text{RUL Reliability Screening}
\]

현재 단계에서는 실제 True RUL과의 prediction error를 이용하여

\[
\text{Correct RUL / Wrong RUL}
\]

을 직접 판정하지 않는다.

Agent는 센서 이상이 탐지된 경우,

> 현재 RUL 예측이 비정상적인 센서 입력을 기반으로 생성되었으므로 정상 상태에서의 예측과 동일하게 신뢰하기 어렵다.

는 Reliability Warning을 제공한다.

따라서 Agent의 최종 출력은 다음 두 가지로 정의한다.

\[
\boxed{\text{Sensor Status: NORMAL / FAULT}}
\]

\[
\boxed{\text{RUL Reliability: RELIABLE / WARNING}}
\]

여기서 `WARNING`은 현재 RUL 값이 실제로 틀렸음을 의미하지 않고, **입력 센서의 신뢰성이 저하된 상태에서 생성된 예측이므로 사용자 주의가 필요함**을 의미한다.

---

### 1.3 센서 이상 정의

초기 실험에서는 Ground Truth가 명확한 인위적인 센서 이상을 주입한다.

1차 실험에서는 가장 단순하고 해석이 명확한 **Single Sensor Abrupt Bias**를 사용한다.

\[
x'_t=x_t+\alpha\sigma,
\qquad t\geq t_f
\]

여기서

- \(t_f\): Sensor Fault 발생 시점 (cycle 단위. \(t_f\) cycle의 첫 샘플부터 해당 cycle 전체에 적용)
- \(\sigma\): 정상 데이터에서 해당 센서의 표준편차
- \(\alpha\): Fault Severity

초기 Severity는

\[
\alpha\in\{0.5,1.0,2.0\}
\]

으로 구성한다.

1차 실험에서는 \(\sigma\)를 위와 같이 정상 데이터의 전체 표준편차로 정의한다. 이 \(\sigma\)는 운전 조건 변동을 포함하므로 Agent가 관측하는 residual 기반 \(z_w\)(3.5) 스케일과 다를 수 있다. 따라서 1차 실험에서는 주입된 Fault가 \(z_w\) 기준으로 어느 크기에 해당하는지(\(\sigma_w/\sigma\) 비율)를 함께 기록하고, 결과 해석과 향후 severity 조정의 근거로 사용한다(17장 참조).

후속 단계에서는 다음으로 확장한다.

- Sensor Noise
- Gradual Sensor Drift
- Multiple Sensor Fault
- 복합 Sensor Fault

---

## 2. Method

### 2.1 전체 Agent 구조

초기 Agent는 복잡도를 최소화하기 위해 두 개의 Tool만 사용한다.

1. **EDA Tool**
2. **RUL Prediction Tool**

전체 구조는 다음과 같다.

```text
                N-CMAPSS Current Data
                         │
                         ▼
                   ┌───────────┐
                   │ LLM Agent │
                   └─────┬─────┘
                         │
            ┌────────────┴────────────┐
            ▼                         ▼
        EDA Tool                RUL Prediction Tool
            │                         │
   Statistical Evidence          Current RUL
                             Recent RUL trajectory
            │                         │
            └────────────┬────────────┘
                         ▼
                    LLM Reasoning
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
        Sensor Status          RUL Reliability
       NORMAL / FAULT        RELIABLE / WARNING
```

각 Tool은 최종적인 Fault 판정을 수행하지 않는다.

Tool의 역할은 **현재 상태에 대한 Evidence를 계산하여 Agent에게 제공하는 것**이며, 최종 판단은 LLM Agent가 수행한다.

---

### 2.2 시간 단위 정의

N-CMAPSS는 1 cycle(비행) 안에 1 Hz 샘플이 수천 개 존재하고, 비행 중 운전 조건 \(W\)가 계속 변화한다. 따라서 본 연구는 세 개의 시간 계층을 구분한다.

| 계층 | 단위 | 계산 주체 | 역할 |
|---|---|---|---|
| Sample | 1 Hz (subsample 간격 \(\Delta s\)) | EDA Tool | KNN 검색, residual 계산 |
| Window | cycle 내부의 고정 길이 구간 \(L_w\) | EDA Tool | 통계량 계산 |
| Cycle | 1 비행 | EDA Tool / Agent | window 결과 집계, **Agent 판정** |

```text
cycle t (예: 비행 2h, 7,200 samples)
  ├─ window 1  [0, L_w)        → window statistics
  ├─ window 2  [L_w, 2L_w)     → window statistics
  ├─ ...
  └─ window n_t                → window statistics
                 │
        cycle-level aggregation
                 │
        Agent 판정 (cycle t 종료 시점, 1회)
```

- Window는 cycle 내부에서 비중첩으로 구성한다. 초기값은 \(L_w=5\) min, subsample 간격 \(\Delta s=10\) s.
- 비행 길이에 따라 cycle당 window 수 \(n_t\)는 달라진다.
- **Agent는 매 cycle 종료 시점에 1회 판정한다.** 운영 환경에서 검사 주기 \(S\)를 늘리는 경우의 영향은 13장의 Sensitivity Analysis로 다룬다.
- Sensor Fault는 cycle 경계에서 주입되므로 \(t_f\) cycle은 모든 window가 고장 영향을 받는다.

---

## 3. 정상 Reference 구축

EDA Tool을 이용하여 센서 이상을 판단하기 위해서는 현재 센서 상태를 비교할 정상 기준이 필요하다.

본 연구에서는 두 종류의 Normal Reference를 동시에 사용한다.

\[
\boxed{
\text{Global Normal Reference}
+
\text{Operating-condition-aware Local Reference}
}
\]

---

### 3.1 Global Normal Reference

Clean Training Data 전체를 이용하여 센서별 정상 통계량을 미리 계산한다.

\[
R_G=P_{\text{train}}(X)
\]

초기에는 센서별 다음 통계량을 사용한다.

\[
Mean_G,\ Median_G,\ Std_G,\ IQR_G
\]

Global Reference는

> **현재 Sensor Window가 전체 Clean Training Data의 일반적인 정상 통계 특성과 얼마나 다른가**

를 확인하기 위한 기준이다.

---

### 3.2 Operating-condition-aware Local Reference

N-CMAPSS에서는 정상 상태에서도 운전 조건 \(W\)에 따라 센서값이 달라질 수 있다.

따라서 Global Reference만 사용할 경우 정상적인 operating variation을 Sensor Fault로 오인할 가능성이 존재한다.

이를 방지하기 위해 현재 분석 Window의 운전 조건과 유사한 Clean Training Data를 KNN으로 검색하여 Local Normal Reference를 구성한다.

---

### 3.3 Window 단위 KNN Reference

cycle \(t\)의 \(k\)번째 window에 샘플된 subsample된 샘플 집합을

\[
X^{(t,k)}=\{x_j\},\qquad W^{(t,k)}=\{W_j\}
\]

라고 한다. EDA는 window 단위로 통계량을 계산하기 때문에 Local Reference 역시 window 내부의 **모든 샘플의 운전 조건을 고려하여 구성한다.**

각 샘플의 운전 조건 \(W_j\)에 대해 Clean Training Data에서 가장 가까운 \(K\)개의 운전 조건을 검색한다.

\[
\mathcal{N}_{K}(W_j)
=
KNN(W_j,\{W_i^{train}\})
\]

전체 과정은 다음과 같다.

```text
Window (t, k)

W_j1 ── KNN ── K개의 Clean Training Samples
W_j2 ── KNN ── K개의 Clean Training Samples
 ...
W_jn ── KNN ── K개의 Clean Training Samples

                    │

          매칭되는 Sensor 값 추출

                    │

  (a) W-conditioned Normal Reference  (K·n개 pooling)
  (b) 샘플별 기댓값  E[x_j | W_j] = mean of K neighbors
```

(a)는 window 통계량과 비교할 정상 통계 특성을 표현하고, (b)는 샘플별 residual

\[
r_j = x_j - E[x_j\mid W_j]
\]

을 계산하기 위해 사용한다. Residual은 운전 조건에 의한 변동을 제거한 값이므로, window 내부의 운전 조건 변화에 의해 reference 분산이 부풀려져 bias가 가려지는 문제를 방지한다.

---

### 3.4 KNN 검색 방법

KNN에는 Sensor \(X\)를 사용하지 않고 **Operating Condition \(W\)만 사용한다.**

이는 Fault가 주입된 센서값이 정상 Reference 검색 자체에 영향을 미치는 것을 방지하기 위함이다.

운전 조건 변수는 Clean Training Data를 기준으로 Standardization한다.

\[
W'_j
=
\frac{W_j-\mu_j^{train}}
{\sigma_j^{train}}
\]

이후 Euclidean Distance를 사용한다.

\[
d(W_a,W_b)
=
\sqrt{\sum_j(W'_{a,j}-W'_{b,j})^2}
\]

초기 K 후보는

\[
K\in\{50,100,200,500\}
\]

로 설정하고 Clean Validation Data를 통해 결정한다.

KNN은 Fault Detector가 아니라,

\[
\boxed{\text{Operating-condition-aware Normal Reference Retrieval}}
\]

을 위한 deterministic한 검색 방법으로 사용한다.

---

### 3.5 Window 통계량 Calibration

Window residual mean은 수천 개 샘플의 평균이므로 샘플 단위 residual보다 변동 폭이 훨씬 작다. 따라서 window 통계량의 크기를 해석하기 위해 Clean Validation Data의 모든 window에 대해

\[
\bar r^{(t,k)} = \frac{1}{n}\sum_j r_j
\]

를 계산하고, 그 분포의 표준편차를 센서별 \(\sigma_w\)로 저장한다. 이후 모든 window의 residual mean을

\[
z_w^{(t,k)} = \frac{\bar r^{(t,k)}}{\sigma_w}
\]

로 정규화하여 제공한다. 또한 Clean Validation에서의 \(|z_w|\) 분포의 95% 분위 \(q_{95}\)를 저장한다.

\(\sigma_w\)와 \(q_{95}\)는 Fault 판정 threshold가 아니라, **정상 상태에서 해당 통계량이 어느 정도 변동하는지를 Agent에게 알려주는 calibration 정보**이다.

---

## 4. EDA Tool

### 4.1 역할

EDA Tool의 역할은 다음과 같이 정형화한다.

\[
\boxed{
\text{Calculate}
\rightarrow
\text{Retrieve}
\rightarrow
\text{Compare}
\rightarrow
\text{Aggregate}
\rightarrow
\text{Return}
}
\]

구체적으로는 다음을 수행한다.

**Window 단위 (cycle 내부의 각 window마다)**

1. Window 샘플의 통계량 계산
2. Global Normal Reference 조회
3. Window 내 샘플의 운전 조건을 이용한 KNN 검색
4. W-conditioned Normal Reference 및 샘플별 기댓값 계산
5. Residual 및 정규화 통계량 \(z_w\) 계산
6. Window의 각 Reference 간의 통계적 차이 계산

**Cycle 단위 (cycle 종료 시)**

7. 해당 cycle의 모든 window 결과를 cycle-level 집계값으로 요약
8. 현재 cycle의 window 시계열과 이전 cycle들의 집계값을 Agent에게 반환

EDA Tool은 다음을 수행하지 않는다.

- Sensor Fault 여부 결정
- NORMAL / FAULT label 생성
- 임의 Threshold를 통한 Fault 판정
- 이상 센서 Top-K 선택
- 특정 센서 제거

초기 실험에서는 **모든 분석 대상 센서의 Evidence를 Agent에게 제공한다.**

---

### 4.2 EDA 통계량

**Window 단위 통계량.** 초기에는 raw 센서값과 residual 각각에 대해 다음 네 가지를 사용한다.

| 통계량 | 통계적 의미 | 주요 이상 표현 |
|---|---|---|
| Mean | 분포 중심 | Bias |
| Median | 이상치에 강건한 분포 중심 | Bias |
| Standard Deviation | 센서 변동성 | Noise |
| IQR | 이상치에 강건한 분포 폭 | Noise |

Residual mean은 \(\sigma_w\)로 정규화한 \(z_w\)로, residual std는 Clean Validation의 residual std 중앙값에 대한 비율로 함께 제공한다.

**Cycle 단위 집계량.** 한 cycle의 \(n_t\)개 window 결과를 센서별로 다음과 같이 요약한다.

| 집계량 | 정의 | 의미 |
|---|---|---|
| \(z_w\) median | window별 \(z_w\)의 중앙값 | cycle 전체의 위치 이동 |
| \(z_w\) max / min | window별 \(z_w\)의 최댓값·최솟값 | 부분 구간의 이동, spike |
| Exceedance | \(|z_w|>q_{95}\)인 window 수 / \(n_t\) | 이상값이 cycle의 어느 비율에 걸쳐 있는가 |
| First exceed | 처음 \(|z_w|>q_{95}\)가 된 window 번호 | cycle 내 발생 위치 |
| Std ratio median | window별 residual std ratio의 중앙값 | 변동성 변화 |
| Raw vs Global | cycle 전체 raw mean의 Global 편차 | 절대 범위 이탈 |
| Step contrast \(\Delta_\mu\) | 4.3 참조 | 이전 cycle 대비 위치 변화 |
| Spread contrast \(\Delta_\sigma\) | 4.3 참조 | 이전 cycle 대비 변동성 변화 |
| \(T^2\), 센서별 contribution | 4.4 참조 | 다변량 이탈 및 단일 센서 여부 |

후속 단계에서 필요에 따라 다음을 추가한다.

- Q05 / Q95
- Slope
- Lag-1 Autocorrelation
- Skewness
- Kurtosis

---

### 4.3 Cycle 간 변화 통계량 (Step / Spread Contrast)

인접 구간의 평균·분산 차이를 정상 변동 폭으로 정규화한 통계량은 change-point detection의 가장 기본적인 local discrepancy statistic이며 [1, 2], CUSUM [3]의 단위 통계량이기도 하다. EvoTS-Agent [4] 역시 이를 EDA meta-feature로 사용한다. 본 연구에서는 이를 cycle 단위 residual 통계량에 적용한다.

현재 cycle \(t\)의 \(z_w\) median을 \(\tilde z_t\), 이전 \(L_c\)개 cycle의 \(\tilde z\) 중앙값을 \(\tilde z_{prev}\)라 하면

\[
\Delta_\mu(t) = \tilde z_t - \tilde z_{prev}
\]

동일하게 std ratio median \(\tilde s_t\)에 대해

\[
\Delta_\sigma(t) = \tilde s_t - \tilde s_{prev}
\]

로 정의한다. 두 값은 이미 정규화된 통계량의 차이이므로 추가 정규화가 필요하지 않다.

[1, 4]에서와 차이는 두 가지이다. (i) 원시계열이 아니라 W-conditioned residual에 적용하여 운전 조건 변동이 아닌 센서 자체의 변화만 반영한다. (ii) 데이터셋 전체의 최댓값(meta-feature)이 아니라 매 cycle 계산하여 판정 evidence로 사용한다.

---

### 4.4 다변량 Residual 통계량 (Hotelling \(T^2\) 및 Contribution)

단일 센서 고장과 여러 센서가 함께 이동하는 열화·운전 조건 미반영을 구분하기 위해, 센서별 통계량과 별도로 **다변량 통계량**을 제공한다. Hotelling \(T^2\) [5]는 다변량 공정 모니터링(MSPC)의 표준 통계량이며 [6, 7], PCA 기반 센서 고장 식별 [8]의 기반이 된다.

Window \((t,k)\)의 센서별 residual mean 벡터를 \(\bar{\mathbf r}^{(t,k)}\in\mathbb R^{p}\)라 하고, Clean Validation window들의 \(\bar{\mathbf r}\)로부터 평균 \(\boldsymbol\mu_r\)과 공분산 \(\boldsymbol\Sigma_r\)을 추정한다.

\[
T^2_{(t,k)} = (\bar{\mathbf r}^{(t,k)}-\boldsymbol\mu_r)^\top \boldsymbol\Sigma_r^{-1} (\bar{\mathbf r}^{(t,k)}-\boldsymbol\mu_r)
\]

센서 \(i\)의 contribution은 [9, 10]의 분해를 따라

\[
c_i^{(t,k)} = (\bar r_i - \mu_{r,i})\cdot\big[\boldsymbol\Sigma_r^{-1}(\bar{\mathbf r}-\boldsymbol\mu_r)\big]_i,
\qquad \sum_i c_i = T^2
\]

로 정의한다. Cycle 단위로는 \(T^2\)의 median과 max, 그리고 contribution 비율 \(c_i/T^2\)의 cycle median을 센서별로 제공한다.

\(T^2\)의 해석 기준으로 Clean Validation에서의 \(T^2\) 분포(median, 95% 분위)를 함께 제공한다. 이는 3.5의 \(\sigma_w\), \(q_{95}\)와 같이 calibration 정보이며 threshold가 아니다.

Contribution이 한 센서에 집중되면 단일 센서 고장을, 여러 센서에 분산되면 시스템 수준 변화(열화, 운전 조건 미반영)의 evidence가 된다. 단, contribution plot에는 smearing 효과 [7]가 알려져 있으므로 Agent는 이를 단독 근거가 아닌 센서별 \(z_w\)와 함께 해석한다.

\(\boldsymbol\Sigma_r\)이 ill-conditioned인 경우 PCA 기반 \(T^2\)/SPE [7]로 대체할 수 있으며, 이는 Clean Validation에서 조건수를 확인한 뒤 결정한다.

---

## 5. EDA Tool이 Agent에게 제공하는 정보

Agent 입력은 두 층으로 구성한다.

\[
\boxed{
\text{이전 } L_c \text{ cycle의 Cycle-level 집계값}
+
\text{현재 cycle의 Window-level 시계열}
}
\]

- 판정 대상인 **현재 cycle**은 내부 window 통계량을 압축하지 않고 시계열 그대로 제공하여 cycle 내부의 발생 위치와 spike를 보존한다.
- **이전 cycle들**은 정상 변동 폭을 보여주는 배경 정보이므로 집계값으로 압축한다. 초기값은 \(L_c=4\) (현재 cycle 포함 최근 5 cycle).

이 구성은 window 시계열 전체를 여러 cycle에 걸쳐 제공하는 방식(입력 폭발)과 모든 cycle을 집계값으로만 제공하는 방식(현재 cycle 내부 정보 손실)의 중간에 해당한다.

---

### 5.1 Window-level Statistics (현재 cycle)

현재 cycle의 각 window에 대해 다음을 제공한다.

```text
Sensor S7, cycle 103, window 1/24

Current Window
Mean   = 5.32
Median = 5.28
Std    = 0.44
IQR    = 0.57

Residual (x - E[x|W])
Mean   = +0.71   (z_w = +2.9)
Median = +0.69
Std    = 0.21    (std ratio = 1.0)
IQR    = 0.28
```

Agent에게는 24개 window의 전체 block을 반복하지 않고, 핵심 정규화 값의 시계열로 압축하여 제공한다.

```text
Sensor S7, cycle 103 (24 windows)
z_w        : +2.9 +3.1 +2.8 +3.0 +2.9 +2.7 ... +2.8
std ratio  :  1.0  1.0  0.9  1.1  1.0  1.0 ...  1.0
```

---

### 5.2 Global Normal Statistics

전체 Clean Training Data 기준 정상 통계량.

```text
Global Normal Reference
Mean   = 3.91
Median = 3.88
Std    = 0.61
IQR    = 0.79
```

---

### 5.3 Current vs Global Difference

현재 cycle의 raw 통계량과 Global Reference 사이의 차이를 기계적으로 계산한다.

Mean의 경우

\[
D_{\mu,G}
=
\frac{\mu_{current}-\mu_G}
{\sigma_G}
\]

Std의 경우

\[
R_{\sigma,G}
=
\frac{\sigma_{current}}
{\sigma_G}
\]

와 같이 계산할 수 있다.

```text
Current vs Global
Mean deviation   = +0.41
Std ratio        = 0.72
```

Global 비교는 운전 조건 변동을 포함하므로 절대 범위 이탈 확인용 보조 정보로 사용한다.

---

### 5.4 W-conditioned Normal Statistics

Window 내 샘플들의 운전 조건과 유사한 Clean Training Samples를 pooling하여 계산한 정상 통계량.

```text
W-conditioned Normal Reference
Mean   = 4.61
Median = 4.59
Std    = 0.43
IQR    = 0.58
```

---

### 5.5 Current vs W-conditioned Difference

Window raw 통계량과 W-conditioned Reference의 차이.

```text
Current vs W-conditioned
Mean deviation   = +1.65
Std ratio        = 1.02
```

이 값의 분모 \(\sigma_{W}\)는 window 내부의 운전 조건 변동을 포함하므로, 위치 이동의 크기는 5.1의 residual \(z_w\)를 1차 근거로 삼는다.

---

### 5.6 Cycle-level Aggregation (이전 cycle)

이전 \(L_c\)개 cycle에 대해 4.2의 집계량을 제공한다.

```text
Sensor S7
  cycle          :  99    100   101   102
  z_w median     : +0.1  -0.2  +0.0  +0.1
  z_w max        : +0.6  +0.4  +0.5  +0.7
  exceedance     : 0/22  1/24  0/23  0/24
  first exceed   :  -     -     -     -
  std ratio      : 1.0   1.1   0.9   1.0
  raw vs Global  : +0.3  +0.3  +0.4  +0.4
  Δμ / Δσ        : +0.1/+0.0  -0.3/+0.1  +0.2/-0.2  +0.1/+0.1
  T² contrib     : 0.06  0.08  0.05  0.07
```

Cycle 단위 다변량 통계량 (모든 센서 공통):

```text
Multivariate (residual T²)
  cycle          :  99    100   101   102   103
  T² median      :  9.8   11.2  10.1  10.6  61.4
  T² max         : 15.3   17.0  14.8  16.1  68.2
  clean val ref  : median 10.4, q95 19.7
  top contrib    : S7 0.86 (cycle 103)
```

EDA Tool은 이러한 수치를 계산하지만 해당 수치가 Fault인지 여부는 판단하지 않는다.

---

## 6. RUL Prediction Tool

RUL Prediction Tool은 사전에 학습된 Frozen RUL Model을 사용한다.

현재 연구에서 RUL 모델은 Sensor Fault Detector가 아니라,

> **Agent가 최종적으로 신뢰성을 Screening해야 하는 Target Prediction Model**

로 정의한다.

Agent에게 제공하는 정보는 다음과 같다.

### Current RUL Prediction

```text
Current predicted RUL = 47.3 cycles
```

### Recent RUL Prediction History

```text
55.2 → 53.7 → 51.8 → 50.4 → 47.3
```

### Prediction Change Summary

```text
Current prediction change = -3.1
Recent median change      = -1.2
```

RUL Tool 역시 현재 RUL이 정상인지, 틀렸는지를 판단하지 않는다.

---

## 7. Agent 입력 및 Prompt 구조

상세 사양(System Prompt 전문, Output Schema, Runtime Input 템플릿과 예시)은 별도 문서 `agent_spec.md`에 두고, 본 장은 설계 원칙만 기술한다.

### 7.1 System Prompt

System Prompt에는 실제 숫자는 현재 센서값을 넣지 않고 **역할, Evidence의 의미, 추론 순서, 규칙, 출력 형식**만 정의한다.

- 역할: RUL 모델 입력 센서의 Fault 여부를 cycle 단위로 판정
- Evidence 의미: \(z_w\), std ratio, \(T^2\), contribution, \(\Delta_\mu\), \(\Delta_\sigma\)의 정의와 calibration 값(\(q_{95}\), \(T^2\) median/q95)이 threshold가 아님을 명시
- 추론 순서: \(T^2\)와 contribution → 해당 센서의 현재 cycle window 시계열 → 이전 cycle 대비 → 통계량 간 일관성 → RUL 보조 확인
- 규칙: 여러 센서 동시 이동은 열화로 우선 해석, RUL 단독 판정 금지, FAULT ≠ RUL 오류, WARNING ⟺ FAULT
- Confidence: 근거가 얼마나 수렴하는지에 대한 기준을 명시하여, 앵커 없는 자유 점수가 되지 않도록 한다 (agent_spec.md §1 "Confidence calibration" 참조)
- 출력: 정의된 JSON schema만 반환

\[
\boxed{\text{System Prompt = Agent Role + Evidence Semantics + Reasoning Order + Rules}}
\]

### 7.2 Runtime User Input

매 cycle의 Evidence는 다음 순서로 구조화된 텍스트로 전달한다.

| 블록 | 내용 |
|---|---|
| EVALUATION | unit, cycle, window 수 |
| CALIBRATION | \(q_{95}\), std ratio 기준, \(T^2\) median/q95 |
| MULTIVARIATE | 최근 5 cycle의 \(T^2\) median/max, 현재 cycle 센서별 contribution (내림차순, 전 센서) |
| SENSORS | 센서별로 이전 4 cycle 집계(\(z_w\) median/max, exceedance, std ratio median) + 현재 cycle(\(\Delta_\mu, \Delta_\sigma\), exceedance, first exceed, window별 \(z_w\)·std ratio 시계열). contribution 내림차순 정렬, 전 센서 포함 |
| RUL | 현재 예측, 최근 5개, 변화량 |
| TASK | 판정 요청 |

- LLM 입력에는 **정규화된 값만** 포함한다. raw mean/median/std/IQR은 window 테이블에 저장하되 프롬프트에서 제외한다.
- 정렬은 가독성을 위한 것이며 모든 센서를 제공하므로 4.1의 "Top-K 선택 금지"와 충돌하지 않는다.
- 예상 크기: 약 1,000개 수치, 5~6k 토큰.

\[
\boxed{\text{Runtime Input = Calibration + Multivariate + Per-sensor (prev. aggregates + current window series) + RUL}}
\]

### 7.3 Output Schema

```text
sensor_status      : NORMAL | FAULT
rul_reliability    : RELIABLE | WARNING          (WARNING ⟺ FAULT, 코드에서 강제)
suspected_sensors  : list[str]                   (NORMAL이면 빈 리스트)
fault_pattern      : NONE | BIAS_LIKE | NOISE_LIKE | UNCLEAR   (진단용)
confidence         : 0.0 ~ 1.0                   (부속용, 평가 미사용)
key_evidence       : list[str], 1~4개            (판정 근거 수치)
rationale          : str, 120 단어 이내
```

출력은 Pydantic structured output으로 받고, 파싱 실패 시 최대 2회 재시도 후 `ERROR`로 기록한다. WARNING ⟺ FAULT 불일치, NORMAL인데 suspected_sensors 존재 등은 코드에서 보정하고 보정 횟수를 기록한다.

---

## 8. Agent 판단 방식

Agent는 크게 다음 순서로 Evidence를 해석한다.

### Step 1. 현재 cycle의 Window 시계열 확인

모든 센서의 현재 cycle window 시계열(\(z_w\), std ratio)을 확인하고, 이동이 cycle 전체에 걸쳐 있는지, 특정 구간부터 시작되는지, 일시적 spike인지를 파악한다.

### Step 2. 이전 cycle 집계값과 비교

현재 cycle의 값이 이전 cycle들이 보여주는 정상 변동 폭 안에 있는지, 계단형으로 벗어났는지 확인한다.

### Step 3. Global 및 W-conditioned Reference와 비교

Global 편차가 현재 운전 조건에 의해 설명 가능한 변화인지 확인한다.

특히

- Global에서는 차이가 크지만
- W-conditioned 및 residual에서는 정상에 가까운 경우

는 정상적인 operating variation일 가능성을 고려한다.

반대로 residual \(z_w\)에서는 설명되지 않는 변화는 Sensor Fault의 중요한 Evidence로 사용한다.

### Step 4. 여러 통계량 및 센서 간 일관성 확인

예를 들어

- Mean + Median 변화
- Std + IQR 유지

는 Bias-like behavior의 Evidence로 볼 수 있다.

반대로

- Mean/Median 유지
- Std/IQR 증가

는 Noise-like behavior의 Evidence가 될 수 있다.

또한 \(T^2\) contribution을 통해 변화가 하나의 센서에 집중되는지, 여러 센서에 분산되는지 확인한다. 후자의 경우 센서 고장보다 열화 또는 운전 조건 미반영 가능성을 우선 고려한다.

### Step 5. RUL Model Context 확인

RUL trajectory를 확인하되 Sensor Fault Detection의 보조 Evidence로만 사용한다.

### Step 6. 최종 판단

\[
\boxed{\text{Sensor Status: NORMAL / FAULT}}
\]

\[
\boxed{\text{RUL Reliability: RELIABLE / WARNING}}
\]

을 출력한다.

---

## 9. Agent에게 제공하지 않는 정보

실제 runtime 상황을 유지하기 위해 다음 Ground Truth 정보는 Agent에게 제공하지 않는다.

| 정보 | 용도 |
|---|---|
| Fault Injection 여부 | Evaluation |
| Fault Sensor | Evaluation |
| Fault Type | Evaluation |
| Fault Severity | Evaluation |
| Fault Onset \(t_f\) | Evaluation |
| True RUL | Evaluation |
| RUL Prediction Error | Evaluation |
| Ground Truth NORMAL / FAULT | Evaluation |

---

## 10. 실험 설계

### 10.1 Dataset

N-CMAPSS를 사용한다.

데이터를 다음과 같이 구분한다.

#### Clean Training Set

- RUL Model 학습
- Global Normal Reference 구축
- KNN 검색용 Operating Condition 및 Sensor DB 구축

#### Clean Validation Set

- K 결정
- Window 길이 \(L_w\), subsample 간격 \(\Delta s\), 이전 cycle 수 \(L_c\) 결정
- Window 통계량 calibration (\(\sigma_w\), \(q_{95}\))
- Residual 공분산 \(\boldsymbol\Sigma_r\) 추정 및 \(T^2\) calibration
- Prompt 및 실행 Parameter 결정

#### Test Set

- Clean Test Trajectory
- Sensor Fault Injected Test Trajectory

Test 데이터는 Normal Reference 구축에 사용하지 않는다.

---

### 10.2 Agent 구성

| 항목 | 설정 |
|---|---|
| LLM | Qwen2.5-32B-Instruct (quantized; 양자화 방식과 서빙 엔진은 실행 시점에 명시) |
| 파이프라인 프레임워크 | LangChain / LangGraph, 고정 DAG (EDA Tool ∥ RUL Tool → Reasoning) |
| 디코딩 | temperature 0, seed 고정 |
| Structured output | Pydantic schema (7.3), 파싱 실패 시 최대 2회 재시도 |
| 호출 | cycle 5부터 매 cycle 1회 |
| 반복 | 동일 설정 3회 |

---

## 11. 초기 Sensor Fault Scenario

초기 실험에서는 Single Sensor Abrupt Bias Fault를 사용한다.

\[
x'_t=x_t+\alpha\sigma,
\qquad t\geq t_f
\]

Severity:

\[
\alpha\in\{0.5,1.0,2.0\}
\]

이를 통해 Sensor Fault의 강도에 따른 Agent 탐지 성능을 분석한다.

---

## 12. 평가 방식

### 12.1 Fault Ground Truth

Sensor Fault를 인위적으로 주입하므로 실제 Fault Onset

\[
t_f
\]

를 정확하게 정의할 수 있다.

**Warm-up 구간.** Agent 입력은 이전 4 cycle의 집계값을 포함하므로, 각 unit의 **첫 4 cycle(cycle 1~4)을 warm-up 구간**으로 정의한다. 이 구간에서는 EDA 통계량과 cycle 집계값만 계산하여 저장하고 Agent 판정을 수행하지 않는다. Agent 판정은 cycle 5부터 시작하며, cycle 1~4는 TP / FP / FN / TN 어느 분류에도 포함하지 않고 FAR의 분모(monitored cycle)에서도 제외한다. Fault onset \(t_f\)는 수명의 30~80% 구간에서 선택하므로 warm-up 구간과 겹치지 않는다.

Agent는 cycle 5부터 매 cycle 종료 시점에 판정을 수행하며, 처음으로 `FAULT`를 출력한 cycle을

\[
\hat t
\]

라고 정의한다.

---

### 12.2 Detection Tolerance

초기 실험에서는 Fault 발생 이후 최대 \(D=5\) cycle까지 탐지를 허용한다.

\[
\boxed{
t_f
\leq
\hat t
\leq
t_f+D
}
\]

즉,

\[
0\leq\hat t-t_f\leq D
\]

인 경우 성공적인 탐지로 인정한다.

---

### 12.3 Alarm Event

연속된 FAULT 판정 하나를 **Alarm Event**로 처리하고, onset은 첫 FAULT cycle로 정의한다.

```text
Cycle : 100 101 102 103 104 105 106
Agent :  N   N   F   F   F   N   N
                  └
             onset = 102
```

NORMAL이 한 번 이상 나온 뒤 다시 FAULT가 나오면 새로운 Event로 계산한다.

---

### 12.4 TP / FP / FN / TN 정의

TP, FP, FN은 **Alarm Event 단위**로, TN은 **Trajectory 단위**로 정의한다. Event-level 탐지에서는 "정상 Event"가 존재하지 않으므로 TN은 Event 단위로 정의할 수 없기 때문이다.

#### True Positive (TP)

Faulty trajectory에서 onset이 \(t_f \le \text{onset} \le t_f + D\)인 **첫 번째** Alarm Event. Trajectory당 최대 1개이며, 탐지 지연은

\[
d = \text{onset} - t_f
\]

로 정의한다.

```text
t_f = 100, D = 5
Cycle : 99  100 101 102 103
Agent :  N   N   N   F   F     → TP, d = 2
```

TP 이후 같은 trajectory에서 발생하는 Event는 어느 분류에도 포함하지 않는다.

#### False Positive (FP)

고장이 없는 상태에서 발생한 Alarm Event. 각 Event를 1개로 계산한다.

- Clean trajectory에서 발생한 모든 Alarm Event
- Faulty trajectory에서 onset \(< t_f\)인 Alarm Event

```text
Clean  : N N F F N N F N     → FP 2개
Faulty : N F F F F F F F     → onset = 97 < t_f = 100 → FP 1개
```

두 번째 예시처럼 \(t_f\) 이전에 시작한 Alarm이 \(t_f\)를 넘겨 지속되는 경우에는 **FP로만 계산하고 TP 후보에서 제외한다.** 고장 이전부터 켜지고 있는 Alarm은 고장을 탐지한 것이 아니라 우연한 겹침이므로, 이를 TP로 인정하면 무분별하게 FAULT를 출력하는 Agent가 유리해진다.

#### False Negative (FN)

Faulty trajectory에 TP가 존재하지 않는 경우. Trajectory당 최대 1개이며, 다음 세 경우를 모두 포함한다.

| 경우 | 설명 | 추가 표시 |
|---|---|---|
| Alarm 없음 | trajectory 전체에서 FAULT 미출력 | – |
| 늦은 탐지 | Alarm이 \(t_f + D\) 이후에만 발생 | **Late** |
| 사전 Alarm 지속 | \(t_f\) 이전에 시작한 Alarm이 지속되어 \(t_f\) 이후 새 Event가 없음 | FP와 FN 동시 발생 |

```text
늦은 탐지 (t_f = 100, D = 5)
Cycle : 100 101 102 103 104 105 106 107 108
Agent :  N   N   N   N   N   N   N   F   F     → onset = 107 > 105 → FN (Late)
```

Late는 FN에 포함하여 Recall을 계산하되 별도로 집계한다. "탐지하지 못한 것"과 "늦게 탐지한 것"은 다른 실패이며, Tolerance \(D\)를 변화시키는 Sensitivity Analysis에서 Late가 TP로 전환되는 비율이 Tolerance 민감도를 보여준다.

#### True Negative (TN)

Clean trajectory에서 Alarm Event가 **0개**인 경우. Trajectory당 1개.

```text
Clean  : N N N N N N N N N N     → TN
```

#### 요약

| Trajectory | 결과 |
|---|---|
| Clean | TN (Alarm 0개) 또는 FP \(\ge 1\) |
| Faulty | TP 또는 FN (Late 포함), FP가 추가될 수 있음 |

Warm-up 구간(cycle 1~4)의 cycle은 어느 분류에도 포함하지 않는다.

---

## 13. 평가 지표

### Event-level Precision

\[
Precision=
\frac{TP}{TP+FP}
\]

### Event-level Recall

\[
Recall=
\frac{TP}{TP+FN}
\]

### Event-level F1-score

\[
\boxed{
F1=
2
\frac{Precision\cdot Recall}
{Precision+Recall}
}
\]

센서 이상 탐지의 주요 성능 지표로 사용한다.

### Mean Detection Delay

TP로 성공적으로 탐지된 Fault에 대해

\[
d_i=\hat t_i-t_{f,i}
\]

를 계산한다.

\[
\boxed{
MDD=
\frac{1}{N_{TP}}
\sum_i d_i
}
\]

이를 통해 Fault를 얼마나 빠르게 탐지하는지 평가한다.

### Late Detection Rate

FN 중 늦은 탐지의 비율을 보고한다.

\[
LateRate=\frac{N_{Late}}{N_{\text{faulty trajectories}}}
\]

### LLM 판정 실패율

Agent가 유효한 판정을 생성하지 못한 cycle의 비율을 보고한다. 판정 실패는 (i) 출력 형식 오류로 NORMAL/FAULT를 파싱할 수 없는 경우, (ii) API 오류·시간 초과로 응답이 없는 경우를 포함한다.

\[
FailRate=\frac{N_{\text{failed cycles}}}{N_{\text{evaluated cycles}}}
\]

실패한 cycle은 재시도(최대 2회) 후에도 실패하면 `ERROR`로 기록하고, TP/FP/FN 집계에서 제외한다. 이 지표는 탐지 성능이 아니라 Agent의 운영 신뢰성을 나타내며, backbone LLM 간 비교 시 함께 보고한다.

### False Alarm Rate

Clean operation에서 발생하는 불필요한 Alarm을 평가한다.

\[
FAR_{1000}
=
\frac{N_{FP}}
{N_{\text{clean monitored cycles}}}
\times1000
\]

즉 1,000 cycle당 False Alarm 발생 횟수를 보고한다. 분모인 clean monitored cycle은

\[
N_{\text{clean monitored cycles}}
=
\sum_{\text{clean traj.}} (\text{cycle 수} - 4)
+
\sum_{\text{faulty traj.}} (t_f - 5)
\]

즉 Clean trajectory의 warm-up 이후 전체 cycle과 Faulty trajectory의 warm-up 이후 \(t_f\) 이전 cycle의 합이다.

### Severity별 보고

모든 지표는 Fault Severity \(\alpha\in\{0.5,1.0,2.0\}\) 별로 분리하여 보고하고, 전체 평균도 함께 제시한다.

### 반복 실험

LLM 출력의 비결정성을 고려하여 동일 설정을 3회 반복 실행하고 평균 \(\pm\) 표준편차를 보고한다.

최종 실험에서는 Detection Tolerance를

\[
D_{max}\in\{3,5,10\}
\]

으로 변화시키는 Sensitivity Analysis를 수행한다.

### 검사 주기 Sensitivity

운영 환경에서 Agent 검사 주기를 \(S\) cycle로 늘리는 경우의 영향을 평가한다. Agent 입력은 검사 주기와 무관하게 동일하므로, \(S=1\)로 수행한 판정 결과를 \(S\) cycle 간격으로 subsampling하여 추가 LLM 호출 없이 계산한다.

\[
S\in\{1,2,3,5\}
\]

에 대해 Detection Delay와 Recall의 변화를 보고한다.

---

## 14. Ablation

### 14.1 Tool Ablation

RUL Tool의 실제 기여도를 확인하기 위해 다음을 비교한다.

\[
EDA\ only
\]

\[
RUL\ only
\]

\[
EDA+RUL
\]

### 14.2 Reference Ablation

운전 조건 기반 Reference의 효과를 확인하기 위해 다음을 비교한다.

\[
Global\ Reference\ only
\]

\[
W\text{-conditioned Reference only}
\]

\[
Global+W\text{-conditioned Reference}
\]

이를 통해 현재 운전 조건을 고려한 정상 Reference가 False Alarm 감소 및 Fault Detection 성능 개선에 실제로 기여하는지를 확인한다.

### 14.3 EDA 통계량 Ablation

\(T^2\)/contribution 유무, \(\Delta_\mu/\Delta_\sigma\) 유무를 비교하여 각 통계량이 특히 어떤 패턴의 False Alarm 감소에 기여하는지 확인한다.

---

## 15. 초기 연구 범위 요약

| 항목 | 초기 설정 |
|---|---|
| Dataset | N-CMAPSS |
| 연구 대상 | RUL 모델 운영 중 Sensor Fault |
| Agent Primary Task | Sensor Fault Detection |
| Agent 활용 목적 | RUL Reliability Screening |
| Output | NORMAL/FAULT + RELIABLE/WARNING |
| 초기 Fault | Single Sensor Abrupt Bias |
| Severity | 0.5σ / 1.0σ / 2.0σ (σ = 전체 표준편차; \(\sigma_w/\sigma\) 비율 기록) |
| Reference 1 | Global Normal |
| Reference 2 | Sample-level KNN W-conditioned Normal + Residual |
| KNN Query | Window 내 subsample된 각 샘플의 \(W\) |
| KNN Input | Operating Condition only |
| 시간 단위 | Sample(10 s) → Window(5 min) → Cycle |
| EDA Statistics | Raw 및 Residual의 Mean, Median, Std, IQR; \(z_w\) |
| Cycle 집계량 | \(z_w\) median/max/min, Exceedance, First exceed, Std ratio, \(\Delta_\mu\), \(\Delta_\sigma\) |
| 다변량 통계량 | Residual Hotelling \(T^2\) + 센서별 contribution |
| Agent EDA Input | 이전 4 cycle 집계값 + 현재 cycle window 시계열 |
| Agent 판정 주기 | 매 cycle, cycle 5부터 (첫 4 cycle은 warm-up, 평가 제외) |
| 검사 주기 \(S\) | Sensitivity Analysis로 보고 |
| Sensor Selection | 없음, 모든 센서 제공 |
| RUL Tool | Frozen RUL Prediction Model |
| Agent Prompt | System Prompt와 Runtime Evidence 분리 |
| Detection Tolerance | 5 cycles |
| Main Metric | Event-level F1 |
| Time Metric | Mean Detection Delay |
| Additional Metric | False Alarm Rate, Late Rate, LLM 판정 실패율 |
| 반복 | 동일 설정 3회, 평균 ± 표준편차 |

---

## 16. 연구자 핵심 역할 구분

본 연구에서 각 구성 요소의 역할을 다음과 같이 명확하게 구분한다.

### EDA Tool

\[
\boxed{\text{Deterministic Evidence Generator}}
\]

Window 단위로 Sensor Statistics, 정상 Reference Statistics, residual 및 두 값의 차이를 계산하고, cycle 단위로 집계하여 제공한다.

### KNN

\[
\boxed{\text{Normal Context Retriever}}
\]

샘플 단위 운전 조건에서 기대되는 정상 Sensor Reference의 기댓값 \(E[x\mid W]\)를 검색한다.

### RUL Prediction Tool

\[
\boxed{\text{Target Prediction Model}}
\]

현재 Agent가 신뢰성을 Screening해야 하는 RUL 예측값과 최근 prediction behavior를 제공한다.

### LLM Agent

\[
\boxed{\text{Evidence Interpreter + Decision Maker}}
\]

Global 및 W-conditioned 정상 기준과 Current Sensor Evidence를 종합하여 Sensor Fault 여부를 판단하고, 이를 기반으로 RUL Reliability Warning을 생성한다.

---

## 17. 향후 확장 방향

1차 연구에서는

\[
\boxed{
Sensor\ Fault
\rightarrow
Fault\ Detection
\rightarrow
RUL\ Reliability\ Warning
}
\]

구조를 검증한다.

이후에는 다음 Evidence를 추가할 수 있다.

- Fault severity의 \(\sigma\)를 W-conditioned residual window 표준편차 \(\sigma_w\) 기준으로 재정의하여, Agent가 관측하는 \(z_w\) 스케일과 일치되도록 조정 (1차 실험에서 기록한 \(\sigma_w/\sigma\) 비율을 근거로 \(\alpha\) 범위 재설정)
- 규칙 기반 Baseline과의 비교 (W-conditioned residual \(z_w\)에 적용한 CUSUM/EWMA, Clean Validation에서 FAR을 맞춘 EDA Rule threshold)
- MC-Dropout 기반 RUL uncertainty
- RUL temporal consistency
- Model support / OOD 분석
- 실제 RUL prediction error

최종적으로는

\[
Sensor\ Fault
\rightarrow
RUL\ Model\ Impact
\rightarrow
Wrong\ RUL\ Output\ Verification
\]

으로 확장하여,

> **단순히 센서 이상 여부를 탐지하는 것을 넘어 해당 센서 이상이 실제 RUL 모델의 신뢰성을 저하시켰는지 검증하는 RUL Verification Agent**

로 발전시키는 것을 목표로 한다.

---

## 18. 참고문헌

[1] C. Truong, L. Oudre, N. Vayatis, "Selective review of offline change point detection methods," *Signal Processing*, vol. 167, 107299, 2020. (Window-based / local discrepancy 방법 정리, `ruptures`)

[2] M. Basseville, I. V. Nikiforov, *Detection of Abrupt Changes: Theory and Application*, Prentice Hall, 1993.

[3] E. S. Page, "Continuous inspection schemes," *Biometrika*, vol. 41, no. 1/2, pp. 100-115, 1954. (CUSUM)

[4] L. Jiang et al., "EvoTS-Agent: A Self-Evolving LLM Agent for Financial Time Series Change Point Detection," arXiv:2608.17933, 2026. (EDA meta-feature로 local mean/variance discrepancy 사용)

[5] H. Hotelling, "Multivariate quality control," in *Techniques of Statistical Analysis*, McGraw-Hill, 1947.

[6] T. Kourti, J. F. MacGregor, "Multivariate SPC methods for process and product monitoring," *Journal of Quality Technology*, vol. 28, no. 4, pp. 409-428, 1996.

[7] S. J. Qin, "Statistical process monitoring: basics and beyond," *Journal of Chemometrics*, vol. 17, pp. 480-502, 2003. (\(T^2\)/SPE, contribution, smearing 논의)

[8] R. Dunia, S. J. Qin, T. F. Edgar, T. J. McAvoy, "Identification of faulty sensors using principal component analysis," *AIChE Journal*, vol. 42, no. 10, pp. 2797-2812, 1996.

[9] P. Miller, R. E. Swanson, C. E. Heckler, "Contribution plots: a missing link in multivariate quality control," *Applied Mathematics and Computer Science*, vol. 8, no. 4, pp. 775-792, 1998.

[10] J. A. Westerhuis, S. P. Gurden, A. K. Smilde, "Generalized contribution plots in multivariate statistical process monitoring," *Chemometrics and Intelligent Laboratory Systems*, vol. 51, no. 1, pp. 95-114, 2000.
