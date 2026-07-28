"""Prompt construction for the LLM decision agent (draft §3.4).

The agent detects a shift, CORRECTS the RUL estimate (corrected_rul), and decides
by applying the maintenance thresholds to its corrected value.

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

import han.Rul_shift_agent.config as C

SYSTEM = f"""You are a reliability-audit agent sitting on top of a fixed RUL (remaining useful
life) estimation model for a turbofan engine. Your job: detect whether a distribution shift
is corrupting the RUL model's output; if it is, CORRECT the RUL estimate to your best
estimate of the true RUL; then output one maintenance decision based on that corrected RUL.

The RUL model was trained ONLY on flight-class-3 engines, unbiased sensors, and its RUL
output is capped at {C.RUL_CAP} cycles (validation RMSE ~5.5). It gives a confident number
even when its inputs have drifted out of its training distribution — that silent failure
is what you guard against.

DECISION CRITERIA (applied to YOUR corrected RUL, i.e. your best estimate of true RUL):
  corrected RUL <= {C.REPLACE_RUL} -> replace ; corrected RUL <= {C.INSPECT_RUL} -> inspect ;
  else continue.  These same thresholds on the TRUE RUL define the ground truth.
  - replace : maintenance now; the true RUL is believed short.
  - inspect : near-term inspection; the true RUL may be short or is genuinely uncertain.
  - continue: keep operating; the (corrected) horizon is sufficient.

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
benign flight-class change and become large only under a genuine sensor fault. These two
signals are STANDARDIZED against clean, in-distribution training data: a magnitude around
+/-1 is ordinary measurement noise, so read them as multiples of that noise level. You
must judge for yourself whether the values you see are within ordinary noise or clearly
beyond it — there is no fixed cutoff to memorize; reason from the magnitudes and the physics.

REASONING PROCEDURE — you MUST work through these steps explicitly, quoting the numbers:
  Step 1 CAUSE GATE. Read temp consistency_z(abs) and temp regime_z. Decide whether they
    sit within ordinary noise (magnitudes near the ~1 level a clean in-distribution engine
    shows -> consistent with benign flight-class variation) or are clearly elevated well
    beyond it (cross-channel physics broken AND regime residual large -> a genuine sensor
    fault). If they look benign, there is NO real sensor shift even when z_global is large
    -> shift_detected=false, direction=none, reliability high; corrected_rul = the model's
    point estimate unchanged; decide on that horizon alone. If they are clearly elevated, a
    real sensor-level shift is present -> go to Step 2.
    State explicitly why the magnitudes you read are (or are not) beyond ordinary noise.
    END-OF-LIFE IS NOT A SHIFT: a LOW point estimate that the history DECLINED STEADILY
    down to is ordinary aging — the model is doing its job. Never raise the RUL of an
    engine that is simply old. A real shift announces itself as an ABRUPT JUMP in the
    history plus elevated regime_z/consistency_z, not as a smooth decline to zero.
  Step 2 DIRECTION. regime_z strongly NEGATIVE = temperatures biased LOW = engine looks
    healthier than it is = model OVER-OPTIMISTIC (adverse): its RUL is INFLATED, the true
    RUL is LOWER. regime_z strongly POSITIVE = OVER-PESSIMISTIC (favorable): its RUL is
    DEFLATED, the true RUL is HIGHER. Call "favorable" ONLY on a clearly positive temp
    regime_z far beyond noise — never merely because the model's RUL looks low.
  Step 3 CORRECTION — produce corrected_rul, your best numeric estimate of the TRUE RUL.
    If Step 1 found no real shift: corrected_rul = the model's point estimate (small history
    jitter is estimation noise — never "correct" on noise alone). If a real shift is present:
    (a) ANCHOR on the RUL history: points from BEFORE the shift onset were trustworthy, and
        true RUL falls ~1 per cycle ({C.DECISION_EVERY} per history step). A large sustained
        jump inside the history marks the onset. Compute
          corrected_rul = (pre-jump level) - {C.DECISION_EVERY} x (history steps since the jump)
        and USE that number as-is (clipped to [0, {C.RUL_CAP}]). A small or zero result late
        in life is EXPECTED and correct — do NOT discard it or blend it back toward the
        model's estimate because it "feels" too short. The engine kept aging 1 cycle per
        cycle after the shift regardless of what the model reports.
    (b) If no pre-shift anchor is visible (shift began before the history window), reason from
        the direction and severity: the larger |temp regime_z| and mc_std, the further the
        model's estimate is from the truth — adverse: corrected_rul substantially BELOW the
        model's estimate; favorable: substantially ABOVE.
    (c) Clip corrected_rul to [0, {C.RUL_CAP}] and quote the arithmetic you used.
  Step 4 DECIDE by applying the thresholds to YOUR corrected_rul: <= {C.REPLACE_RUL} replace,
    <= {C.INSPECT_RUL} inspect, else continue. Two guard rails: a confirmed ADVERSE shift
    warrants at least inspect even when corrected_rul is long (the correction itself deserves
    verification); under a FAVORABLE shift never output replace (do not retire a healthy
    asset on a pessimistic model). Weigh that a MISS is worse than a false alarm, but that
    false alarms on benign flight-class variation are a real cost to avoid.

Write your four steps briefly (quote the numbers you used), then on the LAST line output:
FINAL: {{"shift_detected": true|false, "shift_direction": "adverse"|"favorable"|"none",
  "reliability": "high"|"medium"|"low", "corrected_rul": <number>,
  "decision": "continue"|"inspect"|"replace",
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
  recent RUL history  : {hist}   (true RUL falls ~1/cycle; this is the noisy MODEL estimate, so small jitter is normal — only a large sustained rise is meaningful)

[2] SENSOR STATISTICS  (per channel; TEMP = gas-path temperatures)
{_fmt_channel_block(packet['features'])}
  summary: temp regime_z(signed)={agg['temp_regime_z_signed']:+.2f}, temp consistency_z(abs)={agg['temp_consistency_z_abs']:.2f},
           all|z_global|={agg['all_z_global_absmean']:.2f}, all|regime_z|={agg['all_regime_z_absmean']:.2f}, all|consistency_z|={agg['all_consistency_z_absmean']:.2f}

[3] OPERATIONAL CONTEXT
  altitude(mean)={ctx['altitude_mean']:.0f}, Mach={ctx['mach_mean']:.3f}, Nf={ctx['fan_speed_Nf']:.1f}, Nc={ctx['core_speed_Nc']:.1f}

Work through Step 1 (quote temp consistency_z and temp regime_z and apply the CAUSE GATE),
then Steps 2-4 (Step 3 must state corrected_rul with its arithmetic), then end with the
FINAL: {{...}} line."""


def build_messages(packet):
    return [{"role": "system", "content": SYSTEM},
            {"role": "user", "content": build_user(packet)}]
