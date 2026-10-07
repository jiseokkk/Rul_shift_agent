# 평가 v2 (시나리오 단위) — Qwen3.8-27B-NVFP4_or500_seed42_20261002-175400

라벨 theta_primary · 첫 판정 t₀ = 55 · Δ = 5, w = 0, H = 40, k = 1 · 첫 경보 원칙 (t₀ 이후 첫 경보, 오염 전 포함) · ERROR 는 경보 아님 (오류율 0.0000) · 규약 docs/eval_v2_scenario.md

시나리오 500 = 저하 159 + 비저하 341 · unit 20 · 판정 로그가 창 끝에 못 미친 시나리오 0

## 1. 메인 표 (기준선 고정)

| method | n_degraded | detection_rate | pre_contam_rate | pre_degr_rate | miss_rate | delay_median | n_nondegraded | scenario_FAR | FAR_clean | FAR_contam | isolation_rate |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 항상 0 | 159 | 0 | 0 | 0 | 1 |  | 341 | 0 | 0 | 0 |  |
| 항상 1 | 159 | 0 | 1 | 0 | 0 |  | 341 | 1 | 1 | 0 |  |
| 무작위 p=0.052 (에이전트 경보율) | 159 | 0.016 | 0.895 | 0.043 | 0.046 | 2.128 | 341 | 0.992 | 0.940 | 0.052 | 0 |
| 무작위 p=0.050 | 159 | 0.018 | 0.892 | 0.045 | 0.045 | 2.042 | 341 | 0.991 | 0.936 | 0.055 | 0 |
| LLM Agent | 159 | 0.132 | 0.239 | 0.226 | 0.403 | 2 | 341 | 0.657 | 0.399 | 0.258 | 0.714 |

## 2. unit bootstrap 95% CI (2000회)

| metric | point | lo | hi |
|---|---|---|---|
| detection_rate | 0.132 | 0.084 | 0.188 |
| pre_contam_rate | 0.239 | 0.120 | 0.364 |
| pre_degr_rate | 0.226 | 0.163 | 0.293 |
| miss_rate | 0.403 | 0.289 | 0.516 |
| scenario_FAR | 0.657 | 0.510 | 0.801 |
| isolation_rate | 0.714 | 0.474 | 0.913 |

## 3. 유형별

| type | n_degraded | detection_rate | pre_contam_rate | pre_degr_rate | miss_rate | delay_median | n_nondegraded | scenario_FAR | FAR_clean | FAR_contam | isolation_rate |
|---|---|---|---|---|---|---|---|---|---|---|---|
| bias | 22 | 0.136 | 0.091 | 0.045 | 0.727 | 0 | 62 | 0.548 | 0.371 | 0.177 | 0.333 |
| gain | 16 | 0.062 | 0.250 | 0.375 | 0.312 | 3 | 68 | 0.529 | 0.382 | 0.147 | 1 |
| multi_C | 46 | 0.065 | 0.239 | 0.043 | 0.652 | 0 | 37 | 0.568 | 0.541 | 0.027 | 0.667 |
| multi_I | 17 | 0.235 | 0.118 | 0 | 0.647 | 4 | 66 | 0.621 | 0.439 | 0.182 | 0.500 |
| noise | 32 | 0.250 | 0.312 | 0.406 | 0.031 | 2.500 | 51 | 0.745 | 0.392 | 0.353 | 0.875 |
| stuck | 26 | 0.077 | 0.346 | 0.538 | 0.038 | 0 | 57 | 0.947 | 0.316 | 0.632 | 1 |

## 4. 센서별

| sensor | n_degraded | detection_rate | pre_contam_rate | pre_degr_rate | miss_rate | delay_median | n_nondegraded | scenario_FAR | FAR_clean | FAR_contam | isolation_rate |
|---|---|---|---|---|---|---|---|---|---|---|---|
| T24 | 43 | 0.163 | 0.302 | 0.302 | 0.233 | 1 | 69 | 0.638 | 0.406 | 0.232 | 0.857 |
| T24+T30+T50 | 63 | 0.111 | 0.206 | 0.032 | 0.651 | 2 | 103 | 0.602 | 0.476 | 0.126 | 0.571 |
| T30 | 2 | 0 | 0 | 1 | 0 |  | 108 | 0.685 | 0.269 | 0.417 |  |
| T50 | 51 | 0.137 | 0.235 | 0.373 | 0.255 | 3 | 61 | 0.721 | 0.492 | 0.230 | 0.714 |

## 5. 오염 시점별

| timing_p | n_degraded | detection_rate | pre_contam_rate | pre_degr_rate | miss_rate | delay_median | n_nondegraded | scenario_FAR | FAR_clean | FAR_contam | isolation_rate |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.200 | 64 | 0.188 | 0 | 0.266 | 0.547 | 1 | 60 | 0.600 | 0 | 0.600 | 0.833 |
| 0.400 | 62 | 0.097 | 0.242 | 0.274 | 0.387 | 0.500 | 63 | 0.571 | 0.190 | 0.381 | 0.500 |
| 0.600 | 32 | 0.094 | 0.688 | 0.062 | 0.156 | 3 | 94 | 0.660 | 0.479 | 0.181 | 0.667 |
| 0.800 | 1 | 0 | 1 | 0 | 0 |  | 124 | 0.726 | 0.637 | 0.089 |  |

### 오염 전 경보율 (저하·비저하 합산, 오염 전 구간 길이 = τ_s − 55)

| timing_p | n | pre_len_median | pre_contam_rate |
|---|---|---|---|
| 0.200 | 124 | 29 | 0 |
| 0.400 | 125 | 58 | 0.216 |
| 0.600 | 126 | 86 | 0.532 |
| 0.800 | 125 | 115 | 0.640 |

## 6. 저하 시나리오 상세

| unit | scenario_id | type | sensor | tau_s | tau_d | window_lo | window_hi | t_hat | result | delay | iso_hit |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | bias_T50_a1.0_pos_p0.2 | bias | T50 | 82 | 90 | 90 | 95 | 90 | TP | 0 | True |
| 1 | gain_T24_a2.0_pos_p0.4 | gain | T24 | 110 | 138 | 138 | 143 | 114 | PreDegr |  |  |
| 1 | multiC_T24+T30+T50_a0.3_na_p0.2 | multi_C | T24+T30+T50 | 82 | 92 | 92 | 97 | 88 | PreDegr |  |  |
| 1 | multiC_T24+T30+T50_a0.3_na_p0.4 | multi_C | T24+T30+T50 | 110 | 117 | 117 | 122 | 129 | Miss |  |  |
| 1 | multiC_T24+T30+T50_a0.5_na_p0.2 | multi_C | T24+T30+T50 | 82 | 90 | 90 | 95 | 90 | TP | 0 | True |
| 1 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 137 | 143 | 143 | 148 | 121 | PreContam |  |  |
| 1 | multiI_T24+T30+T50_a0.3_na_p0.2 | multi_I | T24+T30+T50 | 82 | 93 | 93 | 98 | 96 | TP | 3 | True |
| 1 | noise_T24_b2.0_na_p0.6 | noise | T24 | 137 | 152 | 152 | 157 | 116 | PreContam |  |  |
| 1 | noise_T50_b2.0_na_p0.2 | noise | T50 | 82 | 105 | 105 | 110 | 88 | PreDegr |  |  |
| 1 | stuck_T24_na_na_p0.6 | stuck | T24 | 137 | 148 | 148 | 153 | 116 | PreContam |  |  |
| 1 | stuck_T50_na_na_p0.4 | stuck | T50 | 110 | 116 | 116 | 121 | 113 | PreDegr |  |  |
| 1 | stuck_T50_na_na_p0.6 | stuck | T50 | 137 | 155 | 155 | 160 | 116 | PreContam |  |  |
| 9 | bias_T24_a0.75_neg_p0.4 | bias | T24 | 113 | 121 | 121 | 126 | 134 | Miss |  |  |
| 9 | gain_T50_a2.0_pos_p0.2 | gain | T50 | 84 | 110 | 110 | 115 | 138 | Miss |  |  |
| 9 | multiC_T24+T30+T50_a0.3_na_p0.2 | multi_C | T24+T30+T50 | 84 | 101 | 101 | 106 | 108 | Miss |  |  |
| 9 | multiC_T24+T30+T50_a0.5_na_p0.4 | multi_C | T24+T30+T50 | 113 | 117 | 117 | 122 |  | Miss |  |  |
| 9 | noise_T24_b2.0_na_p0.4 | noise | T24 | 113 | 159 | 159 | 164 | 118 | PreDegr |  |  |
| 9 | stuck_T24_na_na_p0.2 | stuck | T24 | 84 | 123 | 123 | 128 | 97 | PreDegr |  |  |
| 10 | bias_T50_a0.5_pos_p0.4 | bias | T50 | 122 | 146 | 146 | 151 |  | Miss |  |  |
| 10 | gain_T50_a1.5_pos_p0.2 | gain | T50 | 88 | 122 | 122 | 127 | 95 | PreDegr |  |  |
| 10 | multiC_T24+T30+T50_a0.3_na_p0.4 | multi_C | T24+T30+T50 | 122 | 132 | 132 | 137 |  | Miss |  |  |
| 10 | multiC_T24+T30+T50_a0.5_na_p0.2 | multi_C | T24+T30+T50 | 88 | 104 | 104 | 109 | 104 | TP | 0 | True |
| 10 | multiI_T24+T30+T50_a0.5_na_p0.4 | multi_I | T24+T30+T50 | 122 | 127 | 127 | 132 | 132 | TP | 5 | True |
| 10 | noise_T24_b3.0_na_p0.6 | noise | T24 | 155 | 159 | 159 | 164 | 150 | PreContam |  |  |
| 10 | noise_T50_b1.0_na_p0.4 | noise | T50 | 122 | 125 | 125 | 130 | 123 | PreDegr |  |  |
| 10 | stuck_T50_na_na_p0.2 | stuck | T50 | 88 | 145 | 145 | 150 | 97 | PreDegr |  |  |
| 11 | bias_T50_a0.5_pos_p0.4 | bias | T50 | 129 | 136 | 136 | 141 | 136 | TP | 0 | False |
| 11 | bias_T50_a1.0_pos_p0.2 | bias | T50 | 92 | 117 | 117 | 122 | 133 | Miss |  |  |
| 11 | gain_T24_a1.5_pos_p0.6 | gain | T24 | 166 | 197 | 197 | 202 | 146 | PreContam |  |  |
| 11 | multiC_T24+T30+T50_a0.3_na_p0.2 | multi_C | T24+T30+T50 | 92 | 134 | 134 | 139 |  | Miss |  |  |
| 11 | multiC_T24+T30+T50_a0.3_na_p0.4 | multi_C | T24+T30+T50 | 129 | 135 | 135 | 140 | 153 | Miss |  |  |
| 11 | multiC_T24+T30+T50_a0.5_na_p0.2 | multi_C | T24+T30+T50 | 92 | 117 | 117 | 122 | 127 | Miss |  |  |
| 11 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 166 | 172 | 172 | 177 | 146 | PreContam |  |  |
| 11 | multiI_T24+T30+T50_a0.3_na_p0.2 | multi_I | T24+T30+T50 | 92 | 122 | 122 | 127 | 134 | Miss |  |  |
| 11 | noise_T50_b2.0_na_p0.6 | noise | T50 | 166 | 205 | 205 | 210 | 146 | PreContam |  |  |
| 11 | noise_T50_b3.0_na_p0.6 | noise | T50 | 166 | 171 | 171 | 176 | 146 | PreContam |  |  |
| 11 | stuck_T24_na_na_p0.4 | stuck | T24 | 129 | 134 | 134 | 139 | 134 | TP | 0 | True |
| 11 | stuck_T50_na_na_p0.6 | stuck | T50 | 166 | 181 | 181 | 186 | 146 | PreContam |  |  |
| 17 | bias_T50_a0.75_pos_p0.4 | bias | T50 | 143 | 146 | 146 | 151 | 165 | Miss |  |  |
| 17 | gain_T50_a1.5_pos_p0.2 | gain | T50 | 99 | 139 | 139 | 144 | 119 | PreDegr |  |  |
| 17 | multiC_T24+T30+T50_a0.5_na_p0.2 | multi_C | T24+T30+T50 | 99 | 111 | 111 | 116 | 117 | Miss |  |  |
| 17 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 188 | 192 | 192 | 197 | 167 | PreContam |  |  |
| 17 | multiI_T24+T30+T50_a0.5_na_p0.2 | multi_I | T24+T30+T50 | 99 | 147 | 147 | 152 | 165 | Miss |  |  |
| 17 | noise_T24_b1.0_na_p0.2 | noise | T24 | 99 | 140 | 140 | 145 | 142 | TP | 2 | True |
| 17 | noise_T24_b3.0_na_p0.6 | noise | T24 | 188 | 190 | 190 | 195 | 167 | PreContam |  |  |
| 17 | noise_T50_b1.0_na_p0.2 | noise | T50 | 99 | 162 | 162 | 167 | 165 | TP | 3 | False |
| 17 | noise_T50_b3.0_na_p0.2 | noise | T50 | 99 | 110 | 110 | 115 | 100 | PreDegr |  |  |
| 17 | stuck_T50_na_na_p0.2 | stuck | T50 | 99 | 186 | 186 | 191 | 114 | PreDegr |  |  |
| 17 | stuck_T50_na_na_p0.4 | stuck | T50 | 143 | 213 | 213 | 218 | 153 | PreDegr |  |  |
| 26 | bias_T24_a1.0_neg_p0.2 | bias | T24 | 84 | 89 | 89 | 94 |  | Miss |  |  |
| 26 | bias_T24_a1.0_neg_p0.6 | bias | T24 | 141 | 147 | 147 | 152 |  | Miss |  |  |
| 26 | bias_T50_a1.0_neg_p0.4 | bias | T50 | 113 | 116 | 116 | 121 | 128 | Miss |  |  |
| 26 | gain_T24_a2.0_pos_p0.2 | gain | T24 | 84 | 100 | 100 | 105 | 94 | PreDegr |  |  |
| 26 | multiC_T24+T30+T50_a0.3_na_p0.4 | multi_C | T24+T30+T50 | 113 | 117 | 117 | 122 |  | Miss |  |  |
| 26 | multiI_T24+T30+T50_a0.3_na_p0.4 | multi_I | T24+T30+T50 | 113 | 123 | 123 | 128 |  | Miss |  |  |
| 26 | noise_T24_b3.0_na_p0.6 | noise | T24 | 141 | 177 | 177 | 182 | 151 | PreDegr |  |  |
| 26 | noise_T50_b1.0_na_p0.4 | noise | T50 | 113 | 131 | 131 | 136 | 129 | PreDegr |  |  |
| 26 | stuck_T24_na_na_p0.2 | stuck | T24 | 84 | 136 | 136 | 141 | 96 | PreDegr |  |  |
| 32 | bias_T24_a1.0_neg_p0.2 | bias | T24 | 82 | 85 | 85 | 90 |  | Miss |  |  |
| 32 | bias_T50_a0.75_neg_p0.4 | bias | T50 | 109 | 123 | 123 | 128 | 111 | PreDegr |  |  |
| 32 | gain_T50_a2.0_pos_p0.4 | gain | T50 | 109 | 111 | 111 | 116 | 128 | Miss |  |  |
| 32 | multiC_T24+T30+T50_a0.3_na_p0.2 | multi_C | T24+T30+T50 | 82 | 86 | 86 | 91 |  | Miss |  |  |
| 32 | multiC_T24+T30+T50_a0.3_na_p0.4 | multi_C | T24+T30+T50 | 109 | 122 | 122 | 127 |  | Miss |  |  |
| 32 | multiC_T24+T30+T50_a0.5_na_p0.4 | multi_C | T24+T30+T50 | 109 | 114 | 114 | 119 |  | Miss |  |  |
| 32 | noise_T24_b2.0_na_p0.2 | noise | T24 | 82 | 82 | 82 | 87 | 99 | Miss |  |  |
| 32 | noise_T50_b2.0_na_p0.2 | noise | T50 | 82 | 87 | 87 | 92 | 85 | PreDegr |  |  |
| 48 | bias_T50_a0.5_neg_p0.2 | bias | T50 | 90 | 104 | 104 | 109 | 158 | Miss |  |  |
| 48 | gain_T50_a1.5_pos_p0.2 | gain | T50 | 90 | 99 | 99 | 104 | 116 | Miss |  |  |
| 48 | multiC_T24+T30+T50_a0.3_na_p0.4 | multi_C | T24+T30+T50 | 125 | 134 | 134 | 139 | 114 | PreContam |  |  |
| 48 | multiC_T24+T30+T50_a0.5_na_p0.2 | multi_C | T24+T30+T50 | 90 | 94 | 94 | 99 | 119 | Miss |  |  |
| 48 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 161 | 169 | 169 | 174 |  | Miss |  |  |
| 48 | multiI_T24+T30+T50_a0.3_na_p0.2 | multi_I | T24+T30+T50 | 90 | 99 | 99 | 104 | 119 | Miss |  |  |
| 48 | multiI_T24+T30+T50_a0.3_na_p0.4 | multi_I | T24+T30+T50 | 125 | 139 | 139 | 144 | 231 | Miss |  |  |
| 48 | multiI_T24+T30+T50_a0.5_na_p0.2 | multi_I | T24+T30+T50 | 90 | 96 | 96 | 101 |  | Miss |  |  |
| 48 | multiI_T24+T30+T50_a0.5_na_p0.4 | multi_I | T24+T30+T50 | 125 | 132 | 132 | 137 |  | Miss |  |  |
| 48 | stuck_T24_na_na_p0.4 | stuck | T24 | 125 | 190 | 190 | 195 | 137 | PreDegr |  |  |
| 48 | stuck_T50_na_na_p0.4 | stuck | T50 | 125 | 145 | 145 | 150 | 132 | PreDegr |  |  |
| 49 | bias_T24_a0.5_neg_p0.4 | bias | T24 | 119 | 127 | 127 | 132 | 128 | TP | 1 | False |
| 49 | bias_T24_a0.5_pos_p0.4 | bias | T24 | 119 | 129 | 129 | 134 |  | Miss |  |  |
| 49 | gain_T24_a2.0_pos_p0.4 | gain | T24 | 119 | 126 | 126 | 131 | 122 | PreDegr |  |  |
| 49 | multiC_T24+T30+T50_a0.3_na_p0.4 | multi_C | T24+T30+T50 | 119 | 128 | 128 | 133 |  | Miss |  |  |
| 49 | multiC_T24+T30+T50_a0.5_na_p0.2 | multi_C | T24+T30+T50 | 87 | 94 | 94 | 99 | 124 | Miss |  |  |
| 49 | noise_T24_b3.0_na_p0.2 | noise | T24 | 87 | 97 | 97 | 102 | 92 | PreDegr |  |  |
| 49 | noise_T50_b3.0_na_p0.4 | noise | T50 | 119 | 132 | 132 | 137 | 122 | PreDegr |  |  |
| 49 | stuck_T24_na_na_p0.4 | stuck | T24 | 119 | 128 | 128 | 133 | 136 | Miss |  |  |
| 49 | stuck_T24_na_na_p0.8 | stuck | T24 | 183 | 199 | 199 | 204 | 124 | PreContam |  |  |
| 49 | stuck_T50_na_na_p0.6 | stuck | T50 | 151 | 166 | 166 | 171 | 124 | PreContam |  |  |
| 52 | bias_T50_a0.75_pos_p0.4 | bias | T50 | 118 | 123 | 123 | 128 | 100 | PreContam |  |  |
| 52 | bias_T50_a1.0_pos_p0.4 | bias | T50 | 118 | 122 | 122 | 127 | 100 | PreContam |  |  |
| 52 | gain_T24_a1.0_pos_p0.4 | gain | T24 | 118 | 133 | 133 | 138 | 100 | PreContam |  |  |
| 52 | gain_T50_a2.0_pos_p0.4 | gain | T50 | 118 | 122 | 122 | 127 | 100 | PreContam |  |  |
| 52 | multiC_T24+T30+T50_a0.3_na_p0.2 | multi_C | T24+T30+T50 | 87 | 92 | 92 | 97 |  | Miss |  |  |
| 52 | multiC_T24+T30+T50_a0.3_na_p0.4 | multi_C | T24+T30+T50 | 118 | 125 | 125 | 130 | 100 | PreContam |  |  |
| 52 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 150 | 154 | 154 | 159 | 100 | PreContam |  |  |
| 52 | noise_T24_b3.0_na_p0.2 | noise | T24 | 87 | 87 | 87 | 92 | 87 | TP | 0 | True |
| 57 | bias_T50_a0.75_neg_p0.2 | bias | T50 | 71 | 78 | 78 | 83 | 84 | Miss |  |  |
| 57 | multiC_T24+T30+T50_a0.3_na_p0.2 | multi_C | T24+T30+T50 | 71 | 84 | 84 | 89 | 90 | Miss |  |  |
| 57 | multiC_T24+T30+T50_a0.5_na_p0.4 | multi_C | T24+T30+T50 | 88 | 91 | 91 | 96 | 90 | PreDegr |  |  |
| 57 | noise_T50_b2.0_na_p0.2 | noise | T50 | 71 | 75 | 75 | 80 | 79 | TP | 4 | True |
| 57 | noise_T50_b3.0_na_p0.2 | noise | T50 | 71 | 74 | 74 | 79 | 78 | TP | 4 | True |
| 57 | noise_T50_b3.0_na_p0.4 | noise | T50 | 88 | 89 | 89 | 94 | 88 | PreDegr |  |  |
| 63 | bias_T24_a1.0_neg_p0.4 | bias | T24 | 103 | 106 | 106 | 111 | 134 | Miss |  |  |
| 63 | bias_T50_a1.0_pos_p0.2 | bias | T50 | 79 | 84 | 84 | 89 |  | Miss |  |  |
| 63 | multiC_T24+T30+T50_a0.3_na_p0.2 | multi_C | T24+T30+T50 | 79 | 89 | 89 | 94 |  | Miss |  |  |
| 63 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 126 | 135 | 135 | 140 |  | Miss |  |  |
| 63 | multiI_T24+T30+T50_a0.3_na_p0.2 | multi_I | T24+T30+T50 | 79 | 89 | 89 | 94 |  | Miss |  |  |
| 63 | multiI_T24+T30+T50_a0.3_na_p0.4 | multi_I | T24+T30+T50 | 103 | 132 | 132 | 137 | 137 | TP | 5 | False |
| 63 | multiI_T24+T30+T50_a0.5_na_p0.6 | multi_I | T24+T30+T50 | 126 | 135 | 135 | 140 | 137 | TP | 2 | False |
| 63 | stuck_T50_na_na_p0.2 | stuck | T50 | 79 | 98 | 98 | 103 | 97 | PreDegr |  |  |
| 64 | gain_T24_a1.5_pos_p0.4 | gain | T24 | 146 | 185 | 185 | 190 | 112 | PreContam |  |  |
| 64 | multiC_T24+T30+T50_a0.5_na_p0.2 | multi_C | T24+T30+T50 | 101 | 106 | 106 | 111 | 139 | Miss |  |  |
| 64 | multiC_T24+T30+T50_a0.5_na_p0.4 | multi_C | T24+T30+T50 | 146 | 152 | 152 | 157 | 119 | PreContam |  |  |
| 64 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 192 | 197 | 197 | 202 | 112 | PreContam |  |  |
| 64 | multiI_T24+T30+T50_a0.3_na_p0.4 | multi_I | T24+T30+T50 | 146 | 154 | 154 | 159 | 112 | PreContam |  |  |
| 64 | multiI_T24+T30+T50_a0.5_na_p0.6 | multi_I | T24+T30+T50 | 192 | 197 | 197 | 202 | 112 | PreContam |  |  |
| 64 | noise_T24_b3.0_na_p0.2 | noise | T24 | 101 | 104 | 104 | 109 | 106 | TP | 2 | True |
| 64 | noise_T24_b3.0_na_p0.4 | noise | T24 | 146 | 182 | 182 | 187 | 112 | PreContam |  |  |
| 64 | noise_T24_b3.0_na_p0.6 | noise | T24 | 192 | 195 | 195 | 200 | 112 | PreContam |  |  |
| 64 | noise_T50_b2.0_na_p0.6 | noise | T50 | 192 | 207 | 207 | 212 | 112 | PreContam |  |  |
| 64 | stuck_T24_na_na_p0.2 | stuck | T24 | 101 | 187 | 187 | 192 | 113 | PreDegr |  |  |
| 64 | stuck_T50_na_na_p0.4 | stuck | T50 | 146 | 162 | 162 | 167 | 112 | PreContam |  |  |
| 65 | gain_T50_a1.5_pos_p0.2 | gain | T50 | 75 | 82 | 82 | 87 | 106 | Miss |  |  |
| 65 | multiC_T24+T30+T50_a0.5_na_p0.4 | multi_C | T24+T30+T50 | 94 | 97 | 97 | 102 | 92 | PreContam |  |  |
| 65 | noise_T24_b3.0_na_p0.4 | noise | T24 | 94 | 96 | 96 | 101 | 92 | PreContam |  |  |
| 65 | noise_T30_b3.0_na_p0.2 | noise | T30 | 75 | 120 | 120 | 125 | 78 | PreDegr |  |  |
| 67 | bias_T24_a1.0_pos_p0.2 | bias | T24 | 107 | 118 | 118 | 123 | 137 | Miss |  |  |
| 67 | gain_T24_a0.75_neg_p0.2 | gain | T24 | 107 | 190 | 190 | 195 | 139 | PreDegr |  |  |
| 67 | multiC_T24+T30+T50_a0.3_na_p0.4 | multi_C | T24+T30+T50 | 158 | 178 | 178 | 183 | 141 | PreContam |  |  |
| 67 | multiC_T24+T30+T50_a0.5_na_p0.2 | multi_C | T24+T30+T50 | 107 | 115 | 115 | 120 | 139 | Miss |  |  |
| 67 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 210 | 214 | 214 | 219 | 141 | PreContam |  |  |
| 67 | noise_T50_b2.0_na_p0.6 | noise | T50 | 210 | 218 | 218 | 223 | 141 | PreContam |  |  |
| 67 | stuck_T24_na_na_p0.6 | stuck | T24 | 210 | 261 | 261 | 266 | 141 | PreContam |  |  |
| 67 | stuck_T50_na_na_p0.2 | stuck | T50 | 107 | 128 | 128 | 133 | 123 | PreDegr |  |  |
| 67 | stuck_T50_na_na_p0.4 | stuck | T50 | 158 | 190 | 190 | 195 | 141 | PreContam |  |  |
| 68 | bias_T50_a0.3_neg_p0.2 | bias | T50 | 84 | 113 | 113 | 118 |  | Miss |  |  |
| 68 | gain_T24_a1.0_pos_p0.4 | gain | T24 | 113 | 135 | 135 | 140 |  | Miss |  |  |
| 68 | multiC_T24+T30+T50_a0.3_na_p0.4 | multi_C | T24+T30+T50 | 113 | 121 | 121 | 126 |  | Miss |  |  |
| 68 | multiC_T24+T30+T50_a0.5_na_p0.2 | multi_C | T24+T30+T50 | 84 | 88 | 88 | 93 | 97 | Miss |  |  |
| 68 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 141 | 147 | 147 | 152 |  | Miss |  |  |
| 68 | noise_T50_b3.0_na_p0.6 | noise | T50 | 141 | 144 | 144 | 149 | 143 | PreDegr |  |  |
| 68 | stuck_T24_na_na_p0.2 | stuck | T24 | 84 | 93 | 93 | 98 | 93 | TP | 0 | True |
| 70 | noise_T50_b2.0_na_p0.6 | noise | T50 | 104 | 105 | 105 | 110 | 109 | TP | 4 | True |
| 70 | noise_T50_b3.0_na_p0.4 | noise | T50 | 88 | 89 | 89 | 94 | 89 | TP | 0 | True |
| 79 | multiC_T24+T30+T50_a0.3_na_p0.2 | multi_C | T24+T30+T50 | 84 | 92 | 92 | 97 | 92 | TP | 0 | False |
| 79 | stuck_T24_na_na_p0.6 | stuck | T24 | 141 | 156 | 156 | 161 | 100 | PreContam |  |  |
| 85 | bias_T50_a0.75_neg_p0.2 | bias | T50 | 82 | 85 | 85 | 90 | 123 | Miss |  |  |
| 85 | gain_T24_a2.0_pos_p0.6 | gain | T24 | 135 | 149 | 149 | 154 | 152 | TP | 3 | True |
| 85 | multiC_T24+T30+T50_a0.3_na_p0.4 | multi_C | T24+T30+T50 | 108 | 126 | 126 | 131 |  | Miss |  |  |
| 85 | multiC_T24+T30+T50_a0.5_na_p0.4 | multi_C | T24+T30+T50 | 108 | 111 | 111 | 116 |  | Miss |  |  |
| 85 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 135 | 141 | 141 | 146 |  | Miss |  |  |
| 85 | multiI_T24+T30+T50_a0.3_na_p0.2 | multi_I | T24+T30+T50 | 82 | 87 | 87 | 92 |  | Miss |  |  |
| 85 | multiI_T24+T30+T50_a0.3_na_p0.4 | multi_I | T24+T30+T50 | 108 | 116 | 116 | 121 |  | Miss |  |  |
| 85 | multiI_T24+T30+T50_a0.5_na_p0.2 | multi_I | T24+T30+T50 | 82 | 84 | 84 | 89 |  | Miss |  |  |
| 85 | stuck_T24_na_na_p0.4 | stuck | T24 | 108 | 148 | 148 | 153 | 127 | PreDegr |  |  |
| 85 | stuck_T50_na_na_p0.4 | stuck | T50 | 108 | 116 | 116 | 121 | 112 | PreDegr |  |  |
| 90 | multiC_T24+T30+T50_a0.3_na_p0.2 | multi_C | T24+T30+T50 | 75 | 80 | 80 | 85 |  | Miss |  |  |
| 90 | multiC_T24+T30+T50_a0.5_na_p0.2 | multi_C | T24+T30+T50 | 75 | 78 | 78 | 83 |  | Miss |  |  |
| 90 | noise_T30_b3.0_na_p0.4 | noise | T30 | 95 | 103 | 103 | 108 | 95 | PreDegr |  |  |
| 90 | stuck_T24_na_na_p0.4 | stuck | T24 | 95 | 110 | 110 | 115 | 104 | PreDegr |  |  |

## 7. 비저하 시나리오 상세

| unit | scenario_id | type | sensor | tau_s | window_hi | t_hat | result |
|---|---|---|---|---|---|---|---|
| 1 | bias_T24_a0.3_neg_p0.6 | bias | T24 | 137 | 177 | 121 | FP_clean |
| 1 | bias_T24_a0.3_neg_p0.8 | bias | T24 | 165 | 192 | 116 | FP_clean |
| 1 | bias_T24_a0.5_neg_p0.8 | bias | T24 | 165 | 192 | 121 | FP_clean |
| 1 | gain_T24_a0.25_neg_p0.2 | gain | T24 | 82 | 122 | 123 | TN |
| 1 | gain_T24_a0.75_neg_p0.8 | gain | T24 | 165 | 192 | 121 | FP_clean |
| 1 | gain_T30_a1.0_pos_p0.6 | gain | T30 | 137 | 177 | 121 | FP_clean |
| 1 | multiI_T24+T30+T50_a0.3_na_p0.8 | multi_I | T24+T30+T50 | 165 | 192 | 121 | FP_clean |
| 1 | multiI_T24+T30+T50_a0.5_na_p0.2 | multi_I | T24+T30+T50 | 82 | 122 | 96 | FP_contam |
| 1 | multiI_T24+T30+T50_a0.5_na_p0.4 | multi_I | T24+T30+T50 | 110 | 150 | 121 | FP_contam |
| 1 | multiI_T24+T30+T50_a0.5_na_p0.8 | multi_I | T24+T30+T50 | 165 | 192 | 116 | FP_clean |
| 1 | noise_T30_b3.0_na_p0.4 | noise | T30 | 110 | 150 | 110 | FP_contam |
| 1 | noise_T30_b3.0_na_p0.8 | noise | T30 | 165 | 192 | 116 | FP_clean |
| 1 | noise_T50_b1.0_na_p0.6 | noise | T50 | 137 | 177 | 116 | FP_clean |
| 1 | stuck_T24_na_na_p0.4 | stuck | T24 | 110 | 150 | 115 | FP_contam |
| 1 | stuck_T24_na_na_p0.8 | stuck | T24 | 165 | 192 | 116 | FP_clean |
| 9 | bias_T30_a0.75_neg_p0.6 | bias | T30 | 143 | 183 | 151 | FP_contam |
| 9 | bias_T30_a0.75_pos_p0.6 | bias | T30 | 143 | 183 | 200 | TN |
| 9 | bias_T30_a1.0_neg_p0.6 | bias | T30 | 143 | 183 | 151 | FP_contam |
| 9 | gain_T30_a0.75_neg_p0.4 | gain | T30 | 113 | 153 | 151 | FP_contam |
| 9 | gain_T30_a2.0_pos_p0.2 | gain | T30 | 84 | 124 | 96 | FP_contam |
| 9 | gain_T50_a1.5_pos_p0.6 | gain | T50 | 143 | 183 | 151 | FP_contam |
| 9 | multiC_T24+T30+T50_a0.3_na_p0.8 | multi_C | T24+T30+T50 | 172 | 201 | 151 | FP_clean |
| 9 | multiC_T24+T30+T50_a0.5_na_p0.8 | multi_C | T24+T30+T50 | 172 | 201 | 174 | FP_contam |
| 9 | multiI_T24+T30+T50_a0.3_na_p0.4 | multi_I | T24+T30+T50 | 113 | 153 | 151 | FP_contam |
| 9 | multiI_T24+T30+T50_a0.3_na_p0.6 | multi_I | T24+T30+T50 | 143 | 183 | 151 | FP_contam |
| 9 | multiI_T24+T30+T50_a0.5_na_p0.6 | multi_I | T24+T30+T50 | 143 | 183 | 151 | FP_contam |
| 9 | multiI_T24+T30+T50_a0.5_na_p0.8 | multi_I | T24+T30+T50 | 172 | 201 | 151 | FP_clean |
| 9 | noise_T24_b1.0_na_p0.8 | noise | T24 | 172 | 201 | 151 | FP_clean |
| 9 | noise_T30_b1.0_na_p0.6 | noise | T30 | 143 | 183 | 151 | FP_contam |
| 9 | noise_T50_b3.0_na_p0.8 | noise | T50 | 172 | 201 | 151 | FP_clean |
| 9 | stuck_T30_na_na_p0.2 | stuck | T30 | 84 | 124 | 96 | FP_contam |
| 9 | stuck_T30_na_na_p0.8 | stuck | T30 | 172 | 201 | 151 | FP_clean |
| 9 | stuck_T50_na_na_p0.6 | stuck | T50 | 143 | 183 | 153 | FP_contam |
| 10 | bias_T24_a0.3_pos_p0.2 | bias | T24 | 88 | 128 |  | TN |
| 10 | bias_T24_a0.5_pos_p0.8 | bias | T24 | 189 | 222 | 150 | FP_clean |
| 10 | bias_T30_a1.0_neg_p0.2 | bias | T30 | 88 | 128 |  | TN |
| 10 | gain_T24_a1.0_pos_p0.2 | gain | T24 | 88 | 128 | 89 | FP_contam |
| 10 | gain_T30_a0.75_neg_p0.6 | gain | T30 | 155 | 195 | 150 | FP_clean |
| 10 | gain_T50_a0.25_neg_p0.4 | gain | T50 | 122 | 162 |  | TN |
| 10 | multiC_T24+T30+T50_a0.3_na_p0.8 | multi_C | T24+T30+T50 | 189 | 222 | 150 | FP_clean |
| 10 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 155 | 195 | 150 | FP_clean |
| 10 | multiC_T24+T30+T50_a0.5_na_p0.8 | multi_C | T24+T30+T50 | 189 | 222 | 150 | FP_clean |
| 10 | multiI_T24+T30+T50_a0.3_na_p0.8 | multi_I | T24+T30+T50 | 189 | 222 | 150 | FP_clean |
| 10 | multiI_T24+T30+T50_a0.5_na_p0.6 | multi_I | T24+T30+T50 | 155 | 195 | 150 | FP_clean |
| 10 | multiI_T24+T30+T50_a0.5_na_p0.8 | multi_I | T24+T30+T50 | 189 | 222 | 150 | FP_clean |
| 10 | noise_T24_b1.0_na_p0.4 | noise | T24 | 122 | 162 | 130 | FP_contam |
| 10 | noise_T50_b1.0_na_p0.2 | noise | T50 | 88 | 128 | 88 | FP_contam |
| 10 | stuck_T24_na_na_p0.8 | stuck | T24 | 189 | 222 | 150 | FP_clean |
| 10 | stuck_T30_na_na_p0.2 | stuck | T30 | 88 | 128 | 118 | FP_contam |
| 10 | stuck_T30_na_na_p0.4 | stuck | T30 | 122 | 162 | 132 | FP_contam |
| 11 | bias_T30_a0.5_pos_p0.4 | bias | T30 | 129 | 169 | 138 | FP_contam |
| 11 | bias_T30_a0.75_pos_p0.2 | bias | T30 | 92 | 132 | 141 | TN |
| 11 | gain_T30_a2.0_pos_p0.6 | gain | T30 | 166 | 206 | 145 | FP_clean |
| 11 | gain_T50_a0.5_neg_p0.8 | gain | T50 | 203 | 240 | 145 | FP_clean |
| 11 | gain_T50_a1.5_pos_p0.8 | gain | T50 | 203 | 240 | 145 | FP_clean |
| 11 | multiI_T24+T30+T50_a0.3_na_p0.4 | multi_I | T24+T30+T50 | 129 | 169 | 141 | FP_contam |
| 11 | multiI_T24+T30+T50_a0.5_na_p0.4 | multi_I | T24+T30+T50 | 129 | 169 | 151 | FP_contam |
| 11 | multiI_T24+T30+T50_a0.5_na_p0.8 | multi_I | T24+T30+T50 | 203 | 240 | 146 | FP_clean |
| 11 | noise_T30_b1.0_na_p0.8 | noise | T30 | 203 | 240 | 146 | FP_clean |
| 11 | noise_T30_b2.0_na_p0.2 | noise | T30 | 92 | 132 | 138 | TN |
| 11 | noise_T30_b2.0_na_p0.8 | noise | T30 | 203 | 240 | 146 | FP_clean |
| 11 | stuck_T24_na_na_p0.6 | stuck | T24 | 166 | 206 | 146 | FP_clean |
| 11 | stuck_T30_na_na_p0.4 | stuck | T30 | 129 | 169 | 137 | FP_contam |
| 17 | bias_T24_a0.75_neg_p0.8 | bias | T24 | 232 | 272 | 167 | FP_clean |
| 17 | bias_T30_a0.3_pos_p0.4 | bias | T30 | 143 | 183 | 182 | FP_contam |
| 17 | bias_T30_a0.75_pos_p0.6 | bias | T30 | 188 | 228 | 167 | FP_clean |
| 17 | gain_T24_a1.0_pos_p0.2 | gain | T24 | 99 | 139 | 148 | TN |
| 17 | gain_T24_a1.5_pos_p0.8 | gain | T24 | 232 | 272 | 169 | FP_clean |
| 17 | gain_T30_a1.0_pos_p0.8 | gain | T30 | 232 | 272 | 166 | FP_clean |
| 17 | gain_T50_a0.5_neg_p0.6 | gain | T50 | 188 | 228 | 167 | FP_clean |
| 17 | multiC_T24+T30+T50_a0.3_na_p0.8 | multi_C | T24+T30+T50 | 232 | 272 | 167 | FP_clean |
| 17 | multiC_T24+T30+T50_a0.5_na_p0.8 | multi_C | T24+T30+T50 | 232 | 272 | 167 | FP_clean |
| 17 | multiI_T24+T30+T50_a0.3_na_p0.2 | multi_I | T24+T30+T50 | 99 | 139 | 165 | TN |
| 17 | multiI_T24+T30+T50_a0.5_na_p0.6 | multi_I | T24+T30+T50 | 188 | 228 | 167 | FP_clean |
| 17 | multiI_T24+T30+T50_a0.5_na_p0.8 | multi_I | T24+T30+T50 | 232 | 272 | 167 | FP_clean |
| 17 | stuck_T30_na_na_p0.4 | stuck | T30 | 143 | 183 | 152 | FP_contam |
| 17 | stuck_T50_na_na_p0.8 | stuck | T50 | 232 | 272 | 167 | FP_clean |
| 26 | bias_T30_a0.5_neg_p0.8 | bias | T30 | 170 | 199 |  | TN |
| 26 | bias_T30_a0.5_pos_p0.6 | bias | T30 | 141 | 181 |  | TN |
| 26 | gain_T24_a0.25_neg_p0.4 | gain | T24 | 113 | 153 |  | TN |
| 26 | gain_T30_a0.75_neg_p0.8 | gain | T30 | 170 | 199 |  | TN |
| 26 | gain_T50_a0.75_neg_p0.6 | gain | T50 | 141 | 181 |  | TN |
| 26 | gain_T50_a0.75_neg_p0.8 | gain | T50 | 170 | 199 |  | TN |
| 26 | multiC_T24+T30+T50_a0.3_na_p0.6 | multi_C | T24+T30+T50 | 141 | 181 |  | TN |
| 26 | multiC_T24+T30+T50_a0.3_na_p0.8 | multi_C | T24+T30+T50 | 170 | 199 |  | TN |
| 26 | multiC_T24+T30+T50_a0.5_na_p0.8 | multi_C | T24+T30+T50 | 170 | 199 |  | TN |
| 26 | multiI_T24+T30+T50_a0.3_na_p0.6 | multi_I | T24+T30+T50 | 141 | 181 |  | TN |
| 26 | multiI_T24+T30+T50_a0.3_na_p0.8 | multi_I | T24+T30+T50 | 170 | 199 |  | TN |
| 26 | multiI_T24+T30+T50_a0.5_na_p0.4 | multi_I | T24+T30+T50 | 113 | 153 |  | TN |
| 26 | noise_T24_b1.0_na_p0.6 | noise | T24 | 141 | 181 |  | TN |
| 26 | noise_T30_b2.0_na_p0.4 | noise | T30 | 113 | 153 | 129 | FP_contam |
| 26 | stuck_T24_na_na_p0.6 | stuck | T24 | 141 | 181 | 150 | FP_contam |
| 26 | stuck_T30_na_na_p0.4 | stuck | T30 | 113 | 153 | 125 | FP_contam |
| 26 | stuck_T50_na_na_p0.8 | stuck | T50 | 170 | 199 | 197 | FP_contam |
| 32 | bias_T30_a0.3_neg_p0.2 | bias | T30 | 82 | 122 |  | TN |
| 32 | bias_T30_a1.0_neg_p0.2 | bias | T30 | 82 | 122 |  | TN |
| 32 | gain_T30_a0.25_neg_p0.6 | gain | T30 | 137 | 177 |  | TN |
| 32 | gain_T30_a0.75_neg_p0.4 | gain | T30 | 109 | 149 |  | TN |
| 32 | gain_T30_a1.0_pos_p0.4 | gain | T30 | 109 | 149 |  | TN |
| 32 | gain_T50_a0.75_neg_p0.6 | gain | T50 | 137 | 177 |  | TN |
| 32 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 137 | 177 |  | TN |
| 32 | multiI_T24+T30+T50_a0.3_na_p0.4 | multi_I | T24+T30+T50 | 109 | 149 |  | TN |
| 32 | multiI_T24+T30+T50_a0.3_na_p0.6 | multi_I | T24+T30+T50 | 137 | 177 |  | TN |
| 32 | multiI_T24+T30+T50_a0.5_na_p0.2 | multi_I | T24+T30+T50 | 82 | 122 |  | TN |
| 32 | multiI_T24+T30+T50_a0.5_na_p0.8 | multi_I | T24+T30+T50 | 164 | 191 |  | TN |
| 32 | noise_T30_b2.0_na_p0.8 | noise | T30 | 164 | 191 | 189 | FP_contam |
| 32 | noise_T50_b2.0_na_p0.8 | noise | T50 | 164 | 191 | 171 | FP_contam |
| 32 | stuck_T30_na_na_p0.2 | stuck | T30 | 82 | 122 | 93 | FP_contam |
| 32 | stuck_T30_na_na_p0.6 | stuck | T30 | 137 | 177 | 151 | FP_contam |
| 32 | stuck_T30_na_na_p0.8 | stuck | T30 | 164 | 191 | 189 | FP_contam |
| 32 | stuck_T50_na_na_p0.4 | stuck | T50 | 109 | 149 | 117 | FP_contam |
| 48 | bias_T24_a0.3_neg_p0.4 | bias | T24 | 125 | 165 | 159 | FP_contam |
| 48 | bias_T24_a0.3_neg_p0.6 | bias | T24 | 161 | 201 | 182 | FP_contam |
| 48 | bias_T50_a1.0_pos_p0.6 | bias | T50 | 161 | 201 |  | TN |
| 48 | gain_T30_a0.5_neg_p0.6 | gain | T30 | 161 | 201 | 114 | FP_clean |
| 48 | gain_T50_a0.75_neg_p0.6 | gain | T50 | 161 | 201 |  | TN |
| 48 | gain_T50_a2.0_pos_p0.8 | gain | T50 | 196 | 231 | 114 | FP_clean |
| 48 | multiC_T24+T30+T50_a0.3_na_p0.8 | multi_C | T24+T30+T50 | 196 | 231 | 183 | FP_clean |
| 48 | noise_T24_b1.0_na_p0.8 | noise | T24 | 196 | 231 | 183 | FP_clean |
| 48 | noise_T24_b2.0_na_p0.8 | noise | T24 | 196 | 231 | 183 | FP_clean |
| 48 | noise_T30_b1.0_na_p0.6 | noise | T30 | 161 | 201 | 182 | FP_contam |
| 48 | noise_T30_b2.0_na_p0.6 | noise | T30 | 161 | 201 | 162 | FP_contam |
| 48 | stuck_T24_na_na_p0.2 | stuck | T24 | 90 | 130 | 99 | FP_contam |
| 48 | stuck_T30_na_na_p0.6 | stuck | T30 | 161 | 201 | 172 | FP_contam |
| 49 | bias_T30_a0.5_pos_p0.4 | bias | T30 | 119 | 159 | 124 | FP_contam |
| 49 | bias_T50_a0.75_neg_p0.6 | bias | T50 | 151 | 191 | 124 | FP_clean |
| 49 | bias_T50_a0.75_pos_p0.8 | bias | T50 | 183 | 215 | 124 | FP_clean |
| 49 | gain_T24_a0.25_neg_p0.4 | gain | T24 | 119 | 159 | 124 | FP_contam |
| 49 | gain_T24_a0.5_pos_p0.6 | gain | T24 | 151 | 191 | 124 | FP_clean |
| 49 | gain_T30_a2.0_pos_p0.2 | gain | T30 | 87 | 127 | 109 | FP_contam |
| 49 | multiC_T24+T30+T50_a0.3_na_p0.6 | multi_C | T24+T30+T50 | 151 | 191 | 124 | FP_clean |
| 49 | multiC_T24+T30+T50_a0.3_na_p0.8 | multi_C | T24+T30+T50 | 183 | 215 | 124 | FP_clean |
| 49 | multiI_T24+T30+T50_a0.3_na_p0.6 | multi_I | T24+T30+T50 | 151 | 191 | 124 | FP_clean |
| 49 | multiI_T24+T30+T50_a0.3_na_p0.8 | multi_I | T24+T30+T50 | 183 | 215 | 124 | FP_clean |
| 49 | multiI_T24+T30+T50_a0.5_na_p0.2 | multi_I | T24+T30+T50 | 87 | 127 |  | TN |
| 49 | multiI_T24+T30+T50_a0.5_na_p0.6 | multi_I | T24+T30+T50 | 151 | 191 | 124 | FP_clean |
| 49 | noise_T24_b2.0_na_p0.8 | noise | T24 | 183 | 215 | 124 | FP_clean |
| 49 | noise_T50_b1.0_na_p0.8 | noise | T50 | 183 | 215 | 124 | FP_clean |
| 49 | stuck_T30_na_na_p0.2 | stuck | T30 | 87 | 127 | 98 | FP_contam |
| 49 | stuck_T50_na_na_p0.2 | stuck | T50 | 87 | 127 | 99 | FP_contam |
| 52 | bias_T30_a0.75_pos_p0.8 | bias | T30 | 181 | 213 | 96 | FP_clean |
| 52 | bias_T30_a1.0_neg_p0.4 | bias | T30 | 118 | 158 | 100 | FP_clean |
| 52 | bias_T50_a0.3_pos_p0.8 | bias | T50 | 181 | 213 | 100 | FP_clean |
| 52 | gain_T30_a0.25_neg_p0.6 | gain | T30 | 150 | 190 | 100 | FP_clean |
| 52 | gain_T30_a0.5_neg_p0.6 | gain | T30 | 150 | 190 | 100 | FP_clean |
| 52 | multiC_T24+T30+T50_a0.5_na_p0.8 | multi_C | T24+T30+T50 | 181 | 213 | 100 | FP_clean |
| 52 | multiI_T24+T30+T50_a0.3_na_p0.4 | multi_I | T24+T30+T50 | 118 | 158 | 100 | FP_clean |
| 52 | multiI_T24+T30+T50_a0.3_na_p0.6 | multi_I | T24+T30+T50 | 150 | 190 | 100 | FP_clean |
| 52 | multiI_T24+T30+T50_a0.3_na_p0.8 | multi_I | T24+T30+T50 | 181 | 213 | 100 | FP_clean |
| 52 | multiI_T24+T30+T50_a0.5_na_p0.2 | multi_I | T24+T30+T50 | 87 | 127 | 102 | FP_contam |
| 52 | multiI_T24+T30+T50_a0.5_na_p0.6 | multi_I | T24+T30+T50 | 150 | 190 | 100 | FP_clean |
| 52 | noise_T24_b1.0_na_p0.4 | noise | T24 | 118 | 158 | 100 | FP_clean |
| 52 | noise_T24_b2.0_na_p0.8 | noise | T24 | 181 | 213 | 100 | FP_clean |
| 52 | noise_T50_b1.0_na_p0.8 | noise | T50 | 181 | 213 | 100 | FP_clean |
| 52 | stuck_T24_na_na_p0.6 | stuck | T24 | 150 | 190 | 100 | FP_clean |
| 52 | stuck_T24_na_na_p0.8 | stuck | T24 | 181 | 213 | 100 | FP_clean |
| 52 | stuck_T30_na_na_p0.2 | stuck | T30 | 87 | 127 | 94 | FP_contam |
| 52 | stuck_T50_na_na_p0.8 | stuck | T50 | 181 | 213 | 100 | FP_clean |
| 57 | bias_T30_a0.3_neg_p0.4 | bias | T30 | 88 | 128 |  | TN |
| 57 | bias_T30_a0.5_neg_p0.2 | bias | T30 | 71 | 111 |  | TN |
| 57 | bias_T30_a0.75_neg_p0.6 | bias | T30 | 104 | 137 | 89 | FP_clean |
| 57 | gain_T24_a0.25_neg_p0.4 | gain | T24 | 88 | 128 |  | TN |
| 57 | gain_T30_a0.5_neg_p0.2 | gain | T30 | 71 | 111 |  | TN |
| 57 | gain_T50_a0.5_neg_p0.8 | gain | T50 | 121 | 137 | 89 | FP_clean |
| 57 | gain_T50_a1.0_pos_p0.8 | gain | T50 | 121 | 137 | 89 | FP_clean |
| 57 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 104 | 137 | 89 | FP_clean |
| 57 | multiC_T24+T30+T50_a0.5_na_p0.8 | multi_C | T24+T30+T50 | 121 | 137 | 89 | FP_clean |
| 57 | multiI_T24+T30+T50_a0.3_na_p0.4 | multi_I | T24+T30+T50 | 88 | 128 |  | TN |
| 57 | multiI_T24+T30+T50_a0.3_na_p0.8 | multi_I | T24+T30+T50 | 121 | 137 | 89 | FP_clean |
| 57 | multiI_T24+T30+T50_a0.5_na_p0.6 | multi_I | T24+T30+T50 | 104 | 137 | 89 | FP_clean |
| 57 | multiI_T24+T30+T50_a0.5_na_p0.8 | multi_I | T24+T30+T50 | 121 | 137 | 89 | FP_clean |
| 57 | noise_T30_b3.0_na_p0.4 | noise | T30 | 88 | 128 | 89 | FP_contam |
| 57 | stuck_T24_na_na_p0.6 | stuck | T24 | 104 | 137 | 89 | FP_clean |
| 57 | stuck_T30_na_na_p0.2 | stuck | T30 | 71 | 111 | 86 | FP_contam |
| 57 | stuck_T30_na_na_p0.4 | stuck | T30 | 88 | 128 | 95 | FP_contam |
| 57 | stuck_T50_na_na_p0.8 | stuck | T50 | 121 | 137 | 89 | FP_clean |
| 63 | bias_T24_a0.3_pos_p0.2 | bias | T24 | 79 | 119 |  | TN |
| 63 | bias_T50_a0.5_pos_p0.8 | bias | T50 | 150 | 174 |  | TN |
| 63 | gain_T24_a1.0_pos_p0.6 | gain | T24 | 126 | 166 |  | TN |
| 63 | gain_T30_a0.25_neg_p0.8 | gain | T30 | 150 | 174 |  | TN |
| 63 | gain_T50_a0.25_neg_p0.2 | gain | T50 | 79 | 119 |  | TN |
| 63 | gain_T50_a2.0_pos_p0.8 | gain | T50 | 150 | 174 | 157 | FP_contam |
| 63 | multiC_T24+T30+T50_a0.3_na_p0.4 | multi_C | T24+T30+T50 | 103 | 143 |  | TN |
| 63 | multiC_T24+T30+T50_a0.3_na_p0.8 | multi_C | T24+T30+T50 | 150 | 174 |  | TN |
| 63 | multiI_T24+T30+T50_a0.3_na_p0.8 | multi_I | T24+T30+T50 | 150 | 174 |  | TN |
| 63 | noise_T24_b1.0_na_p0.6 | noise | T24 | 126 | 166 |  | TN |
| 63 | noise_T24_b3.0_na_p0.8 | noise | T24 | 150 | 174 | 151 | FP_contam |
| 63 | noise_T30_b2.0_na_p0.2 | noise | T30 | 79 | 119 | 89 | FP_contam |
| 63 | noise_T30_b2.0_na_p0.6 | noise | T30 | 126 | 166 |  | TN |
| 63 | stuck_T24_na_na_p0.4 | stuck | T24 | 103 | 143 | 112 | FP_contam |
| 63 | stuck_T30_na_na_p0.6 | stuck | T30 | 126 | 166 | 136 | FP_contam |
| 63 | stuck_T50_na_na_p0.8 | stuck | T50 | 150 | 174 | 160 | FP_contam |
| 64 | bias_T24_a0.3_neg_p0.8 | bias | T24 | 237 | 277 | 112 | FP_clean |
| 64 | bias_T30_a0.3_neg_p0.4 | bias | T30 | 146 | 186 | 119 | FP_clean |
| 64 | bias_T30_a0.3_pos_p0.6 | bias | T30 | 192 | 232 | 112 | FP_clean |
| 64 | bias_T30_a1.0_pos_p0.6 | bias | T30 | 192 | 232 | 112 | FP_clean |
| 64 | gain_T30_a0.5_neg_p0.8 | gain | T30 | 237 | 277 | 112 | FP_clean |
| 64 | gain_T50_a0.75_neg_p0.4 | gain | T50 | 146 | 186 | 112 | FP_clean |
| 64 | gain_T50_a1.5_pos_p0.8 | gain | T50 | 237 | 277 | 112 | FP_clean |
| 64 | multiC_T24+T30+T50_a0.3_na_p0.8 | multi_C | T24+T30+T50 | 237 | 277 | 112 | FP_clean |
| 64 | multiI_T24+T30+T50_a0.3_na_p0.2 | multi_I | T24+T30+T50 | 101 | 141 | 112 | FP_contam |
| 64 | multiI_T24+T30+T50_a0.3_na_p0.6 | multi_I | T24+T30+T50 | 192 | 232 | 112 | FP_clean |
| 64 | noise_T30_b3.0_na_p0.2 | noise | T30 | 101 | 141 | 105 | FP_contam |
| 64 | stuck_T30_na_na_p0.2 | stuck | T30 | 101 | 141 | 111 | FP_contam |
| 64 | stuck_T50_na_na_p0.6 | stuck | T50 | 192 | 232 | 112 | FP_clean |
| 65 | bias_T24_a0.3_pos_p0.8 | bias | T24 | 133 | 153 | 92 | FP_clean |
| 65 | bias_T24_a0.75_pos_p0.8 | bias | T24 | 133 | 153 | 92 | FP_clean |
| 65 | bias_T30_a1.0_pos_p0.2 | bias | T30 | 75 | 115 | 107 | FP_contam |
| 65 | bias_T50_a0.5_pos_p0.8 | bias | T50 | 133 | 153 | 92 | FP_clean |
| 65 | gain_T24_a1.5_pos_p0.6 | gain | T24 | 114 | 153 | 92 | FP_clean |
| 65 | gain_T24_a2.0_pos_p0.6 | gain | T24 | 114 | 153 | 92 | FP_clean |
| 65 | gain_T30_a0.75_neg_p0.6 | gain | T30 | 114 | 153 | 92 | FP_clean |
| 65 | gain_T50_a0.25_neg_p0.4 | gain | T50 | 94 | 134 | 92 | FP_clean |
| 65 | multiC_T24+T30+T50_a0.3_na_p0.6 | multi_C | T24+T30+T50 | 114 | 153 | 92 | FP_clean |
| 65 | multiC_T24+T30+T50_a0.3_na_p0.8 | multi_C | T24+T30+T50 | 133 | 153 | 92 | FP_clean |
| 65 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 114 | 153 | 92 | FP_clean |
| 65 | multiC_T24+T30+T50_a0.5_na_p0.8 | multi_C | T24+T30+T50 | 133 | 153 | 92 | FP_clean |
| 65 | multiI_T24+T30+T50_a0.3_na_p0.8 | multi_I | T24+T30+T50 | 133 | 153 | 92 | FP_clean |
| 65 | multiI_T24+T30+T50_a0.5_na_p0.2 | multi_I | T24+T30+T50 | 75 | 115 | 97 | FP_contam |
| 65 | multiI_T24+T30+T50_a0.5_na_p0.6 | multi_I | T24+T30+T50 | 114 | 153 | 92 | FP_clean |
| 65 | multiI_T24+T30+T50_a0.5_na_p0.8 | multi_I | T24+T30+T50 | 133 | 153 | 92 | FP_clean |
| 65 | noise_T30_b2.0_na_p0.6 | noise | T30 | 114 | 153 | 92 | FP_clean |
| 65 | noise_T30_b3.0_na_p0.8 | noise | T30 | 133 | 153 | 92 | FP_clean |
| 65 | stuck_T24_na_na_p0.2 | stuck | T24 | 75 | 115 | 83 | FP_contam |
| 65 | stuck_T24_na_na_p0.8 | stuck | T24 | 133 | 153 | 92 | FP_clean |
| 65 | stuck_T30_na_na_p0.8 | stuck | T30 | 133 | 153 | 92 | FP_clean |
| 65 | stuck_T50_na_na_p0.6 | stuck | T50 | 114 | 153 | 92 | FP_clean |
| 65 | stuck_T50_na_na_p0.8 | stuck | T50 | 133 | 153 | 92 | FP_clean |
| 67 | bias_T24_a0.3_neg_p0.2 | bias | T24 | 107 | 147 | 141 | FP_contam |
| 67 | bias_T30_a0.3_neg_p0.8 | bias | T30 | 261 | 301 | 141 | FP_clean |
| 67 | bias_T50_a0.75_pos_p0.8 | bias | T50 | 261 | 301 | 141 | FP_clean |
| 67 | gain_T24_a0.5_neg_p0.2 | gain | T24 | 107 | 147 | 140 | FP_contam |
| 67 | gain_T30_a0.5_neg_p0.4 | gain | T30 | 158 | 198 | 141 | FP_clean |
| 67 | gain_T50_a0.25_neg_p0.8 | gain | T50 | 261 | 301 | 141 | FP_clean |
| 67 | multiC_T24+T30+T50_a0.3_na_p0.8 | multi_C | T24+T30+T50 | 261 | 301 | 141 | FP_clean |
| 67 | multiI_T24+T30+T50_a0.3_na_p0.4 | multi_I | T24+T30+T50 | 158 | 198 | 141 | FP_clean |
| 67 | multiI_T24+T30+T50_a0.3_na_p0.6 | multi_I | T24+T30+T50 | 210 | 250 | 141 | FP_clean |
| 67 | multiI_T24+T30+T50_a0.5_na_p0.2 | multi_I | T24+T30+T50 | 107 | 147 | 141 | FP_contam |
| 67 | multiI_T24+T30+T50_a0.5_na_p0.6 | multi_I | T24+T30+T50 | 210 | 250 | 141 | FP_clean |
| 67 | noise_T24_b1.0_na_p0.4 | noise | T24 | 158 | 198 | 141 | FP_clean |
| 67 | noise_T30_b1.0_na_p0.2 | noise | T30 | 107 | 147 | 137 | FP_contam |
| 67 | noise_T50_b3.0_na_p0.8 | noise | T50 | 261 | 301 | 141 | FP_clean |
| 67 | stuck_T30_na_na_p0.6 | stuck | T30 | 210 | 250 | 141 | FP_clean |
| 68 | bias_T24_a0.3_neg_p0.4 | bias | T24 | 113 | 153 |  | TN |
| 68 | bias_T24_a0.3_pos_p0.6 | bias | T24 | 141 | 181 |  | TN |
| 68 | bias_T30_a1.0_pos_p0.6 | bias | T30 | 141 | 181 |  | TN |
| 68 | bias_T50_a0.75_pos_p0.6 | bias | T50 | 141 | 181 |  | TN |
| 68 | gain_T30_a0.75_neg_p0.2 | gain | T30 | 84 | 124 | 144 | TN |
| 68 | gain_T30_a1.0_pos_p0.8 | gain | T30 | 170 | 199 |  | TN |
| 68 | gain_T50_a1.0_pos_p0.4 | gain | T50 | 113 | 153 |  | TN |
| 68 | multiC_T24+T30+T50_a0.3_na_p0.6 | multi_C | T24+T30+T50 | 141 | 181 |  | TN |
| 68 | multiC_T24+T30+T50_a0.3_na_p0.8 | multi_C | T24+T30+T50 | 170 | 199 |  | TN |
| 68 | multiI_T24+T30+T50_a0.3_na_p0.4 | multi_I | T24+T30+T50 | 113 | 153 | 144 | FP_contam |
| 68 | multiI_T24+T30+T50_a0.3_na_p0.6 | multi_I | T24+T30+T50 | 141 | 181 |  | TN |
| 68 | multiI_T24+T30+T50_a0.3_na_p0.8 | multi_I | T24+T30+T50 | 170 | 199 |  | TN |
| 68 | multiI_T24+T30+T50_a0.5_na_p0.2 | multi_I | T24+T30+T50 | 84 | 124 | 144 | TN |
| 68 | noise_T30_b1.0_na_p0.8 | noise | T30 | 170 | 199 |  | TN |
| 68 | noise_T30_b2.0_na_p0.6 | noise | T30 | 141 | 181 |  | TN |
| 68 | noise_T30_b3.0_na_p0.2 | noise | T30 | 84 | 124 | 86 | FP_contam |
| 68 | stuck_T30_na_na_p0.4 | stuck | T30 | 113 | 153 | 121 | FP_contam |
| 68 | stuck_T50_na_na_p0.6 | stuck | T50 | 141 | 181 | 144 | FP_contam |
| 68 | stuck_T50_na_na_p0.8 | stuck | T50 | 170 | 199 | 185 | FP_contam |
| 70 | bias_T24_a0.5_neg_p0.4 | bias | T24 | 88 | 128 |  | TN |
| 70 | bias_T24_a0.75_neg_p0.8 | bias | T24 | 121 | 137 |  | TN |
| 70 | bias_T24_a1.0_neg_p0.6 | bias | T24 | 104 | 137 |  | TN |
| 70 | bias_T50_a0.3_pos_p0.8 | bias | T50 | 121 | 137 |  | TN |
| 70 | gain_T24_a2.0_pos_p0.8 | gain | T24 | 121 | 137 |  | TN |
| 70 | gain_T30_a0.75_neg_p0.2 | gain | T30 | 71 | 111 |  | TN |
| 70 | gain_T30_a1.0_pos_p0.4 | gain | T30 | 88 | 128 |  | TN |
| 70 | gain_T50_a0.5_neg_p0.2 | gain | T50 | 71 | 111 |  | TN |
| 70 | multiC_T24+T30+T50_a0.3_na_p0.2 | multi_C | T24+T30+T50 | 71 | 111 |  | TN |
| 70 | multiC_T24+T30+T50_a0.3_na_p0.4 | multi_C | T24+T30+T50 | 88 | 128 |  | TN |
| 70 | multiC_T24+T30+T50_a0.5_na_p0.4 | multi_C | T24+T30+T50 | 88 | 128 |  | TN |
| 70 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 104 | 137 |  | TN |
| 70 | multiI_T24+T30+T50_a0.3_na_p0.4 | multi_I | T24+T30+T50 | 88 | 128 |  | TN |
| 70 | multiI_T24+T30+T50_a0.3_na_p0.6 | multi_I | T24+T30+T50 | 104 | 137 |  | TN |
| 70 | multiI_T24+T30+T50_a0.5_na_p0.2 | multi_I | T24+T30+T50 | 71 | 111 |  | TN |
| 70 | multiI_T24+T30+T50_a0.5_na_p0.8 | multi_I | T24+T30+T50 | 121 | 137 |  | TN |
| 70 | noise_T24_b2.0_na_p0.4 | noise | T24 | 88 | 128 |  | TN |
| 70 | noise_T50_b1.0_na_p0.8 | noise | T50 | 121 | 137 |  | TN |
| 70 | stuck_T24_na_na_p0.8 | stuck | T24 | 121 | 137 |  | TN |
| 70 | stuck_T30_na_na_p0.2 | stuck | T30 | 71 | 111 | 81 | FP_contam |
| 70 | stuck_T30_na_na_p0.6 | stuck | T30 | 104 | 137 |  | TN |
| 70 | stuck_T50_na_na_p0.8 | stuck | T50 | 121 | 137 | 133 | FP_contam |
| 79 | bias_T30_a0.5_pos_p0.2 | bias | T30 | 84 | 124 | 110 | FP_contam |
| 79 | bias_T30_a0.5_pos_p0.6 | bias | T30 | 141 | 181 |  | TN |
| 79 | bias_T50_a0.5_neg_p0.6 | bias | T50 | 141 | 181 | 100 | FP_clean |
| 79 | bias_T50_a1.0_pos_p0.6 | bias | T50 | 141 | 181 | 100 | FP_clean |
| 79 | gain_T24_a0.25_neg_p0.2 | gain | T24 | 84 | 124 | 100 | FP_contam |
| 79 | gain_T30_a0.25_neg_p0.4 | gain | T30 | 113 | 153 |  | TN |
| 79 | gain_T30_a0.5_neg_p0.4 | gain | T30 | 113 | 153 |  | TN |
| 79 | gain_T50_a1.0_pos_p0.8 | gain | T50 | 170 | 199 | 100 | FP_clean |
| 79 | multiC_T24+T30+T50_a0.3_na_p0.8 | multi_C | T24+T30+T50 | 170 | 199 | 100 | FP_clean |
| 79 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 141 | 181 |  | TN |
| 79 | multiC_T24+T30+T50_a0.5_na_p0.8 | multi_C | T24+T30+T50 | 170 | 199 | 100 | FP_clean |
| 79 | multiI_T24+T30+T50_a0.5_na_p0.2 | multi_I | T24+T30+T50 | 84 | 124 |  | TN |
| 79 | multiI_T24+T30+T50_a0.5_na_p0.4 | multi_I | T24+T30+T50 | 113 | 153 | 105 | FP_clean |
| 79 | multiI_T24+T30+T50_a0.5_na_p0.6 | multi_I | T24+T30+T50 | 141 | 181 | 100 | FP_clean |
| 79 | multiI_T24+T30+T50_a0.5_na_p0.8 | multi_I | T24+T30+T50 | 170 | 199 | 100 | FP_clean |
| 79 | noise_T24_b1.0_na_p0.2 | noise | T24 | 84 | 124 | 105 | FP_contam |
| 79 | noise_T24_b1.0_na_p0.4 | noise | T24 | 113 | 153 | 100 | FP_clean |
| 79 | noise_T30_b2.0_na_p0.8 | noise | T30 | 170 | 199 | 100 | FP_clean |
| 79 | noise_T50_b2.0_na_p0.6 | noise | T50 | 141 | 181 | 100 | FP_clean |
| 79 | stuck_T30_na_na_p0.2 | stuck | T30 | 84 | 124 | 97 | FP_contam |
| 79 | stuck_T30_na_na_p0.4 | stuck | T30 | 113 | 153 | 100 | FP_clean |
| 79 | stuck_T30_na_na_p0.8 | stuck | T30 | 170 | 199 | 100 | FP_clean |
| 85 | bias_T30_a0.75_neg_p0.2 | bias | T30 | 82 | 122 | 94 | FP_contam |
| 85 | bias_T50_a0.5_neg_p0.6 | bias | T50 | 135 | 175 |  | TN |
| 85 | bias_T50_a0.75_pos_p0.8 | bias | T50 | 161 | 188 |  | TN |
| 85 | gain_T24_a0.5_neg_p0.6 | gain | T24 | 135 | 175 |  | TN |
| 85 | gain_T30_a0.5_neg_p0.2 | gain | T30 | 82 | 122 |  | TN |
| 85 | gain_T30_a1.5_pos_p0.2 | gain | T30 | 82 | 122 | 94 | FP_contam |
| 85 | multiC_T24+T30+T50_a0.5_na_p0.8 | multi_C | T24+T30+T50 | 161 | 188 |  | TN |
| 85 | multiI_T24+T30+T50_a0.3_na_p0.6 | multi_I | T24+T30+T50 | 135 | 175 |  | TN |
| 85 | multiI_T24+T30+T50_a0.5_na_p0.8 | multi_I | T24+T30+T50 | 161 | 188 |  | TN |
| 85 | noise_T30_b1.0_na_p0.4 | noise | T30 | 108 | 148 |  | TN |
| 85 | noise_T30_b2.0_na_p0.2 | noise | T30 | 82 | 122 | 92 | FP_contam |
| 85 | noise_T30_b3.0_na_p0.8 | noise | T30 | 161 | 188 |  | TN |
| 85 | noise_T50_b1.0_na_p0.2 | noise | T50 | 82 | 122 | 97 | FP_contam |
| 85 | stuck_T24_na_na_p0.8 | stuck | T24 | 161 | 188 |  | TN |
| 85 | stuck_T30_na_na_p0.2 | stuck | T30 | 82 | 122 | 90 | FP_contam |
| 90 | bias_T24_a0.3_neg_p0.4 | bias | T24 | 95 | 135 |  | TN |
| 90 | bias_T24_a0.5_pos_p0.8 | bias | T24 | 134 | 154 |  | TN |
| 90 | bias_T30_a0.5_pos_p0.8 | bias | T30 | 134 | 154 |  | TN |
| 90 | bias_T50_a1.0_neg_p0.8 | bias | T50 | 134 | 154 |  | TN |
| 90 | gain_T24_a0.75_neg_p0.8 | gain | T24 | 134 | 154 |  | TN |
| 90 | gain_T24_a1.0_pos_p0.8 | gain | T24 | 134 | 154 |  | TN |
| 90 | gain_T24_a1.5_pos_p0.6 | gain | T24 | 114 | 154 |  | TN |
| 90 | gain_T30_a0.25_neg_p0.8 | gain | T30 | 134 | 154 |  | TN |
| 90 | multiC_T24+T30+T50_a0.3_na_p0.4 | multi_C | T24+T30+T50 | 95 | 135 |  | TN |
| 90 | multiC_T24+T30+T50_a0.3_na_p0.6 | multi_C | T24+T30+T50 | 114 | 154 |  | TN |
| 90 | multiI_T24+T30+T50_a0.3_na_p0.2 | multi_I | T24+T30+T50 | 75 | 115 |  | TN |
| 90 | multiI_T24+T30+T50_a0.3_na_p0.4 | multi_I | T24+T30+T50 | 95 | 135 |  | TN |
| 90 | multiI_T24+T30+T50_a0.3_na_p0.8 | multi_I | T24+T30+T50 | 134 | 154 |  | TN |
| 90 | multiI_T24+T30+T50_a0.5_na_p0.4 | multi_I | T24+T30+T50 | 95 | 135 |  | TN |
| 90 | noise_T24_b1.0_na_p0.4 | noise | T24 | 95 | 135 |  | TN |
| 90 | noise_T30_b1.0_na_p0.4 | noise | T30 | 95 | 135 |  | TN |
| 90 | noise_T50_b2.0_na_p0.8 | noise | T50 | 134 | 154 |  | TN |
| 90 | stuck_T24_na_na_p0.6 | stuck | T24 | 114 | 154 | 148 | FP_contam |
| 90 | stuck_T30_na_na_p0.8 | stuck | T30 | 134 | 154 | 153 | FP_contam |
| 90 | stuck_T50_na_na_p0.6 | stuck | T50 | 114 | 154 | 131 | FP_contam |
