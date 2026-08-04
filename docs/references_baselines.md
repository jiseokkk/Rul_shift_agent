# 오염 데이터셋 설계 + CUSUM/PCA 베이스라인의 서지 근거 (0804 검증)

> 0804 계획 §2.6/§3.4의 인용 앵커를 웹 검증한 결과. ✓ = 원문/공식 소스로 확인됨.

## 1. 데이터셋 자체

- **Arias Chao, M., Kulkarni, C., Goebel, K., Fink, O. (2021).** "Aircraft Engine
  Run-to-Failure Dataset under Real Flight Conditions for Prognostics and
  Diagnostics." *Data* 6(1):5, MDPI. ✓
  https://www.mdpi.com/2306-5729/6/1/5 (+ NASA NTRS 20205001125)
  - 근거로 쓰는 것: X_s 14센서·W 4운항조건 정의, 실비행 조건 기록, 열화-운항이력
    연동 모델링, "마지막에 sensor noise를 추가"하는 생성 절차(→ 센서 오염이
    시뮬레이션 마지막 단계에 얹히는 구조라 우리의 사후 주입과 정합).

## 2. Fault mode 분류 (add / gain / noise / stuck / dropout)

- **Balaban, E., Saxena, A., Bansal, P., Goebel, K., Curran, S. (2009).**
  "Modeling, Detection, and Disambiguation of Sensor Faults for Aerospace
  Applications." *IEEE Sensors Journal* 9(12):1907–1917. ✓ (NASA NTRS 20090033812)
  - 항공우주 센서 fault의 표준 분류·모델링: **bias, drift, scaling(=gain),
    frozen/stuck, dropout** — 우리 mode 축과 1:1 대응.
  - "실측 fault 사례가 드물어 모델 기반 fault를 주입해 평가한다"는 방법론 자체의
    정당화 (시뮬레이션 주입 평가의 근거).

## 3. 터보팬 가스패스 센서에 bias를 주입해 FDI를 평가하는 관행

- **Kobayashi, T., Simon, D.L. (2003).** "Aircraft Engine Sensor/Actuator/Component
  Fault Diagnosis Using a Bank of Kalman Filters." NASA/CR—2003-212298 (NTRS
  20030032975). ✓
- **Kobayashi, T., Simon, D.L. (2004).** "Evaluation of an Enhanced Bank of Kalman
  Filters for In-Flight Aircraft Engine Sensor Fault Diagnostics." NASA (NTRS
  20040110846). ✓
  - fault를 **bias로 모델링해 주입**, cruise 운항점에서 평가, nominal/aged 조건
    병행 — 우리 Block A(σ 스윕)·aged-engine 관점(자연 열화 위 fault)의 선례.

## 4. 방향성(adverse −)의 물리 근거 — EGT 열전대 노화는 저평가 방향

- **WIKA 기술자료**: Type K 열전대의 aging(600–1,200°F, 소폭 상승) vs
  **drift(>1,200°F, 유의한 저하)** 구분. EGT 작동역은 후자. ✓
  https://blog.wika.com/us/knowhow/aging-and-drift-in-type-k-thermocouples/
- **가스터빈 EGT 열전대 자료**: 퇴적물·금속 조직 변화로 **실제보다 낮게 읽음 →
  과온 상태가 미탐지**되는 위험 — 우리 adverse(−, RUL 과대추정 = 열화 은폐)
  방향의 물리적 대응. ✓
- 학술 보강: "Study of thermocouple degradation through accelerated aging under
  corrosive environment" (2023) — 가속 노화 실험 계열.
  - 사용처: §2.2 방향 축의 "− 방향이 물리적으로 우세" 서사. (산업 기술자료가
    포함되므로 논문에서는 보조 인용으로 배치)

## 5. 관계 보존형(coordinated/PC1, all14) 주입의 프레이밍 — FDIA

- **Liu, Y., Ning, P., Reiter, M.K. (2009/2011).** "False Data Injection Attacks
  against State Estimation in Electric Power Grids." ACM CCS 2009; *ACM TISSEC*
  14(1), 2011. (지식 기반 확정 — 정본 인용)
  - 정상 상관구조를 보존하는 조작은 잔차 기반 탐지를 우회한다는 정식화 —
    Block D를 "자연 고장"이 아닌 "적대적(FDIA/stealth)" 카테고리로 분리 보고하는
    근거.

## 6. Detector 방법론 (0729 계획 §10–11에서 이관·통합)

- CUSUM: **Page (1954)** *Biometrika* 41:100–115; **Moustakides (1986)** *Ann.
  Stat.* (최적성); **Basseville & Nikiforov (1993)** *Detection of Abrupt Changes*;
  k=0.5 관행: **Montgomery**, *Introduction to Statistical Quality Control*.
  다변량 정본 대안: **Crosier (1988)** MCUSUM (우리는 per-channel 뱅크+max 선택,
  사유: fault isolation).
- PCA-T²/SPE: **Hotelling (1947)**; **Jackson & Mudholkar (1979)** *Technometrics*
  (SPE/Q); **Qin (2003)** *J. Chemometrics* 서베이; **Chiang, Russell, Braatz
  (2001)** 교과서. Tennessee Eastman 벤치마크의 표준 조합.
- Drift-detection 계보 등재: **Gama et al. (2014)** *ACM Computing Surveys*.

## 7. 표현 계층 (10:1 decimation + sliding window + cycle 집계)

- Arias Chao et al. (2021)의 baseline 및 DS02 후속 연구(PHM 2021 data challenge
  계열)의 일반 관행: 다운샘플링 + ~50 step window + cycle 내 집계.
  (개별 후속 논문 인용은 논문 작성 시점에 대표 2–3편 확정)

## 남은 확인 항목 (논문 작성 전)

1. EGT 센서 정확도 규격의 정식 인용원 (현재 산업 자료 → AS/SAE 규격 또는 계측
   교과서로 승격).
2. 표현 계층의 대표 후속 논문 2–3편 (DS02 RUL, 다운샘플+window 명시된 것).
3. Liu et al. FDIA 서지 페이지 재확인.
