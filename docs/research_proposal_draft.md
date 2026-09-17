# 연구계획서 초안

**국문 제목**: 배포된 잔여수명 예측 모델의 입력 오염 탐지와 출력 신뢰성 판단을 위한 LLM 에이전트 연구

**영문 제목**: An LLM Agent for Detecting Input Corruption and Assessing Output Reliability of Deployed Remaining Useful Life Prediction Models

(대안 — 국문: "LLM 에이전트 기반 RUL 예측 모델 운영 중 성능 저하 탐지" / 영문: "LLM-Agent-Based Monitoring of Performance Degradation in Deployed RUL Prediction Models")

---

## 1. 연구 배경 및 필요성

항공기 엔진, 발전 설비 등 고가 장비의 잔여수명(Remaining Useful Life, RUL) 예측 모델은 학습 시점에 관측된 정상 센서 데이터를 바탕으로 만들어진다. 그러나 실제 운영 환경에서는 센서 편향(bias), 감도 변화(gain), 잡음 증가(noise), 값 고착(stuck) 같은 입력 오염이 흔히 발생하고, 이때 RUL 모델은 오염을 인식하지 못한 채 그럴듯한 숫자를 계속 출력한다. 운영자는 그 숫자가 정상 입력에서 나온 것인지 오염된 입력에 끌려간 것인지 구분할 수 없다.

기존 접근은 두 갈래로 나뉜다. (1) 통계적 공정관리·센서 고장진단(FDI) 기법은 센서 이상은 잘 잡지만 "그 이상이 예측 모델의 출력에 실제로 영향을 주는가"는 답하지 않는다. 모델이 둔감한 센서의 이상은 출력에 영향이 없어 경보가 불필요하다. (2) 예측 모델 자체의 불확실성 추정(MC dropout 등)은 출력 측 신호를 주지만 수명 단계에 따라 자연히 변해 단독으로는 오경보가 많다. 두 정보를 결합해 "지금 이 모델의 출력을 신뢰할 수 있는가"를 판단하는 층이 필요하며, 이 판단은 증거의 조합과 맥락 해석을 요구하므로 대규모 언어모델(LLM) 에이전트가 적합한 후보다.

이 연구가 다루는 근본적 어려움은 **정답 RUL을 배포 중에는 알 수 없다**는 점이다. 따라서 "모델 성능이 저하되었다"를 정확도로 정의하면 배포 환경에서 검증할 수 없다. 본 연구는 성능 저하를 **오염이 없었을 때 같은 모델이 냈을 예측(counterfactual)과의 차이**로 정의하고, 이를 기준으로 에이전트를 평가하는 실험 체계를 구축한다.

## 2. 연구 목표

1. 오염 시나리오와 성능 저하 정답 라벨을 갖춘 벤치마크 데이터셋 구축.
2. 센서 통계와 모델 출력 통계를 증거로 받아 매 운용 주기마다 "출력 신뢰 불가(저하)" 여부를 판정하는 LLM 에이전트 설계·구현.
3. 시간 단위(매 주기 상태)와 사건 단위(저하 시작 탐지·지연)의 두 축으로 에이전트를 평가하고, 규칙 기반 판정기 및 무판단 기준선과 비교.
4. 에이전트에게 주는 증거의 종류(입력 측 / 출력 측 / 결합)와 도구 호출 방식(고정 / 동적)이 탐지 성능에 미치는 영향 규명.

## 3. 연구 내용 및 방법

### 3.1 벤치마크 구축 (완료)

- 데이터: NASA C-MAPSS FD001 (터보팬 엔진 100대, 고장까지의 전 수명 궤적). 80대로 공개 Transformer RUL 모델을 학습하고 20대를 평가용으로 보존.
- 오염 주입: bias·gain·noise·stuck·다중센서(일관/무작위) 6종 × 강도 × 센서 3종 × 주입 시점 4개 = 엔진당 244 시나리오, **총 4,880 시나리오**. 모델이 둔감한 센서(T30)를 음성 대조군으로 포함해 "센서 이상 ≠ 모델 저하"를 구분하는지 시험.
- 성능 저하 라벨: δ(t) = |오염 예측 − clean 예측|이 모델의 자연 변동 95% 지점(9.4 cycle)을 넘는 상태가 7주기 중 5주기 이상 지속되면 저하. 주기별 0/1 라벨과 저하 시작 시점 τ_d. 저하 시나리오 1,345개.
- 검증: 주입·예측·라벨 전량 재계산 일치, 라벨 정의의 논리적 검토(정확도 저하와의 관계, 말기 수렴 구간 처리) 완료.

### 3.2 에이전트 설계 (v1 구현 완료)

```
매 주기 t:  Sensor Tool ∥ RUL Tool → 증거 표 → LLM 판정(JSON) → 검증 → 기록
```

- 에이전트가 볼 수 있는 것은 배포 환경에서 관측 가능한 것만: 센서 이력, 배포 모델의 출력 이력, 모델의 MC dropout 불확실성. clean 예측·정답 RUL·오염 시점은 차단(코드 수준 격리 테스트).
- Sensor Tool: 엔진 자기 이력 기준의 단위 없는 통계(급변, 요동, 고착, 수준 이동) 14센서.
- RUL Tool: 출력 궤적, 기울기(정상 기대 −1/cycle), 급변, 불확실성 비율.
- LLM(Qwen2.5-32B, 로컬 vLLM)은 도구 출력을 해석해 저하 여부·의심 센서·확신도·근거를 낸다. temperature 0, 프롬프트 해시 캐시로 재현성 확보.

### 3.3 평가 체계 (확정)

- 주기 단위: Recall(저하 구간 유지율), FAR(오경보율), Precision·F1(데이터셋 내부 비교용). 오염 전 구간은 시나리오 간 중복을 제거하고, 말기에 두 예측이 모두 0으로 수렴해 관측 불가능한 구간은 채점 제외.
- 사건 단위: 첫 경보 시점이 라벨상 저하 시작 τ_d의 ±5주기 안이면 탐지 성공. Detection Rate, 평균 탐지 지연(MDD), 이른/늦은/누락 비율, 위치 특정률(Isolation).
- 기준선: 항상-정상, 항상-저하, 규칙 임계값 판정기.

### 3.4 예비 결과와 다음 단계

1/4 층화 표본(1,220 시나리오, 약 18만 주기 판정)에서 v1 에이전트는 Recall 0.90, FAR 0.83, Detection Rate 0.27로 **무판단 항상-저하 기준선과 구분되지 않았다.** 원인 분석 결과 엔진 자기 이력만으로 만든 센서 통계는 정상과 저하를 거의 구분하지 못했고(14센서 중 최대 수준이동 1.4 vs 1.9), LLM은 주어진 규칙을 정상 데이터에도 그대로 적용해 경보를 냈다. 이는 과제가 자명하지 않음을 보여주며, 동시에 개선 방향을 특정한다.

- 센서 간 관계 기반 잔차(정상 fleet에서 학습한 다른 센서로부터의 기대값 대비 편차) 추가: 예비 분석에서 단독 판별력 AUROC 0.80 → 0.91, 오염 센서를 1위로 짚는 비율 69%.
- 정상 범위 참조(캘리브레이션) 제시와 확신도 보정.
- 동적 도구 호출(LLM이 필요한 통계를 선택)과 고정 파이프라인 비교.
- 증거 절제(ablation): 입력 측만 / 출력 측만 / 결합.
- 표본 확장: 5-fold 회전으로 평가 엔진 20 → 100.

## 4. 기대 효과

- 학술: 정답 없는 배포 환경에서 예측 모델의 신뢰성을 counterfactual 기준으로 정의·평가하는 벤치마크와 프로토콜. LLM 에이전트가 통계 증거를 결합해 "센서 이상"과 "모델 저하"를 구분하는지에 대한 실증.
- 산업: 예지보전 시스템에 붙일 수 있는 모델 감시 층. 경보 시 어느 센서가 원인인지와 판단 근거를 자연어로 제시해 운영자의 검증 부담을 줄임.
- 확장: FD002~004(다중 운전조건·고장모드), 다른 RUL 모델 구조, 실제 산업 데이터로 이전 가능한 구조.

## 5. 추진 일정

| 기간 | 내용 |
|---|---|
| 1~2개월 | 증거 개선(센서 간 잔차, 캘리브레이션) 및 프롬프트 개정, 전량 4,880 시나리오 재실험 |
| 3~4개월 | 절제 실험(증거 종류, 도구 호출 방식, LLM 종류), 규칙 기반 기준선과 비교, 5-fold 확장 |
| 5~6개월 | FD002~004 및 제2 RUL 모델로 일반화 검증, 논문 작성 |

## 6. 참고문헌 (초안 — 인용 전 원문 확인 필요)

- A. Saxena, K. Goebel, D. Simon, N. Eklund, "Damage propagation modeling for aircraft engine run-to-failure simulation," PHM 2008. (C-MAPSS)
- F. O. Heimes, "Recurrent neural networks for remaining useful life estimation," PHM 2008. (piecewise-linear RUL target)
- Y. Gal, Z. Ghahramani, "Dropout as a Bayesian approximation," ICML 2016. (MC dropout)
- J. Gama et al., "A survey on concept drift adaptation," ACM Computing Surveys, 2014.
- S. Rabanser, S. Günnemann, Z. Lipton, "Failing loudly: An empirical study of methods for detecting dataset shift," NeurIPS 2019.
- M. Basseville, I. V. Nikiforov, *Detection of Abrupt Changes: Theory and Application*, Prentice Hall, 1993. (탐지 지연·오경보율 평가 틀)
- S. J. Qin, "Statistical process monitoring: basics and beyond," J. Chemometrics, 2003. (다변량 센서 고장진단)
