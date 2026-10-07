# 평가 v2 (시나리오 단위) — deepseek-v4-pro-0813_or500_seed42_20261001-003315

라벨 theta_primary · 첫 판정 t₀ = 55 · Δ = 5, w = 0, H = 40, k = 1 · 첫 경보 원칙 (t₀ 이후 첫 경보, 오염 전 포함) · ERROR 는 경보 아님 (오류율 0.0000) · 규약 docs/eval_v2_scenario.md

시나리오 500 = 저하 159 + 비저하 341 · unit 20 · 판정 로그가 창 끝에 못 미친 시나리오 0

## 1. 메인 표 (기준선 고정)

| method | n_degraded | detection_rate | pre_contam_rate | pre_degr_rate | miss_rate | delay_median | n_nondegraded | scenario_FAR | FAR_clean | FAR_contam | isolation_rate |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 항상 0 | 159 | 0 | 0 | 0 | 1 |  | 341 | 0 | 0 | 0 |  |
| 항상 1 | 159 | 0 | 1 | 0 | 0 |  | 341 | 1 | 1 | 0 |  |
| 무작위 p=0.128 (에이전트 경보율) | 159 | 0.003 | 0.989 | 0.006 | 0.002 | 2.200 | 341 | 1 | 0.994 | 0.006 | 0 |
| 무작위 p=0.050 | 159 | 0.018 | 0.892 | 0.045 | 0.045 | 2.042 | 341 | 0.991 | 0.936 | 0.055 | 0 |
| LLM Agent | 159 | 0.082 | 0.503 | 0.252 | 0.164 | 0 | 341 | 0.889 | 0.660 | 0.229 | 0.846 |

## 2. unit bootstrap 95% CI (2000회)

| metric | point | lo | hi |
|---|---|---|---|
| detection_rate | 0.082 | 0.039 | 0.125 |
| pre_contam_rate | 0.503 | 0.369 | 0.624 |
| pre_degr_rate | 0.252 | 0.179 | 0.328 |
| miss_rate | 0.164 | 0.083 | 0.267 |
| scenario_FAR | 0.889 | 0.783 | 0.968 |
| isolation_rate | 0.846 | 0.600 | 1 |

## 3. 유형별

| type | n_degraded | detection_rate | pre_contam_rate | pre_degr_rate | miss_rate | delay_median | n_nondegraded | scenario_FAR | FAR_clean | FAR_contam | isolation_rate |
|---|---|---|---|---|---|---|---|---|---|---|---|
| bias | 22 | 0 | 0.409 | 0.182 | 0.409 |  | 62 | 0.823 | 0.694 | 0.129 |  |
| gain | 16 | 0.125 | 0.438 | 0.375 | 0.062 | 2.500 | 68 | 0.868 | 0.676 | 0.191 | 1 |
| multi_C | 46 | 0.065 | 0.478 | 0.174 | 0.283 | 0 | 37 | 0.811 | 0.757 | 0.054 | 0.333 |
| multi_I | 17 | 0.059 | 0.529 | 0.235 | 0.176 | 2 | 66 | 0.833 | 0.621 | 0.212 | 1 |
| noise | 32 | 0.156 | 0.562 | 0.281 | 0 | 0 | 51 | 1 | 0.667 | 0.333 | 1 |
| stuck | 26 | 0.077 | 0.577 | 0.346 | 0 | 0 | 57 | 1 | 0.579 | 0.421 | 1 |

## 4. 센서별

| sensor | n_degraded | detection_rate | pre_contam_rate | pre_degr_rate | miss_rate | delay_median | n_nondegraded | scenario_FAR | FAR_clean | FAR_contam | isolation_rate |
|---|---|---|---|---|---|---|---|---|---|---|---|
| T24 | 43 | 0.140 | 0.535 | 0.233 | 0.093 | 0 | 69 | 0.913 | 0.667 | 0.246 | 1 |
| T24+T30+T50 | 63 | 0.063 | 0.492 | 0.190 | 0.254 | 0 | 103 | 0.825 | 0.670 | 0.155 | 0.500 |
| T30 | 2 | 0 | 0.500 | 0.500 | 0 |  | 108 | 0.907 | 0.602 | 0.306 |  |
| T50 | 51 | 0.059 | 0.490 | 0.333 | 0.118 | 0 | 61 | 0.934 | 0.738 | 0.197 | 1 |

## 5. 오염 시점별

| timing_p | n_degraded | detection_rate | pre_contam_rate | pre_degr_rate | miss_rate | delay_median | n_nondegraded | scenario_FAR | FAR_clean | FAR_contam | isolation_rate |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.200 | 64 | 0.156 | 0.109 | 0.469 | 0.266 | 0 | 60 | 0.767 | 0.167 | 0.600 | 0.800 |
| 0.400 | 62 | 0.048 | 0.694 | 0.145 | 0.113 | 0 | 63 | 0.873 | 0.667 | 0.206 | 1 |
| 0.600 | 32 | 0 | 0.906 | 0.031 | 0.062 |  | 94 | 0.915 | 0.777 | 0.138 |  |
| 0.800 | 1 | 0 | 1 | 0 | 0 |  | 124 | 0.935 | 0.806 | 0.129 |  |

### 오염 전 경보율 (저하·비저하 합산, 오염 전 구간 길이 = τ_s − 55)

| timing_p | n | pre_len_median | pre_contam_rate |
|---|---|---|---|
| 0.200 | 124 | 29 | 0.137 |
| 0.400 | 125 | 58 | 0.680 |
| 0.600 | 126 | 86 | 0.810 |
| 0.800 | 125 | 115 | 0.808 |

## 6. 저하 시나리오 상세

| unit | scenario_id | type | sensor | tau_s | tau_d | window_lo | window_hi | t_hat | result | delay | iso_hit |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | bias_T50_a1.0_pos_p0.2 | bias | T50 | 82 | 90 | 90 | 95 | 79 | PreContam |  |  |
| 1 | gain_T24_a2.0_pos_p0.4 | gain | T24 | 110 | 138 | 138 | 143 | 79 | PreContam |  |  |
| 1 | multiC_T24+T30+T50_a0.3_na_p0.2 | multi_C | T24+T30+T50 | 82 | 92 | 92 | 97 | 90 | PreDegr |  |  |
| 1 | multiC_T24+T30+T50_a0.3_na_p0.4 | multi_C | T24+T30+T50 | 110 | 117 | 117 | 122 | 108 | PreContam |  |  |
| 1 | multiC_T24+T30+T50_a0.5_na_p0.2 | multi_C | T24+T30+T50 | 82 | 90 | 90 | 95 | 88 | PreDegr |  |  |
| 1 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 137 | 143 | 143 | 148 | 108 | PreContam |  |  |
| 1 | multiI_T24+T30+T50_a0.3_na_p0.2 | multi_I | T24+T30+T50 | 82 | 93 | 93 | 98 | 90 | PreDegr |  |  |
| 1 | noise_T24_b2.0_na_p0.6 | noise | T24 | 137 | 152 | 152 | 157 | 108 | PreContam |  |  |
| 1 | noise_T50_b2.0_na_p0.2 | noise | T50 | 82 | 105 | 105 | 110 | 83 | PreDegr |  |  |
| 1 | stuck_T24_na_na_p0.6 | stuck | T24 | 137 | 148 | 148 | 153 | 108 | PreContam |  |  |
| 1 | stuck_T50_na_na_p0.4 | stuck | T50 | 110 | 116 | 116 | 121 | 108 | PreContam |  |  |
| 1 | stuck_T50_na_na_p0.6 | stuck | T50 | 137 | 155 | 155 | 160 | 108 | PreContam |  |  |
| 9 | bias_T24_a0.75_neg_p0.4 | bias | T24 | 113 | 121 | 121 | 126 | 176 | Miss |  |  |
| 9 | gain_T50_a2.0_pos_p0.2 | gain | T50 | 84 | 110 | 110 | 115 | 87 | PreDegr |  |  |
| 9 | multiC_T24+T30+T50_a0.3_na_p0.2 | multi_C | T24+T30+T50 | 84 | 101 | 101 | 106 | 176 | Miss |  |  |
| 9 | multiC_T24+T30+T50_a0.5_na_p0.4 | multi_C | T24+T30+T50 | 113 | 117 | 117 | 122 | 115 | PreDegr |  |  |
| 9 | noise_T24_b2.0_na_p0.4 | noise | T24 | 113 | 159 | 159 | 164 | 118 | PreDegr |  |  |
| 9 | stuck_T24_na_na_p0.2 | stuck | T24 | 84 | 123 | 123 | 128 | 93 | PreDegr |  |  |
| 10 | bias_T50_a0.5_pos_p0.4 | bias | T50 | 122 | 146 | 146 | 151 | 88 | PreContam |  |  |
| 10 | gain_T50_a1.5_pos_p0.2 | gain | T50 | 88 | 122 | 122 | 127 | 95 | PreDegr |  |  |
| 10 | multiC_T24+T30+T50_a0.3_na_p0.4 | multi_C | T24+T30+T50 | 122 | 132 | 132 | 137 | 88 | PreContam |  |  |
| 10 | multiC_T24+T30+T50_a0.5_na_p0.2 | multi_C | T24+T30+T50 | 88 | 104 | 104 | 109 | 88 | PreDegr |  |  |
| 10 | multiI_T24+T30+T50_a0.5_na_p0.4 | multi_I | T24+T30+T50 | 122 | 127 | 127 | 132 | 88 | PreContam |  |  |
| 10 | noise_T24_b3.0_na_p0.6 | noise | T24 | 155 | 159 | 159 | 164 | 88 | PreContam |  |  |
| 10 | noise_T50_b1.0_na_p0.4 | noise | T50 | 122 | 125 | 125 | 130 | 88 | PreContam |  |  |
| 10 | stuck_T50_na_na_p0.2 | stuck | T50 | 88 | 145 | 145 | 150 | 88 | PreDegr |  |  |
| 11 | bias_T50_a0.5_pos_p0.4 | bias | T50 | 129 | 136 | 136 | 141 | 134 | PreDegr |  |  |
| 11 | bias_T50_a1.0_pos_p0.2 | bias | T50 | 92 | 117 | 117 | 122 | 105 | PreDegr |  |  |
| 11 | gain_T24_a1.5_pos_p0.6 | gain | T24 | 166 | 197 | 197 | 202 | 134 | PreContam |  |  |
| 11 | multiC_T24+T30+T50_a0.3_na_p0.2 | multi_C | T24+T30+T50 | 92 | 134 | 134 | 139 | 124 | PreDegr |  |  |
| 11 | multiC_T24+T30+T50_a0.3_na_p0.4 | multi_C | T24+T30+T50 | 129 | 135 | 135 | 140 | 134 | PreDegr |  |  |
| 11 | multiC_T24+T30+T50_a0.5_na_p0.2 | multi_C | T24+T30+T50 | 92 | 117 | 117 | 122 | 105 | PreDegr |  |  |
| 11 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 166 | 172 | 172 | 177 | 134 | PreContam |  |  |
| 11 | multiI_T24+T30+T50_a0.3_na_p0.2 | multi_I | T24+T30+T50 | 92 | 122 | 122 | 127 | 124 | TP | 2 | True |
| 11 | noise_T50_b2.0_na_p0.6 | noise | T50 | 166 | 205 | 205 | 210 | 134 | PreContam |  |  |
| 11 | noise_T50_b3.0_na_p0.6 | noise | T50 | 166 | 171 | 171 | 176 | 134 | PreContam |  |  |
| 11 | stuck_T24_na_na_p0.4 | stuck | T24 | 129 | 134 | 134 | 139 | 134 | TP | 0 | True |
| 11 | stuck_T50_na_na_p0.6 | stuck | T50 | 166 | 181 | 181 | 186 | 134 | PreContam |  |  |
| 17 | bias_T50_a0.75_pos_p0.4 | bias | T50 | 143 | 146 | 146 | 151 | 165 | Miss |  |  |
| 17 | gain_T50_a1.5_pos_p0.2 | gain | T50 | 99 | 139 | 139 | 144 | 119 | PreDegr |  |  |
| 17 | multiC_T24+T30+T50_a0.5_na_p0.2 | multi_C | T24+T30+T50 | 99 | 111 | 111 | 116 | 117 | Miss |  |  |
| 17 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 188 | 192 | 192 | 197 | 165 | PreContam |  |  |
| 17 | multiI_T24+T30+T50_a0.5_na_p0.2 | multi_I | T24+T30+T50 | 99 | 147 | 147 | 152 | 167 | Miss |  |  |
| 17 | noise_T24_b1.0_na_p0.2 | noise | T24 | 99 | 140 | 140 | 145 | 142 | TP | 2 | True |
| 17 | noise_T24_b3.0_na_p0.6 | noise | T24 | 188 | 190 | 190 | 195 | 165 | PreContam |  |  |
| 17 | noise_T50_b1.0_na_p0.2 | noise | T50 | 99 | 162 | 162 | 167 | 117 | PreDegr |  |  |
| 17 | noise_T50_b3.0_na_p0.2 | noise | T50 | 99 | 110 | 110 | 115 | 100 | PreDegr |  |  |
| 17 | stuck_T50_na_na_p0.2 | stuck | T50 | 99 | 186 | 186 | 191 | 109 | PreDegr |  |  |
| 17 | stuck_T50_na_na_p0.4 | stuck | T50 | 143 | 213 | 213 | 218 | 148 | PreDegr |  |  |
| 26 | bias_T24_a1.0_neg_p0.2 | bias | T24 | 84 | 89 | 89 | 94 | 84 | PreDegr |  |  |
| 26 | bias_T24_a1.0_neg_p0.6 | bias | T24 | 141 | 147 | 147 | 152 | 84 | PreContam |  |  |
| 26 | bias_T50_a1.0_neg_p0.4 | bias | T50 | 113 | 116 | 116 | 121 | 84 | PreContam |  |  |
| 26 | gain_T24_a2.0_pos_p0.2 | gain | T24 | 84 | 100 | 100 | 105 | 84 | PreDegr |  |  |
| 26 | multiC_T24+T30+T50_a0.3_na_p0.4 | multi_C | T24+T30+T50 | 113 | 117 | 117 | 122 | 84 | PreContam |  |  |
| 26 | multiI_T24+T30+T50_a0.3_na_p0.4 | multi_I | T24+T30+T50 | 113 | 123 | 123 | 128 | 84 | PreContam |  |  |
| 26 | noise_T24_b3.0_na_p0.6 | noise | T24 | 141 | 177 | 177 | 182 | 84 | PreContam |  |  |
| 26 | noise_T50_b1.0_na_p0.4 | noise | T50 | 113 | 131 | 131 | 136 | 84 | PreContam |  |  |
| 26 | stuck_T24_na_na_p0.2 | stuck | T24 | 84 | 136 | 136 | 141 | 84 | PreDegr |  |  |
| 32 | bias_T24_a1.0_neg_p0.2 | bias | T24 | 82 | 85 | 85 | 90 | 142 | Miss |  |  |
| 32 | bias_T50_a0.75_neg_p0.4 | bias | T50 | 109 | 123 | 123 | 128 |  | Miss |  |  |
| 32 | gain_T50_a2.0_pos_p0.4 | gain | T50 | 109 | 111 | 111 | 116 | 116 | TP | 5 | True |
| 32 | multiC_T24+T30+T50_a0.3_na_p0.2 | multi_C | T24+T30+T50 | 82 | 86 | 86 | 91 | 182 | Miss |  |  |
| 32 | multiC_T24+T30+T50_a0.3_na_p0.4 | multi_C | T24+T30+T50 | 109 | 122 | 122 | 127 | 182 | Miss |  |  |
| 32 | multiC_T24+T30+T50_a0.5_na_p0.4 | multi_C | T24+T30+T50 | 109 | 114 | 114 | 119 |  | Miss |  |  |
| 32 | noise_T24_b2.0_na_p0.2 | noise | T24 | 82 | 82 | 82 | 87 | 82 | TP | 0 | True |
| 32 | noise_T50_b2.0_na_p0.2 | noise | T50 | 82 | 87 | 87 | 92 | 85 | PreDegr |  |  |
| 48 | bias_T50_a0.5_neg_p0.2 | bias | T50 | 90 | 104 | 104 | 109 | 158 | Miss |  |  |
| 48 | gain_T50_a1.5_pos_p0.2 | gain | T50 | 90 | 99 | 99 | 104 | 99 | TP | 0 | True |
| 48 | multiC_T24+T30+T50_a0.3_na_p0.4 | multi_C | T24+T30+T50 | 125 | 134 | 134 | 139 | 99 | PreContam |  |  |
| 48 | multiC_T24+T30+T50_a0.5_na_p0.2 | multi_C | T24+T30+T50 | 90 | 94 | 94 | 99 | 94 | TP | 0 | True |
| 48 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 161 | 169 | 169 | 174 | 99 | PreContam |  |  |
| 48 | multiI_T24+T30+T50_a0.3_na_p0.2 | multi_I | T24+T30+T50 | 90 | 99 | 99 | 104 | 98 | PreDegr |  |  |
| 48 | multiI_T24+T30+T50_a0.3_na_p0.4 | multi_I | T24+T30+T50 | 125 | 139 | 139 | 144 | 99 | PreContam |  |  |
| 48 | multiI_T24+T30+T50_a0.5_na_p0.2 | multi_I | T24+T30+T50 | 90 | 96 | 96 | 101 | 94 | PreDegr |  |  |
| 48 | multiI_T24+T30+T50_a0.5_na_p0.4 | multi_I | T24+T30+T50 | 125 | 132 | 132 | 137 | 99 | PreContam |  |  |
| 48 | stuck_T24_na_na_p0.4 | stuck | T24 | 125 | 190 | 190 | 195 | 99 | PreContam |  |  |
| 48 | stuck_T50_na_na_p0.4 | stuck | T50 | 125 | 145 | 145 | 150 | 99 | PreContam |  |  |
| 49 | bias_T24_a0.5_neg_p0.4 | bias | T24 | 119 | 127 | 127 | 132 | 101 | PreContam |  |  |
| 49 | bias_T24_a0.5_pos_p0.4 | bias | T24 | 119 | 129 | 129 | 134 | 101 | PreContam |  |  |
| 49 | gain_T24_a2.0_pos_p0.4 | gain | T24 | 119 | 126 | 126 | 131 | 123 | PreDegr |  |  |
| 49 | multiC_T24+T30+T50_a0.3_na_p0.4 | multi_C | T24+T30+T50 | 119 | 128 | 128 | 133 | 191 | Miss |  |  |
| 49 | multiC_T24+T30+T50_a0.5_na_p0.2 | multi_C | T24+T30+T50 | 87 | 94 | 94 | 99 | 100 | Miss |  |  |
| 49 | noise_T24_b3.0_na_p0.2 | noise | T24 | 87 | 97 | 97 | 102 | 88 | PreDegr |  |  |
| 49 | noise_T50_b3.0_na_p0.4 | noise | T50 | 119 | 132 | 132 | 137 | 120 | PreDegr |  |  |
| 49 | stuck_T24_na_na_p0.4 | stuck | T24 | 119 | 128 | 128 | 133 | 124 | PreDegr |  |  |
| 49 | stuck_T24_na_na_p0.8 | stuck | T24 | 183 | 199 | 199 | 204 | 130 | PreContam |  |  |
| 49 | stuck_T50_na_na_p0.6 | stuck | T50 | 151 | 166 | 166 | 171 | 130 | PreContam |  |  |
| 52 | bias_T50_a0.75_pos_p0.4 | bias | T50 | 118 | 123 | 123 | 128 | 94 | PreContam |  |  |
| 52 | bias_T50_a1.0_pos_p0.4 | bias | T50 | 118 | 122 | 122 | 127 | 94 | PreContam |  |  |
| 52 | gain_T24_a1.0_pos_p0.4 | gain | T24 | 118 | 133 | 133 | 138 | 94 | PreContam |  |  |
| 52 | gain_T50_a2.0_pos_p0.4 | gain | T50 | 118 | 122 | 122 | 127 | 94 | PreContam |  |  |
| 52 | multiC_T24+T30+T50_a0.3_na_p0.2 | multi_C | T24+T30+T50 | 87 | 92 | 92 | 97 | 126 | Miss |  |  |
| 52 | multiC_T24+T30+T50_a0.3_na_p0.4 | multi_C | T24+T30+T50 | 118 | 125 | 125 | 130 | 94 | PreContam |  |  |
| 52 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 150 | 154 | 154 | 159 | 94 | PreContam |  |  |
| 52 | noise_T24_b3.0_na_p0.2 | noise | T24 | 87 | 87 | 87 | 92 | 87 | TP | 0 | True |
| 57 | bias_T50_a0.75_neg_p0.2 | bias | T50 | 71 | 78 | 78 | 83 | 60 | PreContam |  |  |
| 57 | multiC_T24+T30+T50_a0.3_na_p0.2 | multi_C | T24+T30+T50 | 71 | 84 | 84 | 89 | 60 | PreContam |  |  |
| 57 | multiC_T24+T30+T50_a0.5_na_p0.4 | multi_C | T24+T30+T50 | 88 | 91 | 91 | 96 | 60 | PreContam |  |  |
| 57 | noise_T50_b2.0_na_p0.2 | noise | T50 | 71 | 75 | 75 | 80 | 60 | PreContam |  |  |
| 57 | noise_T50_b3.0_na_p0.2 | noise | T50 | 71 | 74 | 74 | 79 | 60 | PreContam |  |  |
| 57 | noise_T50_b3.0_na_p0.4 | noise | T50 | 88 | 89 | 89 | 94 | 60 | PreContam |  |  |
| 63 | bias_T24_a1.0_neg_p0.4 | bias | T24 | 103 | 106 | 106 | 111 |  | Miss |  |  |
| 63 | bias_T50_a1.0_pos_p0.2 | bias | T50 | 79 | 84 | 84 | 89 | 160 | Miss |  |  |
| 63 | multiC_T24+T30+T50_a0.3_na_p0.2 | multi_C | T24+T30+T50 | 79 | 89 | 89 | 94 |  | Miss |  |  |
| 63 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 126 | 135 | 135 | 140 |  | Miss |  |  |
| 63 | multiI_T24+T30+T50_a0.3_na_p0.2 | multi_I | T24+T30+T50 | 79 | 89 | 89 | 94 |  | Miss |  |  |
| 63 | multiI_T24+T30+T50_a0.3_na_p0.4 | multi_I | T24+T30+T50 | 103 | 132 | 132 | 137 | 131 | PreDegr |  |  |
| 63 | multiI_T24+T30+T50_a0.5_na_p0.6 | multi_I | T24+T30+T50 | 126 | 135 | 135 | 140 | 148 | Miss |  |  |
| 63 | stuck_T50_na_na_p0.2 | stuck | T50 | 79 | 98 | 98 | 103 | 89 | PreDegr |  |  |
| 64 | gain_T24_a1.5_pos_p0.4 | gain | T24 | 146 | 185 | 185 | 190 | 112 | PreContam |  |  |
| 64 | multiC_T24+T30+T50_a0.5_na_p0.2 | multi_C | T24+T30+T50 | 101 | 106 | 106 | 111 | 106 | TP | 0 | False |
| 64 | multiC_T24+T30+T50_a0.5_na_p0.4 | multi_C | T24+T30+T50 | 146 | 152 | 152 | 157 | 110 | PreContam |  |  |
| 64 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 192 | 197 | 197 | 202 | 110 | PreContam |  |  |
| 64 | multiI_T24+T30+T50_a0.3_na_p0.4 | multi_I | T24+T30+T50 | 146 | 154 | 154 | 159 | 110 | PreContam |  |  |
| 64 | multiI_T24+T30+T50_a0.5_na_p0.6 | multi_I | T24+T30+T50 | 192 | 197 | 197 | 202 | 110 | PreContam |  |  |
| 64 | noise_T24_b3.0_na_p0.2 | noise | T24 | 101 | 104 | 104 | 109 | 105 | TP | 1 | True |
| 64 | noise_T24_b3.0_na_p0.4 | noise | T24 | 146 | 182 | 182 | 187 | 110 | PreContam |  |  |
| 64 | noise_T24_b3.0_na_p0.6 | noise | T24 | 192 | 195 | 195 | 200 | 110 | PreContam |  |  |
| 64 | noise_T50_b2.0_na_p0.6 | noise | T50 | 192 | 207 | 207 | 212 | 110 | PreContam |  |  |
| 64 | stuck_T24_na_na_p0.2 | stuck | T24 | 101 | 187 | 187 | 192 | 110 | PreDegr |  |  |
| 64 | stuck_T50_na_na_p0.4 | stuck | T50 | 146 | 162 | 162 | 167 | 110 | PreContam |  |  |
| 65 | gain_T50_a1.5_pos_p0.2 | gain | T50 | 75 | 82 | 82 | 87 | 97 | Miss |  |  |
| 65 | multiC_T24+T30+T50_a0.5_na_p0.4 | multi_C | T24+T30+T50 | 94 | 97 | 97 | 102 | 83 | PreContam |  |  |
| 65 | noise_T24_b3.0_na_p0.4 | noise | T24 | 94 | 96 | 96 | 101 | 83 | PreContam |  |  |
| 65 | noise_T30_b3.0_na_p0.2 | noise | T30 | 75 | 120 | 120 | 125 | 77 | PreDegr |  |  |
| 67 | bias_T24_a1.0_pos_p0.2 | bias | T24 | 107 | 118 | 118 | 123 | 137 | Miss |  |  |
| 67 | gain_T24_a0.75_neg_p0.2 | gain | T24 | 107 | 190 | 190 | 195 | 120 | PreDegr |  |  |
| 67 | multiC_T24+T30+T50_a0.3_na_p0.4 | multi_C | T24+T30+T50 | 158 | 178 | 178 | 183 | 139 | PreContam |  |  |
| 67 | multiC_T24+T30+T50_a0.5_na_p0.2 | multi_C | T24+T30+T50 | 107 | 115 | 115 | 120 | 139 | Miss |  |  |
| 67 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 210 | 214 | 214 | 219 | 139 | PreContam |  |  |
| 67 | noise_T50_b2.0_na_p0.6 | noise | T50 | 210 | 218 | 218 | 223 | 139 | PreContam |  |  |
| 67 | stuck_T24_na_na_p0.6 | stuck | T24 | 210 | 261 | 261 | 266 | 139 | PreContam |  |  |
| 67 | stuck_T50_na_na_p0.2 | stuck | T50 | 107 | 128 | 128 | 133 | 119 | PreDegr |  |  |
| 67 | stuck_T50_na_na_p0.4 | stuck | T50 | 158 | 190 | 190 | 195 | 139 | PreContam |  |  |
| 68 | bias_T50_a0.3_neg_p0.2 | bias | T50 | 84 | 113 | 113 | 118 | 95 | PreDegr |  |  |
| 68 | gain_T24_a1.0_pos_p0.4 | gain | T24 | 113 | 135 | 135 | 140 | 99 | PreContam |  |  |
| 68 | multiC_T24+T30+T50_a0.3_na_p0.4 | multi_C | T24+T30+T50 | 113 | 121 | 121 | 126 | 99 | PreContam |  |  |
| 68 | multiC_T24+T30+T50_a0.5_na_p0.2 | multi_C | T24+T30+T50 | 84 | 88 | 88 | 93 | 195 | Miss |  |  |
| 68 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 141 | 147 | 147 | 152 | 99 | PreContam |  |  |
| 68 | noise_T50_b3.0_na_p0.6 | noise | T50 | 141 | 144 | 144 | 149 | 99 | PreContam |  |  |
| 68 | stuck_T24_na_na_p0.2 | stuck | T24 | 84 | 93 | 93 | 98 | 93 | TP | 0 | True |
| 70 | noise_T50_b2.0_na_p0.6 | noise | T50 | 104 | 105 | 105 | 110 | 104 | PreDegr |  |  |
| 70 | noise_T50_b3.0_na_p0.4 | noise | T50 | 88 | 89 | 89 | 94 | 89 | TP | 0 | True |
| 79 | multiC_T24+T30+T50_a0.3_na_p0.2 | multi_C | T24+T30+T50 | 84 | 92 | 92 | 97 | 92 | TP | 0 | False |
| 79 | stuck_T24_na_na_p0.6 | stuck | T24 | 141 | 156 | 156 | 161 | 101 | PreContam |  |  |
| 85 | bias_T50_a0.75_neg_p0.2 | bias | T50 | 82 | 85 | 85 | 90 | 111 | Miss |  |  |
| 85 | gain_T24_a2.0_pos_p0.6 | gain | T24 | 135 | 149 | 149 | 154 | 80 | PreContam |  |  |
| 85 | multiC_T24+T30+T50_a0.3_na_p0.4 | multi_C | T24+T30+T50 | 108 | 126 | 126 | 131 | 80 | PreContam |  |  |
| 85 | multiC_T24+T30+T50_a0.5_na_p0.4 | multi_C | T24+T30+T50 | 108 | 111 | 111 | 116 | 80 | PreContam |  |  |
| 85 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 135 | 141 | 141 | 146 | 80 | PreContam |  |  |
| 85 | multiI_T24+T30+T50_a0.3_na_p0.2 | multi_I | T24+T30+T50 | 82 | 87 | 87 | 92 | 80 | PreContam |  |  |
| 85 | multiI_T24+T30+T50_a0.3_na_p0.4 | multi_I | T24+T30+T50 | 108 | 116 | 116 | 121 | 80 | PreContam |  |  |
| 85 | multiI_T24+T30+T50_a0.5_na_p0.2 | multi_I | T24+T30+T50 | 82 | 84 | 84 | 89 | 80 | PreContam |  |  |
| 85 | stuck_T24_na_na_p0.4 | stuck | T24 | 108 | 148 | 148 | 153 | 80 | PreContam |  |  |
| 85 | stuck_T50_na_na_p0.4 | stuck | T50 | 108 | 116 | 116 | 121 | 80 | PreContam |  |  |
| 90 | multiC_T24+T30+T50_a0.3_na_p0.2 | multi_C | T24+T30+T50 | 75 | 80 | 80 | 85 |  | Miss |  |  |
| 90 | multiC_T24+T30+T50_a0.5_na_p0.2 | multi_C | T24+T30+T50 | 75 | 78 | 78 | 83 | 75 | PreDegr |  |  |
| 90 | noise_T30_b3.0_na_p0.4 | noise | T30 | 95 | 103 | 103 | 108 | 76 | PreContam |  |  |
| 90 | stuck_T24_na_na_p0.4 | stuck | T24 | 95 | 110 | 110 | 115 | 76 | PreContam |  |  |

## 7. 비저하 시나리오 상세

| unit | scenario_id | type | sensor | tau_s | window_hi | t_hat | result |
|---|---|---|---|---|---|---|---|
| 1 | bias_T24_a0.3_neg_p0.6 | bias | T24 | 137 | 177 | 113 | FP_clean |
| 1 | bias_T24_a0.3_neg_p0.8 | bias | T24 | 165 | 192 | 79 | FP_clean |
| 1 | bias_T24_a0.5_neg_p0.8 | bias | T24 | 165 | 192 | 79 | FP_clean |
| 1 | gain_T24_a0.25_neg_p0.2 | gain | T24 | 82 | 122 | 79 | FP_clean |
| 1 | gain_T24_a0.75_neg_p0.8 | gain | T24 | 165 | 192 | 113 | FP_clean |
| 1 | gain_T30_a1.0_pos_p0.6 | gain | T30 | 137 | 177 | 79 | FP_clean |
| 1 | multiI_T24+T30+T50_a0.3_na_p0.8 | multi_I | T24+T30+T50 | 165 | 192 | 108 | FP_clean |
| 1 | multiI_T24+T30+T50_a0.5_na_p0.2 | multi_I | T24+T30+T50 | 82 | 122 | 90 | FP_contam |
| 1 | multiI_T24+T30+T50_a0.5_na_p0.4 | multi_I | T24+T30+T50 | 110 | 150 | 108 | FP_clean |
| 1 | multiI_T24+T30+T50_a0.5_na_p0.8 | multi_I | T24+T30+T50 | 165 | 192 | 108 | FP_clean |
| 1 | noise_T30_b3.0_na_p0.4 | noise | T30 | 110 | 150 | 108 | FP_clean |
| 1 | noise_T30_b3.0_na_p0.8 | noise | T30 | 165 | 192 | 108 | FP_clean |
| 1 | noise_T50_b1.0_na_p0.6 | noise | T50 | 137 | 177 | 108 | FP_clean |
| 1 | stuck_T24_na_na_p0.4 | stuck | T24 | 110 | 150 | 108 | FP_clean |
| 1 | stuck_T24_na_na_p0.8 | stuck | T24 | 165 | 192 | 108 | FP_clean |
| 9 | bias_T30_a0.75_neg_p0.6 | bias | T30 | 143 | 183 | 198 | TN |
| 9 | bias_T30_a0.75_pos_p0.6 | bias | T30 | 143 | 183 | 118 | FP_clean |
| 9 | bias_T30_a1.0_neg_p0.6 | bias | T30 | 143 | 183 | 157 | FP_contam |
| 9 | gain_T30_a0.75_neg_p0.4 | gain | T30 | 113 | 153 | 115 | FP_contam |
| 9 | gain_T30_a2.0_pos_p0.2 | gain | T30 | 84 | 124 | 88 | FP_contam |
| 9 | gain_T50_a1.5_pos_p0.6 | gain | T50 | 143 | 183 | 151 | FP_contam |
| 9 | multiC_T24+T30+T50_a0.3_na_p0.8 | multi_C | T24+T30+T50 | 172 | 201 | 174 | FP_contam |
| 9 | multiC_T24+T30+T50_a0.5_na_p0.8 | multi_C | T24+T30+T50 | 172 | 201 | 176 | FP_contam |
| 9 | multiI_T24+T30+T50_a0.3_na_p0.4 | multi_I | T24+T30+T50 | 113 | 153 | 186 | TN |
| 9 | multiI_T24+T30+T50_a0.3_na_p0.6 | multi_I | T24+T30+T50 | 143 | 183 | 151 | FP_contam |
| 9 | multiI_T24+T30+T50_a0.5_na_p0.6 | multi_I | T24+T30+T50 | 143 | 183 | 151 | FP_contam |
| 9 | multiI_T24+T30+T50_a0.5_na_p0.8 | multi_I | T24+T30+T50 | 172 | 201 | 189 | FP_contam |
| 9 | noise_T24_b1.0_na_p0.8 | noise | T24 | 172 | 201 | 172 | FP_contam |
| 9 | noise_T30_b1.0_na_p0.6 | noise | T30 | 143 | 183 | 172 | FP_contam |
| 9 | noise_T50_b3.0_na_p0.8 | noise | T50 | 172 | 201 | 174 | FP_contam |
| 9 | stuck_T30_na_na_p0.2 | stuck | T30 | 84 | 124 | 96 | FP_contam |
| 9 | stuck_T30_na_na_p0.8 | stuck | T30 | 172 | 201 | 176 | FP_contam |
| 9 | stuck_T50_na_na_p0.6 | stuck | T50 | 143 | 183 | 151 | FP_contam |
| 10 | bias_T24_a0.3_pos_p0.2 | bias | T24 | 88 | 128 | 88 | FP_contam |
| 10 | bias_T24_a0.5_pos_p0.8 | bias | T24 | 189 | 222 | 132 | FP_clean |
| 10 | bias_T30_a1.0_neg_p0.2 | bias | T30 | 88 | 128 | 122 | FP_contam |
| 10 | gain_T24_a1.0_pos_p0.2 | gain | T24 | 88 | 128 | 88 | FP_contam |
| 10 | gain_T30_a0.75_neg_p0.6 | gain | T30 | 155 | 195 | 88 | FP_clean |
| 10 | gain_T50_a0.25_neg_p0.4 | gain | T50 | 122 | 162 | 88 | FP_clean |
| 10 | multiC_T24+T30+T50_a0.3_na_p0.8 | multi_C | T24+T30+T50 | 189 | 222 | 88 | FP_clean |
| 10 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 155 | 195 | 88 | FP_clean |
| 10 | multiC_T24+T30+T50_a0.5_na_p0.8 | multi_C | T24+T30+T50 | 189 | 222 | 88 | FP_clean |
| 10 | multiI_T24+T30+T50_a0.3_na_p0.8 | multi_I | T24+T30+T50 | 189 | 222 | 88 | FP_clean |
| 10 | multiI_T24+T30+T50_a0.5_na_p0.6 | multi_I | T24+T30+T50 | 155 | 195 | 88 | FP_clean |
| 10 | multiI_T24+T30+T50_a0.5_na_p0.8 | multi_I | T24+T30+T50 | 189 | 222 | 88 | FP_clean |
| 10 | noise_T24_b1.0_na_p0.4 | noise | T24 | 122 | 162 | 88 | FP_clean |
| 10 | noise_T50_b1.0_na_p0.2 | noise | T50 | 88 | 128 | 112 | FP_contam |
| 10 | stuck_T24_na_na_p0.8 | stuck | T24 | 189 | 222 | 88 | FP_clean |
| 10 | stuck_T30_na_na_p0.2 | stuck | T30 | 88 | 128 | 88 | FP_contam |
| 10 | stuck_T30_na_na_p0.4 | stuck | T30 | 122 | 162 | 88 | FP_clean |
| 11 | bias_T30_a0.5_pos_p0.4 | bias | T30 | 129 | 169 | 134 | FP_contam |
| 11 | bias_T30_a0.75_pos_p0.2 | bias | T30 | 92 | 132 | 138 | TN |
| 11 | gain_T30_a2.0_pos_p0.6 | gain | T30 | 166 | 206 | 134 | FP_clean |
| 11 | gain_T50_a0.5_neg_p0.8 | gain | T50 | 203 | 240 | 134 | FP_clean |
| 11 | gain_T50_a1.5_pos_p0.8 | gain | T50 | 203 | 240 | 134 | FP_clean |
| 11 | multiI_T24+T30+T50_a0.3_na_p0.4 | multi_I | T24+T30+T50 | 129 | 169 | 134 | FP_contam |
| 11 | multiI_T24+T30+T50_a0.5_na_p0.4 | multi_I | T24+T30+T50 | 129 | 169 | 136 | FP_contam |
| 11 | multiI_T24+T30+T50_a0.5_na_p0.8 | multi_I | T24+T30+T50 | 203 | 240 | 134 | FP_clean |
| 11 | noise_T30_b1.0_na_p0.8 | noise | T30 | 203 | 240 | 134 | FP_clean |
| 11 | noise_T30_b2.0_na_p0.2 | noise | T30 | 92 | 132 | 93 | FP_contam |
| 11 | noise_T30_b2.0_na_p0.8 | noise | T30 | 203 | 240 | 134 | FP_clean |
| 11 | stuck_T24_na_na_p0.6 | stuck | T24 | 166 | 206 | 134 | FP_clean |
| 11 | stuck_T30_na_na_p0.4 | stuck | T30 | 129 | 169 | 134 | FP_contam |
| 17 | bias_T24_a0.75_neg_p0.8 | bias | T24 | 232 | 272 | 165 | FP_clean |
| 17 | bias_T30_a0.3_pos_p0.4 | bias | T30 | 143 | 183 | 165 | FP_contam |
| 17 | bias_T30_a0.75_pos_p0.6 | bias | T30 | 188 | 228 | 165 | FP_clean |
| 17 | gain_T24_a1.0_pos_p0.2 | gain | T24 | 99 | 139 | 153 | TN |
| 17 | gain_T24_a1.5_pos_p0.8 | gain | T24 | 232 | 272 | 165 | FP_clean |
| 17 | gain_T30_a1.0_pos_p0.8 | gain | T30 | 232 | 272 | 165 | FP_clean |
| 17 | gain_T50_a0.5_neg_p0.6 | gain | T50 | 188 | 228 | 165 | FP_clean |
| 17 | multiC_T24+T30+T50_a0.3_na_p0.8 | multi_C | T24+T30+T50 | 232 | 272 | 165 | FP_clean |
| 17 | multiC_T24+T30+T50_a0.5_na_p0.8 | multi_C | T24+T30+T50 | 232 | 272 | 165 | FP_clean |
| 17 | multiI_T24+T30+T50_a0.3_na_p0.2 | multi_I | T24+T30+T50 | 99 | 139 | 164 | TN |
| 17 | multiI_T24+T30+T50_a0.5_na_p0.6 | multi_I | T24+T30+T50 | 188 | 228 | 165 | FP_clean |
| 17 | multiI_T24+T30+T50_a0.5_na_p0.8 | multi_I | T24+T30+T50 | 232 | 272 | 165 | FP_clean |
| 17 | stuck_T30_na_na_p0.4 | stuck | T30 | 143 | 183 | 150 | FP_contam |
| 17 | stuck_T50_na_na_p0.8 | stuck | T50 | 232 | 272 | 165 | FP_clean |
| 26 | bias_T30_a0.5_neg_p0.8 | bias | T30 | 170 | 199 | 84 | FP_clean |
| 26 | bias_T30_a0.5_pos_p0.6 | bias | T30 | 141 | 181 | 84 | FP_clean |
| 26 | gain_T24_a0.25_neg_p0.4 | gain | T24 | 113 | 153 | 84 | FP_clean |
| 26 | gain_T30_a0.75_neg_p0.8 | gain | T30 | 170 | 199 | 84 | FP_clean |
| 26 | gain_T50_a0.75_neg_p0.6 | gain | T50 | 141 | 181 | 84 | FP_clean |
| 26 | gain_T50_a0.75_neg_p0.8 | gain | T50 | 170 | 199 | 84 | FP_clean |
| 26 | multiC_T24+T30+T50_a0.3_na_p0.6 | multi_C | T24+T30+T50 | 141 | 181 | 84 | FP_clean |
| 26 | multiC_T24+T30+T50_a0.3_na_p0.8 | multi_C | T24+T30+T50 | 170 | 199 | 84 | FP_clean |
| 26 | multiC_T24+T30+T50_a0.5_na_p0.8 | multi_C | T24+T30+T50 | 170 | 199 | 84 | FP_clean |
| 26 | multiI_T24+T30+T50_a0.3_na_p0.6 | multi_I | T24+T30+T50 | 141 | 181 | 84 | FP_clean |
| 26 | multiI_T24+T30+T50_a0.3_na_p0.8 | multi_I | T24+T30+T50 | 170 | 199 | 84 | FP_clean |
| 26 | multiI_T24+T30+T50_a0.5_na_p0.4 | multi_I | T24+T30+T50 | 113 | 153 | 84 | FP_clean |
| 26 | noise_T24_b1.0_na_p0.6 | noise | T24 | 141 | 181 | 84 | FP_clean |
| 26 | noise_T30_b2.0_na_p0.4 | noise | T30 | 113 | 153 | 84 | FP_clean |
| 26 | stuck_T24_na_na_p0.6 | stuck | T24 | 141 | 181 | 84 | FP_clean |
| 26 | stuck_T30_na_na_p0.4 | stuck | T30 | 113 | 153 | 84 | FP_clean |
| 26 | stuck_T50_na_na_p0.8 | stuck | T50 | 170 | 199 | 84 | FP_clean |
| 32 | bias_T30_a0.3_neg_p0.2 | bias | T30 | 82 | 122 |  | TN |
| 32 | bias_T30_a1.0_neg_p0.2 | bias | T30 | 82 | 122 |  | TN |
| 32 | gain_T30_a0.25_neg_p0.6 | gain | T30 | 137 | 177 |  | TN |
| 32 | gain_T30_a0.75_neg_p0.4 | gain | T30 | 109 | 149 |  | TN |
| 32 | gain_T30_a1.0_pos_p0.4 | gain | T30 | 109 | 149 | 156 | TN |
| 32 | gain_T50_a0.75_neg_p0.6 | gain | T50 | 137 | 177 | 163 | FP_contam |
| 32 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 137 | 177 |  | TN |
| 32 | multiI_T24+T30+T50_a0.3_na_p0.4 | multi_I | T24+T30+T50 | 109 | 149 |  | TN |
| 32 | multiI_T24+T30+T50_a0.3_na_p0.6 | multi_I | T24+T30+T50 | 137 | 177 |  | TN |
| 32 | multiI_T24+T30+T50_a0.5_na_p0.2 | multi_I | T24+T30+T50 | 82 | 122 |  | TN |
| 32 | multiI_T24+T30+T50_a0.5_na_p0.8 | multi_I | T24+T30+T50 | 164 | 191 |  | TN |
| 32 | noise_T30_b2.0_na_p0.8 | noise | T30 | 164 | 191 | 173 | FP_contam |
| 32 | noise_T50_b2.0_na_p0.8 | noise | T50 | 164 | 191 | 171 | FP_contam |
| 32 | stuck_T30_na_na_p0.2 | stuck | T30 | 82 | 122 | 89 | FP_contam |
| 32 | stuck_T30_na_na_p0.6 | stuck | T30 | 137 | 177 | 142 | FP_contam |
| 32 | stuck_T30_na_na_p0.8 | stuck | T30 | 164 | 191 | 170 | FP_contam |
| 32 | stuck_T50_na_na_p0.4 | stuck | T50 | 109 | 149 | 113 | FP_contam |
| 48 | bias_T24_a0.3_neg_p0.4 | bias | T24 | 125 | 165 | 99 | FP_clean |
| 48 | bias_T24_a0.3_neg_p0.6 | bias | T24 | 161 | 201 | 99 | FP_clean |
| 48 | bias_T50_a1.0_pos_p0.6 | bias | T50 | 161 | 201 | 99 | FP_clean |
| 48 | gain_T30_a0.5_neg_p0.6 | gain | T30 | 161 | 201 | 99 | FP_clean |
| 48 | gain_T50_a0.75_neg_p0.6 | gain | T50 | 161 | 201 | 99 | FP_clean |
| 48 | gain_T50_a2.0_pos_p0.8 | gain | T50 | 196 | 231 | 99 | FP_clean |
| 48 | multiC_T24+T30+T50_a0.3_na_p0.8 | multi_C | T24+T30+T50 | 196 | 231 | 99 | FP_clean |
| 48 | noise_T24_b1.0_na_p0.8 | noise | T24 | 196 | 231 | 99 | FP_clean |
| 48 | noise_T24_b2.0_na_p0.8 | noise | T24 | 196 | 231 | 99 | FP_clean |
| 48 | noise_T30_b1.0_na_p0.6 | noise | T30 | 161 | 201 | 99 | FP_clean |
| 48 | noise_T30_b2.0_na_p0.6 | noise | T30 | 161 | 201 | 99 | FP_clean |
| 48 | stuck_T24_na_na_p0.2 | stuck | T24 | 90 | 130 | 98 | FP_contam |
| 48 | stuck_T30_na_na_p0.6 | stuck | T30 | 161 | 201 | 99 | FP_clean |
| 49 | bias_T30_a0.5_pos_p0.4 | bias | T30 | 119 | 159 | 101 | FP_clean |
| 49 | bias_T50_a0.75_neg_p0.6 | bias | T50 | 151 | 191 | 130 | FP_clean |
| 49 | bias_T50_a0.75_pos_p0.8 | bias | T50 | 183 | 215 | 130 | FP_clean |
| 49 | gain_T24_a0.25_neg_p0.4 | gain | T24 | 119 | 159 | 152 | FP_contam |
| 49 | gain_T24_a0.5_pos_p0.6 | gain | T24 | 151 | 191 | 130 | FP_clean |
| 49 | gain_T30_a2.0_pos_p0.2 | gain | T30 | 87 | 127 | 94 | FP_contam |
| 49 | multiC_T24+T30+T50_a0.3_na_p0.6 | multi_C | T24+T30+T50 | 151 | 191 | 130 | FP_clean |
| 49 | multiC_T24+T30+T50_a0.3_na_p0.8 | multi_C | T24+T30+T50 | 183 | 215 | 130 | FP_clean |
| 49 | multiI_T24+T30+T50_a0.3_na_p0.6 | multi_I | T24+T30+T50 | 151 | 191 | 130 | FP_clean |
| 49 | multiI_T24+T30+T50_a0.3_na_p0.8 | multi_I | T24+T30+T50 | 183 | 215 | 130 | FP_clean |
| 49 | multiI_T24+T30+T50_a0.5_na_p0.2 | multi_I | T24+T30+T50 | 87 | 127 | 101 | FP_contam |
| 49 | multiI_T24+T30+T50_a0.5_na_p0.6 | multi_I | T24+T30+T50 | 151 | 191 | 130 | FP_clean |
| 49 | noise_T24_b2.0_na_p0.8 | noise | T24 | 183 | 215 | 130 | FP_clean |
| 49 | noise_T50_b1.0_na_p0.8 | noise | T50 | 183 | 215 | 130 | FP_clean |
| 49 | stuck_T30_na_na_p0.2 | stuck | T30 | 87 | 127 | 94 | FP_contam |
| 49 | stuck_T50_na_na_p0.2 | stuck | T50 | 87 | 127 | 97 | FP_contam |
| 52 | bias_T30_a0.75_pos_p0.8 | bias | T30 | 181 | 213 | 94 | FP_clean |
| 52 | bias_T30_a1.0_neg_p0.4 | bias | T30 | 118 | 158 | 94 | FP_clean |
| 52 | bias_T50_a0.3_pos_p0.8 | bias | T50 | 181 | 213 | 94 | FP_clean |
| 52 | gain_T30_a0.25_neg_p0.6 | gain | T30 | 150 | 190 | 94 | FP_clean |
| 52 | gain_T30_a0.5_neg_p0.6 | gain | T30 | 150 | 190 | 94 | FP_clean |
| 52 | multiC_T24+T30+T50_a0.5_na_p0.8 | multi_C | T24+T30+T50 | 181 | 213 | 94 | FP_clean |
| 52 | multiI_T24+T30+T50_a0.3_na_p0.4 | multi_I | T24+T30+T50 | 118 | 158 | 94 | FP_clean |
| 52 | multiI_T24+T30+T50_a0.3_na_p0.6 | multi_I | T24+T30+T50 | 150 | 190 | 94 | FP_clean |
| 52 | multiI_T24+T30+T50_a0.3_na_p0.8 | multi_I | T24+T30+T50 | 181 | 213 | 94 | FP_clean |
| 52 | multiI_T24+T30+T50_a0.5_na_p0.2 | multi_I | T24+T30+T50 | 87 | 127 | 94 | FP_contam |
| 52 | multiI_T24+T30+T50_a0.5_na_p0.6 | multi_I | T24+T30+T50 | 150 | 190 | 94 | FP_clean |
| 52 | noise_T24_b1.0_na_p0.4 | noise | T24 | 118 | 158 | 94 | FP_clean |
| 52 | noise_T24_b2.0_na_p0.8 | noise | T24 | 181 | 213 | 94 | FP_clean |
| 52 | noise_T50_b1.0_na_p0.8 | noise | T50 | 181 | 213 | 94 | FP_clean |
| 52 | stuck_T24_na_na_p0.6 | stuck | T24 | 150 | 190 | 94 | FP_clean |
| 52 | stuck_T24_na_na_p0.8 | stuck | T24 | 181 | 213 | 94 | FP_clean |
| 52 | stuck_T30_na_na_p0.2 | stuck | T30 | 87 | 127 | 93 | FP_contam |
| 52 | stuck_T50_na_na_p0.8 | stuck | T50 | 181 | 213 | 94 | FP_clean |
| 57 | bias_T30_a0.3_neg_p0.4 | bias | T30 | 88 | 128 | 59 | FP_clean |
| 57 | bias_T30_a0.5_neg_p0.2 | bias | T30 | 71 | 111 | 60 | FP_clean |
| 57 | bias_T30_a0.75_neg_p0.6 | bias | T30 | 104 | 137 | 60 | FP_clean |
| 57 | gain_T24_a0.25_neg_p0.4 | gain | T24 | 88 | 128 | 60 | FP_clean |
| 57 | gain_T30_a0.5_neg_p0.2 | gain | T30 | 71 | 111 | 60 | FP_clean |
| 57 | gain_T50_a0.5_neg_p0.8 | gain | T50 | 121 | 137 | 60 | FP_clean |
| 57 | gain_T50_a1.0_pos_p0.8 | gain | T50 | 121 | 137 | 60 | FP_clean |
| 57 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 104 | 137 | 60 | FP_clean |
| 57 | multiC_T24+T30+T50_a0.5_na_p0.8 | multi_C | T24+T30+T50 | 121 | 137 | 60 | FP_clean |
| 57 | multiI_T24+T30+T50_a0.3_na_p0.4 | multi_I | T24+T30+T50 | 88 | 128 | 60 | FP_clean |
| 57 | multiI_T24+T30+T50_a0.3_na_p0.8 | multi_I | T24+T30+T50 | 121 | 137 | 60 | FP_clean |
| 57 | multiI_T24+T30+T50_a0.5_na_p0.6 | multi_I | T24+T30+T50 | 104 | 137 | 60 | FP_clean |
| 57 | multiI_T24+T30+T50_a0.5_na_p0.8 | multi_I | T24+T30+T50 | 121 | 137 | 60 | FP_clean |
| 57 | noise_T30_b3.0_na_p0.4 | noise | T30 | 88 | 128 | 60 | FP_clean |
| 57 | stuck_T24_na_na_p0.6 | stuck | T24 | 104 | 137 | 60 | FP_clean |
| 57 | stuck_T30_na_na_p0.2 | stuck | T30 | 71 | 111 | 60 | FP_clean |
| 57 | stuck_T30_na_na_p0.4 | stuck | T30 | 88 | 128 | 60 | FP_clean |
| 57 | stuck_T50_na_na_p0.8 | stuck | T50 | 121 | 137 | 60 | FP_clean |
| 63 | bias_T24_a0.3_pos_p0.2 | bias | T24 | 79 | 119 | 160 | TN |
| 63 | bias_T50_a0.5_pos_p0.8 | bias | T50 | 150 | 174 |  | TN |
| 63 | gain_T24_a1.0_pos_p0.6 | gain | T24 | 126 | 166 | 145 | FP_contam |
| 63 | gain_T30_a0.25_neg_p0.8 | gain | T30 | 150 | 174 |  | TN |
| 63 | gain_T50_a0.25_neg_p0.2 | gain | T50 | 79 | 119 |  | TN |
| 63 | gain_T50_a2.0_pos_p0.8 | gain | T50 | 150 | 174 | 156 | FP_contam |
| 63 | multiC_T24+T30+T50_a0.3_na_p0.4 | multi_C | T24+T30+T50 | 103 | 143 |  | TN |
| 63 | multiC_T24+T30+T50_a0.3_na_p0.8 | multi_C | T24+T30+T50 | 150 | 174 |  | TN |
| 63 | multiI_T24+T30+T50_a0.3_na_p0.8 | multi_I | T24+T30+T50 | 150 | 174 |  | TN |
| 63 | noise_T24_b1.0_na_p0.6 | noise | T24 | 126 | 166 | 131 | FP_contam |
| 63 | noise_T24_b3.0_na_p0.8 | noise | T24 | 150 | 174 | 150 | FP_contam |
| 63 | noise_T30_b2.0_na_p0.2 | noise | T30 | 79 | 119 | 89 | FP_contam |
| 63 | noise_T30_b2.0_na_p0.6 | noise | T30 | 126 | 166 | 127 | FP_contam |
| 63 | stuck_T24_na_na_p0.4 | stuck | T24 | 103 | 143 | 108 | FP_contam |
| 63 | stuck_T30_na_na_p0.6 | stuck | T30 | 126 | 166 | 135 | FP_contam |
| 63 | stuck_T50_na_na_p0.8 | stuck | T50 | 150 | 174 | 159 | FP_contam |
| 64 | bias_T24_a0.3_neg_p0.8 | bias | T24 | 237 | 277 | 112 | FP_clean |
| 64 | bias_T30_a0.3_neg_p0.4 | bias | T30 | 146 | 186 | 112 | FP_clean |
| 64 | bias_T30_a0.3_pos_p0.6 | bias | T30 | 192 | 232 | 110 | FP_clean |
| 64 | bias_T30_a1.0_pos_p0.6 | bias | T30 | 192 | 232 | 110 | FP_clean |
| 64 | gain_T30_a0.5_neg_p0.8 | gain | T30 | 237 | 277 | 110 | FP_clean |
| 64 | gain_T50_a0.75_neg_p0.4 | gain | T50 | 146 | 186 | 112 | FP_clean |
| 64 | gain_T50_a1.5_pos_p0.8 | gain | T50 | 237 | 277 | 110 | FP_clean |
| 64 | multiC_T24+T30+T50_a0.3_na_p0.8 | multi_C | T24+T30+T50 | 237 | 277 | 110 | FP_clean |
| 64 | multiI_T24+T30+T50_a0.3_na_p0.2 | multi_I | T24+T30+T50 | 101 | 141 | 110 | FP_contam |
| 64 | multiI_T24+T30+T50_a0.3_na_p0.6 | multi_I | T24+T30+T50 | 192 | 232 | 110 | FP_clean |
| 64 | noise_T30_b3.0_na_p0.2 | noise | T30 | 101 | 141 | 103 | FP_contam |
| 64 | stuck_T30_na_na_p0.2 | stuck | T30 | 101 | 141 | 110 | FP_contam |
| 64 | stuck_T50_na_na_p0.6 | stuck | T50 | 192 | 232 | 110 | FP_clean |
| 65 | bias_T24_a0.3_pos_p0.8 | bias | T24 | 133 | 153 | 83 | FP_clean |
| 65 | bias_T24_a0.75_pos_p0.8 | bias | T24 | 133 | 153 | 101 | FP_clean |
| 65 | bias_T30_a1.0_pos_p0.2 | bias | T30 | 75 | 115 | 83 | FP_contam |
| 65 | bias_T50_a0.5_pos_p0.8 | bias | T50 | 133 | 153 | 83 | FP_clean |
| 65 | gain_T24_a1.5_pos_p0.6 | gain | T24 | 114 | 153 | 83 | FP_clean |
| 65 | gain_T24_a2.0_pos_p0.6 | gain | T24 | 114 | 153 | 83 | FP_clean |
| 65 | gain_T30_a0.75_neg_p0.6 | gain | T30 | 114 | 153 | 83 | FP_clean |
| 65 | gain_T50_a0.25_neg_p0.4 | gain | T50 | 94 | 134 | 83 | FP_clean |
| 65 | multiC_T24+T30+T50_a0.3_na_p0.6 | multi_C | T24+T30+T50 | 114 | 153 | 83 | FP_clean |
| 65 | multiC_T24+T30+T50_a0.3_na_p0.8 | multi_C | T24+T30+T50 | 133 | 153 | 83 | FP_clean |
| 65 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 114 | 153 | 83 | FP_clean |
| 65 | multiC_T24+T30+T50_a0.5_na_p0.8 | multi_C | T24+T30+T50 | 133 | 153 | 83 | FP_clean |
| 65 | multiI_T24+T30+T50_a0.3_na_p0.8 | multi_I | T24+T30+T50 | 133 | 153 | 83 | FP_clean |
| 65 | multiI_T24+T30+T50_a0.5_na_p0.2 | multi_I | T24+T30+T50 | 75 | 115 | 109 | FP_contam |
| 65 | multiI_T24+T30+T50_a0.5_na_p0.6 | multi_I | T24+T30+T50 | 114 | 153 | 83 | FP_clean |
| 65 | multiI_T24+T30+T50_a0.5_na_p0.8 | multi_I | T24+T30+T50 | 133 | 153 | 83 | FP_clean |
| 65 | noise_T30_b2.0_na_p0.6 | noise | T30 | 114 | 153 | 83 | FP_clean |
| 65 | noise_T30_b3.0_na_p0.8 | noise | T30 | 133 | 153 | 83 | FP_clean |
| 65 | stuck_T24_na_na_p0.2 | stuck | T24 | 75 | 115 | 83 | FP_contam |
| 65 | stuck_T24_na_na_p0.8 | stuck | T24 | 133 | 153 | 83 | FP_clean |
| 65 | stuck_T30_na_na_p0.8 | stuck | T30 | 133 | 153 | 83 | FP_clean |
| 65 | stuck_T50_na_na_p0.6 | stuck | T50 | 114 | 153 | 83 | FP_clean |
| 65 | stuck_T50_na_na_p0.8 | stuck | T50 | 133 | 153 | 83 | FP_clean |
| 67 | bias_T24_a0.3_neg_p0.2 | bias | T24 | 107 | 147 | 120 | FP_contam |
| 67 | bias_T30_a0.3_neg_p0.8 | bias | T30 | 261 | 301 | 140 | FP_clean |
| 67 | bias_T50_a0.75_pos_p0.8 | bias | T50 | 261 | 301 | 139 | FP_clean |
| 67 | gain_T24_a0.5_neg_p0.2 | gain | T24 | 107 | 147 | 137 | FP_contam |
| 67 | gain_T30_a0.5_neg_p0.4 | gain | T30 | 158 | 198 | 139 | FP_clean |
| 67 | gain_T50_a0.25_neg_p0.8 | gain | T50 | 261 | 301 | 139 | FP_clean |
| 67 | multiC_T24+T30+T50_a0.3_na_p0.8 | multi_C | T24+T30+T50 | 261 | 301 | 139 | FP_clean |
| 67 | multiI_T24+T30+T50_a0.3_na_p0.4 | multi_I | T24+T30+T50 | 158 | 198 | 139 | FP_clean |
| 67 | multiI_T24+T30+T50_a0.3_na_p0.6 | multi_I | T24+T30+T50 | 210 | 250 | 139 | FP_clean |
| 67 | multiI_T24+T30+T50_a0.5_na_p0.2 | multi_I | T24+T30+T50 | 107 | 147 | 139 | FP_contam |
| 67 | multiI_T24+T30+T50_a0.5_na_p0.6 | multi_I | T24+T30+T50 | 210 | 250 | 139 | FP_clean |
| 67 | noise_T24_b1.0_na_p0.4 | noise | T24 | 158 | 198 | 139 | FP_clean |
| 67 | noise_T30_b1.0_na_p0.2 | noise | T30 | 107 | 147 | 119 | FP_contam |
| 67 | noise_T50_b3.0_na_p0.8 | noise | T50 | 261 | 301 | 139 | FP_clean |
| 67 | stuck_T30_na_na_p0.6 | stuck | T30 | 210 | 250 | 139 | FP_clean |
| 68 | bias_T24_a0.3_neg_p0.4 | bias | T24 | 113 | 153 | 95 | FP_clean |
| 68 | bias_T24_a0.3_pos_p0.6 | bias | T24 | 141 | 181 |  | TN |
| 68 | bias_T30_a1.0_pos_p0.6 | bias | T30 | 141 | 181 | 99 | FP_clean |
| 68 | bias_T50_a0.75_pos_p0.6 | bias | T50 | 141 | 181 | 99 | FP_clean |
| 68 | gain_T30_a0.75_neg_p0.2 | gain | T30 | 84 | 124 | 144 | TN |
| 68 | gain_T30_a1.0_pos_p0.8 | gain | T30 | 170 | 199 | 99 | FP_clean |
| 68 | gain_T50_a1.0_pos_p0.4 | gain | T50 | 113 | 153 | 99 | FP_clean |
| 68 | multiC_T24+T30+T50_a0.3_na_p0.6 | multi_C | T24+T30+T50 | 141 | 181 | 99 | FP_clean |
| 68 | multiC_T24+T30+T50_a0.3_na_p0.8 | multi_C | T24+T30+T50 | 170 | 199 | 99 | FP_clean |
| 68 | multiI_T24+T30+T50_a0.3_na_p0.4 | multi_I | T24+T30+T50 | 113 | 153 | 99 | FP_clean |
| 68 | multiI_T24+T30+T50_a0.3_na_p0.6 | multi_I | T24+T30+T50 | 141 | 181 | 99 | FP_clean |
| 68 | multiI_T24+T30+T50_a0.3_na_p0.8 | multi_I | T24+T30+T50 | 170 | 199 | 99 | FP_clean |
| 68 | multiI_T24+T30+T50_a0.5_na_p0.2 | multi_I | T24+T30+T50 | 84 | 124 | 195 | TN |
| 68 | noise_T30_b1.0_na_p0.8 | noise | T30 | 170 | 199 | 99 | FP_clean |
| 68 | noise_T30_b2.0_na_p0.6 | noise | T30 | 141 | 181 | 99 | FP_clean |
| 68 | noise_T30_b3.0_na_p0.2 | noise | T30 | 84 | 124 | 86 | FP_contam |
| 68 | stuck_T30_na_na_p0.4 | stuck | T30 | 113 | 153 | 99 | FP_clean |
| 68 | stuck_T50_na_na_p0.6 | stuck | T50 | 141 | 181 | 99 | FP_clean |
| 68 | stuck_T50_na_na_p0.8 | stuck | T50 | 170 | 199 | 99 | FP_clean |
| 70 | bias_T24_a0.5_neg_p0.4 | bias | T24 | 88 | 128 |  | TN |
| 70 | bias_T24_a0.75_neg_p0.8 | bias | T24 | 121 | 137 |  | TN |
| 70 | bias_T24_a1.0_neg_p0.6 | bias | T24 | 104 | 137 |  | TN |
| 70 | bias_T50_a0.3_pos_p0.8 | bias | T50 | 121 | 137 |  | TN |
| 70 | gain_T24_a2.0_pos_p0.8 | gain | T24 | 121 | 137 | 128 | FP_contam |
| 70 | gain_T30_a0.75_neg_p0.2 | gain | T30 | 71 | 111 |  | TN |
| 70 | gain_T30_a1.0_pos_p0.4 | gain | T30 | 88 | 128 | 93 | FP_contam |
| 70 | gain_T50_a0.5_neg_p0.2 | gain | T50 | 71 | 111 | 137 | TN |
| 70 | multiC_T24+T30+T50_a0.3_na_p0.2 | multi_C | T24+T30+T50 | 71 | 111 |  | TN |
| 70 | multiC_T24+T30+T50_a0.3_na_p0.4 | multi_C | T24+T30+T50 | 88 | 128 |  | TN |
| 70 | multiC_T24+T30+T50_a0.5_na_p0.4 | multi_C | T24+T30+T50 | 88 | 128 |  | TN |
| 70 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 104 | 137 |  | TN |
| 70 | multiI_T24+T30+T50_a0.3_na_p0.4 | multi_I | T24+T30+T50 | 88 | 128 | 96 | FP_contam |
| 70 | multiI_T24+T30+T50_a0.3_na_p0.6 | multi_I | T24+T30+T50 | 104 | 137 |  | TN |
| 70 | multiI_T24+T30+T50_a0.5_na_p0.2 | multi_I | T24+T30+T50 | 71 | 111 |  | TN |
| 70 | multiI_T24+T30+T50_a0.5_na_p0.8 | multi_I | T24+T30+T50 | 121 | 137 |  | TN |
| 70 | noise_T24_b2.0_na_p0.4 | noise | T24 | 88 | 128 | 90 | FP_contam |
| 70 | noise_T50_b1.0_na_p0.8 | noise | T50 | 121 | 137 | 137 | FP_contam |
| 70 | stuck_T24_na_na_p0.8 | stuck | T24 | 121 | 137 | 129 | FP_contam |
| 70 | stuck_T30_na_na_p0.2 | stuck | T30 | 71 | 111 | 80 | FP_contam |
| 70 | stuck_T30_na_na_p0.6 | stuck | T30 | 104 | 137 | 112 | FP_contam |
| 70 | stuck_T50_na_na_p0.8 | stuck | T50 | 121 | 137 | 125 | FP_contam |
| 79 | bias_T30_a0.5_pos_p0.2 | bias | T30 | 84 | 124 | 101 | FP_contam |
| 79 | bias_T30_a0.5_pos_p0.6 | bias | T30 | 141 | 181 | 105 | FP_clean |
| 79 | bias_T50_a0.5_neg_p0.6 | bias | T50 | 141 | 181 | 101 | FP_clean |
| 79 | bias_T50_a1.0_pos_p0.6 | bias | T50 | 141 | 181 | 107 | FP_clean |
| 79 | gain_T24_a0.25_neg_p0.2 | gain | T24 | 84 | 124 | 96 | FP_contam |
| 79 | gain_T30_a0.25_neg_p0.4 | gain | T30 | 113 | 153 | 101 | FP_clean |
| 79 | gain_T30_a0.5_neg_p0.4 | gain | T30 | 113 | 153 | 101 | FP_clean |
| 79 | gain_T50_a1.0_pos_p0.8 | gain | T50 | 170 | 199 | 101 | FP_clean |
| 79 | multiC_T24+T30+T50_a0.3_na_p0.8 | multi_C | T24+T30+T50 | 170 | 199 | 101 | FP_clean |
| 79 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 141 | 181 | 101 | FP_clean |
| 79 | multiC_T24+T30+T50_a0.5_na_p0.8 | multi_C | T24+T30+T50 | 170 | 199 | 101 | FP_clean |
| 79 | multiI_T24+T30+T50_a0.5_na_p0.2 | multi_I | T24+T30+T50 | 84 | 124 | 105 | FP_contam |
| 79 | multiI_T24+T30+T50_a0.5_na_p0.4 | multi_I | T24+T30+T50 | 113 | 153 | 101 | FP_clean |
| 79 | multiI_T24+T30+T50_a0.5_na_p0.6 | multi_I | T24+T30+T50 | 141 | 181 | 101 | FP_clean |
| 79 | multiI_T24+T30+T50_a0.5_na_p0.8 | multi_I | T24+T30+T50 | 170 | 199 | 101 | FP_clean |
| 79 | noise_T24_b1.0_na_p0.2 | noise | T24 | 84 | 124 | 105 | FP_contam |
| 79 | noise_T24_b1.0_na_p0.4 | noise | T24 | 113 | 153 | 101 | FP_clean |
| 79 | noise_T30_b2.0_na_p0.8 | noise | T30 | 170 | 199 | 101 | FP_clean |
| 79 | noise_T50_b2.0_na_p0.6 | noise | T50 | 141 | 181 | 101 | FP_clean |
| 79 | stuck_T30_na_na_p0.2 | stuck | T30 | 84 | 124 | 90 | FP_contam |
| 79 | stuck_T30_na_na_p0.4 | stuck | T30 | 113 | 153 | 101 | FP_clean |
| 79 | stuck_T30_na_na_p0.8 | stuck | T30 | 170 | 199 | 101 | FP_clean |
| 85 | bias_T30_a0.75_neg_p0.2 | bias | T30 | 82 | 122 | 80 | FP_clean |
| 85 | bias_T50_a0.5_neg_p0.6 | bias | T50 | 135 | 175 | 75 | FP_clean |
| 85 | bias_T50_a0.75_pos_p0.8 | bias | T50 | 161 | 188 | 75 | FP_clean |
| 85 | gain_T24_a0.5_neg_p0.6 | gain | T24 | 135 | 175 | 80 | FP_clean |
| 85 | gain_T30_a0.5_neg_p0.2 | gain | T30 | 82 | 122 | 80 | FP_clean |
| 85 | gain_T30_a1.5_pos_p0.2 | gain | T30 | 82 | 122 | 80 | FP_clean |
| 85 | multiC_T24+T30+T50_a0.5_na_p0.8 | multi_C | T24+T30+T50 | 161 | 188 | 80 | FP_clean |
| 85 | multiI_T24+T30+T50_a0.3_na_p0.6 | multi_I | T24+T30+T50 | 135 | 175 | 80 | FP_clean |
| 85 | multiI_T24+T30+T50_a0.5_na_p0.8 | multi_I | T24+T30+T50 | 161 | 188 | 80 | FP_clean |
| 85 | noise_T30_b1.0_na_p0.4 | noise | T30 | 108 | 148 | 80 | FP_clean |
| 85 | noise_T30_b2.0_na_p0.2 | noise | T30 | 82 | 122 | 80 | FP_clean |
| 85 | noise_T30_b3.0_na_p0.8 | noise | T30 | 161 | 188 | 80 | FP_clean |
| 85 | noise_T50_b1.0_na_p0.2 | noise | T50 | 82 | 122 | 80 | FP_clean |
| 85 | stuck_T24_na_na_p0.8 | stuck | T24 | 161 | 188 | 80 | FP_clean |
| 85 | stuck_T30_na_na_p0.2 | stuck | T30 | 82 | 122 | 80 | FP_clean |
| 90 | bias_T24_a0.3_neg_p0.4 | bias | T24 | 95 | 135 | 76 | FP_clean |
| 90 | bias_T24_a0.5_pos_p0.8 | bias | T24 | 134 | 154 | 76 | FP_clean |
| 90 | bias_T30_a0.5_pos_p0.8 | bias | T30 | 134 | 154 | 76 | FP_clean |
| 90 | bias_T50_a1.0_neg_p0.8 | bias | T50 | 134 | 154 | 76 | FP_clean |
| 90 | gain_T24_a0.75_neg_p0.8 | gain | T24 | 134 | 154 | 76 | FP_clean |
| 90 | gain_T24_a1.0_pos_p0.8 | gain | T24 | 134 | 154 | 76 | FP_clean |
| 90 | gain_T24_a1.5_pos_p0.6 | gain | T24 | 114 | 154 | 76 | FP_clean |
| 90 | gain_T30_a0.25_neg_p0.8 | gain | T30 | 134 | 154 | 76 | FP_clean |
| 90 | multiC_T24+T30+T50_a0.3_na_p0.4 | multi_C | T24+T30+T50 | 95 | 135 | 76 | FP_clean |
| 90 | multiC_T24+T30+T50_a0.3_na_p0.6 | multi_C | T24+T30+T50 | 114 | 154 | 76 | FP_clean |
| 90 | multiI_T24+T30+T50_a0.3_na_p0.2 | multi_I | T24+T30+T50 | 75 | 115 | 76 | FP_contam |
| 90 | multiI_T24+T30+T50_a0.3_na_p0.4 | multi_I | T24+T30+T50 | 95 | 135 | 76 | FP_clean |
| 90 | multiI_T24+T30+T50_a0.3_na_p0.8 | multi_I | T24+T30+T50 | 134 | 154 | 76 | FP_clean |
| 90 | multiI_T24+T30+T50_a0.5_na_p0.4 | multi_I | T24+T30+T50 | 95 | 135 | 76 | FP_clean |
| 90 | noise_T24_b1.0_na_p0.4 | noise | T24 | 95 | 135 | 76 | FP_clean |
| 90 | noise_T30_b1.0_na_p0.4 | noise | T30 | 95 | 135 | 76 | FP_clean |
| 90 | noise_T50_b2.0_na_p0.8 | noise | T50 | 134 | 154 | 76 | FP_clean |
| 90 | stuck_T24_na_na_p0.6 | stuck | T24 | 114 | 154 | 76 | FP_clean |
| 90 | stuck_T30_na_na_p0.8 | stuck | T30 | 134 | 154 | 76 | FP_clean |
| 90 | stuck_T50_na_na_p0.6 | stuck | T50 | 114 | 154 | 76 | FP_clean |
