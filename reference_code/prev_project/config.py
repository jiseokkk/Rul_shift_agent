"""Central configuration — rul_agent_project (연구계획서 v0.3).

Tool-Augmented LLM Agent for Runtime Verification of RUL Prediction under
Distribution Shift.  Stage 1: T1-T4 fixed pipeline + LLM Reliability Judge.

Run everything with the LLMshift interpreter (conda activate가 안 먹는 머신):
    PY=/home/iai4/miniconda3/envs/LLMshift/bin/python
    export PYTHONPATH=/home/iai4/Desktop

Channel definitions / window / model hyperparameters are carried over unchanged
from the legacy project (han/Rul_shift_agent) — verified against the HDF5.
"""
import os

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # project root

# 28GB source HDF5 lives in the shared data location (not copied, not in git).
# 2026-09-03: han/Rul_shift_agent/dataset/ 에서 han/dataset/ 으로 이동 —
# 구 프로젝트 코드 폴더에 대한 의존을 끊기 위함 (데이터는 그대로).
DATA_H5 = "/home/iai4/Desktop/han/dataset/data_set/N-CMAPSS_DS02-006.h5"

# Legacy locked 50-scenario benchmark — PROBE ONLY (v0.3 §10.2). Never promoted.
LEGACY_PROBE_DIR = "/home/iai4/Desktop/han/dataset/corrupted_dataset"

OUT_DIR = os.path.join(HERE, "outputs", "checkpoints")    # model weights, scaler
CALIB_DIR = os.path.join(HERE, "outputs", "calibration")  # tool reference distributions
LOG_DIR = os.path.join(HERE, "outputs", "agent_logs")     # per-decision-point traces
RES_DIR = os.path.join(HERE, "outputs", "results")        # metrics, reports
DATA_DIR = os.path.join(HERE, "data")                     # processed / corrupted
for _d in (OUT_DIR, CALIB_DIR, LOG_DIR, RES_DIR):
    os.makedirs(_d, exist_ok=True)

# --------------------------------------------------------------------------- #
# Channels  (verified against the HDF5; unchanged from legacy)
#   X_s (14 measured) + W (4 operating-condition descriptors) = 18 input channels
# --------------------------------------------------------------------------- #
XS_VARS = ["T24", "T30", "T48", "T50", "P15", "P2", "P21", "P24",
           "Ps30", "P40", "P50", "Nf", "Nc", "Wf"]          # 14 measured sensors
W_VARS = ["alt", "Mach", "TRA", "T2"]                        # 4 operating-condition
INPUT_VARS = XS_VARS + W_VARS                                # 18 model input channels
N_INPUT = len(INPUT_VARS)                                    # 18

# Gas-path temperature channels (legacy_t5 preprocess aggregates need these)
TEMP_CHANNELS = ["T24", "T30", "T48", "T50"]
TEMP_IDX = [INPUT_VARS.index(c) for c in TEMP_CHANNELS]      # [0,1,2,3]

# --------------------------------------------------------------------------- #
# Unit splits — v0.3 §8: Train / Calibration / Test (unit-level, 3-way)
#
# D1 확정 (2026-08-24, 잠금): 4 / 2 / 3.
#   - Calibration 2대: 모든 Tool의 기준 분포와 failure 라벨 τ_b가 여기서
#     나오므로, 표본을 늘리는 쪽(구 5/1 대비)을 택했다 (계획서 §8).
#   - Test 3대는 legacy와 동일: probe 50 시나리오가 u11/14/15 위에 있고,
#     u14/u15는 natural context shift 사례(Stage 3). 학습·캘리브레이션에서
#     절대 제외.
# --------------------------------------------------------------------------- #
TRAIN_UNITS = [2, 5, 10, 18]         # flight class 3 (dev split of the HDF5)
CALIB_UNITS = [16, 20]               # flight class 3 (dev) — calibration references
TEST_UNITS = [11, 14, 15]            # flight classes 3/1/2 — agent test (frozen)

# Early-stopping validation unit (train_rul.py). u16을 model selection에 쓰므로
# u16 기반 calibration 통계는 약간 낙관 편향 가능 — 민감도 체크 시 u20 단독과
# 대조한다 (계획서 §8).
VAL_UNIT = 16

# --------------------------------------------------------------------------- #
# RUL model / windowing  (unchanged from legacy)
# --------------------------------------------------------------------------- #
WINDOW = 50            # down-sampled time steps fed to the LSTM
DECIMATION = 10        # 10:1 decimation of the 1 Hz stream -> 50 steps = 500 s
RUL_CAP = 65           # piecewise-linear RUL cap (cycles)

LSTM_HIDDEN = 64
LSTM_LAYERS = 2
LSTM_DROPOUT = 0.3     # kept > 0 so MC-Dropout has an effect
SEED = 42

TRAIN_EPOCHS = 60
TRAIN_BATCH = 64
TRAIN_LR = 1e-3
TRAIN_STRIDE = 8       # sliding-window stride for training augmentation
MC_SAMPLES = 30        # MC-Dropout forward passes (T2 Uncertainty Tool)

# --------------------------------------------------------------------------- #
# Runtime verification protocol  (v0.3 §6.2)
# --------------------------------------------------------------------------- #
DECISION_EVERY = 3     # a decision point every 3 cycles (확정)

RELIABILITY_DECISIONS = ["ACCEPT", "CAUTION", "REJECT"]
CONFIDENCE_LEVELS = ["HIGH", "MEDIUM", "LOW"]   # evidence-agreement rubric (§6.5)

# Failure label (offline only, v0.3 §9) — TODO(D5): stage 구간·quantile 확정
FAILURE_QUANTILE = 0.95      # tau_b = Q_{0.95}(e | RUL stage = b), 출발값

# --------------------------------------------------------------------------- #
# LLM backend  (vLLM + local Qwen; guided JSON — v0.3 §13.3)
# --------------------------------------------------------------------------- #
LLM_PATH = "/home/iai4/Desktop/SDM/Qwen2.5-32B-AWQ"
LLM_TEMPERATURE = 0.0        # judge
LLM_MAX_TOKENS = 1500
LLM_REPAIR_RETRIES = 1       # pydantic 검증 실패 시 repair 재프롬프트 횟수

# --------------------------------------------------------------------------- #
# legacy_t5 material (Stage 2 예약 — Stage 1 미사용)
# --------------------------------------------------------------------------- #
REGIME_POLY_DEGREE = 2   # polynomial degree for the W-conditioned baseline model
