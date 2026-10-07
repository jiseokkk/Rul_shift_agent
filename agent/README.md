# agent — 에이전트 설계 및 실험

`../data_prep/` 산출물(grid v3, 잠금)을 읽어, LLM 에이전트가 배포된 RUL 모델의 **출력 신뢰성 상실**(오염에 의한 예측 교란)을
매 cycle 탐지하는지 실험한다. 설계·평가 규약: [docs/design_v1.md](docs/design_v1.md). 데이터 요약: [../data_prep/docs/data_prep_summary.md](../data_prep/docs/data_prep_summary.md).

```
cycle t → Sensor Tool ∥ RUL Tool → build_input → LLM 1회 (guided JSON) → post_check → decisions.csv
```

## 폴더

```
agent/
├── configs/   paths.yaml(입력/채점 경로 구분) · agent.yaml(N, judge_from, 해상도, eval: Δ·w·H·k) · llm.yaml · pilot_scenarios.csv
├── docs/      design_v1.md · v1_failure_analysis.md · eval_v2_scenario.md
├── scripts/   build_mc_dropout.py · serve_vllm.sh · run.py · probe.py · add_end_cycle.py · evaluate.py
├── src/
│   ├── data/    inputs.py(에이전트가 볼 수 있는 것만) · truth.py(채점 전용, eval 만 import)
│   ├── tools/   base.py · sensor_tool.py · rul_tool.py
│   ├── llm/     prompts.py · schema.py · client.py(호출 유일 지점) · post_check.py
│   ├── runner/  stream.py(cycle 루프, 동시 실행) · cache.py(프롬프트 해시 캐시) · record.py
│   └── eval/    scenario_table.py · baselines.py · stats.py · report.py (v2) · legacy_v1.py (+cycle_table, unit_table)
├── artifacts/ mc_dropout/(50 pass, unit 별 seed) · cache/decisions/   (gitignore)
├── runs/{run_id}/  decisions.csv · prompts/ · stats/ · eval/{report.md, scenario_table.csv} · eval_v1/ · config_snapshot.yaml   (gitignore)
└── tests/
```

## 실행 (env LLMshift, agent_RUL/ 에서)

```bash
python agent/scripts/build_mc_dropout.py          # 한 번. 3분. MC dropout 50 pass 캐시
python -m pytest agent/tests -q

# vLLM 서버 (GPU 0)
CUDA_VISIBLE_DEVICES=0 python -m vllm.entrypoints.openai.api_server \
    --model /home/iai4/Desktop/SDM/Qwen2.5-32B-AWQ --max-model-len 4096 --port 8000 --seed 42

python agent/scripts/add_end_cycle.py --scenarios pilot_scenarios        # 판정 절단 시점 end_cycle 열 (채점 쪽 계산, runner 는 숫자만 읽음)
python agent/scripts/run.py --scenarios pilot_scenarios --dry-run       # LLM 없이 프롬프트·stats 만 (표 눈으로 확인)
python agent/scripts/probe.py --n 20 --concurrency 1 4                  # 호출당 시간·동시 배수 실측
python agent/scripts/run.py --scenarios pilot_scenarios --tag pilot     # 파일럿 51 시나리오 ≈ 4,850 호출
python agent/scripts/evaluate.py --latest                               # 시나리오 단위 v2 → runs/{run_id}/eval/report.md (docs/eval_v2_scenario.md)
python agent/scripts/compare_scenario_runs.py --runs <id> ... --labels <name> ... --out or500   # 여러 run 비교 → reports/eval_v2/
```

`run.py --units 57 --limit 5` 로 일부만, `--concurrency 8`. 중단 후 같은 명령 재실행이면 캐시로 이어간다.

## OpenRouter 로 LLM 만 교체해 비교 (2026-09-30)

에이전트·도구·프롬프트·평가는 그대로 두고 LLM 만 바꾼다. 설정은 [configs/llm_openrouter.yaml](configs/llm_openrouter.yaml)
(모델 슬러그, reasoning_effort, response_format). 키는 저장소 루트 `.env` 의 `OPENROUTER_API_KEY` (`.env.example` 복사).
표본은 [configs/sample_or500.csv](configs/sample_or500.csv): 6개 유형 × 83~84개, unit·시점·센서·강도·방향 균형
(`scripts/make_balanced_sample.py`). 500 시나리오 = 판정 75,895 cycle = 고유 프롬프트 40,821개.

```bash
python agent/scripts/probe.py --n 20 --concurrency 1 4 --llm llm_openrouter        # 동기 호출 점검: 지연·토큰·reasoning 0·비용

# 배치 (정가 50%). 판정이 memoryless 라 dry-run 프롬프트를 한꺼번에 제출하고 결과를 판정 캐시에 넣는다
python agent/scripts/batch_openrouter.py submit  --scenarios sample_or500 --job or500_test --test 20   # 시험 20건 ≈ $0.01
python agent/scripts/batch_openrouter.py collect --job or500_test --wait                                # 스키마·reasoning 0·비용 확인
python agent/scripts/batch_openrouter.py submit  --scenarios sample_or500 --job or500                   # 본 제출 (캐시에 있는 것은 건너뜀)
python agent/scripts/batch_openrouter.py collect --job or500 --wait                                     # → artifacts/cache/decisions/
python agent/scripts/run.py --scenarios sample_or500 --llm llm_openrouter --tag or500                  # 캐시 재생 → decisions.csv (미스만 동기 호출)
python agent/scripts/evaluate.py --latest
```

동기 호출로 바로 돌리려면 `run.py --scenarios sample_or500 --llm llm_openrouter --tag or500` 만 실행한다 (정가, 동시 8 에서 2~4 시간).
Qwen 결과와의 비교는 같은 시나리오·같은 프롬프트 해시로 짝지어 한다 (`runs/Qwen2.5-32B-AWQ_full_v1_*`).

## 로컬 대형 모델(vLLM 0.29, env vllm-new, GPU 0)로 같은 500개 비교 (2026-10-02)

`/home/iai4/Desktop/vllm/` 의 NVFP4 체크포인트(Qwen3.8-27B-NVFP4, Qwen3.6-35B-A3B-NVFP4)를 [scripts/serve_vllm_new.sh](scripts/serve_vllm_new.sh) 로 띄우고
[configs/llm_local_*.yaml](configs/) 로 호출한다. vLLM 0.29 는 `guided_json` 을 없앴으므로 `json_mode: response_format` (xgrammar) 을 쓴다.
thinking 은 서버 옵션(`--default-chat-template-kwargs enable_thinking`, `--reasoning-parser qwen3`)으로 켜고 끄며, 변형마다 `--served-model-name` 을
다르게 줘서 판정 캐시(키 = model|seed)와 run_id 가 섞이지 않게 한다. bf16 체크포인트(gemma-4-31B-it, GLM-4.7-Flash, Qwen3.8-27B)는 온라인 fp8 로도
28~31 GiB 라 32 GB 한 장에 안 들어간다 → GPU 1 이 비면 TP=2 (`QUANT=fp8`).

```bash
nohup bash agent/scripts/run_local_or500.sh > agent/runs/_local_or500_launch.log 2>&1 &   # 큐: off ×2 → think ×2. 모델마다 서버→probe→run→evaluate→metrics_xlsx
tail -f agent/runs/_local_or500_launch.log                                                 # 결과(v1 지표): reports/or500_metrics_{label}.xlsx, compare_or500_local.md/.xlsx → 보존본은 reports/eval_v1/
```

실측(2026-10-02, Qwen3.8-27B-NVFP4): thinking 끔 — 동시 16 에서 호출당 0.3 s(벽시계), 출력 ≈110 토큰, 500 시나리오 ≈ 4 시간.
thinking 켬 — reasoning 1.7k~4.6k 토큰/호출, 단일 호출 34 s → 500 시나리오에 30 시간 안팎. `max_tokens 6000` 을 넘기면 파싱 실패로 재시도된다.

## 지켜야 하는 규칙

1. `data_prep/` 은 읽기만.
2. **정보 차단** — clean 예측·라벨·τ_s·eval_mask·시나리오 메타는 `src/data/truth.py` 를 통해 `src/eval/` 만 읽는다.
   `tools/ llm/ runner/` 가 이를 import 하면 `tests/test_isolation.py` 가 실패한다. 프롬프트에 scenario_id 를 넣지 않는다.
3. LLM 호출은 `src/llm/client.py` 한 곳. temperature 0, seed 고정, guided_json.
4. 도구는 판정·임계값·센서 선택을 하지 않는다. 14개 전부 반환. LLM 입력에는 단위 없는 값만.
5. `build_input` 출력 바이트가 바뀌면 캐시 전량 무효 (키 = 프롬프트 해시). 프롬프트를 고칠 때 각오할 것.
6. 평가 규칙 변경은 `src/eval/` 과 `docs/eval_v2_scenario.md` 를 함께 수정. 채점 파라미터는 `configs/agent.yaml` `eval:` 한 곳.

## MC dropout seed 에 대한 메모

seed 는 **unit 별**로 고정한다 (`derive_seed(base, unit, "mc")`). 같은 unit 의 모든 시나리오가 같은 dropout 마스크를 쓰므로
τ_s 이전 cycle 의 MC 결과가 바이트 단위로 같고, 그 덕에 τ_s 이전 프롬프트가 시나리오 간 동일해져 LLM 호출이 unit 당 1회로 공유된다.
