# agent_RUL

LLM 에이전트 기반 RUL 모델 출력 신뢰성 상실 탐지 연구. 두 단계로 나뉜다.

```
agent_RUL/
├── data_prep/   1단계. 분할 → clean 학습 → shift 주입 → 추론 → 라벨.  완료 · 잠금 (grid v3, 2026-09-16)
└── agent/       2단계. 에이전트 설계 · 실험.  data_prep 산출물을 읽기 전용으로 사용
```

- 1단계 실행·검증: [data_prep/README.md](data_prep/README.md). 작업 폴더를 `data_prep/` 으로 옮겨 실행한다.
- 2단계 구조·정보 차단 규칙·계약: [agent/README.md](agent/README.md)
- 설계 문서: [data_prep/docs/preparation_plan_final.md](data_prep/docs/preparation_plan_final.md)

```bash
cd data_prep && pip install -r requirements.txt && pytest tests/
```
