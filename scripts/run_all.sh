#!/usr/bin/env bash
# agent_RUL 전체 파이프라인(00~08) 일괄 실행.
#
#   bash scripts/run_all.sh              # 00 부터 전부
#   bash scripts/run_all.sh 05           # 05 부터 재시작 (06 은 기존 파일을 건너뛰므로 이어서 가능)
#   nohup bash scripts/run_all.sh > /dev/null 2>&1 &   # 터미널 닫고 나가도 계속
#
# 로그: reports/log_run_all.txt (전체 요약) + reports/log_<NN>_<이름>.txt (단계별 원본 출력)
#
# 중단 규칙
#   00  원본 재현 검증. 실패해도 경고만 남기고 계속한다 (우리 모델 품질 게이트는 04 가 담당).
#   01  split 이 이미 있으면 건너뛴다 (--force 는 이후 모든 산출물을 무효화하므로 자동으로 쓰지 않는다).
#   그 외 단계가 0 이 아닌 코드로 끝나면 즉시 전체 중단한다.

set -u -o pipefail

CONDA_SH="${CONDA_SH:-$HOME/miniconda3/etc/profile.d/conda.sh}"
ENV_NAME="${ENV_NAME:-LLMshift}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 1

MASTER="$ROOT/reports/log_run_all.txt"
mkdir -p "$ROOT/reports"

START_FROM="${1:-00}"

export PYTHONUNBUFFERED=1
export CUBLAS_WORKSPACE_CONFIG="${CUBLAS_WORKSPACE_CONFIG:-:4096:8}"   # CUDA 결정성
export MPLBACKEND=Agg   # 무인 실행 보험: 원본 utils.py 의 plt.show() 가 창을 기다리며 멈추지 않게

# shellcheck disable=SC1090
source "$CONDA_SH" || { echo "conda.sh 를 찾을 수 없음: $CONDA_SH (CONDA_SH=... 로 지정)"; exit 1; }
conda activate "$ENV_NAME" || { echo "conda env 활성화 실패: $ENV_NAME"; exit 1; }

log() { echo "$*" | tee -a "$MASTER"; }

hhmmss() {  # 초 -> 1h02m03s
    local s=$1
    printf '%dh%02dm%02ds' $((s/3600)) $(((s%3600)/60)) $((s%60))
}

RUN_START=$(date +%s)
: > "$MASTER"
log "================================================================"
log " agent_RUL 파이프라인 시작  $(date '+%Y-%m-%d %H:%M:%S')"
log "================================================================"
log " root     : $ROOT"
log " env      : $ENV_NAME  ($(which python))"
log " python   : $(python -V 2>&1)"
log " torch    : $(python -c 'import torch;print(torch.__version__, "cuda", torch.cuda.is_available())' 2>&1)"
log " gpu      : $(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | paste -sd', ' -)"
log " 시작 단계: $START_FROM"
log ""

STATUS_LINES=()
FAILED=0

run_step() {
    local id="$1" name="$2" fatal="$3"; shift 3
    local steplog="$ROOT/reports/log_${id}_${name}.txt"

    if [[ "$id" < "$START_FROM" ]]; then
        log "[$id $name] 건너뜀 (시작 단계 $START_FROM 이전)"
        STATUS_LINES+=("$(printf '%-3s %-16s %-10s %s' "$id" "$name" "SKIP" "시작 단계 이전")")
        return 0
    fi

    log "----------------------------------------------------------------"
    log "[$id $name] 시작  $(date '+%H:%M:%S')   ->  reports/log_${id}_${name}.txt"
    log "  \$ $*"

    local t0 t1 dt rc
    t0=$(date +%s)
    "$@" 2>&1 | tee "$steplog"
    rc=${PIPESTATUS[0]}
    t1=$(date +%s); dt=$((t1-t0))

    if [[ $rc -eq 0 ]]; then
        log "[$id $name] 완료 (exit 0, $(hhmmss $dt))"
        STATUS_LINES+=("$(printf '%-3s %-16s %-10s %s' "$id" "$name" "OK" "$(hhmmss $dt)")")
        return 0
    fi

    if [[ "$fatal" == "warn" ]]; then
        log "[$id $name] !! 실패 (exit $rc, $(hhmmss $dt)) — 경고만 남기고 계속한다"
        log "   -> reports/log_${id}_${name}.txt 를 확인할 것"
        STATUS_LINES+=("$(printf '%-3s %-16s %-10s %s' "$id" "$name" "WARN($rc)" "$(hhmmss $dt)  계속 진행함")")
        return 0
    fi

    log "[$id $name] !! 실패 (exit $rc, $(hhmmss $dt)) — 전체 중단"
    log "   -> reports/log_${id}_${name}.txt 를 확인할 것"
    STATUS_LINES+=("$(printf '%-3s %-16s %-10s %s' "$id" "$name" "FAIL($rc)" "$(hhmmss $dt)  여기서 중단")")
    FAILED=1
    return 1
}

summary() {
    local end elapsed
    end=$(date +%s); elapsed=$((end-RUN_START))
    log ""
    log "================================================================"
    log " 요약   총 소요 $(hhmmss $elapsed)   종료 $(date '+%Y-%m-%d %H:%M:%S')"
    log "================================================================"
    for l in "${STATUS_LINES[@]}"; do log "  $l"; done
    log ""
    if [[ $FAILED -eq 0 ]]; then
        log " 전체 완료. 확인할 산출물:"
        log "   reports/A_split_summary.md       reports/B_reproduction.md"
        log "   reports/D_delta_distribution.md  reports/D_label_summary.md"
        log "   models/FD001/reproduce_metrics.json"
        log "   labels/FD001/meta/clean_variability.json"
        log ""
        log "   reports/D_reversion_diagnostics.md"
        log "   reports/D_eval_mask_summary.md   labels/FD001/meta/eval_mask*.csv"
        log ""
        log " 남은 사람 작업: 07 의 D_delta_distribution.md 로 theta 를, 09 의"
        log " D_reversion_diagnostics.md 로 (k, m) 을 확인한 뒤 configs/label.yaml 의"
        log " decision 블록을 기록하고 locked: true 로 잠글 것. 값을 바꿨다면 08, 09 재실행:"
        log "   python scripts/08_build_labels.py --sensitivity && python scripts/09_reversion_diagnostics.py"
    else
        log " 중단됨. 위 FAIL 단계의 로그를 확인하고, 고친 뒤 그 단계부터 재시작:"
        log "   bash scripts/run_all.sh <단계번호>"
    fi
    log "================================================================"
}

trap 'log ""; log "!! 사용자/시스템에 의해 중단됨"; summary; exit 130' INT TERM

# ---------------------------------------------------------------- 00
run_step 00 reproduce warn  python scripts/00_reproduce_original.py || true

# ---------------------------------------------------------------- 01
if [[ "01" < "$START_FROM" ]]; then
    log "[01 split] 건너뜀 (시작 단계 $START_FROM 이전)"
    STATUS_LINES+=("$(printf '%-3s %-16s %-10s %s' "01" "split" "SKIP" "시작 단계 이전")")
elif [[ -f "$ROOT/data/split/split_FD001.json" ]]; then
    log "----------------------------------------------------------------"
    log "[01 split] 건너뜀 — data/split/split_FD001.json 이 이미 있음"
    log "   (다시 만들려면: python scripts/01_split.py --force  ※ 이후 모든 산출물 무효화)"
    STATUS_LINES+=("$(printf '%-3s %-16s %-10s %s' "01" "split" "SKIP" "split_FD001.json 이미 존재")")
else
    run_step 01 split fatal  python scripts/01_split.py || { summary; exit 1; }
fi

# ---------------------------------------------------------------- 02~08
run_step 02 train_pre  fatal  python scripts/02_train_pre.py                  || { summary; exit 1; }
run_step 03 train_ft   fatal  python scripts/03_train_ft.py                   || { summary; exit 1; }
run_step 04 evaluate   fatal  python scripts/04_evaluate.py                   || { summary; exit 1; }
run_step 05 infer_clean fatal python scripts/05_infer_clean.py                || { summary; exit 1; }
run_step 06 inject     fatal  python scripts/06_inject_infer.py               || { summary; exit 1; }
run_step 07 delta      fatal  python scripts/07_delta_analysis.py             || { summary; exit 1; }
run_step 08 labels     fatal  python scripts/08_build_labels.py --sensitivity || { summary; exit 1; }
run_step 09 reversion  fatal  python scripts/09_reversion_diagnostics.py   || { summary; exit 1; }
run_step 12 eval_mask  fatal  python scripts/12_build_eval_mask.py        || { summary; exit 1; }

summary
exit 0
