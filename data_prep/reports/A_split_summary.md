# Phase A — Hold-out 분할 요약

- seed: 529, strata: 5, hold-out 20 / train 80
- t0 = seq_len(45) + N = 55, timing_p = [0.2, 0.4, 0.6, 0.8]

## T_u 분포 비교
| group | n | min | q25 | median | q75 | max | mean |
|---|---|---|---|---|---|---|---|
| all | 100 | 128 | 177.0 | 199.0 | 229.2 | 362 | 206.3 |
| train | 80 | 128 | 176.5 | 197.0 | 229.2 | 362 | 206.4 |
| holdout | 20 | 137 | 184.5 | 199.0 | 224.2 | 313 | 205.8 |

## 히스토그램 (bin=20)
| bin | all | holdout |
|---|---|---|
| 120-140 | 4 | 2 |
| 140-160 | 12 | 2 |
| 160-180 | 11 | 1 |
| 180-200 | 25 | 6 |
| 200-220 | 21 | 3 |
| 220-240 | 8 | 2 |
| 240-260 | 6 | 1 |
| 260-280 | 5 | 1 |
| 280-300 | 4 | 1 |
| 300-320 | 1 | 1 |
| 320-340 | 1 | 0 |
| 340-360 | 1 | 0 |

## Hold-out unit 별 τ_s 와 포화 예상 (T_u − τ_s > max_rul)
| unit | T_u | tau_s p0.2 | sat p0.2 | tau_s p0.4 | sat p0.4 | tau_s p0.6 | sat p0.6 | tau_s p0.8 | sat p0.8 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 192 | 82 | False | 110 | False | 137 | False | 165 | False |
| 9 | 201 | 84 | False | 113 | False | 143 | False | 172 | False |
| 10 | 222 | 88 | True | 122 | False | 155 | False | 189 | False |
| 11 | 240 | 92 | True | 129 | False | 166 | False | 203 | False |
| 17 | 276 | 99 | True | 143 | True | 188 | False | 232 | False |
| 26 | 199 | 84 | False | 113 | False | 141 | False | 170 | False |
| 32 | 191 | 82 | False | 109 | False | 137 | False | 164 | False |
| 48 | 231 | 90 | True | 125 | False | 161 | False | 196 | False |
| 49 | 215 | 87 | True | 119 | False | 151 | False | 183 | False |
| 52 | 213 | 87 | True | 118 | False | 150 | False | 181 | False |
| 57 | 137 | 71 | False | 88 | False | 104 | False | 121 | False |
| 63 | 174 | 79 | False | 103 | False | 126 | False | 150 | False |
| 64 | 283 | 101 | True | 146 | True | 192 | False | 237 | False |
| 65 | 153 | 75 | False | 94 | False | 114 | False | 133 | False |
| 67 | 313 | 107 | True | 158 | True | 210 | False | 261 | False |
| 68 | 199 | 84 | False | 113 | False | 141 | False | 170 | False |
| 70 | 137 | 71 | False | 88 | False | 104 | False | 121 | False |
| 79 | 199 | 84 | False | 113 | False | 141 | False | 170 | False |
| 85 | 188 | 82 | False | 108 | False | 135 | False | 161 | False |
| 90 | 154 | 75 | False | 95 | False | 114 | False | 134 | False |

