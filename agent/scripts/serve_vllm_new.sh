#!/usr/bin/env bash
# vLLM 0.29 서버 (env vllm-new, 기본 GPU 0, port 8000). 로컬 대형 모델(NVFP4 등)을 llm_local_*.yaml 과 짝지어 띄운다.
#   MODEL=/home/iai4/Desktop/vllm/Qwen3.8-27B-NVFP4 SERVED=Qwen3.8-27B-NVFP4 bash agent/scripts/serve_vllm_new.sh
#   THINK=1 PARSER=qwen3 MAXLEN=8192 ... bash agent/scripts/serve_vllm_new.sh      # thinking 켠 서버
#   bash agent/scripts/serve_vllm_new.sh stop
#
# SERVED  : /v1/models 의 id. llm_local_*.yaml 의 model 과 같아야 하고, 판정 캐시 키(model|seed)·run_id 가 여기서 나오므로
#           thinking on/off 처럼 서버 옵션만 다른 변형은 SERVED 를 다르게 준다 (예: ...-think).
# THINK   : 0 이면 chat template 의 enable_thinking=false 를 서버 기본값으로 박는다 (Qwen3.x·GLM·Gemma4 하이브리드 모델).
#           1 이면 enable_thinking=true + --reasoning-parser PARSER (구조화 출력 문법을 </think> 뒤에만 적용하기 위해 필수).
# QUANT / OFFLOAD_GB : bf16 체크포인트를 온라인 fp8 로 돌릴 때 (--quantization fp8, --cpu-offload-gb). NVFP4 는 비움.
# VLLM_USE_FLASHINFER_SAMPLER=0 : 이 머신에 nvcc 가 없어 FlashInfer 샘플러 JIT 가 실패할 수 있다 → PyTorch 샘플러
set -u
AGENT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$AGENT/runs/_server"
GPU="${GPU:-0}"
PORT="${PORT:-8000}"

if [[ "${1:-}" == "stop" ]]; then
    for p in $(pgrep -f "vllm.entrypoint[s].openai.api_server|vllm serv[e]|VLLM::EngineCor[e]"); do kill "$p" 2>/dev/null && echo "killed $p"; done
    for i in $(seq 1 24); do pgrep -f "vllm serv[e]|VLLM::EngineCor[e]" >/dev/null || exit 0; sleep 5; done
    pkill -9 -f "vllm serv[e]|VLLM::EngineCor[e]" 2>/dev/null; exit 0
fi

MODEL="${MODEL:?MODEL 경로}"
SERVED="${SERVED:-$(basename "$MODEL")}"
THINK="${THINK:-0}"
PARSER="${PARSER:-}"
MAXLEN="${MAXLEN:-4096}"
UTIL="${UTIL:-0.90}"
QUANT="${QUANT:-}"
OFFLOAD_GB="${OFFLOAD_GB:-0}"
MAXSEQS="${MAXSEQS:-64}"           # 프로파일/cudagraph 메모리. 기본 256 이면 248k 어휘 logits 로 12GiB 를 더 잡다 OOM (2026-10-02 실측)
MAXBATCH="${MAXBATCH:-4096}"
EXTRA="${EXTRA:-}"
LOG="$LOG_DIR/vllm_${SERVED}.log"

ARGS=(serve "$MODEL" --served-model-name "$SERVED" --port "$PORT" --max-model-len "$MAXLEN"
      --gpu-memory-utilization "$UTIL" --max-num-seqs "$MAXSEQS" --max-num-batched-tokens "$MAXBATCH" --seed 42 --language-model-only --limit-mm-per-prompt '{"image":0,"video":0}')
if [[ "$THINK" == "1" ]]; then
    ARGS+=(--default-chat-template-kwargs '{"enable_thinking": true}')
    [[ -n "$PARSER" ]] && ARGS+=(--reasoning-parser "$PARSER")
else
    ARGS+=(--default-chat-template-kwargs '{"enable_thinking": false}')
fi
[[ -n "$QUANT" ]] && ARGS+=(--quantization "$QUANT")
[[ "$OFFLOAD_GB" != "0" ]] && ARGS+=(--cpu-offload-gb "$OFFLOAD_GB")
[[ -n "$EXTRA" ]] && ARGS+=($EXTRA)

source "${CONDA_SH:-$HOME/miniconda3/etc/profile.d/conda.sh}" && conda activate "${ENV_NAME:-vllm-new}"
mkdir -p "$LOG_DIR"
[[ -f "$LOG" ]] && mv -f "$LOG" "$LOG.prev"
echo "vllm ${ARGS[*]}" > "$LOG"
CUDA_VISIBLE_DEVICES="$GPU" VLLM_USE_FLASHINFER_SAMPLER=0 nohup vllm "${ARGS[@]}" >> "$LOG" 2>&1 &
echo "vLLM pid $!  served=$SERVED  log $LOG"
for i in $(seq 1 "${WAIT_STEPS:-240}"); do          # 기본 20분. 첫 로딩은 torch.compile·cudagraph 캡처 때문에 5~10분
    if curl -s -m 3 "http://localhost:$PORT/v1/models" 2>/dev/null | grep -q "\"$SERVED\""; then echo "ready after ~$((i*5))s"; exit 0; fi
    if grep -qE "EngineCore failed to start|Error:|RuntimeError|OutOfMemoryError" "$LOG" 2>/dev/null && ! pgrep -f "vllm serv[e]" >/dev/null; then
        echo "FAILED — see $LOG"; exit 1; fi
    sleep 5
done
echo "timeout — see $LOG"; exit 1
