# grid v1 (구 shift_grid) 산출물 아카이브

2026-09-15 에 `configs/shift_grid.yaml` 의 α/β 범위를 개정하기 전 결과.

## 구 grid
    bias    alpha [0.1, 0.2, 0.3, 0.5]
    gain    alpha [0.1, 0.2, 0.3, 0.5]
    noise   beta  [0.5, 1.0, 2.0]
    multi_C alpha [0.2, 0.3]
    multi_I alpha [0.2, 0.3]

## 개정 사유
저강도 구간이 전부 음성이라 라벨로 쓸 수 없었다.
- bias α=0.1 전 센서 저하율 0.00, α=0.2 도 T50(0.04) 외 0.00
- gain 최대 0.05 (T50 α=0.5) — 유형 자체가 성립 안 됨
- noise β=0.5 전 센서 0.00
- 전체 저하율 0.096, 결정 규칙 2(최저 강도 bias 에서 δ>θ 비율) = 0.000 으로 미달

개정 후: 전체 저하율 0.319, 결정 규칙 2 = 0.016 통과. 시나리오 수는 256/unit 동일.

## 파일
- `D_delta_distribution.md`, `D_label_summary.md` — 구 grid 리포트
- `clean_variability.json` — θ 산출 근거 (grid 와 무관하므로 신 grid 와 동일)
- `shift_grid.yaml` — 구 grid 정의
- `scenario_index.csv.gz` — 구 grid long-format 인덱스 (15,360 행)

구 grid 의 parquet 산출물(shifted/preds/delta/state)은 재생성 가능하므로 보관하지 않는다.
재현하려면 `shift_grid.yaml` 을 되돌리고 `bash scripts/run_all.sh 06` 을 실행한다.
