# run 비교 (시나리오 단위 v2) — or500

작성 2026-10-07. 규약 `docs/eval_v2_scenario.md`: 첫 경보 원칙 (cycle 55 이후 첫 경보, 오염 전 포함), Δ = 5, w = 0, H = 40, k = 1. 저하 159 / 비저하 341 시나리오, unit 20. LLM 재호출 없이 기존 판정 로그를 재채점했다 (v1 실행은 수명 끝까지 판정했으므로 창이 모두 덮인다).

run: qwen2.5-32b = `Qwen2.5-32B-AWQ_full_v1_seed42_20260917-020322__or500` · deepseek-v4-pro = `deepseek-v4-pro-0813_or500_seed42_20261001-003315` · qwen3.8-27b = `Qwen3.8-27B-NVFP4_or500_seed42_20261002-175400` · qwen3.8-27b-think = `Qwen3.8-27B-NVFP4-think_or500_seed42_20261002-223719` · qwen3.6-35b-a3b = `Qwen3.6-35B-A3B-NVFP4_or500_seed42_20261002-203606`

## 1. 메인 표

저하 시나리오: DR + PreContam + PreDegr + Miss = 1. 비저하: FAR = FAR clean + FAR contam. 무작위 기준선은 매 cycle 독립 확률 p 로 경보 (100회 평균); p 는 각 run 의 cycle 당 경보율.

| method | 저하 n | DR | PreContam | PreDegr | Miss | Delay 중앙값 | 비저하 n | FAR | FAR clean | FAR contam | Isolation |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 항상 0 | 159 | 0 | 0 | 0 | 1 |  | 341 | 0 | 0 | 0 |  |
| 항상 1 | 159 | 0 | 1 | 0 | 0 |  | 341 | 1 | 1 | 0 |  |
| 무작위 p=0.128 (에이전트 경보율) | 159 | 0.003 | 0.989 | 0.006 | 0.002 | 2.200 | 341 | 1 | 0.994 | 0.006 | 0 |
| 무작위 p=0.050 | 159 | 0.018 | 0.892 | 0.045 | 0.045 | 2.042 | 341 | 0.991 | 0.936 | 0.055 | 0 |
| 무작위 (p=0.781, qwen2.5-32b 경보율) | 159 | 0 | 1 | 0 | 0 |  | 341 | 1 | 1 | 0 |  |
| **qwen2.5-32b** | 159 | 0 | 1 | 0 | 0 |  | 341 | 1 | 1 | 0 |  |
| 무작위 (p=0.128, deepseek-v4-pro 경보율) | 159 | 0.003 | 0.989 | 0.006 | 0.002 | 2.200 | 341 | 1 | 0.994 | 0.006 | 0 |
| **deepseek-v4-pro** | 159 | 0.082 | 0.503 | 0.252 | 0.164 | 0 | 341 | 0.889 | 0.660 | 0.229 | 0.846 |
| 무작위 (p=0.052, qwen3.8-27b 경보율) | 159 | 0.016 | 0.895 | 0.043 | 0.046 | 2.128 | 341 | 0.992 | 0.940 | 0.052 | 0 |
| **qwen3.8-27b** | 159 | 0.132 | 0.239 | 0.226 | 0.403 | 2 | 341 | 0.657 | 0.399 | 0.258 | 0.714 |
| 무작위 (p=0.261, qwen3.8-27b-think 경보율) | 159 | 0 | 1.000 | 0.000 | 0 |  | 341 | 1 | 1.000 | 0.000 |  |
| **qwen3.8-27b-think** | 159 | 0.013 | 0.868 | 0.113 | 0.006 | 0 | 341 | 1 | 0.956 | 0.044 | 1 |
| 무작위 (p=0.169, qwen3.6-35b-a3b 경보율) | 159 | 0.001 | 0.996 | 0.002 | 0.000 | 1.800 | 341 | 1 | 0.998 | 0.002 | 0 |
| **qwen3.6-35b-a3b** | 159 | 0.126 | 0.597 | 0.189 | 0.088 | 2 | 341 | 0.988 | 0.795 | 0.194 | 0.850 |

## 2. unit bootstrap 95% CI

| metric | run | point | 95% CI |
|---|---|---|---|
| DR | qwen2.5-32b | 0 | [0.000, 0.000] |
| PreContam | qwen2.5-32b | 1 | [1.000, 1.000] |
| PreDegr | qwen2.5-32b | 0 | [0.000, 0.000] |
| Miss | qwen2.5-32b | 0 | [0.000, 0.000] |
| FAR | qwen2.5-32b | 1 | [1.000, 1.000] |
| Isolation | qwen2.5-32b |  | [nan, nan] |
| DR | deepseek-v4-pro | 0.082 | [0.039, 0.125] |
| PreContam | deepseek-v4-pro | 0.503 | [0.369, 0.624] |
| PreDegr | deepseek-v4-pro | 0.252 | [0.179, 0.328] |
| Miss | deepseek-v4-pro | 0.164 | [0.083, 0.267] |
| FAR | deepseek-v4-pro | 0.889 | [0.783, 0.968] |
| Isolation | deepseek-v4-pro | 0.846 | [0.600, 1.000] |
| DR | qwen3.8-27b | 0.132 | [0.084, 0.188] |
| PreContam | qwen3.8-27b | 0.239 | [0.120, 0.364] |
| PreDegr | qwen3.8-27b | 0.226 | [0.163, 0.293] |
| Miss | qwen3.8-27b | 0.403 | [0.289, 0.516] |
| FAR | qwen3.8-27b | 0.657 | [0.510, 0.801] |
| Isolation | qwen3.8-27b | 0.714 | [0.474, 0.913] |
| DR | qwen3.8-27b-think | 0.013 | [0.000, 0.030] |
| PreContam | qwen3.8-27b-think | 0.868 | [0.755, 0.960] |
| PreDegr | qwen3.8-27b-think | 0.113 | [0.033, 0.216] |
| Miss | qwen3.8-27b-think | 0.006 | [0.000, 0.020] |
| FAR | qwen3.8-27b-think | 1 | [1.000, 1.000] |
| Isolation | qwen3.8-27b-think | 1 | [1.000, 1.000] |
| DR | qwen3.6-35b-a3b | 0.126 | [0.073, 0.185] |
| PreContam | qwen3.6-35b-a3b | 0.597 | [0.492, 0.697] |
| PreDegr | qwen3.6-35b-a3b | 0.189 | [0.104, 0.272] |
| Miss | qwen3.6-35b-a3b | 0.088 | [0.031, 0.166] |
| FAR | qwen3.6-35b-a3b | 0.988 | [0.977, 0.997] |
| Isolation | qwen3.6-35b-a3b | 0.850 | [0.700, 1.000] |

## 3. 기준 run (deepseek-v4-pro) 대비 짝지은 차이

같은 시나리오끼리 차이를 구하고 unit 을 복원추출한 CI. `*` = CI 가 0 을 포함하지 않음.

| 비교 | metric | diff | 95% CI | 유의 |
|---|---|---|---|---|
| qwen2.5-32b − deepseek-v4-pro | DR | -0.082 | [-0.125, -0.039] | * |
| qwen2.5-32b − deepseek-v4-pro | PreContam | 0.497 | [0.376, 0.631] | * |
| qwen2.5-32b − deepseek-v4-pro | PreDegr | -0.252 | [-0.328, -0.179] | * |
| qwen2.5-32b − deepseek-v4-pro | Miss | -0.164 | [-0.267, -0.083] | * |
| qwen2.5-32b − deepseek-v4-pro | FAR | 0.111 | [0.032, 0.217] | * |
| qwen2.5-32b − deepseek-v4-pro | Isolation |  | [nan, nan] |  |
| qwen3.8-27b − deepseek-v4-pro | DR | 0.050 | [-0.017, 0.123] |  |
| qwen3.8-27b − deepseek-v4-pro | PreContam | -0.264 | [-0.416, -0.121] | * |
| qwen3.8-27b − deepseek-v4-pro | PreDegr | -0.025 | [-0.113, 0.047] |  |
| qwen3.8-27b − deepseek-v4-pro | Miss | 0.239 | [0.126, 0.348] | * |
| qwen3.8-27b − deepseek-v4-pro | FAR | -0.232 | [-0.353, -0.112] | * |
| qwen3.8-27b − deepseek-v4-pro | Isolation | -0.132 | [-0.427, 0.139] |  |
| qwen3.8-27b-think − deepseek-v4-pro | DR | -0.069 | [-0.113, -0.027] | * |
| qwen3.8-27b-think − deepseek-v4-pro | PreContam | 0.365 | [0.256, 0.481] | * |
| qwen3.8-27b-think − deepseek-v4-pro | PreDegr | -0.138 | [-0.228, -0.045] | * |
| qwen3.8-27b-think − deepseek-v4-pro | Miss | -0.157 | [-0.265, -0.075] | * |
| qwen3.8-27b-think − deepseek-v4-pro | FAR | 0.111 | [0.032, 0.217] | * |
| qwen3.8-27b-think − deepseek-v4-pro | Isolation | 0.154 | [0.000, 0.375] |  |
| qwen3.6-35b-a3b − deepseek-v4-pro | DR | 0.044 | [-0.013, 0.106] |  |
| qwen3.6-35b-a3b − deepseek-v4-pro | PreContam | 0.094 | [-0.013, 0.225] |  |
| qwen3.6-35b-a3b − deepseek-v4-pro | PreDegr | -0.063 | [-0.137, 0.000] |  |
| qwen3.6-35b-a3b − deepseek-v4-pro | Miss | -0.075 | [-0.166, 0.000] |  |
| qwen3.6-35b-a3b − deepseek-v4-pro | FAR | 0.100 | [0.025, 0.198] | * |
| qwen3.6-35b-a3b − deepseek-v4-pro | Isolation | 0.004 | [-0.167, 0.208] |  |

## 4. 유형별 DR · FAR

| type | DR deepseek-v4-pro | DR qwen2.5-32b | DR qwen3.6-35b-a3b | DR qwen3.8-27b | DR qwen3.8-27b-think | FAR deepseek-v4-pro | FAR qwen2.5-32b | FAR qwen3.6-35b-a3b | FAR qwen3.8-27b | FAR qwen3.8-27b-think |
|---|---|---|---|---|---|---|---|---|---|---|
| bias | 0 | 0 | 0.091 | 0.136 | 0 | 0.823 | 1 | 0.952 | 0.548 | 1 |
| gain | 0.125 | 0 | 0.062 | 0.062 | 0.062 | 0.868 | 1 | 1 | 0.529 | 1 |
| multi_C | 0.065 | 0 | 0.239 | 0.065 | 0 | 0.811 | 1 | 0.973 | 0.568 | 1 |
| multi_I | 0.059 | 0 | 0.176 | 0.235 | 0 | 0.833 | 1 | 1 | 0.621 | 1 |
| noise | 0.156 | 0 | 0.062 | 0.250 | 0.031 | 1 | 1 | 1 | 0.745 | 1 |
| stuck | 0.077 | 0 | 0.038 | 0.077 | 0 | 1 | 1 | 1 | 0.947 | 1 |

## 5. 센서별 DR · FAR

| sensor | DR deepseek-v4-pro | DR qwen2.5-32b | DR qwen3.6-35b-a3b | DR qwen3.8-27b | DR qwen3.8-27b-think | FAR deepseek-v4-pro | FAR qwen2.5-32b | FAR qwen3.6-35b-a3b | FAR qwen3.8-27b | FAR qwen3.8-27b-think |
|---|---|---|---|---|---|---|---|---|---|---|
| T24 | 0.140 | 0 | 0.070 | 0.163 | 0.023 | 0.913 | 1 | 0.986 | 0.638 | 1 |
| T24+T30+T50 | 0.063 | 0 | 0.222 | 0.111 | 0 | 0.825 | 1 | 0.990 | 0.602 | 1 |
| T30 | 0 | 0 | 0 | 0 | 0 | 0.907 | 1 | 0.981 | 0.685 | 1 |
| T50 | 0.059 | 0 | 0.059 | 0.137 | 0.020 | 0.934 | 1 | 1 | 0.721 | 1 |

## 6. 오염 시점별 오염 전 경보율 (저하·비저하 합산)

오염 전 구간이 길수록 (늦은 오염) 오경보가 쌓인다.

| timing_p | 오염 전 길이 중앙값 | deepseek-v4-pro | qwen2.5-32b | qwen3.6-35b-a3b | qwen3.8-27b | qwen3.8-27b-think |
|---|---|---|---|---|---|---|
| 0.200 | 29 | 0.137 | 1 | 0.137 | 0 | 0.710 |
| 0.400 | 58 | 0.680 | 1 | 0.792 | 0.216 | 1 |
| 0.600 | 86 | 0.810 | 1 | 0.992 | 0.532 | 1 |
| 0.800 | 115 | 0.808 | 1 | 1 | 0.640 | 1 |

run 별 상세: [qwen2.5-32b](or500_qwen2.5-32b.md) · [deepseek-v4-pro](or500_deepseek-v4-pro.md) · [qwen3.8-27b](or500_qwen3.8-27b.md) · [qwen3.8-27b-think](or500_qwen3.8-27b-think.md) · [qwen3.6-35b-a3b](or500_qwen3.6-35b-a3b.md)
