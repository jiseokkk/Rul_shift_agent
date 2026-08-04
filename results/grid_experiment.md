# Grid experiment — blind-spot matrix

Protocol: FA<=1/100cyc (q=0.97 on u20), hysteresis 2, detection credit = off->on transition at/after onset; SAT = alarming since pre-onset (uninformative). L{n} = detected, latency n cycles.

| scenario | cons | RULΔ | CUSUM | CUSUM_REG | PCA_T2 | PCA_SPE | PCA_T2_REG | PCA_SPE_REG | KLCPD |
|---|---|---|---|---|---|---|---|---|---|
| no_shift | — | — | clean | clean | clean | FA1 | clean | clean | clean |
| natural(u14) | — | — | FA22 | FA19 | FA25 | FA12 | clean | clean | clean |
| natural(u15) | — | — | clean | clean | FA3 | FA2 | clean | clean | clean |
| c1_T48_step_0.5s_neg | 4.03 | 27.36 | MISS | L4 | MISS | L4 | MISS | L4 | MISS |
| c1_T48_step_0.5s_pos | 4.46 | 14.27 | MISS | L4 | MISS | L4 | MISS | L4 | MISS |
| c1_T48_step_1s_neg | 7.99 | 37.84 | L13 | L4 | MISS | L4 | L4 | L4 | MISS |
| c1_T48_step_1s_pos | 8.32 | 20.07 | MISS | L4 | MISS | L4 | L16 | L4 | MISS |
| c1_T48_step_2s_neg | 15.93 | 43.78 | L7 | L4 | L1 | L4 | L4 | L4 | MISS |
| c1_T48_step_2s_pos | 16.1 | 21.07 | L19 | L4 | MISS | L4 | L4 | L4 | MISS |
| c1_T48_ramp_0.5s_neg | 3.81 | 24.78 | MISS | L13 | MISS | L7 | MISS | L7 | MISS |
| c1_T48_ramp_0.5s_pos | 4.77 | 9.4 | MISS | L13 | MISS | L7 | MISS | L7 | MISS |
| c1_T48_ramp_1s_neg | 7.8 | 36.17 | L22 | L10 | MISS | L7 | MISS | L7 | MISS |
| c1_T48_ramp_1s_pos | 8.53 | 14.14 | MISS | L10 | MISS | L7 | L25 | L7 | MISS |
| c1_T48_ramp_2s_neg | 15.78 | 43.5 | L13 | L7 | MISS | L7 | L10 | L4 | MISS |
| c1_T48_ramp_2s_pos | 16.17 | 17.2 | L25 | L7 | MISS | L7 | L10 | L4 | MISS |
| c1_T48_ramp_0.15s_neg | 1.29 | 4.66 | MISS | L19 | MISS | L7 | MISS | L19 | MISS |
| c1_T48_ramp_0.15s_pos | 2.17 | 3.71 | MISS | L22 | MISS | L7 | MISS | L13 | MISS |
| c1_T48_ramp_0.25s_neg | 1.96 | 9.05 | MISS | L16 | MISS | L7 | MISS | L10 | MISS |
| c1_T48_ramp_0.25s_pos | 2.91 | 5.74 | MISS | L16 | MISS | L7 | MISS | L13 | MISS |
| c1_T48_ramp_0.35s_neg | 2.67 | 14.97 | MISS | L13 | MISS | L7 | MISS | L7 | MISS |
| c1_T48_ramp_0.35s_pos | 3.65 | 7.35 | MISS | L16 | MISS | L7 | MISS | L7 | MISS |
| c2_temp4mix_ramp_0.5s_neg | 9.65 | 8.92 | L25 | L10 | MISS | L7 | L10 | L7 | MISS |
| c2_temp4mix_ramp_0.5s_pos | 10.84 | 27.26 | L28 | L10 | MISS | L7 | L10 | L7 | MISS |
| c2_temp4mix_ramp_1s_neg | 19.9 | 13.62 | L16 | L7 | MISS | L7 | L7 | L4 | MISS |
| c2_temp4mix_ramp_1s_pos | 21.08 | 39.34 | L16 | L7 | MISS | L7 | L7 | L4 | MISS |
| c2_temp4mix_ramp_2s_neg | 40.39 | 16.88 | L13 | L7 | MISS | L4 | L7 | L4 | MISS |
| c2_temp4mix_ramp_2s_pos | 41.57 | 43.84 | L13 | L7 | MISS | L7 | L7 | L4 | MISS |
| c3_coord_pc1_ramp_0.5s_neg | 0.91 | 1.1 | L25 | L7 | MISS | L7 | L4 | L4 | MISS |
| c3_coord_pc1_ramp_0.5s_pos | 1.22 | 1.02 | MISS | L7 | MISS | L7 | L4 | L4 | MISS |
| c3_coord_pc1_ramp_1s_neg | 0.85 | 2.44 | L16 | L4 | L13 | L7 | L4 | L4 | MISS |
| c3_coord_pc1_ramp_1s_pos | 1.38 | 2.06 | MISS | L4 | L28 | L7 | L4 | L4 | MISS |
| c3_coord_pc1_ramp_2s_neg | 1.06 | 4.36 | L13 | L4 | L7 | L4 | L4 | L4 | MISS |
| c3_coord_pc1_ramp_2s_pos | 1.71 | 4.53 | L28 | L4 | L13 | L7 | L4 | L4 | MISS |
| c3_coord_pc1_ramp_3s_neg | 1.34 | 5.09 | L13 | L4 | L7 | L4 | L4 | L4 | MISS |
| c3_coord_pc1_ramp_3s_pos | 2.03 | 8.27 | L22 | L4 | L13 | L7 | L4 | L4 | MISS |
| c3_coord_pc1_ramp_4s_neg | 1.65 | 5.22 | L10 | L4 | L7 | L4 | L4 | L4 | MISS |
| c3_coord_pc1_ramp_4s_pos | 2.37 | 10.48 | L19 | L4 | L13 | L7 | L4 | L4 | MISS |
| c4_natural_fault_u14_neg | 7.43 | 34.39 | SAT | SAT | SAT | L3 | MISS | L6 | MISS |
| c4_natural_fault_u14_pos | 8.75 | 16.4 | SAT | SAT | SAT | L3 | L18 | L6 | MISS |
| c4_natural_fault_u15_neg | 8.09 | 36.4 | MISS | L10 | L31 | L1 | L19 | L7 | MISS |
| c4_natural_fault_u15_pos | 8.34 | 13.7 | L31 | L10 | L31 | L1 | L25 | L4 | MISS |
| m_gain_T48_ramp_1s_neg | 7.89 | 36.56 | L22 | L10 | MISS | L7 | MISS | L7 | MISS |
| m_gain_T48_ramp_1s_pos | 8.61 | 13.87 | MISS | L10 | MISS | L7 | L19 | L7 | MISS |
| m_noise_T48_ramp_1s | 2.08 | 5.58 | MISS | L31 | MISS | L7 | MISS | L22 | MISS |
| m_stuck_T48 | 4.37 | 13.21 | MISS | L4 | MISS | L4 | MISS | L4 | MISS |
| m_lag_T48_ramp | 1.23 | 1.51 | MISS | MISS | MISS | L7 | MISS | MISS | MISS |
| p_exp_T48_1s_neg | 6.23 | 34.69 | MISS | L10 | MISS | L7 | MISS | L7 | MISS |
| p_slow_T48_1s_neg | 4.81 | 22.87 | MISS | L13 | MISS | L7 | MISS | L7 | MISS |
| p_exp_T48_1s_pos | 7.06 | 12.27 | MISS | L10 | MISS | L7 | L31 | L7 | MISS |
| p_slow_T48_1s_pos | 5.72 | 8.37 | MISS | L16 | MISS | L7 | MISS | L7 | MISS |
| s_all14_ramp_1s_neg | 2.02 | 3.94 | L16 | L4 | L7 | L7 | L4 | L4 | MISS |
| s_all14_ramp_1s_pos | 2.64 | 2.38 | MISS | L4 | L19 | L7 | L4 | L4 | MISS |

## Pooled metrics by category (8.2, hysteresis, transition+SAT credit)

| detector | category | precision | recall | F1 | FPR | SAT series |
|---|---|---|---|---|---|---|
| CUSUM | natural | 0.67 | 0.19 | 0.29 | 0.07 | 2 |
| CUSUM | adversarial | 0.57 | 0.36 | 0.44 | 0.07 | 0 |
| CUSUM_REG | natural | 0.91 | 0.69 | 0.79 | 0.05 | 2 |
| CUSUM_REG | adversarial | 0.81 | 0.89 | 0.85 | 0.05 | 0 |
| KLCPD | natural | 0.0 | 0.0 | 0.0 | 0.0 | 0 |
| KLCPD | adversarial | 0.0 | 0.0 | 0.0 | 0.0 | 0 |
| PCA_SPE | natural | 0.9 | 0.6 | 0.72 | 0.06 | 0 |
| PCA_SPE | adversarial | 0.79 | 0.8 | 0.79 | 0.06 | 0 |
| PCA_SPE_REG | natural | 1.0 | 0.79 | 0.88 | 0.0 | 0 |
| PCA_SPE_REG | adversarial | 1.0 | 0.91 | 0.95 | 0.0 | 0 |
| PCA_T2 | natural | 0.09 | 0.01 | 0.02 | 0.1 | 2 |
| PCA_T2 | adversarial | 0.55 | 0.47 | 0.51 | 0.1 | 0 |
| PCA_T2_REG | natural | 1.0 | 0.28 | 0.44 | 0.0 | 0 |
| PCA_T2_REG | adversarial | 1.0 | 0.91 | 0.95 | 0.0 | 0 |
