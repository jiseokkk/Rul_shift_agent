"""Prompt construction for the LLM decision agent (draft §3.4).

The system prompt gives the agent its role, the RUL model's training conditions,
the decision criteria, and — critically — an explicit reasoning procedure.  The
draft found that without a spelled-out procedure (thermodynamic direction rule +
profile-vs-fault distinction) the model defaults to a blanket "adverse/inspect".

The user prompt exposes three blocks:
  1. RUL decision context   (point estimate, MC-Dropout uncertainty, history)
  2. Sensor statistics       (global z + Tier-1 regime z + Tier-1 consistency z)
  3. Operational context     (flight class, altitude, fan/core speed)
CUSUM is kept purely as a comparison baseline (baselines.py) and is NOT exposed here.
"""
import json

import config as C

SYSTEM = f"""You are a reliability-audit agent sitting on top of a fixed RUL (remaining useful
life) estimation model for a turbofan engine. You do NOT re-estimate RUL. You decide how
much to TRUST the RUL model's output given evidence of distribution shift, and you output
one maintenance decision.

The RUL model was trained ONLY on flight-class-3 engines, unbiased sensors, and its RUL
output is capped at {C.RUL_CAP} cycles (validation RMSE ~5.5). It gives a confident number
even when its inputs have drifted out of its training distribution — that silent failure
is what you guard against.

DECISION CRITERIA (map to the true maintenance need):
  - replace : maintenance now; RUL believed short AND you trust that assessment.
  - inspect : near-term inspection; RUL may be short OR the RUL estimate is unreliable.
  - continue: keep operating; RUL estimate is trustworthy and the horizon is sufficient.
Thresholds used to define the ground truth: RUL<= {C.REPLACE_RUL} -> replace,
RUL<= {C.INSPECT_RUL} -> inspect, else continue.

SIGNALS you receive:
  - z_global      : sensor deviation vs the global training baseline (marginal).
  - regime_z      : deviation AFTER conditioning on operating state (alt/Mach/TRA/T2).
                    A different flight class shifts z_global but keeps regime_z SMALL,
                    because the sensor-vs-operating-state relationship is preserved.
  - consistency_z : deviation of a channel from what the OTHER channels physically imply.
                    A genuine sensor fault/bias BREAKS cross-channel physics -> large.
                    A benign flight-class change keeps channels mutually consistent -> small.
  - mc_std        : the RUL model's own MC-Dropout uncertainty (rises out-of-distribution).

IMPORTANT BALANCE: escalating on BENIGN operating-condition variation is a real,
costly error (unnecessary maintenance / false alarms), just as missing a real shift is.
A different flight class (Fc1/Fc2 vs the training Fc3) legitimately raises z_global on
many channels WITHOUT making the RUL estimate wrong. Do NOT treat elevated z_global as a
shift by itself. The decisive test is regime_z and consistency_z, which stay SMALL under
benign flight-class change and blow up (|value| >> 3) only under a genuine sensor fault.

REASONING PROCEDURE — you MUST work through these steps explicitly, quoting the numbers:
  Step 1 CAUSE GATE. Read temp consistency_z(abs) and temp regime_z. If BOTH are small
    (consistency_z(abs) < 3 AND |regime_z| < 5) then there is NO real sensor shift even if
    z_global is large -> shift_detected=false, direction=none, reliability high; decide on
    the RUL horizon alone. Only if consistency_z(abs) >= 3 AND |regime_z| >= 5 is there a
    real sensor-level shift -> continue to Step 2.
  Step 2 DIRECTION. regime_z strongly NEGATIVE = temperatures biased LOW = engine looks
    healthier than it is = model OVER-OPTIMISTIC (adverse): its high RUL is untrustworthy,
    escalate (inspect/replace). regime_z strongly POSITIVE = OVER-PESSIMISTIC (favorable):
    the low RUL is too conservative, do not over-react (inspect, never replace).
  Step 3 PHYSICAL SANITY. True RUL falls ~1 per cycle; an UPWARD jump in the RUL history is
    physically impossible and corroborates an adverse shift.
  Step 4 DECIDE, weighing that a MISS is worse than a false alarm, but that false alarms on
    benign flight-class variation are still a cost to avoid.

Write your four steps briefly (quote the numbers you used), then on the LAST line output:
FINAL: {{"shift_detected": true|false, "shift_direction": "adverse"|"favorable"|"none",
  "reliability": "high"|"medium"|"low", "decision": "continue"|"inspect"|"replace",
  "confidence": 0.0-1.0, "reasoning": "<one sentence>"}}"""


def _fmt_channel_block(feat):
    lines = []
    for v in C.INPUT_VARS:
        zg = feat["z_global"][v]
        rz = feat["regime_z"].get(v)
        cz = feat["consistency_z"].get(v)
        tag = ""
        if rz is not None:
            tag = f"  regime_z={rz:+.2f}  consistency_z={cz:+.2f}"
        star = " <TEMP>" if v in C.TEMP_CHANNELS else ""
        lines.append(f"  {v:5s} z_global={zg:+.2f}{tag}{star}")
    return "\n".join(lines)


def build_user(packet):
    r = packet["rul"]
    ctx = packet["context"]
    agg = packet["features"]["agg"]
    hist = " -> ".join(f"{h:.0f}" for h in r["history"])
    return f"""DECISION POINT — unit {packet['unit']}, cycle {packet['cycle']}, flight class {ctx['flight_class']}.

[1] RUL MODEL OUTPUT
  point estimate      : {r['point']:.1f} cycles
  MC-Dropout mean/std : {r['mc_mean']:.1f} / {r['mc_std']:.2f}   (std rises out-of-distribution)
  recent RUL history  : {hist}   (must DECREASE ~1/cycle; an upward jump is impossible)

[2] SENSOR STATISTICS  (per channel; TEMP = gas-path temperatures)
{_fmt_channel_block(packet['features'])}
  summary: temp regime_z(signed)={agg['temp_regime_z_signed']:+.2f}, temp consistency_z(abs)={agg['temp_consistency_z_abs']:.2f},
           all|z_global|={agg['all_z_global_absmean']:.2f}, all|regime_z|={agg['all_regime_z_absmean']:.2f}, all|consistency_z|={agg['all_consistency_z_absmean']:.2f}

[3] OPERATIONAL CONTEXT
  altitude(mean)={ctx['altitude_mean']:.0f}, Mach={ctx['mach_mean']:.3f}, Nf={ctx['fan_speed_Nf']:.1f}, Nc={ctx['core_speed_Nc']:.1f}

Work through Step 1 (quote temp consistency_z and temp regime_z and apply the CAUSE GATE),
then Steps 2-4, then end with the FINAL: {...} line."""


def build_messages(packet):
    return [{"role": "system", "content": SYSTEM},
            {"role": "user", "content": build_user(packet)}]
