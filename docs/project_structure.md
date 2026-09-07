# agent_rul 폴더 구조

데이터셋은 프로젝트 밖에 있고, 경로는 `configs/paths.yaml` → `config.py` 에서만 참조한다.
전체 흐름 그림: [figures/agent_flow.svg](figures/agent_flow.svg)

```
<workspace>/
├── dataset/                          # 프로젝트 밖. 읽기 전용
│   ├── data_set/N-CMAPSS_DS02-006.h5
│   └── corrupted_dataset/
│       ├── manifest.csv              # GT. evaluation/ 만 읽는다
│       └── <block>/<scenario_id>/series.npz, spec.json
│
└── agent_rul/
    ├── CLAUDE.md · README.md · pyproject.toml
    ├── configs/
    │   ├── paths.yaml                # 외부 데이터 경로, artifacts/results 루트
    │   ├── experiment.yaml           # L_w=300s, Δs=10s, L_c=4, K=100, warm_up=4, D=5, 시나리오, rul_model
    │   └── llm.yaml                  # 모델, base_url, temperature=0, seed, max_retries=2
    ├── docs/
    │   ├── research_plan_v2.md · agent_spec.md · project_structure.md
    │   └── figures/agent_flow.svg
    ├── models/frozen_rul/            # rul_lstm.pt, scaler.npz (학습하지 않음)
    │
    ├── src/agent_rul/                # 19 파일
    │   ├── __main__.py               # CLI: inspect / build-reference / run / evaluate / report
    │   ├── config.py                 # yaml → Config. 모든 경로·파일명은 여기서만 조합
    │   ├── data.py                   # HDF5 로더, 시나리오 로더(GT 필드 제거), window 분할, stream()
    │   ├── utils.py                  # seed, logging, csv/json
    │   ├── reference/                # 1 준비: 정상 기준 (train 데이터, 오프라인, 한 번)
    │   │   ├── knn.py                #   W 표준화 → KD-tree → E[x|W]
    │   │   ├── calibration.py        #   global(mean/std), σ_w, q95, std_ref, Σ_r, T² 기준
    │   │   └── build.py              #   fit 전체 → artifacts/reference/
    │   ├── tools/                    # 2 판정: Agent 도구 (계산 + 이력 + 조회)
    │   │   ├── eda.py                #   compute_window_stats, aggregate_cycle, contrast, EDATool
    │   │   └── rul.py                #   RULNet, RULTool, rul_context
    │   ├── agent/
    │   │   ├── schema.py             #   Decision (Pydantic), DECISION_COLUMNS
    │   │   ├── prompts.py            #   SYSTEM_PROMPT (agent_spec §1 과 동일) + format_input
    │   │   ├── llm.py                #   유일한 LLM 호출 (structured output, 재시도)
    │   │   ├── graph.py              #   LangGraph 고정 DAG + post_check
    │   │   └── runner.py             #   스트림 루프, 판정 캐시, decisions/prompts/stats 기록
    │   └── evaluation/               # 3 평가: GT 를 읽는 유일한 패키지
    │       ├── gt.py                 #   manifest, true_rul, life_fraction
    │       ├── classify.py           #   Alarm Event + TP/FP/FN/TN (12.4)
    │       ├── metrics.py            #   P/R/F1, MDD, FAR_1000, LateRate, FailRate + D/S sensitivity
    │       └── report.py             #   evaluate_run, build_report
    │
    ├── tests/
    │   ├── test_windows.py           # window 분할 경계, stream 순서
    │   ├── test_calibration.py       # σ_w > 0, Σ_r 조건수, T² 분해
    │   ├── test_cycle_agg.py         # 합성 bias → Δμ ≈ α, exceedance, 증분 contrast == 배치
    │   ├── test_eda_tool.py          # EDATool 스트림 == 배치 (합성), warm-up/이력 규칙, 미래 cycle 모름
    │   ├── test_prompts.py           # 템플릿, 토큰 상한, SYSTEM_PROMPT == agent_spec, post_check
    │   ├── test_classify.py          # 12.4 규칙 케이스
    │   ├── test_gt_isolation.py      # Agent 경로에서 evaluation import / GT 필드 접근 금지
    │   └── test_equivalence.py       # 실제 데이터: 스트림 == 배치, 예전 산출물·프롬프트와 비교(STRICT)
    │
    ├── artifacts/                    # 재계산 가능. git 제외
    │   ├── reference/                # global.json, knn.npz, calibration.json
    │   └── cache/                    # ncmapss unit 캐시, decisions/{key}.json 판정 캐시
    └── results/{run_id}/             # git 제외. run_id = {model}_{tag}_seed{seed}_{timestamp}
        ├── config_snapshot.yaml · run.log
        ├── decisions.csv             # 판정 로그 (true_rul, life_fraction 은 evaluate 가 채움)
        ├── prompts/{sid}_{cycle}.txt # 실제 전송된 runtime input
        ├── stats/{sid}/              # 나중에 파 볼 때: window_stats.csv (start_sample 로 원본 추적),
        │                             #   cycle_sensor.csv, cycle.csv, rul.csv
        ├── decisions_labeled.csv · metrics.json · sensitivity.json · per_scenario.csv
        └── (results/report_{tag}.json — report 가 여러 run 을 묶어 생성)
```

## 데이터 흐름

```
1 준비   dataset/data_set (clean unit 2,5,10,18 · 16,20) ── build-reference ── artifacts/reference
                                                                                    │
2 판정   dataset/corrupted_dataset/<sid>/series.npz ── data.stream ── cycle 순서대로 ─┤
            비행 중  window 마다   EDATool.observe_window   (z_w, std_ratio, T², contribution)
            착륙     EDATool.end_cycle (cycle 집계, Δμ Δσ) · RULTool.end_cycle (RUL)
            cycle > warm_up & 이력 ≥ L_c  →  graph: eda.evidence ∥ rul.context → prompt → LLM → post_check
                                          →  results/{run_id}/decisions.csv (+ prompts/, stats/)
3 평가   decisions.csv + manifest.csv (GT) ── evaluate ── metrics.json ── report ── report_{tag}.json
```

build-reference 는 LLM 없이 한 번. run 은 프롬프트/모델을 바꿀 때마다 (캐시 키에 prompt_hash → 안 바뀐 cycle 은 재호출 없음). evaluate 는 run 결과만 읽는다.

## 원칙

- **GT 격리**: manifest.csv / true_rul / t_f 는 `evaluation/` 만 읽는다. `data.py`, `reference/`, `tools/`, `agent/` 가 evaluation 을 import 하거나 GT 필드에 접근하면 `tests/test_gt_isolation.py` 가 실패한다.
- **Tool 은 도착한 cycle 만 안다**: cycle t 판정 시점에 t+1 이후는 메모리에 없다 (`test_eda_tool.py::test_tool_only_knows_arrived_cycles`).
- **경로 하드코딩 금지**: 파일명까지 `config.Paths` 에 있다.
- **artifacts 는 재현 가능**: build-reference 재실행으로 복구. results/ 는 metrics.json 만 보관.
- **캐시 키에 prompt_hash 포함**: `format_input` 출력이 바뀌면 자동 재호출.
- **run_id 에 seed·model 포함**: 반복 3회는 `--seed` 만 다른 run 3개.
