"""Decision agent: LLM (vLLM + local Qwen) or a rule-based reference, plus the
shared Tier-2 decision policy.

  --agent llm   : Qwen (vLLM, AWQ) reads the prompt, 5 samples/point, majority vote.
  --agent rule  : deterministic reference using the SAME signals — lets the whole
                  pipeline run without the LLM and doubles as a "features + rules,
                  no LLM" ablation.

CUSUM is NOT used here — it stays a pure comparison baseline (baselines.py).

Each vote carries a CORRECTED RUL (the agent's best estimate of the true RUL under
the detected shift).  The final decision thresholds the effective RUL: corrected
(median over samples) once the shift is confirmed, the model's raw estimate otherwise.

Tier-2 policy (applied identically to both agents, over the raw votes):
  #5 hysteresis   : the correction is trusted only after the shift persists
                    HYSTERESIS_N consecutive decision points -> a transient shift
                    vote cannot trigger a false correction (Case C false alarms).
  #6 cost-aware   : guard rails around the correction — a confirmed adverse shift
                    floors the action at inspect (the correction itself needs
                    verifying); a favorable shift caps it at inspect (never retire
                    a healthy asset); low confidence prefers the safe middle.
"""
import argparse
import json
from collections import Counter, defaultdict

import numpy as np

import han.Rul_shift_agent.core.config as C
from han.Rul_shift_agent.llmshift.prompt import build_messages

PKT_PATH = C.PKT_DIR + "/packets.json"

# Default ablation config: every Tier-1 signal + Tier-2 mechanism ON.
ABL_FULL = {
    "use_regime": True,        # Tier-1 #1
    "use_consistency": True,   # Tier-1 #2
    "use_uncertainty": True,   # Tier-1 #3
    "hysteresis": True,        # Tier-2 #5
    "cost_aware": True,        # Tier-2 #6
}


# --------------------------------------------------------------------------- #
# Vote aggregation
# --------------------------------------------------------------------------- #
def aggregate(votes):
    """votes: list of per-sample dicts -> aggregated summary."""
    def frac(key, val):
        v = [x for x in votes if x.get(key) is not None]
        return sum(1 for x in v if x.get(key) == val) / len(v) if v else 0.0

    dec = Counter(x.get("decision", "continue") for x in votes)
    maj_dec = max(C.DECISIONS, key=lambda d: (dec.get(d, 0), C.DEC_LEVEL[d]))
    dirs = Counter(x.get("shift_direction", "none") for x in votes)
    maj_dir = dirs.most_common(1)[0][0]
    shift_frac = sum(1 for x in votes if x.get("shift_detected")) / max(1, len(votes))
    conf = np.mean([float(x.get("confidence", 0.5)) for x in votes]) if votes else 0.5
    rel = Counter(x.get("reliability", "high") for x in votes).most_common(1)[0][0]
    # corrected RUL: median over valid numeric samples (robust to one bad parse)
    corr = [float(x["corrected_rul"]) for x in votes
            if isinstance(x.get("corrected_rul"), (int, float))]
    corrected = float(np.clip(np.median(corr), 0.0, C.RUL_CAP)) if corr else None
    return {"decision": maj_dec, "shift_detected": shift_frac >= 0.5,
            "shift_frac": round(shift_frac, 2), "shift_direction": maj_dir,
            "reliability": rel, "confidence": round(float(conf), 2),
            "corrected_rul": None if corrected is None else round(corrected, 2),
            "agreement": round(dec[maj_dec] / max(1, len(votes)), 2)}


# --------------------------------------------------------------------------- #
# Tier-2 decision policy
# --------------------------------------------------------------------------- #
def _threshold_decision(rul):
    if rul <= C.REPLACE_RUL:
        return "replace"
    if rul <= C.INSPECT_RUL:
        return "inspect"
    return "continue"


def apply_policy(packet, agg, state, abl=ABL_FULL):
    """state: mutable dict per (scenario,unit) holding the hysteresis counter.

    Decision rule: threshold the EFFECTIVE RUL — the agent's corrected RUL once a
    shift is confirmed (hysteresis), the model's raw estimate otherwise.  The
    hysteresis gate keeps a single transient shift vote from triggering a false
    correction (Case C natural-shift false alarms)."""
    rul_raw = packet["rul"]["point"]
    shift = agg["shift_detected"]
    direction = agg["shift_direction"]
    corrected = agg.get("corrected_rul")

    # hysteresis counter over consecutive shift-detected points
    state["run"] = state.get("run", 0) + 1 if shift else 0
    need = C.HYSTERESIS_N if abl["hysteresis"] else 1
    confirmed = shift and state["run"] >= need

    # ---- Tier-2 #5 hysteresis gates the correction ----
    use_corr = bool(confirmed and direction != "none" and corrected is not None)
    rul_eff = corrected if use_corr else rul_raw

    lvl = C.DEC_LEVEL[_threshold_decision(rul_eff)]

    # ---- Tier-2 #6 cost-aware guard rails around the correction ----
    if abl["cost_aware"]:
        if confirmed and direction == "adverse":
            # a confirmed adverse shift deserves at least a look, even if the
            # corrected horizon is long — the correction itself needs verifying.
            lvl = max(lvl, C.DEC_LEVEL["inspect"])
        if confirmed and direction == "favorable":
            # over-pessimistic model: never retire a possibly-healthy asset.
            lvl = min(lvl, C.DEC_LEVEL["inspect"])
        if agg["confidence"] < 0.5 and lvl == C.DEC_LEVEL["continue"] and shift:
            lvl = C.DEC_LEVEL["inspect"]             # abstain to the safe middle

    final = C.DECISIONS[lvl]
    return final, {"confirmed_shift": bool(confirmed), "run": state["run"],
                   "rul_used": round(float(rul_eff), 2),
                   "correction_applied": use_corr}


def finalize(packets, raw_votes_by_key, abl=ABL_FULL):
    """raw_votes_by_key: {(scenario,unit,cycle): [vote dicts]} -> decision rows."""
    rows = []
    states = defaultdict(dict)
    groups = defaultdict(list)
    for i, p in enumerate(packets):
        groups[(p["scenario"], p["unit"])].append(i)
    for key, idxs in groups.items():
        idxs.sort(key=lambda i: packets[i]["cycle"])
        for i in idxs:
            p = packets[i]
            votes = raw_votes_by_key.get((p["scenario"], p["unit"], p["cycle"]), [])
            agg = aggregate(votes)
            final, meta = apply_policy(p, agg, states[key], abl)
            rows.append({
                "scenario": p["scenario"], "unit": p["unit"], "cycle": p["cycle"],
                "gt_label": p["gt_label"], "true_rul": p["true_rul"],
                "rul_point": p["rul"]["point"], "mc_std": p["rul"]["mc_std"],
                "agent_raw": agg["decision"], "agent": final,
                "corrected_rul": agg.get("corrected_rul"), "rul_used": meta["rul_used"],
                "correction_applied": meta["correction_applied"],
                "shift_detected": agg["shift_detected"], "shift_frac": agg["shift_frac"],
                "shift_direction": agg["shift_direction"], "confirmed_shift": meta["confirmed_shift"],
                "reliability": agg["reliability"], "confidence": agg["confidence"],
                "agreement": agg["agreement"],
            })
    return rows


# --------------------------------------------------------------------------- #
# Rule-based reference agent (no LLM)
# --------------------------------------------------------------------------- #
def _history_correction(packet):
    """Corrected RUL from the RUL history: the largest step-jump marks the shift
    onset; the pre-jump estimate was trustworthy and true RUL falls 1/cycle, so
    extrapolate it down to now.  None if no onset jump is visible."""
    h = packet["rul"]["history"]
    jumps = [abs(h[i + 1] - h[i]) for i in range(len(h) - 1)]
    if not jumps or max(jumps) < C.CORR_JUMP:
        return None
    i = int(np.argmax(jumps))                  # last trusted point sits before the jump
    steps_since = (len(h) - 1) - i
    return float(np.clip(h[i] - C.DECISION_EVERY * steps_since, 0.0, C.RUL_CAP))


def rule_vote(packet, rng, abl=ABL_FULL):
    agg = packet["features"]["agg"]
    rul = packet["rul"]["point"]
    cons = agg["temp_consistency_z_abs"] if abl["use_consistency"] else 0.0
    max_cons = agg["max_consistency_z_abs"] if abl["use_consistency"] else 0.0
    regime = agg["temp_regime_z_signed"] if abl["use_regime"] else 0.0
    mc_std = packet["rul"]["mc_std"] if abl["use_uncertainty"] else 0.0

    # real sensor-level shift needs BOTH cross-channel inconsistency and regime deviation.
    # With those Tier-1 signals ablated, the agent falls back to the marginal global z
    # (the same marginal view CUSUM has) and can no longer separate cause -> baseline
    # failure mode.  CUSUM itself is not consulted here (it is a pure baseline).
    if abl["use_consistency"] or abl["use_regime"]:
        real_shift = (cons > 3.0 and abs(regime) > 5.0) or max_cons > 6.0
        direction = ("adverse" if regime < 0 else "favorable") if real_shift else "none"
    else:
        gz = agg["all_z_global_absmean"]
        real_shift = gz > 0.6
        direction = "adverse" if real_shift else "none"   # direction-blind fallback

    # deterministic RUL correction: anchor on the pre-shift history level and
    # extrapolate at 1 cycle/cycle (the same procedure the LLM prompt prescribes);
    # if no onset jump is visible, fall back to a regime_z-proportional correction.
    if real_shift and direction != "none":
        corrected = _history_correction(packet)
        if corrected is None:
            corrected = float(np.clip(rul + C.RULE_CORR_GAIN * regime, 0.0, C.RUL_CAP))
    else:
        corrected = float(rul)

    # decision from the corrected horizon
    dec = _threshold_decision(corrected)
    if real_shift and direction == "adverse":
        dec = "inspect" if dec == "continue" else dec

    reliability = "low" if (real_shift and direction == "adverse") else (
        "medium" if real_shift else "high")
    mag = min(1.0, 0.5 + 0.1 * cons + 0.3 * (mc_std > 3))
    conf = float(np.clip(mag + rng.normal(0, 0.03), 0.0, 1.0))
    return {"shift_detected": bool(real_shift), "shift_direction": direction,
            "reliability": reliability, "corrected_rul": round(corrected, 2),
            "decision": dec, "confidence": round(conf, 2),
            "reasoning": "rule"}


def run_rule(packets, samples=C.LLM_SAMPLES, seed=C.SEED, abl=ABL_FULL):
    rng = np.random.default_rng(seed)
    votes = defaultdict(list)
    for p in packets:
        for _ in range(samples):
            votes[(p["scenario"], p["unit"], p["cycle"])].append(rule_vote(p, rng, abl))
    return votes


# --------------------------------------------------------------------------- #
# LLM agent (vLLM + local Qwen AWQ)
# --------------------------------------------------------------------------- #
def parse_json(text):
    """Extract the FINAL decision object.  The reasoning may contain LaTeX braces
    (\\text{...}) or quoted JSON templates, so a first-{-to-last-} slice is not
    reliable: scan '{' positions from the END and return the first valid dict that
    carries a decision — that is the FINAL line's object."""
    dec = json.JSONDecoder()
    fallback = None
    for i in range(len(text) - 1, -1, -1):
        if text[i] != "{":
            continue
        try:
            obj, _ = dec.raw_decode(text[i:])
        except Exception:
            continue
        if isinstance(obj, dict):
            if "decision" in obj:
                return obj
            fallback = fallback or obj
    return fallback or {"parse_error": True}


def run_llm(packets, samples=C.LLM_SAMPLES, gpu_mem=0.90, raw_path=None):
    import os
    os.environ.setdefault("VLLM_USE_FLASHINFER_SAMPLER", "0")
    from vllm import LLM, SamplingParams
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(C.LLM_PATH, trust_remote_code=True)
    llm = LLM(model=C.LLM_PATH, quantization="awq", dtype="float16",
              gpu_memory_utilization=gpu_mem, max_model_len=8192, trust_remote_code=True)
    sp = SamplingParams(temperature=C.LLM_TEMPERATURE, max_tokens=C.LLM_MAX_TOKENS, n=samples)

    prompts = [tok.apply_chat_template(build_messages(p), tokenize=False,
                                       add_generation_prompt=True) for p in packets]
    outs = llm.generate(prompts, sp)

    votes = defaultdict(list)
    raw_fh = open(raw_path, "w") if raw_path else None
    for p, o in zip(packets, outs):
        key = (p["scenario"], p["unit"], p["cycle"])
        for comp in o.outputs:
            j = parse_json(comp.text)
            votes[key].append(j)
            if raw_fh:
                raw_fh.write(json.dumps({"key": list(key), "text": comp.text,
                                         "parsed": j}) + "\n")
    if raw_fh:
        raw_fh.close()
    return votes


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", choices=["rule", "llm"], default="rule")
    ap.add_argument("--gpu_mem", type=float, default=0.90)
    args = ap.parse_args()

    with open(PKT_PATH) as f:
        packets = json.load(f)

    if args.agent == "rule":
        votes = run_rule(packets)
        out = C.RES_DIR + "/agent_decisions_rule.json"
    else:
        raw = C.PKT_DIR + "/agent_results_qwen.jsonl"
        votes = run_llm(packets, gpu_mem=args.gpu_mem, raw_path=raw)
        out = C.RES_DIR + "/agent_decisions_llm.json"

    rows = finalize(packets, votes)
    with open(out, "w") as f:
        json.dump(rows, f, indent=1)
    print(f"[agent:{args.agent}] wrote {len(rows)} decisions -> {out}")


if __name__ == "__main__":
    main()
