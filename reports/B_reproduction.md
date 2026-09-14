# Phase B — 재현 확인


## B-0 원본 그대로 실행 (2026-09-15T03:22:34)
- commit: `5bd33b2b1bb044ab4be1a8cb67fdf8a5d96d1d0a`
- RMSE = 12.29, Score = 220.15 (기대 11.85 ± 1.0) → OK

## B-3 hold-out 제외 재학습 모델의 test_FD001 평가 (2026-09-15T03:25:57)
- torch 2.11.0+cu130, RUL commit `5bd33b2b1bb044ab4be1a8cb67fdf8a5d96d1d0a`, std=0 컬럼 ['op3']
- 기대 12~13 (학습 unit 20% 감소 + 정규화 통계에서 test 제외). 15.0 초과 시 중단

| seed | rmse | score | n |
|---|---|---|---|
| 529 | 13.331 | 324.834 | 100 |
| 530 | 12.980 | 318.451 | 100 |
| 531 | 13.056 | 335.856 | 100 |

## B-4 hold-out clean 추론 검증 (seed 529)
- 결정성: 같은 입력 두 번 → 완전 일치 통과; use_deterministic_algorithms=True
- 정합성 1 (unit 당 무작위 절단점, test 방식): RMSE 11.663, Score 114.9, n=20  vs test RMSE 13.331430435180664
- 정합성 2 (전 cycle, true RUL 구간별):

| rul_range | n | rmse | bias |
|---|---|---|---|
| 0-25 | 500 | 2.837 | -0.505 |
| 25-75 | 1000 | 12.429 | 4.896 |
| 75-125 | 1737 | 14.249 | -1.818 |
| all | 3237 | 12.567 | 0.459 |
