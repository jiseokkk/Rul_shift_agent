"""Pure sensor-fault injection math for the 0804 corrupted dataset (spec: docs/
0804_cusum_pca_baseline_experiment.md §2.2).

Operates on NATIVE 1 Hz per-cycle series (injection happens before decimation,
§2.1).  numpy only -- no torch, no RUL model, no detector dependencies, so the
same engine serves the later OC-MLP/GDN/LLM stages.

Modes: add / gain / noise / stuck.  Profiles: step / ramp15 / ramp40 with
b(c) = min(1, (c - c0 + 1)/L)  (off-by-one corrected: b(c0) = 1/L > 0).
stuck = stuck-at-last-value: freeze at the last native sample of cycle c0-1.
"""
from dataclasses import dataclass, field, asdict

import numpy as np

import han.rul_agent_project.src.config as C

ENGINE_VERSION = "0804.1"
XS_N = len(C.XS_VARS)
GAIN_REF_EPS = 1e-3          # |train mean| guard for the gain denominator (§2.2)


@dataclass
class FaultSpec:
    scenario_id: str
    block: str                       # controls|A|B|C|D|E|F|DEV
    category: str                    # control | sensor_fault | adversarial
    split: str                       # test | dev
    unit: int
    mode: str                        # none|add|gain|noise|stuck
    channels: tuple = ()             # Xs channel names
    profile: str = "none"            # none|step|ramp15|ramp40
    ramp_len: int = 0                # 0 for step/stuck
    onset_frac: float = 0.45
    direction: int = 0               # +1 / -1 (0: noise/stuck/control)
    sigma_mult: float = 0.0
    seed: int = 0
    channel_mult: dict = field(default_factory=dict)   # name -> multiplier
                                                       # (temp4-mix / pc1 loadings)

    def onset_cycle(self, life):
        return int(round(self.onset_frac * life))


def profile_b(spec, c, c0):
    """Injection envelope b(c) for cycle id c (0 before onset)."""
    if c < c0:
        return 0.0
    if spec.profile == "step" or spec.ramp_len == 0:
        return 1.0
    return min(1.0, (c - c0 + 1) / spec.ramp_len)


def inject(series, cycles, spec, ch_std, ch_mean):
    """Apply `spec` to native per-cycle series.

    series : list of (T_c,18) float32 arrays (INPUT_VARS order), cycle order
    cycles : (Ncyc,) int cycle ids (1..life)
    ch_std/ch_mean : (18,) train statistics (feature_models.npz)

    Returns (corrupted_series, extras) -- extras carries the spec.json
    physical-unit fields (delta_raw, gain, stuck bookkeeping).
    """
    life = len(cycles)
    c0 = spec.onset_cycle(life)
    ch_idx = [C.INPUT_VARS.index(ch) for ch in spec.channels]
    for j, ch in zip(ch_idx, spec.channels):
        if j >= XS_N:
            raise ValueError(f"injection restricted to X_s channels, got {ch}")

    mult = np.array([spec.channel_mult.get(ch, 1.0) for ch in spec.channels])
    # full-magnitude physical delta per channel (before profile envelope)
    delta_raw = {ch: float(spec.direction * spec.sigma_mult * ch_std[j] * m)
                 for ch, j, m in zip(spec.channels, ch_idx, mult)}
    extras = {"onset_cycle": c0, "delta_raw": delta_raw}

    out = [s.copy() for s in series]
    if spec.mode == "none":
        return out, extras

    if spec.mode == "gain":
        gain = {}
        for ch, j in zip(spec.channels, ch_idx):
            ref = float(ch_mean[j])
            if abs(ref) < GAIN_REF_EPS:            # §2.2 denominator guard
                raise ValueError(f"gain injection forbidden on near-zero-mean "
                                 f"channel {ch} (ref={ref})")
            gain[ch] = {"gain_reference_type": "train_mean",
                        "gain_reference_value": ref,
                        "gamma": delta_raw[ch] / ref}
        extras["gain"] = gain

    if spec.mode == "stuck":
        pos0 = int(np.searchsorted(cycles, c0))
        if pos0 == 0:
            raise ValueError("stuck onset at first cycle: no last normal sample")
        src = series[pos0 - 1][-1]                 # last native sample of c0-1
        extras["stuck"] = {
            "stuck_value": {ch: float(src[j]) for ch, j in zip(spec.channels, ch_idx)},
            "stuck_source_index": int(sum(len(s) for s in series[:pos0]) - 1),
        }

    rng = np.random.default_rng(spec.seed)
    for pos, c in enumerate(cycles):
        b = profile_b(spec, int(c), c0)
        if b == 0.0 and spec.mode != "noise":
            continue
        x = out[pos]
        for ch, j, m in zip(spec.channels, ch_idx, mult):
            if spec.mode == "add":
                x[:, j] += delta_raw[ch] * b
            elif spec.mode == "gain":
                x[:, j] *= (1.0 + extras["gain"][ch]["gamma"] * b)
            elif spec.mode == "noise":
                # draw every cycle (deterministic stream) but add only post-onset
                eps = rng.normal(0.0, 1.0, size=len(x)).astype(np.float32)
                if b > 0.0:
                    x[:, j] += eps * (spec.sigma_mult * ch_std[j] * m * b)
            elif spec.mode == "stuck":
                x[:, j] = extras["stuck"]["stuck_value"][ch]
            else:
                raise ValueError(f"unknown mode {spec.mode}")
    return out, extras


def spec_dict(spec, extras, life, fc, git_hash, created):
    """Assemble the full spec.json payload (0804 §2.5)."""
    d = asdict(spec)
    d["channels"] = list(spec.channels)
    d.update({
        "flight_class": fc, "life_cycles": life,
        "onset_cycle": extras["onset_cycle"],
        "delta_raw": extras["delta_raw"],
        "injection_level": "native_1hz",
        "provenance": {"git_hash": git_hash, "created": created,
                       "engine_version": ENGINE_VERSION},
    })
    for k in ("gain", "stuck"):
        if k in extras:
            d[k] = extras[k]
    return d
