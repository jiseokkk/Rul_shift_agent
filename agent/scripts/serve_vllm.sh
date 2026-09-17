#!/usr/bin/env bash
# vLLM 서버 (Qwen2.5-32B-AWQ, GPU 0, port 8000). 로그: agent/runs/_server/vllm.log
#   bash agent/scripts/serve_vllm.sh            # 백그라운드로 띄우고 준비될 때까지 기다림
#   bash agent/scripts/serve_vllm.sh stop
#
# VLLM_USE_FLASHINFER_SAMPLER=0 : 이 env 에는 nvcc 가 없어 FlashInfer 샘플러 JIT 가 실패한다 → PyTorch 샘플러 사용
# --max-model-len 4096          : 프롬프트 ≈ 1.5k 토큰 + 출력 300. 짧게 잡아 KV 캐시 여유 확보
set -u
AGENT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG="$AGENT/runs/_server/vllm.log"
MODEL="${MODEL:-/home/iai4/Desktop/SDM/Qwen2.5-32B-AWQ}"
GPU="${GPU:-0}"
PORT="${PORT:-8000}"

if [[ "${1:-}" == "stop" ]]; then
    for p in $(pgrep -f "vllm.entrypoint[s].openai.api_server"); do kill "$p" && echo "killed $p"; done
    exit 0
fi

source "${CONDA_SH:-$HOME/miniconda3/etc/profile.d/conda.sh}" && conda activate "${ENV_NAME:-LLMshift}"
mkdir -p "$(dirname "$LOG")"
[[ -f "$LOG" ]] && mv -f "$LOG" "$LOG.prev"
CUDA_VISIBLE_DEVICES="$GPU" VLLM_USE_FLASHINFER_SAMPLER=0 nohup python -m vllm.entrypoints.openai.api_server \
    --model "$MODEL" --max-model-len 4096 --port "$PORT" --gpu-memory-utilization 0.90 --seed 42 > "$LOG" 2>&1 &
echo "vLLM pid $!  log $LOG"
for i in $(seq 1 84); do
    if curl -s -m 3 "http://localhost:$PORT/v1/models" 2>/dev/null | grep -q '"id"'; then echo "ready after ~$((i*5))s"; exit 0; fi
    if grep -q "EngineCore failed to start" "$LOG" 2>/dev/null; then echo "FAILED — see $LOG"; exit 1; fi
    sleep 5
done
echo "timeout — see $LOG"; exit 1
