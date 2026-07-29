# Grid experiment — blind-spot matrix

Protocol: FA<=1/100cyc (q=0.97 on u20), hysteresis 2. L{n} = detected at latency n cycles; MISS = never; FA{n} = false-alarm points (controls).

| scenario | cons | RULΔ | CUSUM | PCA_T2 | PCA_SPE | RULE |
|---|---|---|---|---|---|---|
| no_shift | — | — | clean | clean | FA1 | clean |
| natural(u14) | — | — | FA22 | FA25 | FA12 | clean |
| natural(u15) | — | — | clean | FA3 | FA2 | clean |
| c1_T48_step_0.5s_neg | 4.03 | 27.36 | MISS | MISS | L4 | L4 |
| c1_T48_step_0.5s_pos | 4.46 | 14.27 | MISS | MISS | L4 | L4 |
| c1_T48_step_1s_neg | 7.99 | 37.84 | L13 | MISS | L4 | L4 |
| c1_T48_step_1s_pos | 8.32 | 20.07 | MISS | MISS | L4 | L4 |
| c1_T48_step_2s_neg | 15.93 | 43.78 | L7 | L1 | L4 | L4 |
| c1_T48_step_2s_pos | 16.1 | 21.07 | L19 | MISS | L4 | L4 |
| c1_T48_ramp_0.5s_neg | 3.81 | 24.78 | MISS | MISS | L7 | L10 |
| c1_T48_ramp_0.5s_pos | 4.77 | 9.4 | MISS | MISS | L7 | L10 |
| c1_T48_ramp_1s_neg | 7.8 | 36.17 | L22 | MISS | L7 | L7 |
| c1_T48_ramp_1s_pos | 8.53 | 14.14 | MISS | MISS | L7 | L7 |
| c1_T48_ramp_2s_neg | 15.78 | 43.5 | L13 | MISS | L7 | L7 |
| c1_T48_ramp_2s_pos | 16.17 | 17.2 | L25 | MISS | L7 | L7 |
| c1_T48_ramp_0.15s_neg | 1.29 | 4.66 | MISS | MISS | L7 | MISS |
| c1_T48_ramp_0.15s_pos | 2.17 | 3.71 | MISS | MISS | L7 | MISS |
| c1_T48_ramp_0.25s_neg | 1.96 | 9.05 | MISS | MISS | L7 | MISS |
| c1_T48_ramp_0.25s_pos | 2.91 | 5.74 | MISS | MISS | L7 | L16 |
| c1_T48_ramp_0.35s_neg | 2.67 | 14.97 | MISS | MISS | L7 | L13 |
| c1_T48_ramp_0.35s_pos | 3.65 | 7.35 | MISS | MISS | L7 | L16 |
| c2_temp4mix_ramp_0.5s_neg | 9.65 | 8.92 | L25 | MISS | L7 | L10 |
| c2_temp4mix_ramp_0.5s_pos | 10.84 | 27.26 | L28 | MISS | L7 | L10 |
| c2_temp4mix_ramp_1s_neg | 19.9 | 13.62 | L16 | MISS | L7 | L7 |
| c2_temp4mix_ramp_1s_pos | 21.08 | 39.34 | L16 | MISS | L7 | L7 |
| c2_temp4mix_ramp_2s_neg | 40.39 | 16.88 | L13 | MISS | L4 | L4 |
| c2_temp4mix_ramp_2s_pos | 41.57 | 43.84 | L13 | MISS | L7 | L7 |
| c3_coord_pc1_ramp_0.5s_neg | 0.91 | 1.1 | L25 | MISS | L7 | MISS |
| c3_coord_pc1_ramp_0.5s_pos | 1.22 | 1.02 | MISS | MISS | L7 | MISS |
| c3_coord_pc1_ramp_1s_neg | 0.85 | 2.44 | L16 | L13 | L7 | MISS |
| c3_coord_pc1_ramp_1s_pos | 1.38 | 2.06 | MISS | L28 | L7 | MISS |
| c3_coord_pc1_ramp_2s_neg | 1.06 | 4.36 | L13 | L7 | L4 | MISS |
| c3_coord_pc1_ramp_2s_pos | 1.71 | 4.53 | L28 | L13 | L7 | MISS |
| c3_coord_pc1_ramp_3s_neg | 1.34 | 5.09 | L13 | L7 | L4 | MISS |
| c3_coord_pc1_ramp_3s_pos | 2.03 | 8.27 | L22 | L13 | L7 | MISS |
| c3_coord_pc1_ramp_4s_neg | 1.65 | 5.22 | L10 | L7 | L4 | MISS |
| c3_coord_pc1_ramp_4s_pos | 2.37 | 10.48 | L19 | L13 | L7 | MISS |
| c4_natural_fault_u14_neg | 7.43 | 34.39 | L0 | L0 | L3 | L6 |
| c4_natural_fault_u14_pos | 8.75 | 16.4 | L0 | L0 | L3 | L9 |
| c4_natural_fault_u15_neg | 8.09 | 36.4 | MISS | L31 | L1 | L7 |
| c4_natural_fault_u15_pos | 8.34 | 13.7 | L31 | L31 | L1 | L7 |

## Pooled harmful-shift metrics (8.2, hysteresis)

| detector | precision | recall | F1 | FPR |
|---|---|---|---|---|
| CUSUM | 0.8 | 0.33 | 0.46 | 0.09 |
| PCA_SPE | 0.91 | 0.68 | 0.78 | 0.07 |
| PCA_T2 | 0.63 | 0.2 | 0.3 | 0.12 |
| RULE | 1.0 | 0.54 | 0.7 | 0.0 |
