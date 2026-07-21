# Experiment Report — Shift-Aware RUL Decision Agent (N-CMAPSS DS02-006)

LLM backbone: Qwen2.5-32B-AWQ (local vLLM, temperature 0.7, 5 samples/point, majority vote). RUL tool: 2-layer LSTM (54,849 params, val RMSE 5.65).

## Table 1 — Decision quality (FNR / FPR / F1)

| Method | No shift | Adverse | Favorable | Natural (Dir B) |
|---|---|---|---|---|
| threshold | 0.22 / 0.00 / 0.88 | 1.00 / 0.00 / 0.00 | 0.00 / 0.27 / 0.86 | 0.06 / 0.00 / 0.97 |
| cusum | 0.22 / 0.00 / 0.88 | 0.00 / 0.09 / 0.95 | 0.00 / 0.27 / 0.86 | 0.00 / 0.45 / 0.72 |
| agent_rule | 0.22 / 0.00 / 0.88 | 0.00 / 0.18 / 0.90 | 0.00 / 0.27 / 0.86 | 0.06 / 0.00 / 0.97 |
| agent_llm | 0.22 / 0.00 / 0.88 | 0.00 / 0.27 / 0.86 | 0.00 / 0.27 / 0.86 | 0.06 / 0.00 / 0.97 |

## Table 2 — Shift detection (Direction A, injection @ cycle 23)

| Method | Precision | Recall | F1 | Latency (cycles) |
|---|---|---|---|---|
| cusum | 1.00 | 0.83 | 0.91 | 8 |
| agent_rule | 1.00 | 0.92 | 0.96 | 5 |
| agent_llm | 1.00 | 1.00 | 1.00 | 2 |

## Table 3 — Ablation (rule agent; adverse & natural)

| Config | Adverse FNR/FPR/F1 | Natural FNR/FPR/F1 | Shift-det F1 |
|---|---|---|---|
| full | 0.00/0.18/0.90 | 0.06/0.00/0.97 | 0.96 |
| no_consistency | 1.00/0.00/0.00 | 0.06/0.00/0.97 | 0.00 |
| no_regime | 1.00/0.00/0.00 | 0.06/0.00/0.97 | 0.96 |
| no_tier1 | 0.00/0.18/0.90 | 0.06/0.65/0.62 | 0.96 |
| no_uncertainty | 0.00/0.18/0.90 | 0.06/0.00/0.97 | 0.96 |
| no_hysteresis | 0.00/0.27/0.86 | 0.06/0.00/0.97 | 1.00 |
| no_cost_aware | 0.00/0.18/0.90 | 0.06/0.00/0.97 | 0.96 |

## Key findings

- **Adverse (silent over-optimism):** threshold misses everything (FNR 1.00); the agent recovers safety (FNR 0.00, F1 0.86).
- **Natural flight-class shift:** direction-blind CUSUM floods false alarms (FPR 0.45); the agent stays quiet (FPR 0.00) thanks to the Tier-1 regime/consistency features. No single baseline wins both directions.
- **No shift:** the agent matches/exceeds baselines (F1 0.88 vs 0.88) with no over-caution penalty.
- **Ablation:** removing the cross-channel consistency residual collapses adverse detection (F1 -> 0.00); removing all Tier-1 features reopens the CUSUM failure on natural shift (FPR -> 0.65).