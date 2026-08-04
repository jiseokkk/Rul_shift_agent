# RUL Shift Agent

LLM 에이전트를 **고정된 RUL 모델 위의 shift 감지·보정·의사결정 레이어**로 쓰는 연구.
N-CMAPSS DS02-006 터보팬 데이터에 센서 fault(bias/gain/noise/stuck)를 주입하고,
"센서 fault vs 자연스러운 운항조건 변화"를 구분하는 shift-aware 결정 계층을 만든다.
predictor는 재학습하지 않는다 — 감지·보정은 전부 모델 바깥의 에이전트 몫.

**현재 상태 (2026-08-04)**: 본 메소드(LLM)와 비교할 **고전 베이스라인
(CUSUM·PCA) 통제 벤치마크가 완성·잠금됨** — 오염 데이터셋 50 시나리오 구축,
9개 detector 변형 실행, 최종 분석까지 완료 (`results/0804_report.md`).
다음 단계는 이 벤치마크 위에서의 LLM 에이전트 재설계.

## 0804 베이스라인 벤치마크 (완료·잠금)

계획서: `docs/0804_cusum_pca_baseline_experiment.md` (설계 근거·프로토콜·사전 등록 예상표 전부 포함)

- **데이터셋** `dataset/corrupted_dataset/` (211MB, 자기완결): native 1Hz 주입 후
  10:1 decimation. 컨트롤 3 + Block A(σ 절벽 18)/B(느린 drift 2)/C(관계 붕괴 6)/
  D(부분공간 정렬 8)/E(fault mode 9)/F(natural 중첩 4) = **test 50개 (잠금)** +
  `devset/` u20 6개(후속 LLM 튜닝 전용, 벤치마크 제외)
- **detector 9변형**: {CUSUM, PCA-T², PCA-SPE} × 입력 {Raw-Xs(14), Raw-XsW(18),
  Regime(28: regime_z+consistency_z)} — 입력 사다리로 "W 제거 vs 조건화" 분리 검증
- **프로토콜**: 듀얼 뷰(native 매 cycle q=0.99 / 비교 3-cycle q=0.97·LLM 비교용),
  hysteresis 2연속, **paired-clean 유효 탐지**(c₀ ≤ T_fault < T_clean — 자연 열화
  알람 오크레딧 차단), 상태 5분류, SAT=primary 실패, FA 예산 raw 1회/100cyc
- **검증**: 자체 CUSUM의 ARL₀를 Montgomery 문헌값과 Monte-Carlo 대조(오차 1~2.3%),
  PCA 방향성 sanity, 생성 데이터 전수 검증(pre-onset 동일성·seed 재현·delta 일치)

### 핵심 결과 (자세히: `results/0804_report.md`)

**만능 detector 없음** — 블록마다 승자가 다르고, 최강 변형도 구조적 대가를 치른다:

| 변형 | 강점 | 대가 |
|---|---|---|
| spe_regime | Block A–D 전승 (0.15σ 포함, latency ~5) | natural unit FA 15.8/100cyc — threshold로 해소 불가 |
| spe_xs | natural 최강건 (u14 FA 0, Block F 완벽) | PC1 사각 0/6, 저σ adverse(−) 전멸 |
| cusum 계열 | A–D 견실 (0.89–1.00), ramp40 누적 강점 | Block F SAT 4/4, u14 raw FA 97/100cyc |
| 공통 | — | **noise 0/54** (window-mean 표현의 구조적 사각) |

신규 발견: **방향 비대칭**(음의 bias가 자연 열화 추세에 숨음 — RUL 과대평가 방향이
더 안 잡힘), spe_xs의 natural 강건성(상관구조를 따라 움직이는 shift는 SPE에 안 보임),
비교 뷰 핸디캡 0(LLM 비교 공정성 실측), cusum_xs≡cusum_xsw(W 제거 무용 실증).

## 실행

```bash
# 환경: conda env LLMshift를 절대 경로로 사용 (conda activate가 안 먹는 머신)
PY=/home/iai4/miniconda3/envs/LLMshift/bin/python
export PYTHONPATH=/home/iai4/Desktop

# 0804 벤치마크 재현 (순서대로; 데이터셋·threshold는 결정적 재생성)
$PY -c "from han.Rul_shift_agent.core.preprocess import fit_feature_models; fit_feature_models()"
$PY -m han.Rul_shift_agent.injection.build_dataset          # 50+6 시나리오 생성·검증
$PY -m han.Rul_shift_agent.baselines.tests.sanity           # ARL0·PCA 검증
$PY -m han.Rul_shift_agent.baselines.stage2_calibrate       # 18 threshold + 안정성
$PY -m han.Rul_shift_agent.baselines.run_experiment         # 본 실험 50×9×2뷰

# (구) LLM 에이전트 파이프라인 — 표현 v2 재정렬 전까지 보류
# $PY -m han.Rul_shift_agent.llmshift.run_all --agent rule --skip_train
```

## 폴더 구조

| 폴더 | 내용 |
|---|---|
| `core/` | config, 데이터 로더(표현 v2: 전체 비행 + sliding window), 특징 적합(regime/consistency + PC1), LSTM RUL 모델(보류), 평가 |
| `injection/` | 데이터셋 생산 계층 — `engine.py`(순수 주입 수학, native 1Hz) + `build_dataset.py`(인벤토리·검증·manifest) |
| `baselines/` | 소비 계층 — `common.py`(파이프라인·듀얼 뷰·paired-clean), `cusum/`·`pca/`(표준형), `tests/`(검증), `stage2_calibrate.py`, `run_experiment.py` |
| `llmshift/` | LLM/rule 에이전트 (구 파이프라인 — 벤치마크 완성 후 재설계 예정) |
| `dataset/corrupted_dataset/` | 잠긴 벤치마크 50 + devset 6 + manifest + preview |
| `results/` | `0804_stage2_report.md`(검증·캘리브레이션·잠금), `0804_stage3/`(원자료·그림), `0804_report.md`(최종 분석), `scores/`(per-cycle score 50개 — 후속 단계 재사용) |
| `docs/` | `0804_cusum_pca_baseline_experiment.md`(계획서), `0729_..._baseline_plan.md`(전체 라인업), `references_baselines.md`(서지 검증) |

원본 데이터 `dataset/data_set/`(≈28GB)은 git에 올리지 않는다 — `config.py`의
`DATA_H5`에 N-CMAPSS DS02-006 h5를 두면 됨. LLM 경로는 `config.py`의 `LLM_PATH`.

## 재현성·잠금 규칙

- 벤치마크 50개·threshold 18개·프로토콜은 **잠금** (2026-08-04, engine 0804.1) —
  test 결과 기반 수정 금지, 사후 추가는 "추가 탐색 실험"으로 분리
- **본 메소드(LLM) 개발·튜닝은 `devset/`(u20)로만** — test는 동결 후 1회 실행
- 난수 전부 seed 고정, spec.json에 git hash·engine version 스탬프

## 다음 단계

1. LLM 에이전트 재설계 (devset 기반; 요구 사항은 `results/0804_report.md` §11 —
   감도-강건성 중재, 방향 인지, 분산형 신호 커버)
2. 라인업 확장: OC-MLP → ContextMMD → GDN (`docs/0729_..._baseline_plan.md`),
   noise/stuck 전용 baseline(variance-CUSUM, flatline)은 LLM 비교 논문 시점 추가
3. LSTM RUL 모델 표현 v2 재학습 (구 `outputs/rul_lstm.pt`는 stale)
4. 채널 일반화(압력 채널 Block A 반복), onset 랜덤화 — 추가 탐색 실험

> 구 파일럿(0728 이전: cons 기반 난이도, rule-vs-LLM 실험, grid_experiment)은
> 삭제·대체됨 — 기록은 git 이력과 `docs/NOTION_*.md` 참고.
