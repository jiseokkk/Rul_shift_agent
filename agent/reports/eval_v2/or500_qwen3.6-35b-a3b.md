# 평가 v2 (시나리오 단위) — Qwen3.6-35B-A3B-NVFP4_or500_seed42_20261002-203606

라벨 theta_primary · 첫 판정 t₀ = 55 · Δ = 5, w = 0, H = 40, k = 1 · 첫 경보 원칙 (t₀ 이후 첫 경보, 오염 전 포함) · ERROR 는 경보 아님 (오류율 0.0000) · 규약 docs/eval_v2_scenario.md

시나리오 500 = 저하 159 + 비저하 341 · unit 20 · 판정 로그가 창 끝에 못 미친 시나리오 0

## 1. 메인 표 (기준선 고정)

| method | n_degraded | detection_rate | pre_contam_rate | pre_degr_rate | miss_rate | delay_median | n_nondegraded | scenario_FAR | FAR_clean | FAR_contam | isolation_rate |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 항상 0 | 159 | 0 | 0 | 0 | 1 |  | 341 | 0 | 0 | 0 |  |
| 항상 1 | 159 | 0 | 1 | 0 | 0 |  | 341 | 1 | 1 | 0 |  |
| 무작위 p=0.169 (에이전트 경보율) | 159 | 0.001 | 0.996 | 0.002 | 0.000 | 1.800 | 341 | 1 | 0.998 | 0.002 | 0 |
| 무작위 p=0.050 | 159 | 0.018 | 0.892 | 0.045 | 0.045 | 2.042 | 341 | 0.991 | 0.936 | 0.055 | 0 |
| LLM Agent | 159 | 0.126 | 0.597 | 0.189 | 0.088 | 2 | 341 | 0.988 | 0.795 | 0.194 | 0.850 |

## 2. unit bootstrap 95% CI (2000회)

| metric | point | lo | hi |
|---|---|---|---|
| detection_rate | 0.126 | 0.073 | 0.185 |
| pre_contam_rate | 0.597 | 0.492 | 0.697 |
| pre_degr_rate | 0.189 | 0.104 | 0.272 |
| miss_rate | 0.088 | 0.031 | 0.166 |
| scenario_FAR | 0.988 | 0.977 | 0.997 |
| isolation_rate | 0.850 | 0.700 | 1 |

## 3. 유형별

| type | n_degraded | detection_rate | pre_contam_rate | pre_degr_rate | miss_rate | delay_median | n_nondegraded | scenario_FAR | FAR_clean | FAR_contam | isolation_rate |
|---|---|---|---|---|---|---|---|---|---|---|---|
| bias | 22 | 0.091 | 0.500 | 0.182 | 0.227 | 4 | 62 | 0.952 | 0.823 | 0.129 | 0.500 |
| gain | 16 | 0.062 | 0.562 | 0.312 | 0.062 | 1 | 68 | 1 | 0.779 | 0.221 | 1 |
| multi_C | 46 | 0.239 | 0.587 | 0.109 | 0.065 | 2 | 37 | 0.973 | 0.892 | 0.081 | 0.909 |
| multi_I | 17 | 0.176 | 0.471 | 0.118 | 0.235 | 2 | 66 | 1 | 0.773 | 0.227 | 0.667 |
| noise | 32 | 0.062 | 0.719 | 0.219 | 0 | 0 | 51 | 1 | 0.804 | 0.196 | 1 |
| stuck | 26 | 0.038 | 0.654 | 0.269 | 0.038 | 0 | 57 | 1 | 0.737 | 0.263 | 1 |

## 4. 센서별

| sensor | n_degraded | detection_rate | pre_contam_rate | pre_degr_rate | miss_rate | delay_median | n_nondegraded | scenario_FAR | FAR_clean | FAR_contam | isolation_rate |
|---|---|---|---|---|---|---|---|---|---|---|---|
| T24 | 43 | 0.070 | 0.698 | 0.186 | 0.047 | 0 | 69 | 0.986 | 0.797 | 0.188 | 0.667 |
| T24+T30+T50 | 63 | 0.222 | 0.556 | 0.111 | 0.111 | 2 | 103 | 0.990 | 0.816 | 0.175 | 0.857 |
| T30 | 2 | 0 | 0.500 | 0.500 | 0 |  | 108 | 0.981 | 0.713 | 0.269 |  |
| T50 | 51 | 0.059 | 0.569 | 0.275 | 0.098 | 1 | 61 | 1 | 0.902 | 0.098 | 1 |

## 5. 오염 시점별

| timing_p | n_degraded | detection_rate | pre_contam_rate | pre_degr_rate | miss_rate | delay_median | n_nondegraded | scenario_FAR | FAR_clean | FAR_contam | isolation_rate |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.200 | 64 | 0.281 | 0.172 | 0.359 | 0.188 | 2 | 60 | 0.933 | 0.100 | 0.833 | 0.833 |
| 0.400 | 62 | 0.032 | 0.839 | 0.113 | 0.016 | 2 | 63 | 1 | 0.746 | 0.254 | 1 |
| 0.600 | 32 | 0 | 0.969 | 0 | 0.031 |  | 94 | 1 | 1 | 0 |  |
| 0.800 | 1 | 0 | 1 | 0 | 0 |  | 124 | 1 | 1 | 0 |  |

### 오염 전 경보율 (저하·비저하 합산, 오염 전 구간 길이 = τ_s − 55)

| timing_p | n | pre_len_median | pre_contam_rate |
|---|---|---|---|
| 0.200 | 124 | 29 | 0.137 |
| 0.400 | 125 | 58 | 0.792 |
| 0.600 | 126 | 86 | 0.992 |
| 0.800 | 125 | 115 | 1 |

## 6. 저하 시나리오 상세

| unit | scenario_id | type | sensor | tau_s | tau_d | window_lo | window_hi | t_hat | result | delay | iso_hit |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | bias_T50_a1.0_pos_p0.2 | bias | T50 | 82 | 90 | 90 | 95 | 87 | PreDegr |  |  |
| 1 | gain_T24_a2.0_pos_p0.4 | gain | T24 | 110 | 138 | 138 | 143 | 96 | PreContam |  |  |
| 1 | multiC_T24+T30+T50_a0.3_na_p0.2 | multi_C | T24+T30+T50 | 82 | 92 | 92 | 97 | 93 | TP | 1 | True |
| 1 | multiC_T24+T30+T50_a0.3_na_p0.4 | multi_C | T24+T30+T50 | 110 | 117 | 117 | 122 | 96 | PreContam |  |  |
| 1 | multiC_T24+T30+T50_a0.5_na_p0.2 | multi_C | T24+T30+T50 | 82 | 90 | 90 | 95 | 87 | PreDegr |  |  |
| 1 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 137 | 143 | 143 | 148 | 96 | PreContam |  |  |
| 1 | multiI_T24+T30+T50_a0.3_na_p0.2 | multi_I | T24+T30+T50 | 82 | 93 | 93 | 98 | 90 | PreDegr |  |  |
| 1 | noise_T24_b2.0_na_p0.6 | noise | T24 | 137 | 152 | 152 | 157 | 96 | PreContam |  |  |
| 1 | noise_T50_b2.0_na_p0.2 | noise | T50 | 82 | 105 | 105 | 110 | 83 | PreDegr |  |  |
| 1 | stuck_T24_na_na_p0.6 | stuck | T24 | 137 | 148 | 148 | 153 | 96 | PreContam |  |  |
| 1 | stuck_T50_na_na_p0.4 | stuck | T50 | 110 | 116 | 116 | 121 | 96 | PreContam |  |  |
| 1 | stuck_T50_na_na_p0.6 | stuck | T50 | 137 | 155 | 155 | 160 | 96 | PreContam |  |  |
| 9 | bias_T24_a0.75_neg_p0.4 | bias | T24 | 113 | 121 | 121 | 126 | 110 | PreContam |  |  |
| 9 | gain_T50_a2.0_pos_p0.2 | gain | T50 | 84 | 110 | 110 | 115 | 87 | PreDegr |  |  |
| 9 | multiC_T24+T30+T50_a0.3_na_p0.2 | multi_C | T24+T30+T50 | 84 | 101 | 101 | 106 | 105 | TP | 4 | True |
| 9 | multiC_T24+T30+T50_a0.5_na_p0.4 | multi_C | T24+T30+T50 | 113 | 117 | 117 | 122 | 110 | PreContam |  |  |
| 9 | noise_T24_b2.0_na_p0.4 | noise | T24 | 113 | 159 | 159 | 164 | 110 | PreContam |  |  |
| 9 | stuck_T24_na_na_p0.2 | stuck | T24 | 84 | 123 | 123 | 128 | 110 | PreDegr |  |  |
| 10 | bias_T50_a0.5_pos_p0.4 | bias | T50 | 122 | 146 | 146 | 151 | 112 | PreContam |  |  |
| 10 | gain_T50_a1.5_pos_p0.2 | gain | T50 | 88 | 122 | 122 | 127 | 95 | PreDegr |  |  |
| 10 | multiC_T24+T30+T50_a0.3_na_p0.4 | multi_C | T24+T30+T50 | 122 | 132 | 132 | 137 | 112 | PreContam |  |  |
| 10 | multiC_T24+T30+T50_a0.5_na_p0.2 | multi_C | T24+T30+T50 | 88 | 104 | 104 | 109 | 88 | PreDegr |  |  |
| 10 | multiI_T24+T30+T50_a0.5_na_p0.4 | multi_I | T24+T30+T50 | 122 | 127 | 127 | 132 | 112 | PreContam |  |  |
| 10 | noise_T24_b3.0_na_p0.6 | noise | T24 | 155 | 159 | 159 | 164 | 112 | PreContam |  |  |
| 10 | noise_T50_b1.0_na_p0.4 | noise | T50 | 122 | 125 | 125 | 130 | 112 | PreContam |  |  |
| 10 | stuck_T50_na_na_p0.2 | stuck | T50 | 88 | 145 | 145 | 150 | 95 | PreDegr |  |  |
| 11 | bias_T50_a0.5_pos_p0.4 | bias | T50 | 129 | 136 | 136 | 141 | 132 | PreDegr |  |  |
| 11 | bias_T50_a1.0_pos_p0.2 | bias | T50 | 92 | 117 | 117 | 122 | 109 | PreDegr |  |  |
| 11 | gain_T24_a1.5_pos_p0.6 | gain | T24 | 166 | 197 | 197 | 202 | 136 | PreContam |  |  |
| 11 | multiC_T24+T30+T50_a0.3_na_p0.2 | multi_C | T24+T30+T50 | 92 | 134 | 134 | 139 | 125 | PreDegr |  |  |
| 11 | multiC_T24+T30+T50_a0.3_na_p0.4 | multi_C | T24+T30+T50 | 129 | 135 | 135 | 140 | 132 | PreDegr |  |  |
| 11 | multiC_T24+T30+T50_a0.5_na_p0.2 | multi_C | T24+T30+T50 | 92 | 117 | 117 | 122 | 124 | Miss |  |  |
| 11 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 166 | 172 | 172 | 177 | 132 | PreContam |  |  |
| 11 | multiI_T24+T30+T50_a0.3_na_p0.2 | multi_I | T24+T30+T50 | 92 | 122 | 122 | 127 | 124 | TP | 2 | True |
| 11 | noise_T50_b2.0_na_p0.6 | noise | T50 | 166 | 205 | 205 | 210 | 132 | PreContam |  |  |
| 11 | noise_T50_b3.0_na_p0.6 | noise | T50 | 166 | 171 | 171 | 176 | 132 | PreContam |  |  |
| 11 | stuck_T24_na_na_p0.4 | stuck | T24 | 129 | 134 | 134 | 139 | 132 | PreDegr |  |  |
| 11 | stuck_T50_na_na_p0.6 | stuck | T50 | 166 | 181 | 181 | 186 | 132 | PreContam |  |  |
| 17 | bias_T50_a0.75_pos_p0.4 | bias | T50 | 143 | 146 | 146 | 151 | 150 | TP | 4 | True |
| 17 | gain_T50_a1.5_pos_p0.2 | gain | T50 | 99 | 139 | 139 | 144 | 118 | PreDegr |  |  |
| 17 | multiC_T24+T30+T50_a0.5_na_p0.2 | multi_C | T24+T30+T50 | 99 | 111 | 111 | 116 | 115 | TP | 4 | True |
| 17 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 188 | 192 | 192 | 197 | 165 | PreContam |  |  |
| 17 | multiI_T24+T30+T50_a0.5_na_p0.2 | multi_I | T24+T30+T50 | 99 | 147 | 147 | 152 | 166 | Miss |  |  |
| 17 | noise_T24_b1.0_na_p0.2 | noise | T24 | 99 | 140 | 140 | 145 | 127 | PreDegr |  |  |
| 17 | noise_T24_b3.0_na_p0.6 | noise | T24 | 188 | 190 | 190 | 195 | 156 | PreContam |  |  |
| 17 | noise_T50_b1.0_na_p0.2 | noise | T50 | 99 | 162 | 162 | 167 | 118 | PreDegr |  |  |
| 17 | noise_T50_b3.0_na_p0.2 | noise | T50 | 99 | 110 | 110 | 115 | 100 | PreDegr |  |  |
| 17 | stuck_T50_na_na_p0.2 | stuck | T50 | 99 | 186 | 186 | 191 | 119 | PreDegr |  |  |
| 17 | stuck_T50_na_na_p0.4 | stuck | T50 | 143 | 213 | 213 | 218 | 153 | PreDegr |  |  |
| 26 | bias_T24_a1.0_neg_p0.2 | bias | T24 | 84 | 89 | 89 | 94 | 81 | PreContam |  |  |
| 26 | bias_T24_a1.0_neg_p0.6 | bias | T24 | 141 | 147 | 147 | 152 | 163 | Miss |  |  |
| 26 | bias_T50_a1.0_neg_p0.4 | bias | T50 | 113 | 116 | 116 | 121 | 81 | PreContam |  |  |
| 26 | gain_T24_a2.0_pos_p0.2 | gain | T24 | 84 | 100 | 100 | 105 | 81 | PreContam |  |  |
| 26 | multiC_T24+T30+T50_a0.3_na_p0.4 | multi_C | T24+T30+T50 | 113 | 117 | 117 | 122 | 81 | PreContam |  |  |
| 26 | multiI_T24+T30+T50_a0.3_na_p0.4 | multi_I | T24+T30+T50 | 113 | 123 | 123 | 128 | 81 | PreContam |  |  |
| 26 | noise_T24_b3.0_na_p0.6 | noise | T24 | 141 | 177 | 177 | 182 | 81 | PreContam |  |  |
| 26 | noise_T50_b1.0_na_p0.4 | noise | T50 | 113 | 131 | 131 | 136 | 81 | PreContam |  |  |
| 26 | stuck_T24_na_na_p0.2 | stuck | T24 | 84 | 136 | 136 | 141 | 81 | PreContam |  |  |
| 32 | bias_T24_a1.0_neg_p0.2 | bias | T24 | 82 | 85 | 85 | 90 | 72 | PreContam |  |  |
| 32 | bias_T50_a0.75_neg_p0.4 | bias | T50 | 109 | 123 | 123 | 128 | 72 | PreContam |  |  |
| 32 | gain_T50_a2.0_pos_p0.4 | gain | T50 | 109 | 111 | 111 | 116 | 72 | PreContam |  |  |
| 32 | multiC_T24+T30+T50_a0.3_na_p0.2 | multi_C | T24+T30+T50 | 82 | 86 | 86 | 91 | 72 | PreContam |  |  |
| 32 | multiC_T24+T30+T50_a0.3_na_p0.4 | multi_C | T24+T30+T50 | 109 | 122 | 122 | 127 | 72 | PreContam |  |  |
| 32 | multiC_T24+T30+T50_a0.5_na_p0.4 | multi_C | T24+T30+T50 | 109 | 114 | 114 | 119 | 72 | PreContam |  |  |
| 32 | noise_T24_b2.0_na_p0.2 | noise | T24 | 82 | 82 | 82 | 87 | 72 | PreContam |  |  |
| 32 | noise_T50_b2.0_na_p0.2 | noise | T50 | 82 | 87 | 87 | 92 | 72 | PreContam |  |  |
| 48 | bias_T50_a0.5_neg_p0.2 | bias | T50 | 90 | 104 | 104 | 109 | 156 | Miss |  |  |
| 48 | gain_T50_a1.5_pos_p0.2 | gain | T50 | 90 | 99 | 99 | 104 | 100 | TP | 1 | True |
| 48 | multiC_T24+T30+T50_a0.3_na_p0.4 | multi_C | T24+T30+T50 | 125 | 134 | 134 | 139 | 111 | PreContam |  |  |
| 48 | multiC_T24+T30+T50_a0.5_na_p0.2 | multi_C | T24+T30+T50 | 90 | 94 | 94 | 99 | 99 | TP | 5 | True |
| 48 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 161 | 169 | 169 | 174 | 111 | PreContam |  |  |
| 48 | multiI_T24+T30+T50_a0.3_na_p0.2 | multi_I | T24+T30+T50 | 90 | 99 | 99 | 104 | 99 | TP | 0 | True |
| 48 | multiI_T24+T30+T50_a0.3_na_p0.4 | multi_I | T24+T30+T50 | 125 | 139 | 139 | 144 | 111 | PreContam |  |  |
| 48 | multiI_T24+T30+T50_a0.5_na_p0.2 | multi_I | T24+T30+T50 | 90 | 96 | 96 | 101 | 98 | TP | 2 | False |
| 48 | multiI_T24+T30+T50_a0.5_na_p0.4 | multi_I | T24+T30+T50 | 125 | 132 | 132 | 137 | 111 | PreContam |  |  |
| 48 | stuck_T24_na_na_p0.4 | stuck | T24 | 125 | 190 | 190 | 195 | 111 | PreContam |  |  |
| 48 | stuck_T50_na_na_p0.4 | stuck | T50 | 125 | 145 | 145 | 150 | 111 | PreContam |  |  |
| 49 | bias_T24_a0.5_neg_p0.4 | bias | T24 | 119 | 127 | 127 | 132 | 101 | PreContam |  |  |
| 49 | bias_T24_a0.5_pos_p0.4 | bias | T24 | 119 | 129 | 129 | 134 | 113 | PreContam |  |  |
| 49 | gain_T24_a2.0_pos_p0.4 | gain | T24 | 119 | 126 | 126 | 131 | 101 | PreContam |  |  |
| 49 | multiC_T24+T30+T50_a0.3_na_p0.4 | multi_C | T24+T30+T50 | 119 | 128 | 128 | 133 | 101 | PreContam |  |  |
| 49 | multiC_T24+T30+T50_a0.5_na_p0.2 | multi_C | T24+T30+T50 | 87 | 94 | 94 | 99 | 105 | Miss |  |  |
| 49 | noise_T24_b3.0_na_p0.2 | noise | T24 | 87 | 97 | 97 | 102 | 88 | PreDegr |  |  |
| 49 | noise_T50_b3.0_na_p0.4 | noise | T50 | 119 | 132 | 132 | 137 | 101 | PreContam |  |  |
| 49 | stuck_T24_na_na_p0.4 | stuck | T24 | 119 | 128 | 128 | 133 | 101 | PreContam |  |  |
| 49 | stuck_T24_na_na_p0.8 | stuck | T24 | 183 | 199 | 199 | 204 | 101 | PreContam |  |  |
| 49 | stuck_T50_na_na_p0.6 | stuck | T50 | 151 | 166 | 166 | 171 | 101 | PreContam |  |  |
| 52 | bias_T50_a0.75_pos_p0.4 | bias | T50 | 118 | 123 | 123 | 128 | 96 | PreContam |  |  |
| 52 | bias_T50_a1.0_pos_p0.4 | bias | T50 | 118 | 122 | 122 | 127 | 96 | PreContam |  |  |
| 52 | gain_T24_a1.0_pos_p0.4 | gain | T24 | 118 | 133 | 133 | 138 | 96 | PreContam |  |  |
| 52 | gain_T50_a2.0_pos_p0.4 | gain | T50 | 118 | 122 | 122 | 127 | 96 | PreContam |  |  |
| 52 | multiC_T24+T30+T50_a0.3_na_p0.2 | multi_C | T24+T30+T50 | 87 | 92 | 92 | 97 | 94 | TP | 2 | True |
| 52 | multiC_T24+T30+T50_a0.3_na_p0.4 | multi_C | T24+T30+T50 | 118 | 125 | 125 | 130 | 96 | PreContam |  |  |
| 52 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 150 | 154 | 154 | 159 | 96 | PreContam |  |  |
| 52 | noise_T24_b3.0_na_p0.2 | noise | T24 | 87 | 87 | 87 | 92 | 87 | TP | 0 | True |
| 57 | bias_T50_a0.75_neg_p0.2 | bias | T50 | 71 | 78 | 78 | 83 | 63 | PreContam |  |  |
| 57 | multiC_T24+T30+T50_a0.3_na_p0.2 | multi_C | T24+T30+T50 | 71 | 84 | 84 | 89 | 63 | PreContam |  |  |
| 57 | multiC_T24+T30+T50_a0.5_na_p0.4 | multi_C | T24+T30+T50 | 88 | 91 | 91 | 96 | 63 | PreContam |  |  |
| 57 | noise_T50_b2.0_na_p0.2 | noise | T50 | 71 | 75 | 75 | 80 | 63 | PreContam |  |  |
| 57 | noise_T50_b3.0_na_p0.2 | noise | T50 | 71 | 74 | 74 | 79 | 63 | PreContam |  |  |
| 57 | noise_T50_b3.0_na_p0.4 | noise | T50 | 88 | 89 | 89 | 94 | 63 | PreContam |  |  |
| 63 | bias_T24_a1.0_neg_p0.4 | bias | T24 | 103 | 106 | 106 | 111 | 119 | Miss |  |  |
| 63 | bias_T50_a1.0_pos_p0.2 | bias | T50 | 79 | 84 | 84 | 89 | 90 | Miss |  |  |
| 63 | multiC_T24+T30+T50_a0.3_na_p0.2 | multi_C | T24+T30+T50 | 79 | 89 | 89 | 94 |  | Miss |  |  |
| 63 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 126 | 135 | 135 | 140 | 106 | PreContam |  |  |
| 63 | multiI_T24+T30+T50_a0.3_na_p0.2 | multi_I | T24+T30+T50 | 79 | 89 | 89 | 94 | 113 | Miss |  |  |
| 63 | multiI_T24+T30+T50_a0.3_na_p0.4 | multi_I | T24+T30+T50 | 103 | 132 | 132 | 137 | 113 | PreDegr |  |  |
| 63 | multiI_T24+T30+T50_a0.5_na_p0.6 | multi_I | T24+T30+T50 | 126 | 135 | 135 | 140 | 106 | PreContam |  |  |
| 63 | stuck_T50_na_na_p0.2 | stuck | T50 | 79 | 98 | 98 | 103 | 107 | Miss |  |  |
| 64 | gain_T24_a1.5_pos_p0.4 | gain | T24 | 146 | 185 | 185 | 190 | 110 | PreContam |  |  |
| 64 | multiC_T24+T30+T50_a0.5_na_p0.2 | multi_C | T24+T30+T50 | 101 | 106 | 106 | 111 | 108 | TP | 2 | True |
| 64 | multiC_T24+T30+T50_a0.5_na_p0.4 | multi_C | T24+T30+T50 | 146 | 152 | 152 | 157 | 101 | PreContam |  |  |
| 64 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 192 | 197 | 197 | 202 | 101 | PreContam |  |  |
| 64 | multiI_T24+T30+T50_a0.3_na_p0.4 | multi_I | T24+T30+T50 | 146 | 154 | 154 | 159 | 101 | PreContam |  |  |
| 64 | multiI_T24+T30+T50_a0.5_na_p0.6 | multi_I | T24+T30+T50 | 192 | 197 | 197 | 202 | 101 | PreContam |  |  |
| 64 | noise_T24_b3.0_na_p0.2 | noise | T24 | 101 | 104 | 104 | 109 | 101 | PreDegr |  |  |
| 64 | noise_T24_b3.0_na_p0.4 | noise | T24 | 146 | 182 | 182 | 187 | 101 | PreContam |  |  |
| 64 | noise_T24_b3.0_na_p0.6 | noise | T24 | 192 | 195 | 195 | 200 | 101 | PreContam |  |  |
| 64 | noise_T50_b2.0_na_p0.6 | noise | T50 | 192 | 207 | 207 | 212 | 101 | PreContam |  |  |
| 64 | stuck_T24_na_na_p0.2 | stuck | T24 | 101 | 187 | 187 | 192 | 101 | PreDegr |  |  |
| 64 | stuck_T50_na_na_p0.4 | stuck | T50 | 146 | 162 | 162 | 167 | 101 | PreContam |  |  |
| 65 | gain_T50_a1.5_pos_p0.2 | gain | T50 | 75 | 82 | 82 | 87 | 92 | Miss |  |  |
| 65 | multiC_T24+T30+T50_a0.5_na_p0.4 | multi_C | T24+T30+T50 | 94 | 97 | 97 | 102 | 83 | PreContam |  |  |
| 65 | noise_T24_b3.0_na_p0.4 | noise | T24 | 94 | 96 | 96 | 101 | 83 | PreContam |  |  |
| 65 | noise_T30_b3.0_na_p0.2 | noise | T30 | 75 | 120 | 120 | 125 | 75 | PreDegr |  |  |
| 67 | bias_T24_a1.0_pos_p0.2 | bias | T24 | 107 | 118 | 118 | 123 | 122 | TP | 4 | False |
| 67 | gain_T24_a0.75_neg_p0.2 | gain | T24 | 107 | 190 | 190 | 195 | 122 | PreDegr |  |  |
| 67 | multiC_T24+T30+T50_a0.3_na_p0.4 | multi_C | T24+T30+T50 | 158 | 178 | 178 | 183 | 134 | PreContam |  |  |
| 67 | multiC_T24+T30+T50_a0.5_na_p0.2 | multi_C | T24+T30+T50 | 107 | 115 | 115 | 120 | 120 | TP | 5 | True |
| 67 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 210 | 214 | 214 | 219 | 131 | PreContam |  |  |
| 67 | noise_T50_b2.0_na_p0.6 | noise | T50 | 210 | 218 | 218 | 223 | 131 | PreContam |  |  |
| 67 | stuck_T24_na_na_p0.6 | stuck | T24 | 210 | 261 | 261 | 266 | 131 | PreContam |  |  |
| 67 | stuck_T50_na_na_p0.2 | stuck | T50 | 107 | 128 | 128 | 133 | 121 | PreDegr |  |  |
| 67 | stuck_T50_na_na_p0.4 | stuck | T50 | 158 | 190 | 190 | 195 | 131 | PreContam |  |  |
| 68 | bias_T50_a0.3_neg_p0.2 | bias | T50 | 84 | 113 | 113 | 118 | 110 | PreDegr |  |  |
| 68 | gain_T24_a1.0_pos_p0.4 | gain | T24 | 113 | 135 | 135 | 140 | 125 | PreDegr |  |  |
| 68 | multiC_T24+T30+T50_a0.3_na_p0.4 | multi_C | T24+T30+T50 | 113 | 121 | 121 | 126 | 120 | PreDegr |  |  |
| 68 | multiC_T24+T30+T50_a0.5_na_p0.2 | multi_C | T24+T30+T50 | 84 | 88 | 88 | 93 | 91 | TP | 3 | True |
| 68 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 141 | 147 | 147 | 152 | 126 | PreContam |  |  |
| 68 | noise_T50_b3.0_na_p0.6 | noise | T50 | 141 | 144 | 144 | 149 | 126 | PreContam |  |  |
| 68 | stuck_T24_na_na_p0.2 | stuck | T24 | 84 | 93 | 93 | 98 | 93 | TP | 0 | True |
| 70 | noise_T50_b2.0_na_p0.6 | noise | T50 | 104 | 105 | 105 | 110 | 96 | PreContam |  |  |
| 70 | noise_T50_b3.0_na_p0.4 | noise | T50 | 88 | 89 | 89 | 94 | 89 | TP | 0 | True |
| 79 | multiC_T24+T30+T50_a0.3_na_p0.2 | multi_C | T24+T30+T50 | 84 | 92 | 92 | 97 | 92 | TP | 0 | False |
| 79 | stuck_T24_na_na_p0.6 | stuck | T24 | 141 | 156 | 156 | 161 | 99 | PreContam |  |  |
| 85 | bias_T50_a0.75_neg_p0.2 | bias | T50 | 82 | 85 | 85 | 90 | 116 | Miss |  |  |
| 85 | gain_T24_a2.0_pos_p0.6 | gain | T24 | 135 | 149 | 149 | 154 | 94 | PreContam |  |  |
| 85 | multiC_T24+T30+T50_a0.3_na_p0.4 | multi_C | T24+T30+T50 | 108 | 126 | 126 | 131 | 94 | PreContam |  |  |
| 85 | multiC_T24+T30+T50_a0.5_na_p0.4 | multi_C | T24+T30+T50 | 108 | 111 | 111 | 116 | 88 | PreContam |  |  |
| 85 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 135 | 141 | 141 | 146 | 94 | PreContam |  |  |
| 85 | multiI_T24+T30+T50_a0.3_na_p0.2 | multi_I | T24+T30+T50 | 82 | 87 | 87 | 92 | 122 | Miss |  |  |
| 85 | multiI_T24+T30+T50_a0.3_na_p0.4 | multi_I | T24+T30+T50 | 108 | 116 | 116 | 121 | 94 | PreContam |  |  |
| 85 | multiI_T24+T30+T50_a0.5_na_p0.2 | multi_I | T24+T30+T50 | 82 | 84 | 84 | 89 | 112 | Miss |  |  |
| 85 | stuck_T24_na_na_p0.4 | stuck | T24 | 108 | 148 | 148 | 153 | 94 | PreContam |  |  |
| 85 | stuck_T50_na_na_p0.4 | stuck | T50 | 108 | 116 | 116 | 121 | 94 | PreContam |  |  |
| 90 | multiC_T24+T30+T50_a0.3_na_p0.2 | multi_C | T24+T30+T50 | 75 | 80 | 80 | 85 | 80 | TP | 0 | True |
| 90 | multiC_T24+T30+T50_a0.5_na_p0.2 | multi_C | T24+T30+T50 | 75 | 78 | 78 | 83 | 78 | TP | 0 | True |
| 90 | noise_T30_b3.0_na_p0.4 | noise | T30 | 95 | 103 | 103 | 108 | 86 | PreContam |  |  |
| 90 | stuck_T24_na_na_p0.4 | stuck | T24 | 95 | 110 | 110 | 115 | 86 | PreContam |  |  |

## 7. 비저하 시나리오 상세

| unit | scenario_id | type | sensor | tau_s | window_hi | t_hat | result |
|---|---|---|---|---|---|---|---|
| 1 | bias_T24_a0.3_neg_p0.6 | bias | T24 | 137 | 177 | 96 | FP_clean |
| 1 | bias_T24_a0.3_neg_p0.8 | bias | T24 | 165 | 192 | 96 | FP_clean |
| 1 | bias_T24_a0.5_neg_p0.8 | bias | T24 | 165 | 192 | 96 | FP_clean |
| 1 | gain_T24_a0.25_neg_p0.2 | gain | T24 | 82 | 122 | 88 | FP_contam |
| 1 | gain_T24_a0.75_neg_p0.8 | gain | T24 | 165 | 192 | 96 | FP_clean |
| 1 | gain_T30_a1.0_pos_p0.6 | gain | T30 | 137 | 177 | 95 | FP_clean |
| 1 | multiI_T24+T30+T50_a0.3_na_p0.8 | multi_I | T24+T30+T50 | 165 | 192 | 96 | FP_clean |
| 1 | multiI_T24+T30+T50_a0.5_na_p0.2 | multi_I | T24+T30+T50 | 82 | 122 | 91 | FP_contam |
| 1 | multiI_T24+T30+T50_a0.5_na_p0.4 | multi_I | T24+T30+T50 | 110 | 150 | 96 | FP_clean |
| 1 | multiI_T24+T30+T50_a0.5_na_p0.8 | multi_I | T24+T30+T50 | 165 | 192 | 96 | FP_clean |
| 1 | noise_T30_b3.0_na_p0.4 | noise | T30 | 110 | 150 | 96 | FP_clean |
| 1 | noise_T30_b3.0_na_p0.8 | noise | T30 | 165 | 192 | 96 | FP_clean |
| 1 | noise_T50_b1.0_na_p0.6 | noise | T50 | 137 | 177 | 96 | FP_clean |
| 1 | stuck_T24_na_na_p0.4 | stuck | T24 | 110 | 150 | 96 | FP_clean |
| 1 | stuck_T24_na_na_p0.8 | stuck | T24 | 165 | 192 | 96 | FP_clean |
| 9 | bias_T30_a0.75_neg_p0.6 | bias | T30 | 143 | 183 | 110 | FP_clean |
| 9 | bias_T30_a0.75_pos_p0.6 | bias | T30 | 143 | 183 | 110 | FP_clean |
| 9 | bias_T30_a1.0_neg_p0.6 | bias | T30 | 143 | 183 | 110 | FP_clean |
| 9 | gain_T30_a0.75_neg_p0.4 | gain | T30 | 113 | 153 | 110 | FP_clean |
| 9 | gain_T30_a2.0_pos_p0.2 | gain | T30 | 84 | 124 | 90 | FP_contam |
| 9 | gain_T50_a1.5_pos_p0.6 | gain | T50 | 143 | 183 | 122 | FP_clean |
| 9 | multiC_T24+T30+T50_a0.3_na_p0.8 | multi_C | T24+T30+T50 | 172 | 201 | 110 | FP_clean |
| 9 | multiC_T24+T30+T50_a0.5_na_p0.8 | multi_C | T24+T30+T50 | 172 | 201 | 110 | FP_clean |
| 9 | multiI_T24+T30+T50_a0.3_na_p0.4 | multi_I | T24+T30+T50 | 113 | 153 | 110 | FP_clean |
| 9 | multiI_T24+T30+T50_a0.3_na_p0.6 | multi_I | T24+T30+T50 | 143 | 183 | 110 | FP_clean |
| 9 | multiI_T24+T30+T50_a0.5_na_p0.6 | multi_I | T24+T30+T50 | 143 | 183 | 110 | FP_clean |
| 9 | multiI_T24+T30+T50_a0.5_na_p0.8 | multi_I | T24+T30+T50 | 172 | 201 | 110 | FP_clean |
| 9 | noise_T24_b1.0_na_p0.8 | noise | T24 | 172 | 201 | 110 | FP_clean |
| 9 | noise_T30_b1.0_na_p0.6 | noise | T30 | 143 | 183 | 110 | FP_clean |
| 9 | noise_T50_b3.0_na_p0.8 | noise | T50 | 172 | 201 | 110 | FP_clean |
| 9 | stuck_T30_na_na_p0.2 | stuck | T30 | 84 | 124 | 96 | FP_contam |
| 9 | stuck_T30_na_na_p0.8 | stuck | T30 | 172 | 201 | 110 | FP_clean |
| 9 | stuck_T50_na_na_p0.6 | stuck | T50 | 143 | 183 | 110 | FP_clean |
| 10 | bias_T24_a0.3_pos_p0.2 | bias | T24 | 88 | 128 | 131 | TN |
| 10 | bias_T24_a0.5_pos_p0.8 | bias | T24 | 189 | 222 | 88 | FP_clean |
| 10 | bias_T30_a1.0_neg_p0.2 | bias | T30 | 88 | 128 | 112 | FP_contam |
| 10 | gain_T24_a1.0_pos_p0.2 | gain | T24 | 88 | 128 | 95 | FP_contam |
| 10 | gain_T30_a0.75_neg_p0.6 | gain | T30 | 155 | 195 | 132 | FP_clean |
| 10 | gain_T50_a0.25_neg_p0.4 | gain | T50 | 122 | 162 | 112 | FP_clean |
| 10 | multiC_T24+T30+T50_a0.3_na_p0.8 | multi_C | T24+T30+T50 | 189 | 222 | 112 | FP_clean |
| 10 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 155 | 195 | 112 | FP_clean |
| 10 | multiC_T24+T30+T50_a0.5_na_p0.8 | multi_C | T24+T30+T50 | 189 | 222 | 112 | FP_clean |
| 10 | multiI_T24+T30+T50_a0.3_na_p0.8 | multi_I | T24+T30+T50 | 189 | 222 | 112 | FP_clean |
| 10 | multiI_T24+T30+T50_a0.5_na_p0.6 | multi_I | T24+T30+T50 | 155 | 195 | 112 | FP_clean |
| 10 | multiI_T24+T30+T50_a0.5_na_p0.8 | multi_I | T24+T30+T50 | 189 | 222 | 112 | FP_clean |
| 10 | noise_T24_b1.0_na_p0.4 | noise | T24 | 122 | 162 | 112 | FP_clean |
| 10 | noise_T50_b1.0_na_p0.2 | noise | T50 | 88 | 128 | 88 | FP_contam |
| 10 | stuck_T24_na_na_p0.8 | stuck | T24 | 189 | 222 | 112 | FP_clean |
| 10 | stuck_T30_na_na_p0.2 | stuck | T30 | 88 | 128 | 112 | FP_contam |
| 10 | stuck_T30_na_na_p0.4 | stuck | T30 | 122 | 162 | 112 | FP_clean |
| 11 | bias_T30_a0.5_pos_p0.4 | bias | T30 | 129 | 169 | 124 | FP_clean |
| 11 | bias_T30_a0.75_pos_p0.2 | bias | T30 | 92 | 132 | 137 | TN |
| 11 | gain_T30_a2.0_pos_p0.6 | gain | T30 | 166 | 206 | 132 | FP_clean |
| 11 | gain_T50_a0.5_neg_p0.8 | gain | T50 | 203 | 240 | 136 | FP_clean |
| 11 | gain_T50_a1.5_pos_p0.8 | gain | T50 | 203 | 240 | 134 | FP_clean |
| 11 | multiI_T24+T30+T50_a0.3_na_p0.4 | multi_I | T24+T30+T50 | 129 | 169 | 131 | FP_contam |
| 11 | multiI_T24+T30+T50_a0.5_na_p0.4 | multi_I | T24+T30+T50 | 129 | 169 | 137 | FP_contam |
| 11 | multiI_T24+T30+T50_a0.5_na_p0.8 | multi_I | T24+T30+T50 | 203 | 240 | 132 | FP_clean |
| 11 | noise_T30_b1.0_na_p0.8 | noise | T30 | 203 | 240 | 132 | FP_clean |
| 11 | noise_T30_b2.0_na_p0.2 | noise | T30 | 92 | 132 | 99 | FP_contam |
| 11 | noise_T30_b2.0_na_p0.8 | noise | T30 | 203 | 240 | 132 | FP_clean |
| 11 | stuck_T24_na_na_p0.6 | stuck | T24 | 166 | 206 | 132 | FP_clean |
| 11 | stuck_T30_na_na_p0.4 | stuck | T30 | 129 | 169 | 134 | FP_contam |
| 17 | bias_T24_a0.75_neg_p0.8 | bias | T24 | 232 | 272 | 165 | FP_clean |
| 17 | bias_T30_a0.3_pos_p0.4 | bias | T30 | 143 | 183 | 166 | FP_contam |
| 17 | bias_T30_a0.75_pos_p0.6 | bias | T30 | 188 | 228 | 156 | FP_clean |
| 17 | gain_T24_a1.0_pos_p0.2 | gain | T24 | 99 | 139 | 125 | FP_contam |
| 17 | gain_T24_a1.5_pos_p0.8 | gain | T24 | 232 | 272 | 156 | FP_clean |
| 17 | gain_T30_a1.0_pos_p0.8 | gain | T30 | 232 | 272 | 156 | FP_clean |
| 17 | gain_T50_a0.5_neg_p0.6 | gain | T50 | 188 | 228 | 164 | FP_clean |
| 17 | multiC_T24+T30+T50_a0.3_na_p0.8 | multi_C | T24+T30+T50 | 232 | 272 | 165 | FP_clean |
| 17 | multiC_T24+T30+T50_a0.5_na_p0.8 | multi_C | T24+T30+T50 | 232 | 272 | 156 | FP_clean |
| 17 | multiI_T24+T30+T50_a0.3_na_p0.2 | multi_I | T24+T30+T50 | 99 | 139 | 119 | FP_contam |
| 17 | multiI_T24+T30+T50_a0.5_na_p0.6 | multi_I | T24+T30+T50 | 188 | 228 | 156 | FP_clean |
| 17 | multiI_T24+T30+T50_a0.5_na_p0.8 | multi_I | T24+T30+T50 | 232 | 272 | 156 | FP_clean |
| 17 | stuck_T30_na_na_p0.4 | stuck | T30 | 143 | 183 | 148 | FP_contam |
| 17 | stuck_T50_na_na_p0.8 | stuck | T50 | 232 | 272 | 156 | FP_clean |
| 26 | bias_T30_a0.5_neg_p0.8 | bias | T30 | 170 | 199 | 97 | FP_clean |
| 26 | bias_T30_a0.5_pos_p0.6 | bias | T30 | 141 | 181 | 81 | FP_clean |
| 26 | gain_T24_a0.25_neg_p0.4 | gain | T24 | 113 | 153 | 81 | FP_clean |
| 26 | gain_T30_a0.75_neg_p0.8 | gain | T30 | 170 | 199 | 81 | FP_clean |
| 26 | gain_T50_a0.75_neg_p0.6 | gain | T50 | 141 | 181 | 81 | FP_clean |
| 26 | gain_T50_a0.75_neg_p0.8 | gain | T50 | 170 | 199 | 81 | FP_clean |
| 26 | multiC_T24+T30+T50_a0.3_na_p0.6 | multi_C | T24+T30+T50 | 141 | 181 | 81 | FP_clean |
| 26 | multiC_T24+T30+T50_a0.3_na_p0.8 | multi_C | T24+T30+T50 | 170 | 199 | 81 | FP_clean |
| 26 | multiC_T24+T30+T50_a0.5_na_p0.8 | multi_C | T24+T30+T50 | 170 | 199 | 81 | FP_clean |
| 26 | multiI_T24+T30+T50_a0.3_na_p0.6 | multi_I | T24+T30+T50 | 141 | 181 | 81 | FP_clean |
| 26 | multiI_T24+T30+T50_a0.3_na_p0.8 | multi_I | T24+T30+T50 | 170 | 199 | 81 | FP_clean |
| 26 | multiI_T24+T30+T50_a0.5_na_p0.4 | multi_I | T24+T30+T50 | 113 | 153 | 81 | FP_clean |
| 26 | noise_T24_b1.0_na_p0.6 | noise | T24 | 141 | 181 | 81 | FP_clean |
| 26 | noise_T30_b2.0_na_p0.4 | noise | T30 | 113 | 153 | 81 | FP_clean |
| 26 | stuck_T24_na_na_p0.6 | stuck | T24 | 141 | 181 | 81 | FP_clean |
| 26 | stuck_T30_na_na_p0.4 | stuck | T30 | 113 | 153 | 81 | FP_clean |
| 26 | stuck_T50_na_na_p0.8 | stuck | T50 | 170 | 199 | 81 | FP_clean |
| 32 | bias_T30_a0.3_neg_p0.2 | bias | T30 | 82 | 122 | 130 | TN |
| 32 | bias_T30_a1.0_neg_p0.2 | bias | T30 | 82 | 122 | 72 | FP_clean |
| 32 | gain_T30_a0.25_neg_p0.6 | gain | T30 | 137 | 177 | 72 | FP_clean |
| 32 | gain_T30_a0.75_neg_p0.4 | gain | T30 | 109 | 149 | 72 | FP_clean |
| 32 | gain_T30_a1.0_pos_p0.4 | gain | T30 | 109 | 149 | 72 | FP_clean |
| 32 | gain_T50_a0.75_neg_p0.6 | gain | T50 | 137 | 177 | 72 | FP_clean |
| 32 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 137 | 177 | 72 | FP_clean |
| 32 | multiI_T24+T30+T50_a0.3_na_p0.4 | multi_I | T24+T30+T50 | 109 | 149 | 72 | FP_clean |
| 32 | multiI_T24+T30+T50_a0.3_na_p0.6 | multi_I | T24+T30+T50 | 137 | 177 | 72 | FP_clean |
| 32 | multiI_T24+T30+T50_a0.5_na_p0.2 | multi_I | T24+T30+T50 | 82 | 122 | 72 | FP_clean |
| 32 | multiI_T24+T30+T50_a0.5_na_p0.8 | multi_I | T24+T30+T50 | 164 | 191 | 72 | FP_clean |
| 32 | noise_T30_b2.0_na_p0.8 | noise | T30 | 164 | 191 | 72 | FP_clean |
| 32 | noise_T50_b2.0_na_p0.8 | noise | T50 | 164 | 191 | 72 | FP_clean |
| 32 | stuck_T30_na_na_p0.2 | stuck | T30 | 82 | 122 | 72 | FP_clean |
| 32 | stuck_T30_na_na_p0.6 | stuck | T30 | 137 | 177 | 72 | FP_clean |
| 32 | stuck_T30_na_na_p0.8 | stuck | T30 | 164 | 191 | 72 | FP_clean |
| 32 | stuck_T50_na_na_p0.4 | stuck | T50 | 109 | 149 | 72 | FP_clean |
| 48 | bias_T24_a0.3_neg_p0.4 | bias | T24 | 125 | 165 | 111 | FP_clean |
| 48 | bias_T24_a0.3_neg_p0.6 | bias | T24 | 161 | 201 | 111 | FP_clean |
| 48 | bias_T50_a1.0_pos_p0.6 | bias | T50 | 161 | 201 | 99 | FP_clean |
| 48 | gain_T30_a0.5_neg_p0.6 | gain | T30 | 161 | 201 | 99 | FP_clean |
| 48 | gain_T50_a0.75_neg_p0.6 | gain | T50 | 161 | 201 | 111 | FP_clean |
| 48 | gain_T50_a2.0_pos_p0.8 | gain | T50 | 196 | 231 | 111 | FP_clean |
| 48 | multiC_T24+T30+T50_a0.3_na_p0.8 | multi_C | T24+T30+T50 | 196 | 231 | 111 | FP_clean |
| 48 | noise_T24_b1.0_na_p0.8 | noise | T24 | 196 | 231 | 111 | FP_clean |
| 48 | noise_T24_b2.0_na_p0.8 | noise | T24 | 196 | 231 | 111 | FP_clean |
| 48 | noise_T30_b1.0_na_p0.6 | noise | T30 | 161 | 201 | 111 | FP_clean |
| 48 | noise_T30_b2.0_na_p0.6 | noise | T30 | 161 | 201 | 111 | FP_clean |
| 48 | stuck_T24_na_na_p0.2 | stuck | T24 | 90 | 130 | 102 | FP_contam |
| 48 | stuck_T30_na_na_p0.6 | stuck | T30 | 161 | 201 | 111 | FP_clean |
| 49 | bias_T30_a0.5_pos_p0.4 | bias | T30 | 119 | 159 | 101 | FP_clean |
| 49 | bias_T50_a0.75_neg_p0.6 | bias | T50 | 151 | 191 | 113 | FP_clean |
| 49 | bias_T50_a0.75_pos_p0.8 | bias | T50 | 183 | 215 | 113 | FP_clean |
| 49 | gain_T24_a0.25_neg_p0.4 | gain | T24 | 119 | 159 | 113 | FP_clean |
| 49 | gain_T24_a0.5_pos_p0.6 | gain | T24 | 151 | 191 | 113 | FP_clean |
| 49 | gain_T30_a2.0_pos_p0.2 | gain | T30 | 87 | 127 | 93 | FP_contam |
| 49 | multiC_T24+T30+T50_a0.3_na_p0.6 | multi_C | T24+T30+T50 | 151 | 191 | 101 | FP_clean |
| 49 | multiC_T24+T30+T50_a0.3_na_p0.8 | multi_C | T24+T30+T50 | 183 | 215 | 101 | FP_clean |
| 49 | multiI_T24+T30+T50_a0.3_na_p0.6 | multi_I | T24+T30+T50 | 151 | 191 | 101 | FP_clean |
| 49 | multiI_T24+T30+T50_a0.3_na_p0.8 | multi_I | T24+T30+T50 | 183 | 215 | 101 | FP_clean |
| 49 | multiI_T24+T30+T50_a0.5_na_p0.2 | multi_I | T24+T30+T50 | 87 | 127 | 111 | FP_contam |
| 49 | multiI_T24+T30+T50_a0.5_na_p0.6 | multi_I | T24+T30+T50 | 151 | 191 | 101 | FP_clean |
| 49 | noise_T24_b2.0_na_p0.8 | noise | T24 | 183 | 215 | 101 | FP_clean |
| 49 | noise_T50_b1.0_na_p0.8 | noise | T50 | 183 | 215 | 101 | FP_clean |
| 49 | stuck_T30_na_na_p0.2 | stuck | T30 | 87 | 127 | 101 | FP_contam |
| 49 | stuck_T50_na_na_p0.2 | stuck | T50 | 87 | 127 | 99 | FP_contam |
| 52 | bias_T30_a0.75_pos_p0.8 | bias | T30 | 181 | 213 | 96 | FP_clean |
| 52 | bias_T30_a1.0_neg_p0.4 | bias | T30 | 118 | 158 | 96 | FP_clean |
| 52 | bias_T50_a0.3_pos_p0.8 | bias | T50 | 181 | 213 | 96 | FP_clean |
| 52 | gain_T30_a0.25_neg_p0.6 | gain | T30 | 150 | 190 | 96 | FP_clean |
| 52 | gain_T30_a0.5_neg_p0.6 | gain | T30 | 150 | 190 | 96 | FP_clean |
| 52 | multiC_T24+T30+T50_a0.5_na_p0.8 | multi_C | T24+T30+T50 | 181 | 213 | 96 | FP_clean |
| 52 | multiI_T24+T30+T50_a0.3_na_p0.4 | multi_I | T24+T30+T50 | 118 | 158 | 96 | FP_clean |
| 52 | multiI_T24+T30+T50_a0.3_na_p0.6 | multi_I | T24+T30+T50 | 150 | 190 | 96 | FP_clean |
| 52 | multiI_T24+T30+T50_a0.3_na_p0.8 | multi_I | T24+T30+T50 | 181 | 213 | 96 | FP_clean |
| 52 | multiI_T24+T30+T50_a0.5_na_p0.2 | multi_I | T24+T30+T50 | 87 | 127 | 96 | FP_contam |
| 52 | multiI_T24+T30+T50_a0.5_na_p0.6 | multi_I | T24+T30+T50 | 150 | 190 | 96 | FP_clean |
| 52 | noise_T24_b1.0_na_p0.4 | noise | T24 | 118 | 158 | 96 | FP_clean |
| 52 | noise_T24_b2.0_na_p0.8 | noise | T24 | 181 | 213 | 96 | FP_clean |
| 52 | noise_T50_b1.0_na_p0.8 | noise | T50 | 181 | 213 | 96 | FP_clean |
| 52 | stuck_T24_na_na_p0.6 | stuck | T24 | 150 | 190 | 96 | FP_clean |
| 52 | stuck_T24_na_na_p0.8 | stuck | T24 | 181 | 213 | 96 | FP_clean |
| 52 | stuck_T30_na_na_p0.2 | stuck | T30 | 87 | 127 | 94 | FP_contam |
| 52 | stuck_T50_na_na_p0.8 | stuck | T50 | 181 | 213 | 96 | FP_clean |
| 57 | bias_T30_a0.3_neg_p0.4 | bias | T30 | 88 | 128 | 63 | FP_clean |
| 57 | bias_T30_a0.5_neg_p0.2 | bias | T30 | 71 | 111 | 66 | FP_clean |
| 57 | bias_T30_a0.75_neg_p0.6 | bias | T30 | 104 | 137 | 63 | FP_clean |
| 57 | gain_T24_a0.25_neg_p0.4 | gain | T24 | 88 | 128 | 63 | FP_clean |
| 57 | gain_T30_a0.5_neg_p0.2 | gain | T30 | 71 | 111 | 63 | FP_clean |
| 57 | gain_T50_a0.5_neg_p0.8 | gain | T50 | 121 | 137 | 63 | FP_clean |
| 57 | gain_T50_a1.0_pos_p0.8 | gain | T50 | 121 | 137 | 63 | FP_clean |
| 57 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 104 | 137 | 63 | FP_clean |
| 57 | multiC_T24+T30+T50_a0.5_na_p0.8 | multi_C | T24+T30+T50 | 121 | 137 | 63 | FP_clean |
| 57 | multiI_T24+T30+T50_a0.3_na_p0.4 | multi_I | T24+T30+T50 | 88 | 128 | 63 | FP_clean |
| 57 | multiI_T24+T30+T50_a0.3_na_p0.8 | multi_I | T24+T30+T50 | 121 | 137 | 63 | FP_clean |
| 57 | multiI_T24+T30+T50_a0.5_na_p0.6 | multi_I | T24+T30+T50 | 104 | 137 | 63 | FP_clean |
| 57 | multiI_T24+T30+T50_a0.5_na_p0.8 | multi_I | T24+T30+T50 | 121 | 137 | 63 | FP_clean |
| 57 | noise_T30_b3.0_na_p0.4 | noise | T30 | 88 | 128 | 63 | FP_clean |
| 57 | stuck_T24_na_na_p0.6 | stuck | T24 | 104 | 137 | 63 | FP_clean |
| 57 | stuck_T30_na_na_p0.2 | stuck | T30 | 71 | 111 | 63 | FP_clean |
| 57 | stuck_T30_na_na_p0.4 | stuck | T30 | 88 | 128 | 63 | FP_clean |
| 57 | stuck_T50_na_na_p0.8 | stuck | T50 | 121 | 137 | 63 | FP_clean |
| 63 | bias_T24_a0.3_pos_p0.2 | bias | T24 | 79 | 119 | 105 | FP_contam |
| 63 | bias_T50_a0.5_pos_p0.8 | bias | T50 | 150 | 174 | 106 | FP_clean |
| 63 | gain_T24_a1.0_pos_p0.6 | gain | T24 | 126 | 166 | 106 | FP_clean |
| 63 | gain_T30_a0.25_neg_p0.8 | gain | T30 | 150 | 174 | 106 | FP_clean |
| 63 | gain_T50_a0.25_neg_p0.2 | gain | T50 | 79 | 119 | 106 | FP_contam |
| 63 | gain_T50_a2.0_pos_p0.8 | gain | T50 | 150 | 174 | 106 | FP_clean |
| 63 | multiC_T24+T30+T50_a0.3_na_p0.4 | multi_C | T24+T30+T50 | 103 | 143 | 115 | FP_contam |
| 63 | multiC_T24+T30+T50_a0.3_na_p0.8 | multi_C | T24+T30+T50 | 150 | 174 | 106 | FP_clean |
| 63 | multiI_T24+T30+T50_a0.3_na_p0.8 | multi_I | T24+T30+T50 | 150 | 174 | 106 | FP_clean |
| 63 | noise_T24_b1.0_na_p0.6 | noise | T24 | 126 | 166 | 106 | FP_clean |
| 63 | noise_T24_b3.0_na_p0.8 | noise | T24 | 150 | 174 | 106 | FP_clean |
| 63 | noise_T30_b2.0_na_p0.2 | noise | T30 | 79 | 119 | 85 | FP_contam |
| 63 | noise_T30_b2.0_na_p0.6 | noise | T30 | 126 | 166 | 106 | FP_clean |
| 63 | stuck_T24_na_na_p0.4 | stuck | T24 | 103 | 143 | 113 | FP_contam |
| 63 | stuck_T30_na_na_p0.6 | stuck | T30 | 126 | 166 | 106 | FP_clean |
| 63 | stuck_T50_na_na_p0.8 | stuck | T50 | 150 | 174 | 106 | FP_clean |
| 64 | bias_T24_a0.3_neg_p0.8 | bias | T24 | 237 | 277 | 110 | FP_clean |
| 64 | bias_T30_a0.3_neg_p0.4 | bias | T30 | 146 | 186 | 110 | FP_clean |
| 64 | bias_T30_a0.3_pos_p0.6 | bias | T30 | 192 | 232 | 101 | FP_clean |
| 64 | bias_T30_a1.0_pos_p0.6 | bias | T30 | 192 | 232 | 101 | FP_clean |
| 64 | gain_T30_a0.5_neg_p0.8 | gain | T30 | 237 | 277 | 110 | FP_clean |
| 64 | gain_T50_a0.75_neg_p0.4 | gain | T50 | 146 | 186 | 110 | FP_clean |
| 64 | gain_T50_a1.5_pos_p0.8 | gain | T50 | 237 | 277 | 101 | FP_clean |
| 64 | multiC_T24+T30+T50_a0.3_na_p0.8 | multi_C | T24+T30+T50 | 237 | 277 | 106 | FP_clean |
| 64 | multiI_T24+T30+T50_a0.3_na_p0.2 | multi_I | T24+T30+T50 | 101 | 141 | 106 | FP_contam |
| 64 | multiI_T24+T30+T50_a0.3_na_p0.6 | multi_I | T24+T30+T50 | 192 | 232 | 101 | FP_clean |
| 64 | noise_T30_b3.0_na_p0.2 | noise | T30 | 101 | 141 | 101 | FP_contam |
| 64 | stuck_T30_na_na_p0.2 | stuck | T30 | 101 | 141 | 101 | FP_contam |
| 64 | stuck_T50_na_na_p0.6 | stuck | T50 | 192 | 232 | 101 | FP_clean |
| 65 | bias_T24_a0.3_pos_p0.8 | bias | T24 | 133 | 153 | 83 | FP_clean |
| 65 | bias_T24_a0.75_pos_p0.8 | bias | T24 | 133 | 153 | 83 | FP_clean |
| 65 | bias_T30_a1.0_pos_p0.2 | bias | T30 | 75 | 115 | 83 | FP_contam |
| 65 | bias_T50_a0.5_pos_p0.8 | bias | T50 | 133 | 153 | 97 | FP_clean |
| 65 | gain_T24_a1.5_pos_p0.6 | gain | T24 | 114 | 153 | 83 | FP_clean |
| 65 | gain_T24_a2.0_pos_p0.6 | gain | T24 | 114 | 153 | 97 | FP_clean |
| 65 | gain_T30_a0.75_neg_p0.6 | gain | T30 | 114 | 153 | 97 | FP_clean |
| 65 | gain_T50_a0.25_neg_p0.4 | gain | T50 | 94 | 134 | 83 | FP_clean |
| 65 | multiC_T24+T30+T50_a0.3_na_p0.6 | multi_C | T24+T30+T50 | 114 | 153 | 83 | FP_clean |
| 65 | multiC_T24+T30+T50_a0.3_na_p0.8 | multi_C | T24+T30+T50 | 133 | 153 | 83 | FP_clean |
| 65 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 114 | 153 | 83 | FP_clean |
| 65 | multiC_T24+T30+T50_a0.5_na_p0.8 | multi_C | T24+T30+T50 | 133 | 153 | 83 | FP_clean |
| 65 | multiI_T24+T30+T50_a0.3_na_p0.8 | multi_I | T24+T30+T50 | 133 | 153 | 83 | FP_clean |
| 65 | multiI_T24+T30+T50_a0.5_na_p0.2 | multi_I | T24+T30+T50 | 75 | 115 | 98 | FP_contam |
| 65 | multiI_T24+T30+T50_a0.5_na_p0.6 | multi_I | T24+T30+T50 | 114 | 153 | 83 | FP_clean |
| 65 | multiI_T24+T30+T50_a0.5_na_p0.8 | multi_I | T24+T30+T50 | 133 | 153 | 83 | FP_clean |
| 65 | noise_T30_b2.0_na_p0.6 | noise | T30 | 114 | 153 | 83 | FP_clean |
| 65 | noise_T30_b3.0_na_p0.8 | noise | T30 | 133 | 153 | 83 | FP_clean |
| 65 | stuck_T24_na_na_p0.2 | stuck | T24 | 75 | 115 | 83 | FP_contam |
| 65 | stuck_T24_na_na_p0.8 | stuck | T24 | 133 | 153 | 83 | FP_clean |
| 65 | stuck_T30_na_na_p0.8 | stuck | T30 | 133 | 153 | 83 | FP_clean |
| 65 | stuck_T50_na_na_p0.6 | stuck | T50 | 114 | 153 | 83 | FP_clean |
| 65 | stuck_T50_na_na_p0.8 | stuck | T50 | 133 | 153 | 83 | FP_clean |
| 67 | bias_T24_a0.3_neg_p0.2 | bias | T24 | 107 | 147 | 130 | FP_contam |
| 67 | bias_T30_a0.3_neg_p0.8 | bias | T30 | 261 | 301 | 133 | FP_clean |
| 67 | bias_T50_a0.75_pos_p0.8 | bias | T50 | 261 | 301 | 133 | FP_clean |
| 67 | gain_T24_a0.5_neg_p0.2 | gain | T24 | 107 | 147 | 125 | FP_contam |
| 67 | gain_T30_a0.5_neg_p0.4 | gain | T30 | 158 | 198 | 133 | FP_clean |
| 67 | gain_T50_a0.25_neg_p0.8 | gain | T50 | 261 | 301 | 132 | FP_clean |
| 67 | multiC_T24+T30+T50_a0.3_na_p0.8 | multi_C | T24+T30+T50 | 261 | 301 | 133 | FP_clean |
| 67 | multiI_T24+T30+T50_a0.3_na_p0.4 | multi_I | T24+T30+T50 | 158 | 198 | 133 | FP_clean |
| 67 | multiI_T24+T30+T50_a0.3_na_p0.6 | multi_I | T24+T30+T50 | 210 | 250 | 132 | FP_clean |
| 67 | multiI_T24+T30+T50_a0.5_na_p0.2 | multi_I | T24+T30+T50 | 107 | 147 | 133 | FP_contam |
| 67 | multiI_T24+T30+T50_a0.5_na_p0.6 | multi_I | T24+T30+T50 | 210 | 250 | 133 | FP_clean |
| 67 | noise_T24_b1.0_na_p0.4 | noise | T24 | 158 | 198 | 131 | FP_clean |
| 67 | noise_T30_b1.0_na_p0.2 | noise | T30 | 107 | 147 | 121 | FP_contam |
| 67 | noise_T50_b3.0_na_p0.8 | noise | T50 | 261 | 301 | 131 | FP_clean |
| 67 | stuck_T30_na_na_p0.6 | stuck | T30 | 210 | 250 | 131 | FP_clean |
| 68 | bias_T24_a0.3_neg_p0.4 | bias | T24 | 113 | 153 | 85 | FP_clean |
| 68 | bias_T24_a0.3_pos_p0.6 | bias | T24 | 141 | 181 | 126 | FP_clean |
| 68 | bias_T30_a1.0_pos_p0.6 | bias | T30 | 141 | 181 | 126 | FP_clean |
| 68 | bias_T50_a0.75_pos_p0.6 | bias | T50 | 141 | 181 | 126 | FP_clean |
| 68 | gain_T30_a0.75_neg_p0.2 | gain | T30 | 84 | 124 | 109 | FP_contam |
| 68 | gain_T30_a1.0_pos_p0.8 | gain | T30 | 170 | 199 | 126 | FP_clean |
| 68 | gain_T50_a1.0_pos_p0.4 | gain | T50 | 113 | 153 | 127 | FP_contam |
| 68 | multiC_T24+T30+T50_a0.3_na_p0.6 | multi_C | T24+T30+T50 | 141 | 181 | 126 | FP_clean |
| 68 | multiC_T24+T30+T50_a0.3_na_p0.8 | multi_C | T24+T30+T50 | 170 | 199 | 126 | FP_clean |
| 68 | multiI_T24+T30+T50_a0.3_na_p0.4 | multi_I | T24+T30+T50 | 113 | 153 | 126 | FP_contam |
| 68 | multiI_T24+T30+T50_a0.3_na_p0.6 | multi_I | T24+T30+T50 | 141 | 181 | 126 | FP_clean |
| 68 | multiI_T24+T30+T50_a0.3_na_p0.8 | multi_I | T24+T30+T50 | 170 | 199 | 126 | FP_clean |
| 68 | multiI_T24+T30+T50_a0.5_na_p0.2 | multi_I | T24+T30+T50 | 84 | 124 | 100 | FP_contam |
| 68 | noise_T30_b1.0_na_p0.8 | noise | T30 | 170 | 199 | 126 | FP_clean |
| 68 | noise_T30_b2.0_na_p0.6 | noise | T30 | 141 | 181 | 126 | FP_clean |
| 68 | noise_T30_b3.0_na_p0.2 | noise | T30 | 84 | 124 | 87 | FP_contam |
| 68 | stuck_T30_na_na_p0.4 | stuck | T30 | 113 | 153 | 123 | FP_contam |
| 68 | stuck_T50_na_na_p0.6 | stuck | T50 | 141 | 181 | 126 | FP_clean |
| 68 | stuck_T50_na_na_p0.8 | stuck | T50 | 170 | 199 | 126 | FP_clean |
| 70 | bias_T24_a0.5_neg_p0.4 | bias | T24 | 88 | 128 | 101 | FP_contam |
| 70 | bias_T24_a0.75_neg_p0.8 | bias | T24 | 121 | 137 | 97 | FP_clean |
| 70 | bias_T24_a1.0_neg_p0.6 | bias | T24 | 104 | 137 | 96 | FP_clean |
| 70 | bias_T50_a0.3_pos_p0.8 | bias | T50 | 121 | 137 | 96 | FP_clean |
| 70 | gain_T24_a2.0_pos_p0.8 | gain | T24 | 121 | 137 | 96 | FP_clean |
| 70 | gain_T30_a0.75_neg_p0.2 | gain | T30 | 71 | 111 | 97 | FP_contam |
| 70 | gain_T30_a1.0_pos_p0.4 | gain | T30 | 88 | 128 | 97 | FP_contam |
| 70 | gain_T50_a0.5_neg_p0.2 | gain | T50 | 71 | 111 | 97 | FP_contam |
| 70 | multiC_T24+T30+T50_a0.3_na_p0.2 | multi_C | T24+T30+T50 | 71 | 111 | 135 | TN |
| 70 | multiC_T24+T30+T50_a0.3_na_p0.4 | multi_C | T24+T30+T50 | 88 | 128 | 98 | FP_contam |
| 70 | multiC_T24+T30+T50_a0.5_na_p0.4 | multi_C | T24+T30+T50 | 88 | 128 | 93 | FP_contam |
| 70 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 104 | 137 | 96 | FP_clean |
| 70 | multiI_T24+T30+T50_a0.3_na_p0.4 | multi_I | T24+T30+T50 | 88 | 128 | 102 | FP_contam |
| 70 | multiI_T24+T30+T50_a0.3_na_p0.6 | multi_I | T24+T30+T50 | 104 | 137 | 96 | FP_clean |
| 70 | multiI_T24+T30+T50_a0.5_na_p0.2 | multi_I | T24+T30+T50 | 71 | 111 | 102 | FP_contam |
| 70 | multiI_T24+T30+T50_a0.5_na_p0.8 | multi_I | T24+T30+T50 | 121 | 137 | 96 | FP_clean |
| 70 | noise_T24_b2.0_na_p0.4 | noise | T24 | 88 | 128 | 100 | FP_contam |
| 70 | noise_T50_b1.0_na_p0.8 | noise | T50 | 121 | 137 | 96 | FP_clean |
| 70 | stuck_T24_na_na_p0.8 | stuck | T24 | 121 | 137 | 96 | FP_clean |
| 70 | stuck_T30_na_na_p0.2 | stuck | T30 | 71 | 111 | 81 | FP_contam |
| 70 | stuck_T30_na_na_p0.6 | stuck | T30 | 104 | 137 | 96 | FP_clean |
| 70 | stuck_T50_na_na_p0.8 | stuck | T50 | 121 | 137 | 96 | FP_clean |
| 79 | bias_T30_a0.5_pos_p0.2 | bias | T30 | 84 | 124 | 105 | FP_contam |
| 79 | bias_T30_a0.5_pos_p0.6 | bias | T30 | 141 | 181 | 99 | FP_clean |
| 79 | bias_T50_a0.5_neg_p0.6 | bias | T50 | 141 | 181 | 99 | FP_clean |
| 79 | bias_T50_a1.0_pos_p0.6 | bias | T50 | 141 | 181 | 99 | FP_clean |
| 79 | gain_T24_a0.25_neg_p0.2 | gain | T24 | 84 | 124 | 99 | FP_contam |
| 79 | gain_T30_a0.25_neg_p0.4 | gain | T30 | 113 | 153 | 99 | FP_clean |
| 79 | gain_T30_a0.5_neg_p0.4 | gain | T30 | 113 | 153 | 99 | FP_clean |
| 79 | gain_T50_a1.0_pos_p0.8 | gain | T50 | 170 | 199 | 99 | FP_clean |
| 79 | multiC_T24+T30+T50_a0.3_na_p0.8 | multi_C | T24+T30+T50 | 170 | 199 | 99 | FP_clean |
| 79 | multiC_T24+T30+T50_a0.5_na_p0.6 | multi_C | T24+T30+T50 | 141 | 181 | 99 | FP_clean |
| 79 | multiC_T24+T30+T50_a0.5_na_p0.8 | multi_C | T24+T30+T50 | 170 | 199 | 99 | FP_clean |
| 79 | multiI_T24+T30+T50_a0.5_na_p0.2 | multi_I | T24+T30+T50 | 84 | 124 | 99 | FP_contam |
| 79 | multiI_T24+T30+T50_a0.5_na_p0.4 | multi_I | T24+T30+T50 | 113 | 153 | 99 | FP_clean |
| 79 | multiI_T24+T30+T50_a0.5_na_p0.6 | multi_I | T24+T30+T50 | 141 | 181 | 99 | FP_clean |
| 79 | multiI_T24+T30+T50_a0.5_na_p0.8 | multi_I | T24+T30+T50 | 170 | 199 | 99 | FP_clean |
| 79 | noise_T24_b1.0_na_p0.2 | noise | T24 | 84 | 124 | 107 | FP_contam |
| 79 | noise_T24_b1.0_na_p0.4 | noise | T24 | 113 | 153 | 99 | FP_clean |
| 79 | noise_T30_b2.0_na_p0.8 | noise | T30 | 170 | 199 | 99 | FP_clean |
| 79 | noise_T50_b2.0_na_p0.6 | noise | T50 | 141 | 181 | 99 | FP_clean |
| 79 | stuck_T30_na_na_p0.2 | stuck | T30 | 84 | 124 | 93 | FP_contam |
| 79 | stuck_T30_na_na_p0.4 | stuck | T30 | 113 | 153 | 99 | FP_clean |
| 79 | stuck_T30_na_na_p0.8 | stuck | T30 | 170 | 199 | 99 | FP_clean |
| 85 | bias_T30_a0.75_neg_p0.2 | bias | T30 | 82 | 122 | 88 | FP_contam |
| 85 | bias_T50_a0.5_neg_p0.6 | bias | T50 | 135 | 175 | 94 | FP_clean |
| 85 | bias_T50_a0.75_pos_p0.8 | bias | T50 | 161 | 188 | 88 | FP_clean |
| 85 | gain_T24_a0.5_neg_p0.6 | gain | T24 | 135 | 175 | 94 | FP_clean |
| 85 | gain_T30_a0.5_neg_p0.2 | gain | T30 | 82 | 122 | 88 | FP_contam |
| 85 | gain_T30_a1.5_pos_p0.2 | gain | T30 | 82 | 122 | 88 | FP_contam |
| 85 | multiC_T24+T30+T50_a0.5_na_p0.8 | multi_C | T24+T30+T50 | 161 | 188 | 94 | FP_clean |
| 85 | multiI_T24+T30+T50_a0.3_na_p0.6 | multi_I | T24+T30+T50 | 135 | 175 | 94 | FP_clean |
| 85 | multiI_T24+T30+T50_a0.5_na_p0.8 | multi_I | T24+T30+T50 | 161 | 188 | 94 | FP_clean |
| 85 | noise_T30_b1.0_na_p0.4 | noise | T30 | 108 | 148 | 94 | FP_clean |
| 85 | noise_T30_b2.0_na_p0.2 | noise | T30 | 82 | 122 | 88 | FP_contam |
| 85 | noise_T30_b3.0_na_p0.8 | noise | T30 | 161 | 188 | 94 | FP_clean |
| 85 | noise_T50_b1.0_na_p0.2 | noise | T50 | 82 | 122 | 88 | FP_contam |
| 85 | stuck_T24_na_na_p0.8 | stuck | T24 | 161 | 188 | 94 | FP_clean |
| 85 | stuck_T30_na_na_p0.2 | stuck | T30 | 82 | 122 | 88 | FP_contam |
| 90 | bias_T24_a0.3_neg_p0.4 | bias | T24 | 95 | 135 | 86 | FP_clean |
| 90 | bias_T24_a0.5_pos_p0.8 | bias | T24 | 134 | 154 | 86 | FP_clean |
| 90 | bias_T30_a0.5_pos_p0.8 | bias | T30 | 134 | 154 | 86 | FP_clean |
| 90 | bias_T50_a1.0_neg_p0.8 | bias | T50 | 134 | 154 | 86 | FP_clean |
| 90 | gain_T24_a0.75_neg_p0.8 | gain | T24 | 134 | 154 | 86 | FP_clean |
| 90 | gain_T24_a1.0_pos_p0.8 | gain | T24 | 134 | 154 | 86 | FP_clean |
| 90 | gain_T24_a1.5_pos_p0.6 | gain | T24 | 114 | 154 | 86 | FP_clean |
| 90 | gain_T30_a0.25_neg_p0.8 | gain | T30 | 134 | 154 | 86 | FP_clean |
| 90 | multiC_T24+T30+T50_a0.3_na_p0.4 | multi_C | T24+T30+T50 | 95 | 135 | 86 | FP_clean |
| 90 | multiC_T24+T30+T50_a0.3_na_p0.6 | multi_C | T24+T30+T50 | 114 | 154 | 86 | FP_clean |
| 90 | multiI_T24+T30+T50_a0.3_na_p0.2 | multi_I | T24+T30+T50 | 75 | 115 | 86 | FP_contam |
| 90 | multiI_T24+T30+T50_a0.3_na_p0.4 | multi_I | T24+T30+T50 | 95 | 135 | 86 | FP_clean |
| 90 | multiI_T24+T30+T50_a0.3_na_p0.8 | multi_I | T24+T30+T50 | 134 | 154 | 86 | FP_clean |
| 90 | multiI_T24+T30+T50_a0.5_na_p0.4 | multi_I | T24+T30+T50 | 95 | 135 | 86 | FP_clean |
| 90 | noise_T24_b1.0_na_p0.4 | noise | T24 | 95 | 135 | 86 | FP_clean |
| 90 | noise_T30_b1.0_na_p0.4 | noise | T30 | 95 | 135 | 86 | FP_clean |
| 90 | noise_T50_b2.0_na_p0.8 | noise | T50 | 134 | 154 | 86 | FP_clean |
| 90 | stuck_T24_na_na_p0.6 | stuck | T24 | 114 | 154 | 86 | FP_clean |
| 90 | stuck_T30_na_na_p0.8 | stuck | T30 | 134 | 154 | 86 | FP_clean |
| 90 | stuck_T50_na_na_p0.6 | stuck | T50 | 114 | 154 | 86 | FP_clean |
