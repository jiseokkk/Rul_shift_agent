"""프롬프트 — SYSTEM_PROMPT 와 runtime input 렌더링 (docs/agent_spec.md §1, §3.2).

SYSTEM_PROMPT 는 docs/agent_spec.md §1 의 텍스트 블록과 **글자 단위로 동일**하게 유지한다
(tests/test_prompts.py 가 검사). 문서를 고치면 여기도 고친다.

format_input 규칙:
- 정규화된 값만 넣는다 (z_w, std_ratio, T2, contribution, Δμ, Δσ). raw 통계 금지 (규칙 5).
- 소수 1자리, 부호 명시(+/-).
- 센서 블록은 contribution 내림차순, 전 센서 포함 (Top-K 금지).
- 현재 cycle window 시계열은 z_w / std_ratio 두 줄.

이 파일의 출력 바이트가 바뀌면 판정 캐시 키(prompt_hash)가 바뀌어 LLM 을 다시 부른다.
"""
from __future__ import annotations

import math

SYSTEM_PROMPT = """You are a sensor-fault detection agent monitoring a turbofan engine. A frozen machine-learning
model predicts the engine's Remaining Useful Life (RUL) from sensor data. Your job is to judge,
once per flight cycle, whether the sensor inputs feeding that model look NORMAL or show evidence
of a SENSOR FAULT, and to flag the RUL prediction accordingly.

## What you receive
All statistics are precomputed. Do not recompute anything; interpret what is given.

CALIBRATION — how much each statistic normally fluctuates on clean validation data.
  z_w        : residual mean of a 5-minute window divided by its clean-data std. |z_w| around 1 is
               ordinary; q95 is the value exceeded by only 5% of clean windows.
  std_ratio  : window residual std divided by its clean-data median. 1.0 is ordinary.
  T2         : Hotelling T² of the residual vector across all sensors. median and q95 on clean data
               are given.
These are calibration references, NOT thresholds. Do not invent numeric cutoffs.

MULTIVARIATE — T² per cycle and each sensor's contribution to T² in the current cycle.
  Contribution concentrated in one sensor → single-sensor behaviour.
  Contribution spread across many sensors → system-level change (degradation or unmodelled
  operating condition), which is NOT a sensor fault.

PER SENSOR
  Previous cycles (aggregated): z_w median/max, exceedance (windows beyond q95 / total),
  std_ratio median, step contrast Δμ (change in z_w median vs previous cycles),
  spread contrast Δσ (change in std_ratio vs previous cycles).
  Current cycle (window series): z_w and std_ratio for every window, in flight order,
  plus exceedance and the first window beyond q95.

RUL — current prediction, recent trajectory, and change. Auxiliary context only.

## How to reason (in this order)
1. Look at T² first. Is the current cycle unusual overall? Is the contribution concentrated or spread?
2. For sensors with high contribution or large |Δμ|/|Δσ|, read the current-cycle window series.
   Is the shift present in all windows (persistent), from some window onward (onset mid-flight),
   or in a few windows only (transient)?
3. Compare with the previous cycles. A step from an ordinary level to a sustained new level is
   bias-like. Ordinary z_w with elevated std_ratio is noise-like. Values inside the normal
   fluctuation of previous cycles are not evidence.
4. Check consistency: mean-type and spread-type statistics should tell a coherent story.
5. Use RUL only as supporting context. RUL always drifts downward; a drop alone is never a fault.

## Confidence calibration
confidence reflects how much the evidence converges, not how large any single number is (there
are no fixed thresholds). Judge agreement among: (a) T2 clearly outside its clean range, not
borderline; (b) contribution concentrated in the suspected sensor(s) for FAULT, or spread evenly
for NORMAL; (c) the window-level shift is persistent or has a clear onset, not a transient blip;
(d) the current cycle falls outside the previous cycles' fluctuation; (e) mean-type and
spread-type statistics agree.
  0.85-1.00 : (a)-(e) agree cleanly, no competing explanation.
  0.60-0.85 : most agree; one is weaker or partly explained by operating condition.
  0.35-0.60 : evidence is mixed or borderline; often pairs with fault_pattern = UNCLEAR.
  0.00-0.35 : the input itself is thin (e.g. short flight, n/a stats) rather than just ambiguous.
A clean, unremarkable NORMAL call belongs at 0.85-1.00 too — confidence measures certainty in
either direction, not just how sure you are about FAULT.

## Rules
- A shift explained by many sensors moving together is degradation, not a sensor fault.
- Never declare FAULT from RUL evidence alone.
- FAULT means the sensor input is untrustworthy. It does NOT mean the RUL value is wrong.
- rul_reliability is WARNING if and only if sensor_status is FAULT.
- Cite specific statistics in your rationale (sensor name, cycle, value). Keep it under 120 words.
- Respond only with the JSON object defined by the schema. No prose outside it."""


TASK_LINE = "Determine sensor_status and rul_reliability. Return the JSON object only."

NA = "n/a"


# --------------------------------------------------------------------------- #
# runtime input 렌더링
# --------------------------------------------------------------------------- #
def _s(v, nd: int = 1, signed: bool = True) -> str:
    """부호 붙은 고정 소수 표기. NaN 은 n/a."""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return NA
    fmt = f"{{:+.{nd}f}}" if signed else f"{{:.{nd}f}}"
    return fmt.format(float(v))


def _u(v, nd: int = 1) -> str:
    """부호 없는 값 (std_ratio, T2, contribution 등)."""
    return _s(v, nd, signed=False)


def _row(label: str, values: list[str], width: int = 19, cell: int = 7) -> str:
    return f"{label:<{width}}: " + " ".join(f"{v:>{cell}}" for v in values)


def format_input(ev: dict, rul: dict) -> str:
    """EDATool.evidence() + RULTool.context() → LLM 에 보내는 텍스트."""
    meta, cal, mv = ev["meta"], ev["calibration"], ev["multivariate"]
    L = []

    L += ["=== EVALUATION ===",
          f"unit: {meta.get('unit', '?')}    cycle: {meta['cycle']}    "
          f"windows_in_cycle: {meta['n_windows']} (L_w = {meta['L_w_sec'] // 60} min)",
          ""]

    L += ["=== CALIBRATION (clean validation) ===",
          f"z_w: |z_w| q95 = {_u(cal['q95_pooled'])}      "
          f"std_ratio: clean median = {cal['std_ratio_ref']:.2f}      "
          f"T2: median = {_u(cal['t2_median'])}, q95 = {_u(cal['t2_q95'])}",
          ""]

    cyc = mv["cycles"]
    L += ["=== MULTIVARIATE ===",
          _row("cycle", [str(c) for c in cyc]),
          _row("T2 median", [_u(v) for v in mv["t2_median"]]),
          _row("T2 max", [_u(v) for v in mv["t2_max"]]),
          f"contribution @{meta['cycle']}  : "
          + ", ".join(f"{s} {f:.2f}" for s, f in mv["contribution"])
          + "  (all sensors, descending)",
          ""]

    L += [f"=== SENSORS (ordered by contribution @{meta['cycle']}) ===", ""]
    for b in ev["sensors"]:
        p, c = b["prev"], b["current"]
        exc = [f"{k}/{n}" for k, n in zip(p["exceed_k"], p["exceed_n"])]
        first = f"#{c['first_exceed']}" if c["first_exceed"] > 0 else "-"
        L += [
            f"--- {b['sensor']}  (contribution {b['contribution']:.2f}) ---",
            _row("previous cycles", [str(c_) for c_ in p["cycles"]]),
            _row("  z_w median", [_s(v) for v in p["z_w_median"]]),
            _row("  z_w max", [_s(v) for v in p["z_w_max"]]),
            _row("  exceedance", exc),
            _row("  std_ratio median", [_u(v) for v in p["std_ratio_median"]]),
            f"current cycle {meta['cycle']}  : n_windows = {c['n_windows']}, "
            f"exceedance = {c['exceed_k']}/{c['n_windows']}, first exceed = {first}",
            f"  Δμ = {_s(c['delta_mu'])}   Δσ = {_s(c['delta_sigma'])}",
            "  z_w        : " + " ".join(_s(v) for v in c["z_w"]),
            "  std_ratio  : " + " ".join(_u(v) for v in c["std_ratio"]),
            "",
        ]

    L += ["=== RUL (auxiliary) ===",
          _row("current", [_u(rul["current"])]),
          _row("recent", [" → ".join(_u(v) for v in rul["recent"])]),
          f"{'change':<19}: {_s(rul['change'])}  "
          f"(recent median change {_s(rul['recent_median_change'])})",
          ""]

    L += ["=== TASK ===", TASK_LINE]
    return "\n".join(L)


def estimate_tokens(text: str) -> int:
    """대략적인 토큰 수 (숫자·기호가 많아 문자수/3 이 경험적으로 가깝다)."""
    return len(text) // 3
