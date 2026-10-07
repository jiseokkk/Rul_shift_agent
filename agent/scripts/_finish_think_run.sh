#!/usr/bin/env bash
# 2026-10-05: 사용자 지시로 큐의 마지막 항목(Qwen3.6 thinking)은 돌리지 않는다. 진행 중인 run.py(pid 2550782)가 끝나면 뒷단계만 수행.
set -u
cd /home/iai4/Desktop/han/agent_RUL
RUN_ID=Qwen3.8-27B-NVFP4-think_or500_seed42_20261002-223719
while kill -0 2550782 2>/dev/null; do sleep 60; done
echo "[$(date '+%F %T') ] run.py 종료 → 채점"
source ~/miniconda3/etc/profile.d/conda.sh && conda activate LLMshift
if [[ -f agent/runs/$RUN_ID/decisions.csv ]]; then
  python agent/scripts/evaluate.py --run-id $RUN_ID 2>&1 | tail -2
  python agent/scripts/metrics_xlsx.py --run-id $RUN_ID --out or500_metrics_qwen3.8-27b-nvfp4-think 2>&1 | tail -2
  python agent/scripts/compare_runs.py \
      --runs Qwen2.5-32B-AWQ_full_v1_seed42_20260917-020322__or500 deepseek-v4-pro-0813_or500_seed42_20261001-003315 \
             Qwen3.8-27B-NVFP4_or500_seed42_20261002-175400 Qwen3.6-35B-A3B-NVFP4_or500_seed42_20261002-203606 $RUN_ID \
      --labels qwen2.5-32b-awq deepseek-v4-pro qwen3.8-27b-nvfp4 qwen3.6-35b-a3b-nvfp4 qwen3.8-27b-nvfp4-think \
      --out compare_or500_local --xlsx --sample sample_or500 2>&1 | tail -3
fi
bash agent/scripts/serve_vllm_new.sh stop
echo "[$(date '+%F %T') ] ALL DONE (Qwen3.6 thinking 은 지시로 생략)"
