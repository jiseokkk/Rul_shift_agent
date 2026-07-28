# 베이스라인 선정 + RUL 보정/의사결정 평가 설계 (문헌 조사 기반)

> 2026-07-28 문헌 조사 결과 정리. 인용은 전부 원문 페이지에서 검증됨 (미확인 항목은 표시).

---

## Part 1 — Shift 감지 베이스라인

현재: RUL-threshold, per-channel CUSUM (h는 unit 20에서 zero-FAR 캘리브레이션).
리뷰어 커뮤니티 3곳(quickest detection / streaming ML / PHM·공정 모니터링)을 모두 만족시키는 추천 세트:

### 필수 추가 (구현 비용 낮음 → 높음 순)

| # | 방법 | 계열 | 입력 | 구현 | 핵심 인용 |
|---|---|---|---|---|---|
| 1 | **Page-Hinkley** | 고전 순차 감지 | per-channel z | `river.drift.PageHinkley` (~3줄/채널) | Page 1954, Biometrika; Gama et al. 2014, ACM CSUR (스트리밍 정식화) |
| 2 | **EWMA chart** | 고전 순차 감지 | per-channel z | NumPy ~5줄 (λ=0.05–0.25, L≈2.7–3.0) | Roberts 1959; Lucas & Saccucci 1990, Technometrics |
| 3 | **GLR** | 고전 순차 감지 | per-channel z | 슬라이딩 창 ~20–30줄 (라이브러리 없음) | Willsky & Jones 1976, IEEE TAC; Basseville & Nikiforov 1993 (교과서) |
| 4 | **ADWIN** | 스트리밍 드리프트 | per-channel z (회귀에 바로 적용 가능) | `river.drift.ADWIN(delta=0.002)` | Bifet & Gavaldà 2007, SDM |
| 5 | **KSWIN** | 스트리밍 드리프트 | per-channel z (비모수 → gain fault도 잡음) | `river.drift.KSWIN` | Raab et al. 2020, Neurocomputing |
| 6 | **PCA T²/SPE(Q)** | **다변량** 공정 모니터링 | 20채널 벡터 전체 | sklearn PCA + closed-form limit ~25줄 | Jackson & Mudholkar 1979, Technometrics (Q limit); Qin 2012, Annu. Rev. Control (서베이) |
| 7 | **BOCPD** | 확률적 변화점 | per-channel 또는 SPE 스칼라 | Adams & MacKay 재귀 직접 구현 ~60–80줄 | Adams & MacKay 2007, arXiv:0710.3742 |
| 8 | **LSTM-AE 재구성 오차** | PHM 학습형 | healthy 데이터로 학습, 재구성 잔차 | 학습 필요 (비용 큼) | Malhotra et al. 2016, arXiv:1607.00148 |

선택(완전성용): DDM/EDDM (에러 이진화 필요 — 잔차를 1{|z|>τ}로 바꿔야 함, magnitude 정보 소실을 명시), Shiryaev-Roberts (CUSUM과 사실상 동급), Mahalanobis χ² chart (T²의 단순판, Ledoit-Wolf shrinkage 권장).

### 왜 이 조합인가
- **GLR**: shift magnitude를 모른다고 가정 → 우리 SNR-스윕 난이도 설계(cons 3/4/6)와 정확히 맞물림. CUSUM은 tuned δ에서만 최적.
- **PCA-SPE**: 소수 채널의 bias는 채널 간 상관을 깨뜨려 SPE에 잡힘 — 우리 consistency_z와 개념적으로 같은 신호의 "고전판". 공정 모니터링 리뷰어의 1순위 요구. contribution plot으로 fault isolation까지 됨. **주의**: DS02 비행조건 변동 때문에 raw 신호가 아니라 regime-conditioned z (우리 regime_z 파이프라인 출력)에 fit할 것.
- **BOCPD**: calibrated 확률을 내는 "확률적 추론기" — LLM 에이전트와의 내러티브 대비가 좋음.
- **ADWIN/KSWIN**: 스트리밍 ML 커뮤니티 기대치. river 한 줄이라 비용 거의 0.

### 공정성 프로토콜 (전 방법 공통)
1. 입력 통일: packets의 `z_global_vec` 시퀀스 (에이전트와 동일 신호).
2. 캘리브레이션 통일: unit 20에서 zero in-distribution FAR (CUSUM과 동일 절차). 다채널 방법은 20채널 다중검정 보정(채널별 임계 or max-statistic).
3. 평가 축 통일: recall / precision / **latency (cycles)** / FPR on natural·no_shift — `run_experiment.shift_recall` 사용 (evaluate.shift_detection의 scenario=='adverse' 하드코딩 버그 주의).

### PHM 문헌 앵커 (related work 절)
- Arias Chao et al. 2019 (arXiv:1908.01529, IJPHM 게재판 서지 미확인): C-MAPSS 계열 물리모델 잔차 기반 FDI — 가장 가까운 선행.
- Arunan et al. 2024, Control Eng. Practice (arXiv:2401.04351): C-MAPSS에서 change-point 감지를 RUL 파이프라인에 통합.
- Biggio et al. 2021 (arXiv:2104.03613): N-CMAPSS deep GP 불확실성 — MC-dropout/앙상블 분산 OOD 신호 베이스라인의 근거 인용.
- Turbofan Sensor-FDI-Bench (PHME 2026): 우리와 동일한 fault taxonomy(step/drift) 주입 벤치마크 — concurrent work로 인용.

---

## Part 2 — RUL 보정 + decision 실험 설계

### 포지셔닝 (조사 결론)
"고정된 predictor + 외부 감지·보정 에이전트"를 그대로 하는 선행 논문은 **없음**. 문헌은 네 갈래:
(a) predictor를 강건하게 재학습 (Li et al. 2023, IEEE/CAA JAS — adversarial sensor-invariant), (b) 입력 재구성/임퓨테이션 (Zhang & Liu 2022, Machines), (c) test-time adaptation (Zhang et al. 2025, IEEE TII), (d) RUL 궤적 필터링 (KF 계열, Machines 2026). → novelty claim 가능, 동시에 이 네 갈래가 보정 축의 비교 대상 후보.

### 보정 축 비교 대상 (추천 2 + 인용만 2)

1. **Kalman filter + innovation gating (필수 구현)** — 상태모델 `RUL(t+1)=RUL(t)−1`, 관측=LSTM 출력, innovation이 크면 관측 기각(gate). 우리 앵커 방식은 이것의 "관측 완전 기각" 극단 케이스라서, **"KF로 되는데 왜 LLM인가"라는 리뷰어 질문에 반드시 필요**. 구현 ~30줄. 예상 결과: no_shift/natural에선 KF가 매끈하게 이기고, shift에선 gate 임계 튜닝에 민감(우리 hysteresis+cause gate가 차별점) — 이 대비 자체가 스토리.
2. **AE 임퓨테이션 (선택 구현)** — healthy 데이터로 denoising AE 학습, 오염 채널을 재구성값으로 교체 후 **고정 LSTM에 재투입**. "출력 보정 vs 입력 복원" 대비 축. 어느 채널이 오염됐는지 isolation이 선행돼야 한다는 점을 명시(우리는 consistency contribution으로 가능).
3. TTA(c)와 robust 재학습(a)은 "predictor를 바꾸는 다른 패러다임"으로 related work에서 구분만 — 재학습 없는 것이 우리 설정의 제약 조건임을 명시.

### RUL 축 지표 (RMSE만으로는 부족)

- **NASA PHM08 비대칭 score** (Saxena et al. 2008, PHM08): d=예측−참, s=exp(−d/13)−1 (이른 예측), exp(d/10)−1 (늦은 예측). **늦은(과대) 예측을 더 무겁게 벌점** — adverse에서 LSTM이 64로 포화하는 우리 실패 모드를 정확히 벌주는 지표. clean / corrupted-uncorrected / corrected 세그먼트별 보고.
- **α-λ accuracy** (Saxena et al. 2010, IJPHM; α=0.2, λ={0.25,0.5,0.75}): 각 체크포인트에서 예측이 (1±α)·true RUL cone 안에 드는지. **"보정이 accuracy cone을 복원한다"는 헤드라인 figure**: shift 후 raw는 cone 이탈, corrected는 복귀.
- **Prognostic Horizon**: corrupted는 horizon 상실, agent는 보존 — unit별 1숫자 요약.
- NASA 공식 구현: github.com/nasa/PrognosticsMetricsLibrary.

### Decision 축 — cost 기반 평가 (문헌 표준)

핵심 인용: Nguyen & Medjaher 2019, RESS ("decision quality가 진짜 지표"의 원조); de Pater et al. 2022, RESS (alarm+safety-factor 스케줄링, cost 분해 템플릿); Mitici et al. 2023, RESS (probabilistic RUL → renewal-reward, wasted-life vs unscheduled-failure 트레이드오프).

비용 모델 골격 (문헌 공통):
```
C_total = c_p·(예방 교체 수) + c_f·(미예측 고장 수) + c_w·(교체 시점 잔여 RUL, wasted life) [+ c_i·(inspect 수)]
c_f / c_p ≈ 5–10 (민감도 분석: 2/5/10으로 스윕)
```

평가 프로토콜:
1. 각 정책이 unit 수명 동안 내린 결정 시퀀스를 시뮬레이트 — replace 실행 시점의 true RUL이 wasted life, true RUL이 0에 닿을 때까지 replace 없으면 unscheduled failure.
2. **Regret = C_policy − C_oracle** (oracle = true RUL에 threshold 적용). 시나리오별(adverse/favorable/natural/no_shift) 보고.
3. 정책 비교군: threshold-on-raw / threshold+CUSUM escalation / **threshold-on-corrected** (KF, rule anchor, LLM 각각) / oracle.
4. 부가 지표: false-alarm 수(natural·no_shift에서 불필요 inspect/replace), c_f/c_p 스윕 곡선 (LLM의 FPR 비용이 어디서 역전되는지 보여줌).

이 구조의 장점: "favorable 오탐(멀쩡한데 replace)"은 wasted life로, "adverse 미탐(64 믿고 continue)"은 c_f로 **자동으로 비대칭 벌점**이 매겨져서, 지금 threshold FNR/FPR로만 보던 것이 한 축의 돈 단위로 합쳐짐.

### 실험 매트릭스 (정리)

| 축 | 방법 | 시나리오 | 지표 |
|---|---|---|---|
| 감지 | CUSUM, PH, EWMA, GLR, ADWIN, KSWIN, PCA-SPE/T², BOCPD, (AE), rule agent, LLM | adverse(cons 3/4/6 × scope), natural, no_shift | recall, precision, latency, FPR |
| 보정 | raw LSTM, KF-gated, (AE-임퓨테이션), rule anchor, LLM | adverse, favorable (+ fallback 검증용 early-onset) | RMSE, NASA score, α-λ, PH — clean/corrupt/corrected 구간별 |
| 결정 | threshold-raw, threshold+CUSUM, threshold-corrected×{KF, rule, LLM}, oracle | 전체 | C_total 분해, regret, c_f/c_p 스윕 |

### 추가로 필요한 보강 실험
- **fallback 경로 검증**: onset 앞당기기(예: 20%) 또는 HISTORY_K 축소 — 현재 보고 성능은 전부 앵커 경로라는 한계 해소.
- **멀티 유닛**: 현재 corrupted는 unit 11 단독 — 최소 unit 14/15 (Fc 다른 방향)에도 주입해 일반화 표.

### LLM-PHM related work (차별점)
- Lukens et al. 2024 (PHM Conf.): LLM copilot — 정성 평가만.
- Deng et al. 2024 (PHME): GPT-4 RAG 정비 처방 — RUL 미사용, 정성 평가.
- PHM-GPT (Engineering 2025), PHM-Bench (arXiv:2508.02490), LLM-as-RUL-predictor 계열 (arXiv:2410.03134 등): LLM이 predictor를 **대체**.
→ "고정 predictor를 **감독·보정**하는 LLM + cost 기반 정량 decision 평가" 조합이 비어 있는 자리.
