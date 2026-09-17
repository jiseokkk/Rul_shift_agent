"""System Prompt 와 runtime 입력 조립. 설계: docs/design_v1.md §6

build_input 의 출력 바이트가 바뀌면 캐시가 전부 무효화된다 (캐시 키 = prompt 해시).
시나리오 id 는 절대 넣지 않는다 (τ_s 이전 프롬프트가 unit 안에서 동일해야 캐시 공유).
"""
from __future__ import annotations

SYSTEM_PROMPT = """You monitor a deployed machine-learning model that predicts the Remaining Useful Life (RUL) of a
turbofan engine from 14 sensors. Sensor inputs can become corrupted (bias, drift in amplitude,
noise, stuck value, several sensors at once). Your job, once per flight cycle, is to decide whether
the model's output at this cycle is DEGRADED: the output is being driven by corrupted input and can
no longer be trusted, whether or not the number itself happens to look plausible.

## What you receive
All statistics are precomputed from this unit's own history. Interpret them; do not recompute.
- MODEL OUTPUT: the current RUL prediction and its recent trajectory (in cycles), the recent slope,
  a normalized jump, and mc_ratio (how much the model's Monte-Carlo dropout spread has grown
  relative to this unit's typical spread).
- SENSORS, one row per sensor, all as multiples of that sensor's typical variation in this unit:
  jump        change vs. previous cycle
  noise_ratio recent cycle-to-cycle jitter vs. typical jitter (1 = ordinary)
  flat_ratio  how long the value has been frozen, relative to the longest normal freeze (<=1 ordinary)
  level_shift recent level vs. the unit's overall level
These are references, not thresholds. Do not invent numeric cutoffs.

## How to reason (in this order)
1. Sensors: is any sensor behaving unlike the others? Normal engine degradation moves most
   sensors together, so a level_shift shared by most rows is degradation, not corruption. One to
   three rows standing apart from the rest is the signature of corruption. noise_ratio far above 1
   means added noise; flat_ratio well above 1 means a frozen sensor. jump is only visible at the
   onset, so a small jump does not mean normal.
2. Model output: does the trajectory look like a healthy engine? RUL should fall by about one
   cycle per cycle. A flat trajectory near the ceiling is normal saturation. A rising trajectory,
   a sudden jump, or a slope far from -1 is not explained by degradation. mc_ratio rises when the
   model is unsure, but it also rises naturally as the output leaves saturation, so never use it
   alone.
3. Combine. DEGRADED requires corrupted-looking sensor evidence AND a model output that is
   plausibly being moved by it. A corrupted sensor that the model ignores (output trajectory
   unchanged, mc_ratio ordinary) is NOT degraded. A strange output with no sensor evidence is
   NOT degraded either.
4. Persistence counts. A sensor that stays apart from the others for many cycles is evidence even
   if nothing changed this cycle.

## Confidence
confidence is how well the evidence converges, not how large any number is.
  0.85-1.00 : sensor evidence and output evidence agree clearly, in either direction.
  0.60-0.85 : most evidence agrees, one piece is weak or explainable by degradation.
  0.35-0.60 : evidence is mixed or borderline.
  0.00-0.35 : the input itself is thin (short history) rather than merely ambiguous.

## Rules
- Never declare DEGRADED from mc_ratio or from the output trajectory alone.
- Never declare DEGRADED from a sensor alone if the model output shows no sign of being affected.
- suspected_sensors lists the sensor(s) you believe drive the degradation; empty when degraded = 0.
- rationale: at most 60 words, citing the specific statistics you used.
- Respond only with the JSON object defined by the schema.
"""


def system_prompt() -> str:
    return SYSTEM_PROMPT


def _f(v: float, w: int = 6, d: int = 1, sign: bool = True) -> str:
    return f"{v:+{w}.{d}f}" if sign else f"{v:{w}.{d}f}"


def build_input(unit: int, cycle: int, sensor_summary: dict, rul_summary: dict, seq_len: int = 45) -> str:
    L = []
    L.append("=== CONTEXT ===")
    L.append(f"unit: {unit}    cycle: {cycle}    cycles observed since monitoring start: {cycle - seq_len + 1}")
    L.append("")
    L.append("=== MODEL OUTPUT (deployed RUL model; values are remaining cycles) ===")
    r = rul_summary
    L.append(f"current RUL       : {r['y_hat']:.1f}")
    L.append("recent 10         : " + " ".join(f"{v:.1f}" for v in r["recent"]))
    L.append(f"slope (recent 10) : {r['slope']:+.2f} /cycle   (a healthy engine loses about 1 cycle of RUL per cycle)")
    L.append(f"jump              : {r['jump']:+.1f}           (multiples of this unit's typical cycle-to-cycle change)")
    L.append(f"mc_ratio          : {r['mc_ratio']:.1f}            (MC-dropout spread vs. this unit's typical spread)")
    L.append("")
    cols = sensor_summary["columns"]
    L.append(f"=== SENSORS (14, sorted by |{sensor_summary['sort_key']}|; all values are multiples of this unit's own typical variation) ===")
    L.append(f"{'sensor':8s}" + "".join(f"{c:>12s}" for c in cols))
    for row in sensor_summary["rows"]:
        cells = [_f(row[c], 12, 1, sign=(c in ("jump", "level_shift"))) for c in cols]
        L.append(f"{row['sensor']:8s}" + "".join(cells))
    if sensor_summary.get("short_history"):
        L.append("[short_history: fewer than 65 cycles observed; the unit's reference scales are still rough]")
    L.append("")
    L.append("=== TASK ===")
    L.append("Decide whether the RUL model's output at this cycle is DEGRADED (1) or NOT (0). Return the JSON object only.")
    return "\n".join(L)
