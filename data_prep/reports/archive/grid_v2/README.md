# grid v2 산출물 아카이브

2026-09-16 에 gain neg α 를 1 미만으로 제한(v3)하기 전 결과. v2 는 2026-09-15 개정 grid.

## v2 grid (gain 만 v3 와 다름)
    bias    alpha [0.3, 0.5, 0.75, 1.0]  dir pos/neg
    gain    alpha [0.5, 1.0, 1.5, 2.0]   dir pos/neg   ← neg α≥1 이 문제
    noise   beta  [1.0, 2.0, 3.0]
    stuck
    multi_C alpha [0.3, 0.5]
    multi_I alpha [0.3, 0.5]
    256 시나리오/unit, 5,120 전체, 라벨 15,360 행

## 개정 사유
gain 은 x ← μ_r + (x − μ_r)(1 + d·α). neg 에서 배율 (1 − α) 는
α=1.0 → 0 (센서가 μ_r 에 고정 = stuck), α=1.5 → −0.5, α=2.0 → −1 (열화 방향 반전).
실제 파일에서 α=1.0 neg 주입 후 std 0, α≥1.5 neg 는 원본과 상관 −1.00 을 확인.
"gain" 유형 720 시나리오(unit당 3 센서 × 3 α × 4 시점)가 stuck·반전 고장이어서 유형별 통계가 섞여 있었다.
v3: gain neg α ∈ {0.25, 0.5, 0.75}, pos 는 유지. 244 시나리오/unit, 4,880 전체.

## v2 주요 수치 (θ_primary 9.399, k=5, m=7)
전체 저하율 0.319 · gain 저하율 α=0.5 0.05, 1.0 0.26, 1.5 0.43, 2.0 0.56 (pos·neg 합산)

## 파일
- `D_delta_distribution.md`, `D_label_summary.md`, `D_reversion_diagnostics.md`, `D_eval_mask_summary.md`
- `clean_variability.json` — θ 근거 (clean 예측만 쓰므로 v3 와 동일)
- `shift_grid.yaml` — v2 grid 정의
- `scenario_index.csv.gz` — v2 long-format 인덱스 (15,360 행)

parquet 산출물은 재생성 가능하므로 보관하지 않는다. gain neg α∈{1.0,1.5,2.0} 의 shifted/preds/delta/state 파일은 v3 전환 시 삭제했다.
