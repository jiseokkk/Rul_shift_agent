"""Central configuration for the N-CMAPSS distribution-shift-aware RUL agent.

Paper concept (draft_v2): an LLM agent sits as a *decision layer* over a fixed
RUL model, integrating preprocessed sensor statistics + operational context +
RUL output to make shift-aware maintenance decisions (replace / inspect /
continue).  This repo reproduces that pipeline on N-CMAPSS DS02-006 and adds the
Tier-1 / Tier-2 improvements discussed with the author.

Run everything with the LLMshift interpreter:
    /home/iai4/miniconda3/envs/LLMshift/bin/python
"""
import os

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
HERE = os.path.dirname(os.path.abspath(__file__))
DATA_H5 = "/home/iai4/Desktop/han/dataset/data_set/N-CMAPSS_DS02-006.h5"

OUT_DIR = os.path.join(HERE, "outputs")     # model weights, scaler, baselines, feature models
PKT_DIR = os.path.join(HERE, "packets")     # decision-point packets + agent raw outputs
RES_DIR = os.path.join(HERE, "results")     # metrics.json, report.md
FIG_DIR = os.path.join(HERE, "figures")     # figures 1-3
for _d in (OUT_DIR, PKT_DIR, RES_DIR, FIG_DIR):
    os.makedirs(_d, exist_ok=True)

# --------------------------------------------------------------------------- #
# Channels  (verified against the HDF5)
#   X_s (14 measured) + W (4 operating-condition descriptors) = 18 input channels
# --------------------------------------------------------------------------- #
XS_VARS = ["T24", "T30", "T48", "T50", "P15", "P2", "P21", "P24",
           "Ps30", "P40", "P50", "Nf", "Nc", "Wf"]          # 14 measured sensors
W_VARS = ["alt", "Mach", "TRA", "T2"]                        # 4 operating-condition
INPUT_VARS = XS_VARS + W_VARS                                # 18 model input channels
N_INPUT = len(INPUT_VARS)                                    # 18

# Gas-path temperature channels used for Direction-A sensor-bias injection
TEMP_CHANNELS = ["T24", "T30", "T48", "T50"]
TEMP_IDX = [INPUT_VARS.index(c) for c in TEMP_CHANNELS]      # [0,1,2,3]

# --------------------------------------------------------------------------- #
# Unit / flight-class splits  (verified against the HDF5)
# --------------------------------------------------------------------------- #
TRAIN_UNITS = [2, 5, 10, 16, 18]     # flight class 3 (in *_dev)
VAL_UNIT = 20                        # flight class 3 (in *_dev) — validation + CUSUM calibration
TEST_UNITS = {
    11: 3,   # flight class 3, 59 cycles — no-shift + Direction A (bias injection)
    14: 1,   # flight class 1, 76 cycles — Direction B (natural shift)
    15: 2,   # flight class 2, 67 cycles — Direction B (natural shift)
}
DIR_A_UNIT = 11
DIR_B_UNITS = [14, 15]

# --------------------------------------------------------------------------- #
# RUL model / windowing  (draft §3.2)
# --------------------------------------------------------------------------- #
WINDOW = 50            # down-sampled time steps fed to the LSTM
DECIMATION = 10        # 10:1 decimation of the 1 Hz stream -> 50 steps = 500 s of flight
RUL_CAP = 65           # piecewise-linear RUL cap (cycles)

LSTM_HIDDEN = 64
LSTM_LAYERS = 2
LSTM_DROPOUT = 0.3     # kept > 0 so MC-Dropout (Tier-1 #3) has an effect
SEED = 42

TRAIN_EPOCHS = 60
TRAIN_BATCH = 64
TRAIN_LR = 1e-3
TRAIN_STRIDE = 8       # sliding-window stride for training augmentation (within a flight)
MC_SAMPLES = 30        # MC-Dropout forward passes for predictive uncertainty

# --------------------------------------------------------------------------- #
# Decision protocol  (draft §3.5)
# --------------------------------------------------------------------------- #
DECISION_EVERY = 3     # a decision point every 3 cycles
BIAS_ONSET_CYCLE = 23  # Direction-A injection point on unit 11 (40% of 59-cycle life)
BIAS_SIGMA = 2.0       # +/- 2 training standard deviations on the temperature channels

# Decision thresholds on RUL (cycles) -> ground-truth labels + threshold baseline
REPLACE_RUL = 10       # RUL <= 10  -> Replace
INSPECT_RUL = 25       # RUL <= 25  -> Inspect ; else Continue

DECISIONS = ["continue", "inspect", "replace"]   # ordered by escalation level
DEC_LEVEL = {"continue": 0, "inspect": 1, "replace": 2}

# --------------------------------------------------------------------------- #
# Baselines  (draft §3.5.3)
# --------------------------------------------------------------------------- #
CUSUM_K = 0.5          # reference value (in sigma units)
CUSUM_TARGET_FAR = 0.0 # calibrate h on VAL_UNIT for zero in-distribution false-alarm rate

# --------------------------------------------------------------------------- #
# Agent / LLM backend  (vLLM + local Qwen)
# --------------------------------------------------------------------------- #
LLM_PATH = "/home/iai4/Desktop/SDM/Qwen2.5-32B-AWQ"
LLM_SAMPLES = 5        # samples per decision point (majority vote)
LLM_TEMPERATURE = 0.7
LLM_MAX_TOKENS = 1500   # v2 prompt reasons longer; 900 truncated ~18% of FINAL JSONs
HISTORY_K = 20         # RUL-history length exposed to the agent (decision points).
                       # Long enough to keep the PRE-shift level visible for the
                       # whole life -> the agent can anchor its RUL correction on it.

# Tier-2 #5 hysteresis: consecutive shift votes required before escalating on shift
HYSTERESIS_N = 2
# RUL correction: once a shift is confirmed the agent's corrected RUL (median over
# samples) replaces the model's point estimate in the threshold decision rule.
# Rule-reference agent: a history step-jump larger than this marks the shift onset;
# the pre-jump level extrapolated at 1 cycle/cycle is the corrected RUL.
CORR_JUMP = 10.0
# Fallback (no visible onset jump): cycles of correction per unit of signed temp regime_z.
RULE_CORR_GAIN = 1.0
# Tier-2 #6 cost-aware decision: miss (FN) is this many times costlier than a false alarm
COST_RATIO_FN_FP = 5.0

# Feature-derivation knobs (Tier-1)
REGIME_POLY_DEGREE = 2   # polynomial degree for the W-conditioned baseline model
