# agent — 에이전트 설계 및 실험

`../data_prep/` 산출물(grid v3, 잠금)을 읽어, LLM 에이전트가 배포된 RUL 모델의 **출력 신뢰성 상실**(오염에 의한 예측 교란)을
매 cycle 탐지하는지 실험한다. 설계·평가 규약: [docs/design_v1.md](docs/design_v1.md). 데이터 요약: [../data_prep/docs/data_prep_summary.md](../data_prep/docs/data_prep_summary.md).

```
cycle t → Sensor Tool ∥ RUL Tool → build_input → LLM 1회 (guided JSON) → post_check → decisions.csv
```

## 폴더

```
agent/
├── configs/   paths.yaml(입력/채점 경로 구분) · agent.yaml(N, judge_from, w, D, 해상도) · llm.yaml · pilot_scenarios.csv
├── docs/      design_v1.md
├── scripts/   build_mc_dropout.py · serve_vllm.sh · run.py · probe.py · evaluate.py
├── src/
│   ├── data/    inputs.py(에이전트가 볼 수 있는 것만) · truth.py(채점 전용, eval 만 import)
│   ├── tools/   base.py · sensor_tool.py · rul_tool.py
│   ├── llm/     prompts.py · schema.py · client.py(호출 유일 지점) · post_check.py
│   ├── runner/  stream.py(cycle 루프, 동시 실행) · cache.py(프롬프트 해시 캐시) · record.py
│   └── eval/    cycle_table.py · unit_table.py · report.py
├── artifacts/ mc_dropout/(50 pass, unit 별 seed) · cache/decisions/   (gitignore)
├── runs/{run_id}/  decisions.csv · prompts/ · stats/ · eval/report.md · config_snapshot.yaml   (gitignore)
└── tests/
```

## 실행 (env LLMshift, agent_RUL/ 에서)

```bash
python agent/scripts/build_mc_dropout.py          # 한 번. 3분. MC dropout 50 pass 캐시
python -m pytest agent/tests -q

# vLLM 서버 (GPU 0)
CUDA_VISIBLE_DEVICES=0 python -m vllm.entrypoints.openai.api_server \
    --model /home/iai4/Desktop/SDM/Qwen2.5-32B-AWQ --max-model-len 4096 --port 8000 --seed 42

python agent/scripts/run.py --scenarios pilot_scenarios --dry-run       # LLM 없이 프롬프트·stats 만 (표 눈으로 확인)
python agent/scripts/probe.py --n 20 --concurrency 1 4                  # 호출당 시간·동시 배수 실측
python agent/scripts/run.py --scenarios pilot_scenarios --tag pilot     # 파일럿 51 시나리오 ≈ 4,850 호출
python agent/scripts/evaluate.py --latest                               # → runs/{run_id}/eval/report.md
```

`run.py --units 57 --limit 5` 로 일부만, `--concurrency 8`. 중단 후 같은 명령 재실행이면 캐시로 이어간다.

## 지켜야 하는 규칙

1. `data_prep/` 은 읽기만.
2. **정보 차단** — clean 예측·라벨·τ_s·eval_mask·시나리오 메타는 `src/data/truth.py` 를 통해 `src/eval/` 만 읽는다.
   `tools/ llm/ runner/` 가 이를 import 하면 `tests/test_isolation.py` 가 실패한다. 프롬프트에 scenario_id 를 넣지 않는다.
3. LLM 호출은 `src/llm/client.py` 한 곳. temperature 0, seed 고정, guided_json.
4. 도구는 판정·임계값·센서 선택을 하지 않는다. 14개 전부 반환. LLM 입력에는 단위 없는 값만.
5. `build_input` 출력 바이트가 바뀌면 캐시 전량 무효 (키 = 프롬프트 해시). 프롬프트를 고칠 때 각오할 것.
6. 평가 규칙 변경은 `src/eval/` 과 `docs/design_v1.md` §7 을 함께 수정.

## MC dropout seed 에 대한 메모

seed 는 **unit 별**로 고정한다 (`derive_seed(base, unit, "mc")`). 같은 unit 의 모든 시나리오가 같은 dropout 마스크를 쓰므로
τ_s 이전 cycle 의 MC 결과가 바이트 단위로 같고, 그 덕에 τ_s 이전 프롬프트가 시나리오 간 동일해져 LLM 호출이 unit 당 1회로 공유된다.
