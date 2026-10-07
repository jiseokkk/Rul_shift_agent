# 평가 v2 (시나리오 단위) — Qwen3.8-27B-NVFP4-think_or500_seed42_20261002-223719

라벨 theta_primary · 첫 판정 t₀ = 55 · Δ = 5, w = 0, H = 40, k = 1 · 첫 경보 원칙 (t₀ 이후 첫 경보, 오염 전 포함) · ERROR 는 경보 아님 (오류율 0.0596) · 규약 docs/eval_v2_scenario.md

시나리오 500 = 저하 159 + 비저하 341 · unit 20 · 판정 로그가 창 끝에 못 미친 시나리오 0

## 1. 메인 표 (기준선 고정)

| method | n_degraded | detection_rate | pre_contam_rate | pre_degr_rate | miss_rate | delay_median | n_nondegraded | scenario_FAR | FAR_clean | FAR_contam | isolation_rate |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 항상 0 | 159 | 0 | 0 | 0 | 1 |  | 341 | 0 | 0 | 0 |  |
| 항상 1 | 159 | 0 | 1 | 0 | 0 |  | 341 | 1 | 1 | 0 |  |
| 무작위 p=0.261 (에이전트 경보율) | 159 | 0 | 1.000 | 0.000 | 0 |  | 341 | 1 | 1.000 | 0.000 |  |
| 무작위 p=0.050 | 159 | 0.018 | 0.892 | 0.045 | 0.045 | 2.042 | 341 | 0.991 | 0.936 | 0.055 | 0 |
| LLM Agent | 159 | 0.013 | 0.868 | 0.113 | 0.006 | 0 | 341 | 1 | 0.956 | 0.044 | 1 |

## 2. unit bootstrap 95% CI (2000회)

| metric | point | lo | hi |
|---|---|---|---|
| detection_rate | 0.013 | 0 | 0.030 |
| pre_contam_rate | 0.868 | 0.755 | 0.960 |
| pre_degr_rate | 0.113 | 0.033 | 0.216 |
| miss_rate | 0.006 | 0 | 0.020 |
| scenario_FAR | 1 | 1 | 1 |
| isolation_rate | 1 | 1 | 1 |

## 3. 유형별

| type | n_degraded | detection_rate | pre_contam_rate | pre_degr_rate | miss_rate | delay_median | n_nondegraded | scenario_FAR | FAR_clean | FAR_contam | isolation_rate |
|---|---|---|---|---|---|---|---|---|---|---|---|
| bias | 22 | 0 | 0.955 | 0.045 | 0 |  | 62 | 1 | 0.952 | 0.048 |  |
| gain | 16 | 0.062 | 0.750 | 0.188 | 0 | 0 | 68 | 1 | 0.956 | 0.044 | 1 |
| multi_C | 46 | 0 | 0.891 | 0.087 | 0.022 |  | 37 | 1 | 1 | 0 |  |
| multi_I | 17 | 0 | 0.882 | 0.118 | 0 |  | 66 | 1 | 0.955 | 0.045 |  |
| noise | 32 | 0.031 | 0.844 | 0.125 | 0 | 0 | 51 | 1 | 0.961 | 0.039 | 1 |
| stuck | 26 | 0 | 0.846 | 0.154 | 0 |  | 57 | 1 | 0.930 | 0.070 |  |

## 4. 센서별

| sensor | n_degraded | detection_rate | pre_contam_rate | pre_degr_rate | miss_rate | delay_median | n_nondegraded | scenario_FAR | FAR_clean | FAR_contam | isolation_rate |
|---|---|---|---|---|---|---|---|---|---|---|---|
| T24 | 43 | 0.023 | 0.930 | 0.047 | 0 | 0 | 69 | 1 | 0.928 | 0.072 | 1 |
| T24+T30+T50 | 63 | 0 | 0.889 | 0.095 | 0.016 |  | 103 | 1 | 0.971 | 0.029 |  |
| T30 | 2 | 0 | 0.500 | 0.500 | 0 |  | 108 | 1 | 0.954 | 0.046 |  |
| T50 | 51 | 0.020 | 0.804 | 0.176 | 0 | 0 | 61 | 1 | 0.967 | 0.033 | 1 |

## 5. 오염 시점별

| timing_p | n_degraded | detection_rate | pre_contam_rate | pre_degr_rate | miss_rate | delay_median | n_nondegraded | scenario_FAR | FAR_clean | FAR_contam | isolation_rate |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.200 | 64 | 0.031 | 0.672 | 0.281 | 0.016 | 0 | 60 | 1 | 0.750 | 0.250 | 1 |
| 0.400 | 62 | 0 | 1 | 0 | 0 |  | 63 | 1 | 1 | 0 |  |
| 0.600 | 32 | 0 | 1 | 0 | 0 |  | 94 | 1 | 1 | 0 |  |
| 0.800 | 1 | 0 | 1 | 0 | 0 |  | 124 | 1 | 1 | 0 |  |

### 오염 전 경보율 (저하·비저하 합산, 오염 전 구간 길이 = τ_s − 55)

| timing_p | n | pre_len_median | pre_contam_rate |
|---|---|---|---|
| 0.200 | 124 | 29 | 0.710 |
| 0.400 | 125 | 58 | 1 |
| 0.600 | 126 | 86 | 1 |
| 0.800 | 125 | 115 | 1 |

## 6. 저하 시나리오 상세

| unit | scenario_id | type | sensor | tau_s | tau_d | window_lo | window_hi | t_hat | result | delay | iso_hit |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | bias_T50_a1.0_pos_p0.2 | bias | T50 | 82 | 90 | 90 | 95 | 72 | PreContam |  |  |
| 1 | gain_T24_a2.0_pos_p0.4 | gain | T24 | 110 | 138 | 138 | 143 | 73 | PreContam |  |  |
| 1 | multiC_T24+T30+T50_a0.3_na_p0.2 | multi_C | T24+T30+T50 | 82 | 92 | 92 | 97 | 75 | PreContam |  |  |
| 1 | multiC_T24+T30+T50_a0.3_na_p0.4 | multi_C | T24+T30+T50 | 110 | 117 | 117 | 122 | 73 | PreContam |  |  |
| 1 | multiC_T24+T30+T50_a0.5_na_p0.2 | multi_C | T24+T30+T50 | 82 | 90 | 90 | 95 | 73 | PreContam |  |  |
| 1 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 137 | 143 | 143 | 148 | 72 | PreContam |  |  |
| 1 | multiI_T24+T30+T50_a0.3_na_p0.2 | multi_I | T24+T30+T50 | 82 | 93 | 93 | 98 | 75 | PreContam |  |  |
| 1 | noise_T24_b2.0_na_p0.6 | noise | T24 | 137 | 152 | 152 | 157 | 72 | PreContam |  |  |
| 1 | noise_T50_b2.0_na_p0.2 | noise | T50 | 82 | 105 | 105 | 110 | 72 | PreContam |  |  |
| 1 | stuck_T24_na_na_p0.6 | stuck | T24 | 137 | 148 | 148 | 153 | 72 | PreContam |  |  |
| 1 | stuck_T50_na_na_p0.4 | stuck | T50 | 110 | 116 | 116 | 121 | 72 | PreContam |  |  |
| 1 | stuck_T50_na_na_p0.6 | stuck | T50 | 137 | 155 | 155 | 160 | 72 | PreContam |  |  |
| 9 | bias_T24_a0.75_neg_p0.4 | bias | T24 | 113 | 121 | 121 | 126 | 82 | PreContam |  |  |
| 9 | gain_T50_a2.0_pos_p0.2 | gain | T50 | 84 | 110 | 110 | 115 | 87 | PreDegr |  |  |
| 9 | multiC_T24+T30+T50_a0.3_na_p0.2 | multi_C | T24+T30+T50 | 84 | 101 | 101 | 106 | 97 | PreDegr |  |  |
| 9 | multiC_T24+T30+T50_a0.5_na_p0.4 | multi_C | T24+T30+T50 | 113 | 117 | 117 | 122 | 96 | PreContam |  |  |
| 9 | noise_T24_b2.0_na_p0.4 | noise | T24 | 113 | 159 | 159 | 164 | 96 | PreContam |  |  |
| 9 | stuck_T24_na_na_p0.2 | stuck | T24 | 84 | 123 | 123 | 128 | 86 | PreDegr |  |  |
| 10 | bias_T50_a0.5_pos_p0.4 | bias | T50 | 122 | 146 | 146 | 151 | 94 | PreContam |  |  |
| 10 | gain_T50_a1.5_pos_p0.2 | gain | T50 | 88 | 122 | 122 | 127 | 89 | PreDegr |  |  |
| 10 | multiC_T24+T30+T50_a0.3_na_p0.4 | multi_C | T24+T30+T50 | 122 | 132 | 132 | 137 | 95 | PreContam |  |  |
| 10 | multiC_T24+T30+T50_a0.5_na_p0.2 | multi_C | T24+T30+T50 | 88 | 104 | 104 | 109 | 111 | Miss |  |  |
| 10 | multiI_T24+T30+T50_a0.5_na_p0.4 | multi_I | T24+T30+T50 | 122 | 127 | 127 | 132 | 95 | PreContam |  |  |
| 10 | noise_T24_b3.0_na_p0.6 | noise | T24 | 155 | 159 | 159 | 164 | 95 | PreContam |  |  |
| 10 | noise_T50_b1.0_na_p0.4 | noise | T50 | 122 | 125 | 125 | 130 | 95 | PreContam |  |  |
| 10 | stuck_T50_na_na_p0.2 | stuck | T50 | 88 | 145 | 145 | 150 | 90 | PreDegr |  |  |
| 11 | bias_T50_a0.5_pos_p0.4 | bias | T50 | 129 | 136 | 136 | 141 | 76 | PreContam |  |  |
| 11 | bias_T50_a1.0_pos_p0.2 | bias | T50 | 92 | 117 | 117 | 122 | 76 | PreContam |  |  |
| 11 | gain_T24_a1.5_pos_p0.6 | gain | T24 | 166 | 197 | 197 | 202 | 76 | PreContam |  |  |
| 11 | multiC_T24+T30+T50_a0.3_na_p0.2 | multi_C | T24+T30+T50 | 92 | 134 | 134 | 139 | 76 | PreContam |  |  |
| 11 | multiC_T24+T30+T50_a0.3_na_p0.4 | multi_C | T24+T30+T50 | 129 | 135 | 135 | 140 | 76 | PreContam |  |  |
| 11 | multiC_T24+T30+T50_a0.5_na_p0.2 | multi_C | T24+T30+T50 | 92 | 117 | 117 | 122 | 76 | PreContam |  |  |
| 11 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 166 | 172 | 172 | 177 | 76 | PreContam |  |  |
| 11 | multiI_T24+T30+T50_a0.3_na_p0.2 | multi_I | T24+T30+T50 | 92 | 122 | 122 | 127 | 76 | PreContam |  |  |
| 11 | noise_T50_b2.0_na_p0.6 | noise | T50 | 166 | 205 | 205 | 210 | 76 | PreContam |  |  |
| 11 | noise_T50_b3.0_na_p0.6 | noise | T50 | 166 | 171 | 171 | 176 | 76 | PreContam |  |  |
| 11 | stuck_T24_na_na_p0.4 | stuck | T24 | 129 | 134 | 134 | 139 | 76 | PreContam |  |  |
| 11 | stuck_T50_na_na_p0.6 | stuck | T50 | 166 | 181 | 181 | 186 | 76 | PreContam |  |  |
| 17 | bias_T50_a0.75_pos_p0.4 | bias | T50 | 143 | 146 | 146 | 151 | 111 | PreContam |  |  |
| 17 | gain_T50_a1.5_pos_p0.2 | gain | T50 | 99 | 139 | 139 | 144 | 139 | TP | 0 | True |
| 17 | multiC_T24+T30+T50_a0.5_na_p0.2 | multi_C | T24+T30+T50 | 99 | 111 | 111 | 116 | 108 | PreDegr |  |  |
| 17 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 188 | 192 | 192 | 197 | 125 | PreContam |  |  |
| 17 | multiI_T24+T30+T50_a0.5_na_p0.2 | multi_I | T24+T30+T50 | 99 | 147 | 147 | 152 | 125 | PreDegr |  |  |
| 17 | noise_T24_b1.0_na_p0.2 | noise | T24 | 99 | 140 | 140 | 145 | 106 | PreDegr |  |  |
| 17 | noise_T24_b3.0_na_p0.6 | noise | T24 | 188 | 190 | 190 | 195 | 125 | PreContam |  |  |
| 17 | noise_T50_b1.0_na_p0.2 | noise | T50 | 99 | 162 | 162 | 167 | 114 | PreDegr |  |  |
| 17 | noise_T50_b3.0_na_p0.2 | noise | T50 | 99 | 110 | 110 | 115 | 105 | PreDegr |  |  |
| 17 | stuck_T50_na_na_p0.2 | stuck | T50 | 99 | 186 | 186 | 191 | 107 | PreDegr |  |  |
| 17 | stuck_T50_na_na_p0.4 | stuck | T50 | 143 | 213 | 213 | 218 | 125 | PreContam |  |  |
| 26 | bias_T24_a1.0_neg_p0.2 | bias | T24 | 84 | 89 | 89 | 94 | 75 | PreContam |  |  |
| 26 | bias_T24_a1.0_neg_p0.6 | bias | T24 | 141 | 147 | 147 | 152 | 70 | PreContam |  |  |
| 26 | bias_T50_a1.0_neg_p0.4 | bias | T50 | 113 | 116 | 116 | 121 | 56 | PreContam |  |  |
| 26 | gain_T24_a2.0_pos_p0.2 | gain | T24 | 84 | 100 | 100 | 105 | 56 | PreContam |  |  |
| 26 | multiC_T24+T30+T50_a0.3_na_p0.4 | multi_C | T24+T30+T50 | 113 | 117 | 117 | 122 | 56 | PreContam |  |  |
| 26 | multiI_T24+T30+T50_a0.3_na_p0.4 | multi_I | T24+T30+T50 | 113 | 123 | 123 | 128 | 56 | PreContam |  |  |
| 26 | noise_T24_b3.0_na_p0.6 | noise | T24 | 141 | 177 | 177 | 182 | 56 | PreContam |  |  |
| 26 | noise_T50_b1.0_na_p0.4 | noise | T50 | 113 | 131 | 131 | 136 | 56 | PreContam |  |  |
| 26 | stuck_T24_na_na_p0.2 | stuck | T24 | 84 | 136 | 136 | 141 | 56 | PreContam |  |  |
| 32 | bias_T24_a1.0_neg_p0.2 | bias | T24 | 82 | 85 | 85 | 90 | 68 | PreContam |  |  |
| 32 | bias_T50_a0.75_neg_p0.4 | bias | T50 | 109 | 123 | 123 | 128 | 68 | PreContam |  |  |
| 32 | gain_T50_a2.0_pos_p0.4 | gain | T50 | 109 | 111 | 111 | 116 | 68 | PreContam |  |  |
| 32 | multiC_T24+T30+T50_a0.3_na_p0.2 | multi_C | T24+T30+T50 | 82 | 86 | 86 | 91 | 68 | PreContam |  |  |
| 32 | multiC_T24+T30+T50_a0.3_na_p0.4 | multi_C | T24+T30+T50 | 109 | 122 | 122 | 127 | 68 | PreContam |  |  |
| 32 | multiC_T24+T30+T50_a0.5_na_p0.4 | multi_C | T24+T30+T50 | 109 | 114 | 114 | 119 | 68 | PreContam |  |  |
| 32 | noise_T24_b2.0_na_p0.2 | noise | T24 | 82 | 82 | 82 | 87 | 68 | PreContam |  |  |
| 32 | noise_T50_b2.0_na_p0.2 | noise | T50 | 82 | 87 | 87 | 92 | 68 | PreContam |  |  |
| 48 | bias_T50_a0.5_neg_p0.2 | bias | T50 | 90 | 104 | 104 | 109 | 76 | PreContam |  |  |
| 48 | gain_T50_a1.5_pos_p0.2 | gain | T50 | 90 | 99 | 99 | 104 | 76 | PreContam |  |  |
| 48 | multiC_T24+T30+T50_a0.3_na_p0.4 | multi_C | T24+T30+T50 | 125 | 134 | 134 | 139 | 76 | PreContam |  |  |
| 48 | multiC_T24+T30+T50_a0.5_na_p0.2 | multi_C | T24+T30+T50 | 90 | 94 | 94 | 99 | 76 | PreContam |  |  |
| 48 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 161 | 169 | 169 | 174 | 76 | PreContam |  |  |
| 48 | multiI_T24+T30+T50_a0.3_na_p0.2 | multi_I | T24+T30+T50 | 90 | 99 | 99 | 104 | 76 | PreContam |  |  |
| 48 | multiI_T24+T30+T50_a0.3_na_p0.4 | multi_I | T24+T30+T50 | 125 | 139 | 139 | 144 | 76 | PreContam |  |  |
| 48 | multiI_T24+T30+T50_a0.5_na_p0.2 | multi_I | T24+T30+T50 | 90 | 96 | 96 | 101 | 76 | PreContam |  |  |
| 48 | multiI_T24+T30+T50_a0.5_na_p0.4 | multi_I | T24+T30+T50 | 125 | 132 | 132 | 137 | 76 | PreContam |  |  |
| 48 | stuck_T24_na_na_p0.4 | stuck | T24 | 125 | 190 | 190 | 195 | 76 | PreContam |  |  |
| 48 | stuck_T50_na_na_p0.4 | stuck | T50 | 125 | 145 | 145 | 150 | 76 | PreContam |  |  |
| 49 | bias_T24_a0.5_neg_p0.4 | bias | T24 | 119 | 127 | 127 | 132 | 56 | PreContam |  |  |
| 49 | bias_T24_a0.5_pos_p0.4 | bias | T24 | 119 | 129 | 129 | 134 | 56 | PreContam |  |  |
| 49 | gain_T24_a2.0_pos_p0.4 | gain | T24 | 119 | 126 | 126 | 131 | 56 | PreContam |  |  |
| 49 | multiC_T24+T30+T50_a0.3_na_p0.4 | multi_C | T24+T30+T50 | 119 | 128 | 128 | 133 | 56 | PreContam |  |  |
| 49 | multiC_T24+T30+T50_a0.5_na_p0.2 | multi_C | T24+T30+T50 | 87 | 94 | 94 | 99 | 56 | PreContam |  |  |
| 49 | noise_T24_b3.0_na_p0.2 | noise | T24 | 87 | 97 | 97 | 102 | 56 | PreContam |  |  |
| 49 | noise_T50_b3.0_na_p0.4 | noise | T50 | 119 | 132 | 132 | 137 | 56 | PreContam |  |  |
| 49 | stuck_T24_na_na_p0.4 | stuck | T24 | 119 | 128 | 128 | 133 | 56 | PreContam |  |  |
| 49 | stuck_T24_na_na_p0.8 | stuck | T24 | 183 | 199 | 199 | 204 | 56 | PreContam |  |  |
| 49 | stuck_T50_na_na_p0.6 | stuck | T50 | 151 | 166 | 166 | 171 | 56 | PreContam |  |  |
| 52 | bias_T50_a0.75_pos_p0.4 | bias | T50 | 118 | 123 | 123 | 128 | 88 | PreContam |  |  |
| 52 | bias_T50_a1.0_pos_p0.4 | bias | T50 | 118 | 122 | 122 | 127 | 88 | PreContam |  |  |
| 52 | gain_T24_a1.0_pos_p0.4 | gain | T24 | 118 | 133 | 133 | 138 | 88 | PreContam |  |  |
| 52 | gain_T50_a2.0_pos_p0.4 | gain | T50 | 118 | 122 | 122 | 127 | 88 | PreContam |  |  |
| 52 | multiC_T24+T30+T50_a0.3_na_p0.2 | multi_C | T24+T30+T50 | 87 | 92 | 92 | 97 | 87 | PreDegr |  |  |
| 52 | multiC_T24+T30+T50_a0.3_na_p0.4 | multi_C | T24+T30+T50 | 118 | 125 | 125 | 130 | 88 | PreContam |  |  |
| 52 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 150 | 154 | 154 | 159 | 88 | PreContam |  |  |
| 52 | noise_T24_b3.0_na_p0.2 | noise | T24 | 87 | 87 | 87 | 92 | 87 | TP | 0 | True |
| 57 | bias_T50_a0.75_neg_p0.2 | bias | T50 | 71 | 78 | 78 | 83 | 62 | PreContam |  |  |
| 57 | multiC_T24+T30+T50_a0.3_na_p0.2 | multi_C | T24+T30+T50 | 71 | 84 | 84 | 89 | 62 | PreContam |  |  |
| 57 | multiC_T24+T30+T50_a0.5_na_p0.4 | multi_C | T24+T30+T50 | 88 | 91 | 91 | 96 | 62 | PreContam |  |  |
| 57 | noise_T50_b2.0_na_p0.2 | noise | T50 | 71 | 75 | 75 | 80 | 62 | PreContam |  |  |
| 57 | noise_T50_b3.0_na_p0.2 | noise | T50 | 71 | 74 | 74 | 79 | 62 | PreContam |  |  |
| 57 | noise_T50_b3.0_na_p0.4 | noise | T50 | 88 | 89 | 89 | 94 | 62 | PreContam |  |  |
| 63 | bias_T24_a1.0_neg_p0.4 | bias | T24 | 103 | 106 | 106 | 111 | 79 | PreContam |  |  |
| 63 | bias_T50_a1.0_pos_p0.2 | bias | T50 | 79 | 84 | 84 | 89 | 81 | PreDegr |  |  |
| 63 | multiC_T24+T30+T50_a0.3_na_p0.2 | multi_C | T24+T30+T50 | 79 | 89 | 89 | 94 | 79 | PreDegr |  |  |
| 63 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 126 | 135 | 135 | 140 | 79 | PreContam |  |  |
| 63 | multiI_T24+T30+T50_a0.3_na_p0.2 | multi_I | T24+T30+T50 | 79 | 89 | 89 | 94 | 79 | PreDegr |  |  |
| 63 | multiI_T24+T30+T50_a0.3_na_p0.4 | multi_I | T24+T30+T50 | 103 | 132 | 132 | 137 | 79 | PreContam |  |  |
| 63 | multiI_T24+T30+T50_a0.5_na_p0.6 | multi_I | T24+T30+T50 | 126 | 135 | 135 | 140 | 79 | PreContam |  |  |
| 63 | stuck_T50_na_na_p0.2 | stuck | T50 | 79 | 98 | 98 | 103 | 79 | PreDegr |  |  |
| 64 | gain_T24_a1.5_pos_p0.4 | gain | T24 | 146 | 185 | 185 | 190 | 96 | PreContam |  |  |
| 64 | multiC_T24+T30+T50_a0.5_na_p0.2 | multi_C | T24+T30+T50 | 101 | 106 | 106 | 111 | 96 | PreContam |  |  |
| 64 | multiC_T24+T30+T50_a0.5_na_p0.4 | multi_C | T24+T30+T50 | 146 | 152 | 152 | 157 | 96 | PreContam |  |  |
| 64 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 192 | 197 | 197 | 202 | 96 | PreContam |  |  |
| 64 | multiI_T24+T30+T50_a0.3_na_p0.4 | multi_I | T24+T30+T50 | 146 | 154 | 154 | 159 | 96 | PreContam |  |  |
| 64 | multiI_T24+T30+T50_a0.5_na_p0.6 | multi_I | T24+T30+T50 | 192 | 197 | 197 | 202 | 96 | PreContam |  |  |
| 64 | noise_T24_b3.0_na_p0.2 | noise | T24 | 101 | 104 | 104 | 109 | 96 | PreContam |  |  |
| 64 | noise_T24_b3.0_na_p0.4 | noise | T24 | 146 | 182 | 182 | 187 | 96 | PreContam |  |  |
| 64 | noise_T24_b3.0_na_p0.6 | noise | T24 | 192 | 195 | 195 | 200 | 96 | PreContam |  |  |
| 64 | noise_T50_b2.0_na_p0.6 | noise | T50 | 192 | 207 | 207 | 212 | 96 | PreContam |  |  |
| 64 | stuck_T24_na_na_p0.2 | stuck | T24 | 101 | 187 | 187 | 192 | 96 | PreContam |  |  |
| 64 | stuck_T50_na_na_p0.4 | stuck | T50 | 146 | 162 | 162 | 167 | 96 | PreContam |  |  |
| 65 | gain_T50_a1.5_pos_p0.2 | gain | T50 | 75 | 82 | 82 | 87 | 77 | PreDegr |  |  |
| 65 | multiC_T24+T30+T50_a0.5_na_p0.4 | multi_C | T24+T30+T50 | 94 | 97 | 97 | 102 | 77 | PreContam |  |  |
| 65 | noise_T24_b3.0_na_p0.4 | noise | T24 | 94 | 96 | 96 | 101 | 77 | PreContam |  |  |
| 65 | noise_T30_b3.0_na_p0.2 | noise | T30 | 75 | 120 | 120 | 125 | 75 | PreDegr |  |  |
| 67 | bias_T24_a1.0_pos_p0.2 | bias | T24 | 107 | 118 | 118 | 123 | 73 | PreContam |  |  |
| 67 | gain_T24_a0.75_neg_p0.2 | gain | T24 | 107 | 190 | 190 | 195 | 61 | PreContam |  |  |
| 67 | multiC_T24+T30+T50_a0.3_na_p0.4 | multi_C | T24+T30+T50 | 158 | 178 | 178 | 183 | 61 | PreContam |  |  |
| 67 | multiC_T24+T30+T50_a0.5_na_p0.2 | multi_C | T24+T30+T50 | 107 | 115 | 115 | 120 | 61 | PreContam |  |  |
| 67 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 210 | 214 | 214 | 219 | 61 | PreContam |  |  |
| 67 | noise_T50_b2.0_na_p0.6 | noise | T50 | 210 | 218 | 218 | 223 | 61 | PreContam |  |  |
| 67 | stuck_T24_na_na_p0.6 | stuck | T24 | 210 | 261 | 261 | 266 | 61 | PreContam |  |  |
| 67 | stuck_T50_na_na_p0.2 | stuck | T50 | 107 | 128 | 128 | 133 | 61 | PreContam |  |  |
| 67 | stuck_T50_na_na_p0.4 | stuck | T50 | 158 | 190 | 190 | 195 | 61 | PreContam |  |  |
| 68 | bias_T50_a0.3_neg_p0.2 | bias | T50 | 84 | 113 | 113 | 118 | 58 | PreContam |  |  |
| 68 | gain_T24_a1.0_pos_p0.4 | gain | T24 | 113 | 135 | 135 | 140 | 58 | PreContam |  |  |
| 68 | multiC_T24+T30+T50_a0.3_na_p0.4 | multi_C | T24+T30+T50 | 113 | 121 | 121 | 126 | 58 | PreContam |  |  |
| 68 | multiC_T24+T30+T50_a0.5_na_p0.2 | multi_C | T24+T30+T50 | 84 | 88 | 88 | 93 | 58 | PreContam |  |  |
| 68 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 141 | 147 | 147 | 152 | 58 | PreContam |  |  |
| 68 | noise_T50_b3.0_na_p0.6 | noise | T50 | 141 | 144 | 144 | 149 | 58 | PreContam |  |  |
| 68 | stuck_T24_na_na_p0.2 | stuck | T24 | 84 | 93 | 93 | 98 | 58 | PreContam |  |  |
| 70 | noise_T50_b2.0_na_p0.6 | noise | T50 | 104 | 105 | 105 | 110 | 64 | PreContam |  |  |
| 70 | noise_T50_b3.0_na_p0.4 | noise | T50 | 88 | 89 | 89 | 94 | 64 | PreContam |  |  |
| 79 | multiC_T24+T30+T50_a0.3_na_p0.2 | multi_C | T24+T30+T50 | 84 | 92 | 92 | 97 | 67 | PreContam |  |  |
| 79 | stuck_T24_na_na_p0.6 | stuck | T24 | 141 | 156 | 156 | 161 | 67 | PreContam |  |  |
| 85 | bias_T50_a0.75_neg_p0.2 | bias | T50 | 82 | 85 | 85 | 90 | 78 | PreContam |  |  |
| 85 | gain_T24_a2.0_pos_p0.6 | gain | T24 | 135 | 149 | 149 | 154 | 78 | PreContam |  |  |
| 85 | multiC_T24+T30+T50_a0.3_na_p0.4 | multi_C | T24+T30+T50 | 108 | 126 | 126 | 131 | 78 | PreContam |  |  |
| 85 | multiC_T24+T30+T50_a0.5_na_p0.4 | multi_C | T24+T30+T50 | 108 | 111 | 111 | 116 | 78 | PreContam |  |  |
| 85 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 135 | 141 | 141 | 146 | 78 | PreContam |  |  |
| 85 | multiI_T24+T30+T50_a0.3_na_p0.2 | multi_I | T24+T30+T50 | 82 | 87 | 87 | 92 | 78 | PreContam |  |  |
| 85 | multiI_T24+T30+T50_a0.3_na_p0.4 | multi_I | T24+T30+T50 | 108 | 116 | 116 | 121 | 78 | PreContam |  |  |
| 85 | multiI_T24+T30+T50_a0.5_na_p0.2 | multi_I | T24+T30+T50 | 82 | 84 | 84 | 89 | 78 | PreContam |  |  |
| 85 | stuck_T24_na_na_p0.4 | stuck | T24 | 108 | 148 | 148 | 153 | 78 | PreContam |  |  |
| 85 | stuck_T50_na_na_p0.4 | stuck | T50 | 108 | 116 | 116 | 121 | 78 | PreContam |  |  |
| 90 | multiC_T24+T30+T50_a0.3_na_p0.2 | multi_C | T24+T30+T50 | 75 | 80 | 80 | 85 | 61 | PreContam |  |  |
| 90 | multiC_T24+T30+T50_a0.5_na_p0.2 | multi_C | T24+T30+T50 | 75 | 78 | 78 | 83 | 61 | PreContam |  |  |
| 90 | noise_T30_b3.0_na_p0.4 | noise | T30 | 95 | 103 | 103 | 108 | 61 | PreContam |  |  |
| 90 | stuck_T24_na_na_p0.4 | stuck | T24 | 95 | 110 | 110 | 115 | 61 | PreContam |  |  |

## 7. 비저하 시나리오 상세

| unit | scenario_id | type | sensor | tau_s | window_hi | t_hat | result |
|---|---|---|---|---|---|---|---|
| 1 | bias_T24_a0.3_neg_p0.6 | bias | T24 | 137 | 177 | 73 | FP_clean |
| 1 | bias_T24_a0.3_neg_p0.8 | bias | T24 | 165 | 192 | 75 | FP_clean |
| 1 | bias_T24_a0.5_neg_p0.8 | bias | T24 | 165 | 192 | 72 | FP_clean |
| 1 | gain_T24_a0.25_neg_p0.2 | gain | T24 | 82 | 122 | 69 | FP_clean |
| 1 | gain_T24_a0.75_neg_p0.8 | gain | T24 | 165 | 192 | 75 | FP_clean |
| 1 | gain_T30_a1.0_pos_p0.6 | gain | T30 | 137 | 177 | 72 | FP_clean |
| 1 | multiI_T24+T30+T50_a0.3_na_p0.8 | multi_I | T24+T30+T50 | 165 | 192 | 75 | FP_clean |
| 1 | multiI_T24+T30+T50_a0.5_na_p0.2 | multi_I | T24+T30+T50 | 82 | 122 | 73 | FP_clean |
| 1 | multiI_T24+T30+T50_a0.5_na_p0.4 | multi_I | T24+T30+T50 | 110 | 150 | 73 | FP_clean |
| 1 | multiI_T24+T30+T50_a0.5_na_p0.8 | multi_I | T24+T30+T50 | 165 | 192 | 72 | FP_clean |
| 1 | noise_T30_b3.0_na_p0.4 | noise | T30 | 110 | 150 | 72 | FP_clean |
| 1 | noise_T30_b3.0_na_p0.8 | noise | T30 | 165 | 192 | 72 | FP_clean |
| 1 | noise_T50_b1.0_na_p0.6 | noise | T50 | 137 | 177 | 72 | FP_clean |
| 1 | stuck_T24_na_na_p0.4 | stuck | T24 | 110 | 150 | 72 | FP_clean |
| 1 | stuck_T24_na_na_p0.8 | stuck | T24 | 165 | 192 | 72 | FP_clean |
| 9 | bias_T30_a0.75_neg_p0.6 | bias | T30 | 143 | 183 | 96 | FP_clean |
| 9 | bias_T30_a0.75_pos_p0.6 | bias | T30 | 143 | 183 | 79 | FP_clean |
| 9 | bias_T30_a1.0_neg_p0.6 | bias | T30 | 143 | 183 | 79 | FP_clean |
| 9 | gain_T30_a0.75_neg_p0.4 | gain | T30 | 113 | 153 | 79 | FP_clean |
| 9 | gain_T30_a2.0_pos_p0.2 | gain | T30 | 84 | 124 | 82 | FP_clean |
| 9 | gain_T50_a1.5_pos_p0.6 | gain | T50 | 143 | 183 | 96 | FP_clean |
| 9 | multiC_T24+T30+T50_a0.3_na_p0.8 | multi_C | T24+T30+T50 | 172 | 201 | 96 | FP_clean |
| 9 | multiC_T24+T30+T50_a0.5_na_p0.8 | multi_C | T24+T30+T50 | 172 | 201 | 96 | FP_clean |
| 9 | multiI_T24+T30+T50_a0.3_na_p0.4 | multi_I | T24+T30+T50 | 113 | 153 | 96 | FP_clean |
| 9 | multiI_T24+T30+T50_a0.3_na_p0.6 | multi_I | T24+T30+T50 | 143 | 183 | 96 | FP_clean |
| 9 | multiI_T24+T30+T50_a0.5_na_p0.6 | multi_I | T24+T30+T50 | 143 | 183 | 96 | FP_clean |
| 9 | multiI_T24+T30+T50_a0.5_na_p0.8 | multi_I | T24+T30+T50 | 172 | 201 | 96 | FP_clean |
| 9 | noise_T24_b1.0_na_p0.8 | noise | T24 | 172 | 201 | 96 | FP_clean |
| 9 | noise_T30_b1.0_na_p0.6 | noise | T30 | 143 | 183 | 96 | FP_clean |
| 9 | noise_T50_b3.0_na_p0.8 | noise | T50 | 172 | 201 | 96 | FP_clean |
| 9 | stuck_T30_na_na_p0.2 | stuck | T30 | 84 | 124 | 85 | FP_contam |
| 9 | stuck_T30_na_na_p0.8 | stuck | T30 | 172 | 201 | 96 | FP_clean |
| 9 | stuck_T50_na_na_p0.6 | stuck | T50 | 143 | 183 | 96 | FP_clean |
| 10 | bias_T24_a0.3_pos_p0.2 | bias | T24 | 88 | 128 | 88 | FP_contam |
| 10 | bias_T24_a0.5_pos_p0.8 | bias | T24 | 189 | 222 | 95 | FP_clean |
| 10 | bias_T30_a1.0_neg_p0.2 | bias | T30 | 88 | 128 | 87 | FP_clean |
| 10 | gain_T24_a1.0_pos_p0.2 | gain | T24 | 88 | 128 | 88 | FP_contam |
| 10 | gain_T30_a0.75_neg_p0.6 | gain | T30 | 155 | 195 | 95 | FP_clean |
| 10 | gain_T50_a0.25_neg_p0.4 | gain | T50 | 122 | 162 | 94 | FP_clean |
| 10 | multiC_T24+T30+T50_a0.3_na_p0.8 | multi_C | T24+T30+T50 | 189 | 222 | 95 | FP_clean |
| 10 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 155 | 195 | 95 | FP_clean |
| 10 | multiC_T24+T30+T50_a0.5_na_p0.8 | multi_C | T24+T30+T50 | 189 | 222 | 95 | FP_clean |
| 10 | multiI_T24+T30+T50_a0.3_na_p0.8 | multi_I | T24+T30+T50 | 189 | 222 | 95 | FP_clean |
| 10 | multiI_T24+T30+T50_a0.5_na_p0.6 | multi_I | T24+T30+T50 | 155 | 195 | 95 | FP_clean |
| 10 | multiI_T24+T30+T50_a0.5_na_p0.8 | multi_I | T24+T30+T50 | 189 | 222 | 95 | FP_clean |
| 10 | noise_T24_b1.0_na_p0.4 | noise | T24 | 122 | 162 | 95 | FP_clean |
| 10 | noise_T50_b1.0_na_p0.2 | noise | T50 | 88 | 128 | 88 | FP_contam |
| 10 | stuck_T24_na_na_p0.8 | stuck | T24 | 189 | 222 | 95 | FP_clean |
| 10 | stuck_T30_na_na_p0.2 | stuck | T30 | 88 | 128 | 91 | FP_contam |
| 10 | stuck_T30_na_na_p0.4 | stuck | T30 | 122 | 162 | 95 | FP_clean |
| 11 | bias_T30_a0.5_pos_p0.4 | bias | T30 | 129 | 169 | 76 | FP_clean |
| 11 | bias_T30_a0.75_pos_p0.2 | bias | T30 | 92 | 132 | 76 | FP_clean |
| 11 | gain_T30_a2.0_pos_p0.6 | gain | T30 | 166 | 206 | 76 | FP_clean |
| 11 | gain_T50_a0.5_neg_p0.8 | gain | T50 | 203 | 240 | 76 | FP_clean |
| 11 | gain_T50_a1.5_pos_p0.8 | gain | T50 | 203 | 240 | 76 | FP_clean |
| 11 | multiI_T24+T30+T50_a0.3_na_p0.4 | multi_I | T24+T30+T50 | 129 | 169 | 76 | FP_clean |
| 11 | multiI_T24+T30+T50_a0.5_na_p0.4 | multi_I | T24+T30+T50 | 129 | 169 | 76 | FP_clean |
| 11 | multiI_T24+T30+T50_a0.5_na_p0.8 | multi_I | T24+T30+T50 | 203 | 240 | 76 | FP_clean |
| 11 | noise_T30_b1.0_na_p0.8 | noise | T30 | 203 | 240 | 76 | FP_clean |
| 11 | noise_T30_b2.0_na_p0.2 | noise | T30 | 92 | 132 | 76 | FP_clean |
| 11 | noise_T30_b2.0_na_p0.8 | noise | T30 | 203 | 240 | 76 | FP_clean |
| 11 | stuck_T24_na_na_p0.6 | stuck | T24 | 166 | 206 | 76 | FP_clean |
| 11 | stuck_T30_na_na_p0.4 | stuck | T30 | 129 | 169 | 76 | FP_clean |
| 17 | bias_T24_a0.75_neg_p0.8 | bias | T24 | 232 | 272 | 125 | FP_clean |
| 17 | bias_T30_a0.3_pos_p0.4 | bias | T30 | 143 | 183 | 125 | FP_clean |
| 17 | bias_T30_a0.75_pos_p0.6 | bias | T30 | 188 | 228 | 108 | FP_clean |
| 17 | gain_T24_a1.0_pos_p0.2 | gain | T24 | 99 | 139 | 106 | FP_contam |
| 17 | gain_T24_a1.5_pos_p0.8 | gain | T24 | 232 | 272 | 125 | FP_clean |
| 17 | gain_T30_a1.0_pos_p0.8 | gain | T30 | 232 | 272 | 125 | FP_clean |
| 17 | gain_T50_a0.5_neg_p0.6 | gain | T50 | 188 | 228 | 125 | FP_clean |
| 17 | multiC_T24+T30+T50_a0.3_na_p0.8 | multi_C | T24+T30+T50 | 232 | 272 | 125 | FP_clean |
| 17 | multiC_T24+T30+T50_a0.5_na_p0.8 | multi_C | T24+T30+T50 | 232 | 272 | 125 | FP_clean |
| 17 | multiI_T24+T30+T50_a0.3_na_p0.2 | multi_I | T24+T30+T50 | 99 | 139 | 122 | FP_contam |
| 17 | multiI_T24+T30+T50_a0.5_na_p0.6 | multi_I | T24+T30+T50 | 188 | 228 | 125 | FP_clean |
| 17 | multiI_T24+T30+T50_a0.5_na_p0.8 | multi_I | T24+T30+T50 | 232 | 272 | 125 | FP_clean |
| 17 | stuck_T30_na_na_p0.4 | stuck | T30 | 143 | 183 | 125 | FP_clean |
| 17 | stuck_T50_na_na_p0.8 | stuck | T50 | 232 | 272 | 125 | FP_clean |
| 26 | bias_T30_a0.5_neg_p0.8 | bias | T30 | 170 | 199 | 56 | FP_clean |
| 26 | bias_T30_a0.5_pos_p0.6 | bias | T30 | 141 | 181 | 56 | FP_clean |
| 26 | gain_T24_a0.25_neg_p0.4 | gain | T24 | 113 | 153 | 56 | FP_clean |
| 26 | gain_T30_a0.75_neg_p0.8 | gain | T30 | 170 | 199 | 56 | FP_clean |
| 26 | gain_T50_a0.75_neg_p0.6 | gain | T50 | 141 | 181 | 56 | FP_clean |
| 26 | gain_T50_a0.75_neg_p0.8 | gain | T50 | 170 | 199 | 56 | FP_clean |
| 26 | multiC_T24+T30+T50_a0.3_na_p0.6 | multi_C | T24+T30+T50 | 141 | 181 | 56 | FP_clean |
| 26 | multiC_T24+T30+T50_a0.3_na_p0.8 | multi_C | T24+T30+T50 | 170 | 199 | 56 | FP_clean |
| 26 | multiC_T24+T30+T50_a0.5_na_p0.8 | multi_C | T24+T30+T50 | 170 | 199 | 56 | FP_clean |
| 26 | multiI_T24+T30+T50_a0.3_na_p0.6 | multi_I | T24+T30+T50 | 141 | 181 | 56 | FP_clean |
| 26 | multiI_T24+T30+T50_a0.3_na_p0.8 | multi_I | T24+T30+T50 | 170 | 199 | 56 | FP_clean |
| 26 | multiI_T24+T30+T50_a0.5_na_p0.4 | multi_I | T24+T30+T50 | 113 | 153 | 56 | FP_clean |
| 26 | noise_T24_b1.0_na_p0.6 | noise | T24 | 141 | 181 | 56 | FP_clean |
| 26 | noise_T30_b2.0_na_p0.4 | noise | T30 | 113 | 153 | 56 | FP_clean |
| 26 | stuck_T24_na_na_p0.6 | stuck | T24 | 141 | 181 | 56 | FP_clean |
| 26 | stuck_T30_na_na_p0.4 | stuck | T30 | 113 | 153 | 56 | FP_clean |
| 26 | stuck_T50_na_na_p0.8 | stuck | T50 | 170 | 199 | 56 | FP_clean |
| 32 | bias_T30_a0.3_neg_p0.2 | bias | T30 | 82 | 122 | 68 | FP_clean |
| 32 | bias_T30_a1.0_neg_p0.2 | bias | T30 | 82 | 122 | 68 | FP_clean |
| 32 | gain_T30_a0.25_neg_p0.6 | gain | T30 | 137 | 177 | 68 | FP_clean |
| 32 | gain_T30_a0.75_neg_p0.4 | gain | T30 | 109 | 149 | 68 | FP_clean |
| 32 | gain_T30_a1.0_pos_p0.4 | gain | T30 | 109 | 149 | 68 | FP_clean |
| 32 | gain_T50_a0.75_neg_p0.6 | gain | T50 | 137 | 177 | 68 | FP_clean |
| 32 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 137 | 177 | 68 | FP_clean |
| 32 | multiI_T24+T30+T50_a0.3_na_p0.4 | multi_I | T24+T30+T50 | 109 | 149 | 68 | FP_clean |
| 32 | multiI_T24+T30+T50_a0.3_na_p0.6 | multi_I | T24+T30+T50 | 137 | 177 | 68 | FP_clean |
| 32 | multiI_T24+T30+T50_a0.5_na_p0.2 | multi_I | T24+T30+T50 | 82 | 122 | 68 | FP_clean |
| 32 | multiI_T24+T30+T50_a0.5_na_p0.8 | multi_I | T24+T30+T50 | 164 | 191 | 68 | FP_clean |
| 32 | noise_T30_b2.0_na_p0.8 | noise | T30 | 164 | 191 | 68 | FP_clean |
| 32 | noise_T50_b2.0_na_p0.8 | noise | T50 | 164 | 191 | 68 | FP_clean |
| 32 | stuck_T30_na_na_p0.2 | stuck | T30 | 82 | 122 | 68 | FP_clean |
| 32 | stuck_T30_na_na_p0.6 | stuck | T30 | 137 | 177 | 68 | FP_clean |
| 32 | stuck_T30_na_na_p0.8 | stuck | T30 | 164 | 191 | 68 | FP_clean |
| 32 | stuck_T50_na_na_p0.4 | stuck | T50 | 109 | 149 | 68 | FP_clean |
| 48 | bias_T24_a0.3_neg_p0.4 | bias | T24 | 125 | 165 | 110 | FP_clean |
| 48 | bias_T24_a0.3_neg_p0.6 | bias | T24 | 161 | 201 | 110 | FP_clean |
| 48 | bias_T50_a1.0_pos_p0.6 | bias | T50 | 161 | 201 | 111 | FP_clean |
| 48 | gain_T30_a0.5_neg_p0.6 | gain | T30 | 161 | 201 | 76 | FP_clean |
| 48 | gain_T50_a0.75_neg_p0.6 | gain | T50 | 161 | 201 | 76 | FP_clean |
| 48 | gain_T50_a2.0_pos_p0.8 | gain | T50 | 196 | 231 | 76 | FP_clean |
| 48 | multiC_T24+T30+T50_a0.3_na_p0.8 | multi_C | T24+T30+T50 | 196 | 231 | 76 | FP_clean |
| 48 | noise_T24_b1.0_na_p0.8 | noise | T24 | 196 | 231 | 76 | FP_clean |
| 48 | noise_T24_b2.0_na_p0.8 | noise | T24 | 196 | 231 | 76 | FP_clean |
| 48 | noise_T30_b1.0_na_p0.6 | noise | T30 | 161 | 201 | 76 | FP_clean |
| 48 | noise_T30_b2.0_na_p0.6 | noise | T30 | 161 | 201 | 76 | FP_clean |
| 48 | stuck_T24_na_na_p0.2 | stuck | T24 | 90 | 130 | 76 | FP_clean |
| 48 | stuck_T30_na_na_p0.6 | stuck | T30 | 161 | 201 | 76 | FP_clean |
| 49 | bias_T30_a0.5_pos_p0.4 | bias | T30 | 119 | 159 | 56 | FP_clean |
| 49 | bias_T50_a0.75_neg_p0.6 | bias | T50 | 151 | 191 | 56 | FP_clean |
| 49 | bias_T50_a0.75_pos_p0.8 | bias | T50 | 183 | 215 | 56 | FP_clean |
| 49 | gain_T24_a0.25_neg_p0.4 | gain | T24 | 119 | 159 | 56 | FP_clean |
| 49 | gain_T24_a0.5_pos_p0.6 | gain | T24 | 151 | 191 | 56 | FP_clean |
| 49 | gain_T30_a2.0_pos_p0.2 | gain | T30 | 87 | 127 | 56 | FP_clean |
| 49 | multiC_T24+T30+T50_a0.3_na_p0.6 | multi_C | T24+T30+T50 | 151 | 191 | 56 | FP_clean |
| 49 | multiC_T24+T30+T50_a0.3_na_p0.8 | multi_C | T24+T30+T50 | 183 | 215 | 56 | FP_clean |
| 49 | multiI_T24+T30+T50_a0.3_na_p0.6 | multi_I | T24+T30+T50 | 151 | 191 | 56 | FP_clean |
| 49 | multiI_T24+T30+T50_a0.3_na_p0.8 | multi_I | T24+T30+T50 | 183 | 215 | 56 | FP_clean |
| 49 | multiI_T24+T30+T50_a0.5_na_p0.2 | multi_I | T24+T30+T50 | 87 | 127 | 56 | FP_clean |
| 49 | multiI_T24+T30+T50_a0.5_na_p0.6 | multi_I | T24+T30+T50 | 151 | 191 | 56 | FP_clean |
| 49 | noise_T24_b2.0_na_p0.8 | noise | T24 | 183 | 215 | 56 | FP_clean |
| 49 | noise_T50_b1.0_na_p0.8 | noise | T50 | 183 | 215 | 56 | FP_clean |
| 49 | stuck_T30_na_na_p0.2 | stuck | T30 | 87 | 127 | 56 | FP_clean |
| 49 | stuck_T50_na_na_p0.2 | stuck | T50 | 87 | 127 | 56 | FP_clean |
| 52 | bias_T30_a0.75_pos_p0.8 | bias | T30 | 181 | 213 | 88 | FP_clean |
| 52 | bias_T30_a1.0_neg_p0.4 | bias | T30 | 118 | 158 | 88 | FP_clean |
| 52 | bias_T50_a0.3_pos_p0.8 | bias | T50 | 181 | 213 | 88 | FP_clean |
| 52 | gain_T30_a0.25_neg_p0.6 | gain | T30 | 150 | 190 | 88 | FP_clean |
| 52 | gain_T30_a0.5_neg_p0.6 | gain | T30 | 150 | 190 | 88 | FP_clean |
| 52 | multiC_T24+T30+T50_a0.5_na_p0.8 | multi_C | T24+T30+T50 | 181 | 213 | 88 | FP_clean |
| 52 | multiI_T24+T30+T50_a0.3_na_p0.4 | multi_I | T24+T30+T50 | 118 | 158 | 88 | FP_clean |
| 52 | multiI_T24+T30+T50_a0.3_na_p0.6 | multi_I | T24+T30+T50 | 150 | 190 | 88 | FP_clean |
| 52 | multiI_T24+T30+T50_a0.3_na_p0.8 | multi_I | T24+T30+T50 | 181 | 213 | 88 | FP_clean |
| 52 | multiI_T24+T30+T50_a0.5_na_p0.2 | multi_I | T24+T30+T50 | 87 | 127 | 93 | FP_contam |
| 52 | multiI_T24+T30+T50_a0.5_na_p0.6 | multi_I | T24+T30+T50 | 150 | 190 | 88 | FP_clean |
| 52 | noise_T24_b1.0_na_p0.4 | noise | T24 | 118 | 158 | 88 | FP_clean |
| 52 | noise_T24_b2.0_na_p0.8 | noise | T24 | 181 | 213 | 88 | FP_clean |
| 52 | noise_T50_b1.0_na_p0.8 | noise | T50 | 181 | 213 | 88 | FP_clean |
| 52 | stuck_T24_na_na_p0.6 | stuck | T24 | 150 | 190 | 88 | FP_clean |
| 52 | stuck_T24_na_na_p0.8 | stuck | T24 | 181 | 213 | 88 | FP_clean |
| 52 | stuck_T30_na_na_p0.2 | stuck | T30 | 87 | 127 | 89 | FP_contam |
| 52 | stuck_T50_na_na_p0.8 | stuck | T50 | 181 | 213 | 88 | FP_clean |
| 57 | bias_T30_a0.3_neg_p0.4 | bias | T30 | 88 | 128 | 61 | FP_clean |
| 57 | bias_T30_a0.5_neg_p0.2 | bias | T30 | 71 | 111 | 61 | FP_clean |
| 57 | bias_T30_a0.75_neg_p0.6 | bias | T30 | 104 | 137 | 62 | FP_clean |
| 57 | gain_T24_a0.25_neg_p0.4 | gain | T24 | 88 | 128 | 62 | FP_clean |
| 57 | gain_T30_a0.5_neg_p0.2 | gain | T30 | 71 | 111 | 62 | FP_clean |
| 57 | gain_T50_a0.5_neg_p0.8 | gain | T50 | 121 | 137 | 62 | FP_clean |
| 57 | gain_T50_a1.0_pos_p0.8 | gain | T50 | 121 | 137 | 62 | FP_clean |
| 57 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 104 | 137 | 62 | FP_clean |
| 57 | multiC_T24+T30+T50_a0.5_na_p0.8 | multi_C | T24+T30+T50 | 121 | 137 | 62 | FP_clean |
| 57 | multiI_T24+T30+T50_a0.3_na_p0.4 | multi_I | T24+T30+T50 | 88 | 128 | 62 | FP_clean |
| 57 | multiI_T24+T30+T50_a0.3_na_p0.8 | multi_I | T24+T30+T50 | 121 | 137 | 62 | FP_clean |
| 57 | multiI_T24+T30+T50_a0.5_na_p0.6 | multi_I | T24+T30+T50 | 104 | 137 | 62 | FP_clean |
| 57 | multiI_T24+T30+T50_a0.5_na_p0.8 | multi_I | T24+T30+T50 | 121 | 137 | 62 | FP_clean |
| 57 | noise_T30_b3.0_na_p0.4 | noise | T30 | 88 | 128 | 62 | FP_clean |
| 57 | stuck_T24_na_na_p0.6 | stuck | T24 | 104 | 137 | 62 | FP_clean |
| 57 | stuck_T30_na_na_p0.2 | stuck | T30 | 71 | 111 | 62 | FP_clean |
| 57 | stuck_T30_na_na_p0.4 | stuck | T30 | 88 | 128 | 62 | FP_clean |
| 57 | stuck_T50_na_na_p0.8 | stuck | T50 | 121 | 137 | 62 | FP_clean |
| 63 | bias_T24_a0.3_pos_p0.2 | bias | T24 | 79 | 119 | 79 | FP_contam |
| 63 | bias_T50_a0.5_pos_p0.8 | bias | T50 | 150 | 174 | 81 | FP_clean |
| 63 | gain_T24_a1.0_pos_p0.6 | gain | T24 | 126 | 166 | 79 | FP_clean |
| 63 | gain_T30_a0.25_neg_p0.8 | gain | T30 | 150 | 174 | 79 | FP_clean |
| 63 | gain_T50_a0.25_neg_p0.2 | gain | T50 | 79 | 119 | 79 | FP_contam |
| 63 | gain_T50_a2.0_pos_p0.8 | gain | T50 | 150 | 174 | 79 | FP_clean |
| 63 | multiC_T24+T30+T50_a0.3_na_p0.4 | multi_C | T24+T30+T50 | 103 | 143 | 79 | FP_clean |
| 63 | multiC_T24+T30+T50_a0.3_na_p0.8 | multi_C | T24+T30+T50 | 150 | 174 | 79 | FP_clean |
| 63 | multiI_T24+T30+T50_a0.3_na_p0.8 | multi_I | T24+T30+T50 | 150 | 174 | 79 | FP_clean |
| 63 | noise_T24_b1.0_na_p0.6 | noise | T24 | 126 | 166 | 79 | FP_clean |
| 63 | noise_T24_b3.0_na_p0.8 | noise | T24 | 150 | 174 | 79 | FP_clean |
| 63 | noise_T30_b2.0_na_p0.2 | noise | T30 | 79 | 119 | 79 | FP_contam |
| 63 | noise_T30_b2.0_na_p0.6 | noise | T30 | 126 | 166 | 79 | FP_clean |
| 63 | stuck_T24_na_na_p0.4 | stuck | T24 | 103 | 143 | 79 | FP_clean |
| 63 | stuck_T30_na_na_p0.6 | stuck | T30 | 126 | 166 | 79 | FP_clean |
| 63 | stuck_T50_na_na_p0.8 | stuck | T50 | 150 | 174 | 79 | FP_clean |
| 64 | bias_T24_a0.3_neg_p0.8 | bias | T24 | 237 | 277 | 78 | FP_clean |
| 64 | bias_T30_a0.3_neg_p0.4 | bias | T30 | 146 | 186 | 96 | FP_clean |
| 64 | bias_T30_a0.3_pos_p0.6 | bias | T30 | 192 | 232 | 96 | FP_clean |
| 64 | bias_T30_a1.0_pos_p0.6 | bias | T30 | 192 | 232 | 96 | FP_clean |
| 64 | gain_T30_a0.5_neg_p0.8 | gain | T30 | 237 | 277 | 96 | FP_clean |
| 64 | gain_T50_a0.75_neg_p0.4 | gain | T50 | 146 | 186 | 96 | FP_clean |
| 64 | gain_T50_a1.5_pos_p0.8 | gain | T50 | 237 | 277 | 96 | FP_clean |
| 64 | multiC_T24+T30+T50_a0.3_na_p0.8 | multi_C | T24+T30+T50 | 237 | 277 | 96 | FP_clean |
| 64 | multiI_T24+T30+T50_a0.3_na_p0.2 | multi_I | T24+T30+T50 | 101 | 141 | 96 | FP_clean |
| 64 | multiI_T24+T30+T50_a0.3_na_p0.6 | multi_I | T24+T30+T50 | 192 | 232 | 96 | FP_clean |
| 64 | noise_T30_b3.0_na_p0.2 | noise | T30 | 101 | 141 | 96 | FP_clean |
| 64 | stuck_T30_na_na_p0.2 | stuck | T30 | 101 | 141 | 96 | FP_clean |
| 64 | stuck_T50_na_na_p0.6 | stuck | T50 | 192 | 232 | 96 | FP_clean |
| 65 | bias_T24_a0.3_pos_p0.8 | bias | T24 | 133 | 153 | 77 | FP_clean |
| 65 | bias_T24_a0.75_pos_p0.8 | bias | T24 | 133 | 153 | 77 | FP_clean |
| 65 | bias_T30_a1.0_pos_p0.2 | bias | T30 | 75 | 115 | 77 | FP_contam |
| 65 | bias_T50_a0.5_pos_p0.8 | bias | T50 | 133 | 153 | 77 | FP_clean |
| 65 | gain_T24_a1.5_pos_p0.6 | gain | T24 | 114 | 153 | 77 | FP_clean |
| 65 | gain_T24_a2.0_pos_p0.6 | gain | T24 | 114 | 153 | 77 | FP_clean |
| 65 | gain_T30_a0.75_neg_p0.6 | gain | T30 | 114 | 153 | 77 | FP_clean |
| 65 | gain_T50_a0.25_neg_p0.4 | gain | T50 | 94 | 134 | 77 | FP_clean |
| 65 | multiC_T24+T30+T50_a0.3_na_p0.6 | multi_C | T24+T30+T50 | 114 | 153 | 77 | FP_clean |
| 65 | multiC_T24+T30+T50_a0.3_na_p0.8 | multi_C | T24+T30+T50 | 133 | 153 | 77 | FP_clean |
| 65 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 114 | 153 | 77 | FP_clean |
| 65 | multiC_T24+T30+T50_a0.5_na_p0.8 | multi_C | T24+T30+T50 | 133 | 153 | 77 | FP_clean |
| 65 | multiI_T24+T30+T50_a0.3_na_p0.8 | multi_I | T24+T30+T50 | 133 | 153 | 77 | FP_clean |
| 65 | multiI_T24+T30+T50_a0.5_na_p0.2 | multi_I | T24+T30+T50 | 75 | 115 | 77 | FP_contam |
| 65 | multiI_T24+T30+T50_a0.5_na_p0.6 | multi_I | T24+T30+T50 | 114 | 153 | 77 | FP_clean |
| 65 | multiI_T24+T30+T50_a0.5_na_p0.8 | multi_I | T24+T30+T50 | 133 | 153 | 77 | FP_clean |
| 65 | noise_T30_b2.0_na_p0.6 | noise | T30 | 114 | 153 | 77 | FP_clean |
| 65 | noise_T30_b3.0_na_p0.8 | noise | T30 | 133 | 153 | 77 | FP_clean |
| 65 | stuck_T24_na_na_p0.2 | stuck | T24 | 75 | 115 | 77 | FP_contam |
| 65 | stuck_T24_na_na_p0.8 | stuck | T24 | 133 | 153 | 77 | FP_clean |
| 65 | stuck_T30_na_na_p0.8 | stuck | T30 | 133 | 153 | 77 | FP_clean |
| 65 | stuck_T50_na_na_p0.6 | stuck | T50 | 114 | 153 | 77 | FP_clean |
| 65 | stuck_T50_na_na_p0.8 | stuck | T50 | 133 | 153 | 77 | FP_clean |
| 67 | bias_T24_a0.3_neg_p0.2 | bias | T24 | 107 | 147 | 73 | FP_clean |
| 67 | bias_T30_a0.3_neg_p0.8 | bias | T30 | 261 | 301 | 61 | FP_clean |
| 67 | bias_T50_a0.75_pos_p0.8 | bias | T50 | 261 | 301 | 65 | FP_clean |
| 67 | gain_T24_a0.5_neg_p0.2 | gain | T24 | 107 | 147 | 61 | FP_clean |
| 67 | gain_T30_a0.5_neg_p0.4 | gain | T30 | 158 | 198 | 61 | FP_clean |
| 67 | gain_T50_a0.25_neg_p0.8 | gain | T50 | 261 | 301 | 61 | FP_clean |
| 67 | multiC_T24+T30+T50_a0.3_na_p0.8 | multi_C | T24+T30+T50 | 261 | 301 | 61 | FP_clean |
| 67 | multiI_T24+T30+T50_a0.3_na_p0.4 | multi_I | T24+T30+T50 | 158 | 198 | 61 | FP_clean |
| 67 | multiI_T24+T30+T50_a0.3_na_p0.6 | multi_I | T24+T30+T50 | 210 | 250 | 61 | FP_clean |
| 67 | multiI_T24+T30+T50_a0.5_na_p0.2 | multi_I | T24+T30+T50 | 107 | 147 | 61 | FP_clean |
| 67 | multiI_T24+T30+T50_a0.5_na_p0.6 | multi_I | T24+T30+T50 | 210 | 250 | 61 | FP_clean |
| 67 | noise_T24_b1.0_na_p0.4 | noise | T24 | 158 | 198 | 61 | FP_clean |
| 67 | noise_T30_b1.0_na_p0.2 | noise | T30 | 107 | 147 | 61 | FP_clean |
| 67 | noise_T50_b3.0_na_p0.8 | noise | T50 | 261 | 301 | 61 | FP_clean |
| 67 | stuck_T30_na_na_p0.6 | stuck | T30 | 210 | 250 | 61 | FP_clean |
| 68 | bias_T24_a0.3_neg_p0.4 | bias | T24 | 113 | 153 | 68 | FP_clean |
| 68 | bias_T24_a0.3_pos_p0.6 | bias | T24 | 141 | 181 | 58 | FP_clean |
| 68 | bias_T30_a1.0_pos_p0.6 | bias | T30 | 141 | 181 | 58 | FP_clean |
| 68 | bias_T50_a0.75_pos_p0.6 | bias | T50 | 141 | 181 | 58 | FP_clean |
| 68 | gain_T30_a0.75_neg_p0.2 | gain | T30 | 84 | 124 | 58 | FP_clean |
| 68 | gain_T30_a1.0_pos_p0.8 | gain | T30 | 170 | 199 | 58 | FP_clean |
| 68 | gain_T50_a1.0_pos_p0.4 | gain | T50 | 113 | 153 | 58 | FP_clean |
| 68 | multiC_T24+T30+T50_a0.3_na_p0.6 | multi_C | T24+T30+T50 | 141 | 181 | 58 | FP_clean |
| 68 | multiC_T24+T30+T50_a0.3_na_p0.8 | multi_C | T24+T30+T50 | 170 | 199 | 58 | FP_clean |
| 68 | multiI_T24+T30+T50_a0.3_na_p0.4 | multi_I | T24+T30+T50 | 113 | 153 | 58 | FP_clean |
| 68 | multiI_T24+T30+T50_a0.3_na_p0.6 | multi_I | T24+T30+T50 | 141 | 181 | 58 | FP_clean |
| 68 | multiI_T24+T30+T50_a0.3_na_p0.8 | multi_I | T24+T30+T50 | 170 | 199 | 58 | FP_clean |
| 68 | multiI_T24+T30+T50_a0.5_na_p0.2 | multi_I | T24+T30+T50 | 84 | 124 | 58 | FP_clean |
| 68 | noise_T30_b1.0_na_p0.8 | noise | T30 | 170 | 199 | 58 | FP_clean |
| 68 | noise_T30_b2.0_na_p0.6 | noise | T30 | 141 | 181 | 58 | FP_clean |
| 68 | noise_T30_b3.0_na_p0.2 | noise | T30 | 84 | 124 | 58 | FP_clean |
| 68 | stuck_T30_na_na_p0.4 | stuck | T30 | 113 | 153 | 58 | FP_clean |
| 68 | stuck_T50_na_na_p0.6 | stuck | T50 | 141 | 181 | 58 | FP_clean |
| 68 | stuck_T50_na_na_p0.8 | stuck | T50 | 170 | 199 | 58 | FP_clean |
| 70 | bias_T24_a0.5_neg_p0.4 | bias | T24 | 88 | 128 | 61 | FP_clean |
| 70 | bias_T24_a0.75_neg_p0.8 | bias | T24 | 121 | 137 | 68 | FP_clean |
| 70 | bias_T24_a1.0_neg_p0.6 | bias | T24 | 104 | 137 | 64 | FP_clean |
| 70 | bias_T50_a0.3_pos_p0.8 | bias | T50 | 121 | 137 | 64 | FP_clean |
| 70 | gain_T24_a2.0_pos_p0.8 | gain | T24 | 121 | 137 | 64 | FP_clean |
| 70 | gain_T30_a0.75_neg_p0.2 | gain | T30 | 71 | 111 | 64 | FP_clean |
| 70 | gain_T30_a1.0_pos_p0.4 | gain | T30 | 88 | 128 | 64 | FP_clean |
| 70 | gain_T50_a0.5_neg_p0.2 | gain | T50 | 71 | 111 | 64 | FP_clean |
| 70 | multiC_T24+T30+T50_a0.3_na_p0.2 | multi_C | T24+T30+T50 | 71 | 111 | 64 | FP_clean |
| 70 | multiC_T24+T30+T50_a0.3_na_p0.4 | multi_C | T24+T30+T50 | 88 | 128 | 64 | FP_clean |
| 70 | multiC_T24+T30+T50_a0.5_na_p0.4 | multi_C | T24+T30+T50 | 88 | 128 | 64 | FP_clean |
| 70 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 104 | 137 | 64 | FP_clean |
| 70 | multiI_T24+T30+T50_a0.3_na_p0.4 | multi_I | T24+T30+T50 | 88 | 128 | 64 | FP_clean |
| 70 | multiI_T24+T30+T50_a0.3_na_p0.6 | multi_I | T24+T30+T50 | 104 | 137 | 64 | FP_clean |
| 70 | multiI_T24+T30+T50_a0.5_na_p0.2 | multi_I | T24+T30+T50 | 71 | 111 | 64 | FP_clean |
| 70 | multiI_T24+T30+T50_a0.5_na_p0.8 | multi_I | T24+T30+T50 | 121 | 137 | 64 | FP_clean |
| 70 | noise_T24_b2.0_na_p0.4 | noise | T24 | 88 | 128 | 64 | FP_clean |
| 70 | noise_T50_b1.0_na_p0.8 | noise | T50 | 121 | 137 | 64 | FP_clean |
| 70 | stuck_T24_na_na_p0.8 | stuck | T24 | 121 | 137 | 64 | FP_clean |
| 70 | stuck_T30_na_na_p0.2 | stuck | T30 | 71 | 111 | 64 | FP_clean |
| 70 | stuck_T30_na_na_p0.6 | stuck | T30 | 104 | 137 | 64 | FP_clean |
| 70 | stuck_T50_na_na_p0.8 | stuck | T50 | 121 | 137 | 64 | FP_clean |
| 79 | bias_T30_a0.5_pos_p0.2 | bias | T30 | 84 | 124 | 67 | FP_clean |
| 79 | bias_T30_a0.5_pos_p0.6 | bias | T30 | 141 | 181 | 90 | FP_clean |
| 79 | bias_T50_a0.5_neg_p0.6 | bias | T50 | 141 | 181 | 67 | FP_clean |
| 79 | bias_T50_a1.0_pos_p0.6 | bias | T50 | 141 | 181 | 67 | FP_clean |
| 79 | gain_T24_a0.25_neg_p0.2 | gain | T24 | 84 | 124 | 67 | FP_clean |
| 79 | gain_T30_a0.25_neg_p0.4 | gain | T30 | 113 | 153 | 67 | FP_clean |
| 79 | gain_T30_a0.5_neg_p0.4 | gain | T30 | 113 | 153 | 67 | FP_clean |
| 79 | gain_T50_a1.0_pos_p0.8 | gain | T50 | 170 | 199 | 67 | FP_clean |
| 79 | multiC_T24+T30+T50_a0.3_na_p0.8 | multi_C | T24+T30+T50 | 170 | 199 | 67 | FP_clean |
| 79 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 141 | 181 | 67 | FP_clean |
| 79 | multiC_T24+T30+T50_a0.5_na_p0.8 | multi_C | T24+T30+T50 | 170 | 199 | 67 | FP_clean |
| 79 | multiI_T24+T30+T50_a0.5_na_p0.2 | multi_I | T24+T30+T50 | 84 | 124 | 67 | FP_clean |
| 79 | multiI_T24+T30+T50_a0.5_na_p0.4 | multi_I | T24+T30+T50 | 113 | 153 | 67 | FP_clean |
| 79 | multiI_T24+T30+T50_a0.5_na_p0.6 | multi_I | T24+T30+T50 | 141 | 181 | 67 | FP_clean |
| 79 | multiI_T24+T30+T50_a0.5_na_p0.8 | multi_I | T24+T30+T50 | 170 | 199 | 67 | FP_clean |
| 79 | noise_T24_b1.0_na_p0.2 | noise | T24 | 84 | 124 | 67 | FP_clean |
| 79 | noise_T24_b1.0_na_p0.4 | noise | T24 | 113 | 153 | 67 | FP_clean |
| 79 | noise_T30_b2.0_na_p0.8 | noise | T30 | 170 | 199 | 67 | FP_clean |
| 79 | noise_T50_b2.0_na_p0.6 | noise | T50 | 141 | 181 | 67 | FP_clean |
| 79 | stuck_T30_na_na_p0.2 | stuck | T30 | 84 | 124 | 67 | FP_clean |
| 79 | stuck_T30_na_na_p0.4 | stuck | T30 | 113 | 153 | 67 | FP_clean |
| 79 | stuck_T30_na_na_p0.8 | stuck | T30 | 170 | 199 | 67 | FP_clean |
| 85 | bias_T30_a0.75_neg_p0.2 | bias | T30 | 82 | 122 | 81 | FP_clean |
| 85 | bias_T50_a0.5_neg_p0.6 | bias | T50 | 135 | 175 | 89 | FP_clean |
| 85 | bias_T50_a0.75_pos_p0.8 | bias | T50 | 161 | 188 | 78 | FP_clean |
| 85 | gain_T24_a0.5_neg_p0.6 | gain | T24 | 135 | 175 | 78 | FP_clean |
| 85 | gain_T30_a0.5_neg_p0.2 | gain | T30 | 82 | 122 | 78 | FP_clean |
| 85 | gain_T30_a1.5_pos_p0.2 | gain | T30 | 82 | 122 | 78 | FP_clean |
| 85 | multiC_T24+T30+T50_a0.5_na_p0.8 | multi_C | T24+T30+T50 | 161 | 188 | 78 | FP_clean |
| 85 | multiI_T24+T30+T50_a0.3_na_p0.6 | multi_I | T24+T30+T50 | 135 | 175 | 78 | FP_clean |
| 85 | multiI_T24+T30+T50_a0.5_na_p0.8 | multi_I | T24+T30+T50 | 161 | 188 | 78 | FP_clean |
| 85 | noise_T30_b1.0_na_p0.4 | noise | T30 | 108 | 148 | 78 | FP_clean |
| 85 | noise_T30_b2.0_na_p0.2 | noise | T30 | 82 | 122 | 78 | FP_clean |
| 85 | noise_T30_b3.0_na_p0.8 | noise | T30 | 161 | 188 | 78 | FP_clean |
| 85 | noise_T50_b1.0_na_p0.2 | noise | T50 | 82 | 122 | 78 | FP_clean |
| 85 | stuck_T24_na_na_p0.8 | stuck | T24 | 161 | 188 | 78 | FP_clean |
| 85 | stuck_T30_na_na_p0.2 | stuck | T30 | 82 | 122 | 78 | FP_clean |
| 90 | bias_T24_a0.3_neg_p0.4 | bias | T24 | 95 | 135 | 61 | FP_clean |
| 90 | bias_T24_a0.5_pos_p0.8 | bias | T24 | 134 | 154 | 76 | FP_clean |
| 90 | bias_T30_a0.5_pos_p0.8 | bias | T30 | 134 | 154 | 61 | FP_clean |
| 90 | bias_T50_a1.0_neg_p0.8 | bias | T50 | 134 | 154 | 61 | FP_clean |
| 90 | gain_T24_a0.75_neg_p0.8 | gain | T24 | 134 | 154 | 61 | FP_clean |
| 90 | gain_T24_a1.0_pos_p0.8 | gain | T24 | 134 | 154 | 61 | FP_clean |
| 90 | gain_T24_a1.5_pos_p0.6 | gain | T24 | 114 | 154 | 61 | FP_clean |
| 90 | gain_T30_a0.25_neg_p0.8 | gain | T30 | 134 | 154 | 61 | FP_clean |
| 90 | multiC_T24+T30+T50_a0.3_na_p0.4 | multi_C | T24+T30+T50 | 95 | 135 | 61 | FP_clean |
| 90 | multiC_T24+T30+T50_a0.3_na_p0.6 | multi_C | T24+T30+T50 | 114 | 154 | 61 | FP_clean |
| 90 | multiI_T24+T30+T50_a0.3_na_p0.2 | multi_I | T24+T30+T50 | 75 | 115 | 61 | FP_clean |
| 90 | multiI_T24+T30+T50_a0.3_na_p0.4 | multi_I | T24+T30+T50 | 95 | 135 | 61 | FP_clean |
| 90 | multiI_T24+T30+T50_a0.3_na_p0.8 | multi_I | T24+T30+T50 | 134 | 154 | 61 | FP_clean |
| 90 | multiI_T24+T30+T50_a0.5_na_p0.4 | multi_I | T24+T30+T50 | 95 | 135 | 61 | FP_clean |
| 90 | noise_T24_b1.0_na_p0.4 | noise | T24 | 95 | 135 | 61 | FP_clean |
| 90 | noise_T30_b1.0_na_p0.4 | noise | T30 | 95 | 135 | 61 | FP_clean |
| 90 | noise_T50_b2.0_na_p0.8 | noise | T50 | 134 | 154 | 61 | FP_clean |
| 90 | stuck_T24_na_na_p0.6 | stuck | T24 | 114 | 154 | 61 | FP_clean |
| 90 | stuck_T30_na_na_p0.8 | stuck | T30 | 134 | 154 | 61 | FP_clean |
| 90 | stuck_T50_na_na_p0.6 | stuck | T50 | 114 | 154 | 61 | FP_clean |
