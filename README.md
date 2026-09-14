# agent_RUL — 사전 준비 파이프라인 (Phase A–D)

LLM 에이전트 기반 RUL 모델 성능 저하 탐지 연구의 준비 단계 코드.
설계 문서: [docs/preparation_plan_final.md](docs/preparation_plan_final.md).

```
agent_RUL/
├── RUL/            ← 원본 clone (mjliu-advertising/RUL). 수정 금지. 위치는 configs/paths.yaml
├── src/            data → model → label → analysis  (각 계층은 앞 계층 산출물만 읽음)
├── configs/        모든 숫자. label.yaml 은 D-2 후 확정값 기록
├── scripts/        00~08 번호 순 실행 (.py, OS 무관)
├── tests/          pytest
├── data/ models/ preds/ labels/ reports/   산출물 (Git 포함 여부는 .gitignore 참조)
└── docs/
```

## 설치

```bash
pip install -r requirements.txt
pytest tests/          # 원본 데이터·weight 없이 돌아가는 단위 테스트
```

## 실행 순서

| 스크립트 | Phase | 산출물 | 중단 조건 |
|---|---|---|---|
| `00_reproduce_original.py` | B-0 | `reproduce_metrics.json["original"]` | RMSE ≠ 11.85 ± 1 |
| `01_split.py` | A | `data/split/split_FD001.json`, `reports/A_split_summary.md` | — |
| `02_train_pre.py` | B-1 | `models/FD001/pre_FD0013_holdout.pt`, `data/norm/norm_params_pre_FD0013.npy` | — |
| `03_train_ft.py` | B-2 | `models/FD001/ft_s{529,530,531}.pt`, `data/norm/norm_params_ft_FD001.npy` | std=0 컬럼 ≠ [op3] 경고 |
| `04_evaluate.py` | B-3 | `reproduce_metrics.json["finetune"]`, `reports/B_reproduction.md` | RMSE > 15 |
| `05_infer_clean.py` | B-4 | `preds/FD001/clean/s{seed}/u{unit}.parquet` [time, pred, rul_true] | 결정성 실패 |
| `06_inject_infer.py` | C | `data/shifted/…`, `preds/FD001/shift/s529/…`, `scenario_index.csv`(메타) | — |
| `07_delta_analysis.py` | D-1, D-2 | `labels/FD001/delta/…`, `labels/FD001/meta/clean_variability.json`, `reports/D_delta_distribution.md` | τ_s 이전 δ ≠ 0 |
| *(사람)* | D-2 | `configs/label.yaml` θ·k·m 확정 | |
| `08_build_labels.py` | D-3~5 | `labels/FD001/state/{θ}/…`, `scenario_index.csv`(long), `reports/D_label_summary.md` | — |
| `09_reversion_diagnostics.py` | D 마감 | `labels/FD001/meta/reversion_events.csv`, `reports/D_reversion_diagnostics.md` | — |
| *(사람)* | D 마감 | `configs/label.yaml` `decision` 기록 후 `locked: true` | |
| `12_build_eval_mask.py` | D 마감 | `labels/FD001/meta/eval_mask*.csv`, `reports/D_eval_mask_summary.md` | 마스크 이후 양성 라벨 |
| `10_plot_scenario.py` | (선택) | `reports/figures/scenarios/*.png` | — |
| `11_sensor_sensitivity.py` | (선택) | `reports/B_sensor_sensitivity.md` | — |

```bash
python scripts/00_reproduce_original.py
python scripts/01_split.py
python scripts/02_train_pre.py
python scripts/03_train_ft.py
python scripts/04_evaluate.py
python scripts/05_infer_clean.py
python scripts/06_inject_infer.py
python scripts/07_delta_analysis.py
python scripts/08_build_labels.py --sensitivity
python scripts/09_reversion_diagnostics.py
python scripts/12_build_eval_mask.py
```

전체를 한 번에 돌리려면 (conda activate 포함, 단계별 로그·요약표를 `reports/log_run_all.txt` 에 남긴다):

```bash
bash scripts/run_all.sh          # 00 부터. 실패한 단계에서 중단 (00 만 경고 후 계속)
bash scripts/run_all.sh 06       # 06 부터 재시작
```

## 진단 도구

`09_reversion_diagnostics.py` — 복귀(1→0) 이벤트를 A(flicker)/B(말기 수렴)/C(진짜 복귀) 로
분류하고 (k, m) 대안을 비교한다. 기존 state parquet 은 건드리지 않는다 (메모리에서 재라벨링).

`11_sensor_sensitivity.py` — hold-out 전 window 에 센서를 하나씩 +0.5σ 이동시켜 |Δŷ| 를 잰다.
Phase C 주입이 정규화 공간에서 정확히 α 이므로 "같은 크기 주입에 모델이 얼마나 반응하는가" 와 같다.

```bash
python scripts/09_reversion_diagnostics.py --km 5,7 7,10 7,7 5,10
python scripts/11_sensor_sensitivity.py --amp 0.5
```

## 평가용 마스크

cycle 단위 채점에서는 시나리오별 '최종 1→0 전이 이후 재진입 없는 구간' 을 indeterminate 로
제외한다 (`labels/FD001/meta/eval_mask.csv`). 그 구간의 라벨 0 은 정직하지만 에이전트는
clean 예측을 볼 수 없어 δ 소멸을 관측할 방법이 없기 때문이다. **라벨 파일은 바꾸지 않는다.**
마스크 적용을 주 결과로, 미적용을 부록으로 둘 다 보고하고 마스크 비율을 명시할 것.
unit 단위 평가는 첫 진입만 쓰므로 무관하다. 근거·규모는 `reports/D_eval_mask_summary.md`.

## 시나리오 그림

`10_plot_scenario.py` 는 산출물만 읽어 한 (unit, scenario) 의 3단 패널을 그린다 (재학습·재추론 없음).
정답 RUL · clean/shift 예측 · |δ| 와 θ · 주입 센서 궤적을 τ_s / τ_d / 저하 라벨 구간과 함께 보여준다.

```bash
python scripts/10_plot_scenario.py --examples                      # 유형별 대표 + T30 음성 대조군
python scripts/10_plot_scenario.py --unit 1 --scenario bias_T24_a1.0_neg_p0.2
python scripts/10_plot_scenario.py --type gain --degraded --list   # 후보만 보기
python scripts/10_plot_scenario.py --examples --theta theta_alt1   # 적응형 θ 로
```

파일럿: `06_inject_infer.py --units 3 4 --limit 20` 처럼 일부만 돌려볼 수 있다.

주의: `00_reproduce_original.py` 는 GPU 머신에서 실행해야 한다. 원본 `pre_FD0013.pt` 가 CUDA 에서 저장됐고
원본 코드가 `map_location` 없이 `torch.load` 하기 때문이다 (RUL/ 은 수정하지 않는다). 01 이후는 CPU 에서도 동작한다.

## 검증 상태 (2026-09-15)

- `pytest tests/` 27개 통과 (torch 2.14 CPU, Python 3.14)
- 형식만 같은 합성 데이터로 01→08 전체 파이프라인 실행 확인: 5,120 주입·추론, δ assert 0건 오류, 15,360 라벨 행, 리포트 4종 생성
- 실제 C-MAPSS 데이터·GPU 에서의 재현 수치(11.85 / 12~13)는 아직 미확인

## 원본과 다른 점 (논문 기술용)

- hold-out 20 unit 을 사전학습·미세조정·정규화 통계에서 제외 (`exclude_units`)
- 정규화 통계에서 test set 제외 (원본은 train+test 합산). 사전학습·미세조정 통계는 원본처럼 별개
- FD003 id offset: 원본 `iloc[-1,0]` → 필터링된 train id 의 `max()`
- DataLoader `shuffle=True` 항상 (원본은 cuda 일 때만). GPU 실행 시 동일
- 전 cycle 슬라이딩 추론 루틴 신규 (`src/model/infer_full.py`). 원본은 test 마지막 window 만 평가
- 모델 정의는 원본 그대로 (`src/model/nets.py`). 원본 `pre_FD0013.pt` 를 그대로 로드 가능

## 검증 항목

- `tests/test_shift.py`: τ_s 이전 완전 불변, bias 크기 = α·σ_r, stuck 값 = x(τ_s), noise/multi_I seed 재현, 계획서 τ_s 표
- `tests/test_hysteresis.py`: 진입·복귀 경계, 역방향 채우기, 초기 구간, 적응 θ
- `tests/test_infer_determinism.py`: 같은 입력 두 번 → 완전 일치, window 정렬이 원본 gen_sequence 와 동일
- `tests/test_delta_labels.py`: τ_s 이전 δ≠0 예외, θ 해석, θ_alt1 바닥
