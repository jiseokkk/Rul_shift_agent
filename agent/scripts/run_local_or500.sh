#!/usr/bin/env bash
# 로컬 vLLM(env vllm-new, GPU 0)로 LLM 만 바꿔 가며 sample_or500 500 시나리오를 같은 절차로 돌린다.
#   nohup bash agent/scripts/run_local_or500.sh > agent/runs/_local_or500_launch.log 2>&1 &
# 모델마다: 서버 기동 → probe(지연·토큰) → run.py(판정, 캐시로 재개 가능) → evaluate → metrics_xlsx(reports/or500_metrics_{label}.xlsx)
# 끝나면 compare_runs 로 Qwen2.5-32B·DeepSeek V4 Pro 와 나란히 표를 만든다 (reports/compare_or500_local.md/.xlsx).
# 이미 reports/or500_metrics_{label}.xlsx 가 있는 모델은 건너뛴다. 서버 기동 실패는 기록하고 다음 모델로 넘어간다.
set -u
AGENT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT="$(dirname "$AGENT")"
cd "$ROOT"
source "${CONDA_SH:-$HOME/miniconda3/etc/profile.d/conda.sh}"
VLLM_DIR=/home/iai4/Desktop/vllm
export GPU="${GPU:-0}"

# label | llm config | MODEL 경로 | SERVED | THINK | PARSER | MAXLEN
QUEUE=(
  "qwen3.8-27b-nvfp4|llm_local_qwen38_27b_nvfp4|$VLLM_DIR/Qwen3.8-27B-NVFP4|Qwen3.8-27B-NVFP4|0||4096"
  "qwen3.6-35b-a3b-nvfp4|llm_local_qwen36_35b_a3b_nvfp4|$VLLM_DIR/Qwen3.6-35B-A3B-NVFP4|Qwen3.6-35B-A3B-NVFP4|0||4096"
  "qwen3.8-27b-nvfp4-think|llm_local_qwen38_27b_nvfp4_think|$VLLM_DIR/Qwen3.8-27B-NVFP4|Qwen3.8-27B-NVFP4-think|1|qwen3|8192"
  "qwen3.6-35b-a3b-nvfp4-think|llm_local_qwen36_35b_a3b_nvfp4_think|$VLLM_DIR/Qwen3.6-35B-A3B-NVFP4|Qwen3.6-35B-A3B-NVFP4-think|1|qwen3|8192"
)
[[ $# -gt 0 ]] && QUEUE=("$@")      # 인자로 항목을 직접 줄 수도 있다

ts() { date '+%Y-%m-%d %H:%M:%S'; }
RUN_IDS=(); LABELS=()
for entry in "${QUEUE[@]}"; do
  IFS='|' read -r LABEL CFG MODEL SERVED THINK PARSER MAXLEN <<< "$entry"
  XLSX="$AGENT/reports/or500_metrics_${LABEL}.xlsx"
  echo; echo "[$(ts)] ===== $LABEL  ($SERVED, think=$THINK)"
  if [[ -f "$XLSX" ]]; then
    echo "[$(ts)] skip: $XLSX 있음"
    RID=$(ls -dt "$AGENT"/runs/${SERVED}_or500_seed42_* 2>/dev/null | head -1); [[ -n "$RID" ]] && { RUN_IDS+=("$(basename "$RID")"); LABELS+=("$LABEL"); }
    continue
  fi
  bash "$AGENT/scripts/serve_vllm_new.sh" stop >/dev/null 2>&1
  if ! MODEL="$MODEL" SERVED="$SERVED" THINK="$THINK" PARSER="$PARSER" MAXLEN="$MAXLEN" bash "$AGENT/scripts/serve_vllm_new.sh"; then
    echo "[$(ts)] 서버 기동 실패: $LABEL → 건너뜀 (로그 $AGENT/runs/_server/vllm_${SERVED}.log)"
    bash "$AGENT/scripts/serve_vllm_new.sh" stop >/dev/null 2>&1; continue
  fi
  conda activate LLMshift
  echo "[$(ts)] probe"; python "$AGENT/scripts/probe.py" --n 20 --concurrency 8 16 --llm "$CFG" 2>&1 | tail -12
  RUN_ID="${SERVED}_or500_seed42_$(date +%Y%m%d-%H%M%S)"
  echo "[$(ts)] run → $RUN_ID"
  python "$AGENT/scripts/run.py" --scenarios sample_or500 --llm "$CFG" --tag or500 --run-id "$RUN_ID" 2>&1 | tail -3
  if [[ -f "$AGENT/runs/$RUN_ID/decisions.csv" ]]; then
    echo "[$(ts)] evaluate"; python "$AGENT/scripts/evaluate.py" --run-id "$RUN_ID" 2>&1 | tail -2
    echo "[$(ts)] metrics_xlsx → or500_metrics_${LABEL}"; python "$AGENT/scripts/metrics_xlsx.py" --run-id "$RUN_ID" --out "or500_metrics_${LABEL}" 2>&1 | tail -2
    RUN_IDS+=("$RUN_ID"); LABELS+=("$LABEL")
  else
    echo "[$(ts)] decisions.csv 없음: $LABEL 실패"
  fi
  conda deactivate
  bash "$AGENT/scripts/serve_vllm_new.sh" stop >/dev/null 2>&1
done

if [[ ${#RUN_IDS[@]} -gt 0 ]]; then
  conda activate LLMshift
  echo; echo "[$(ts)] compare_runs → reports/compare_or500_local"
  python "$AGENT/scripts/compare_runs.py" \
      --runs Qwen2.5-32B-AWQ_full_v1_seed42_20260917-020322__or500 deepseek-v4-pro-0813_or500_seed42_20261001-003315 "${RUN_IDS[@]}" \
      --labels qwen2.5-32b-awq deepseek-v4-pro "${LABELS[@]}" --out compare_or500_local --xlsx --sample sample_or500 2>&1 | tail -5
fi
echo "[$(ts)] ALL DONE"
