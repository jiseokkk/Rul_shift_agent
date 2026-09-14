"""Phase B-3: test_FD001 재현 평가 (seed 3개) → reproduce_metrics.json["finetune"], reports/B_reproduction.md
RMSE > --max-rmse(15) 이면 종료코드 2 (중단·원인 확인)."""
from __future__ import annotations

import argparse
from datetime import datetime

import torch

from _bootstrap import setup, load_json, save_json
from src.common import git_commit_hash, md_table
from src.data.loaders import build_finetune, load_norm_params, zero_std_columns
from src.model.evaluate import evaluate_test
from src.model.train_ft import load_ft_model


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="*", default=None)
    ap.add_argument("--max-rmse", type=float, default=15.0)
    a = ap.parse_args()

    paths, cfg = setup()
    seeds = a.seeds or cfg["finetune"]["seeds"]
    split = load_json(paths.split_json)
    norm = load_norm_params(paths.norm_ft)
    _, test_ds, _ = build_finetune(paths, cfg, split, norm_params=norm)

    metrics = load_json(paths.reproduce_metrics) if paths.reproduce_metrics.exists() else {}
    metrics.setdefault("finetune", {})
    metrics["env"] = {"torch": torch.__version__, "cuda": torch.cuda.is_available(),
                      "rul_commit": git_commit_hash(paths.rul_repo), "zero_std_columns": zero_std_columns(norm),
                      "norm_params_ft": str(paths.norm_ft.relative_to(paths.root)),
                      "date": datetime.now().isoformat(timespec="seconds")}
    rows = []
    worst = 0.0
    for s in seeds:
        model = load_ft_model(paths.ft_model(s), cfg)
        r = evaluate_test(model, test_ds, cfg["batch_size"])
        metrics["finetune"][str(s)] = {"rmse": r["rmse"], "score": r["score"], "n": r["n"]}
        rows.append({"seed": s, "rmse": r["rmse"], "score": r["score"], "n": r["n"]})
        worst = max(worst, r["rmse"])
        print(f"seed {s}: RMSE={r['rmse']:.3f} Score={r['score']:.2f}")
    save_json(metrics, paths.reproduce_metrics)

    rep = paths.reports_dir / "B_reproduction.md"
    txt = rep.read_text(encoding="utf-8") if rep.exists() else "# Phase B — 재현 확인\n\n"
    txt += (f"\n## B-3 hold-out 제외 재학습 모델의 test_FD001 평가 ({metrics['env']['date']})\n"
            f"- torch {torch.__version__}, RUL commit `{metrics['env']['rul_commit']}`, std=0 컬럼 {metrics['env']['zero_std_columns']}\n"
            f"- 기대 12~13 (학습 unit 20% 감소 + 정규화 통계에서 test 제외). {a.max_rmse} 초과 시 중단\n\n"
            + md_table(rows, fmt="{:.3f}"))
    rep.write_text(txt, encoding="utf-8")
    if worst > a.max_rmse:
        print(f"RMSE {worst:.2f} > {a.max_rmse}: 중단. 컬럼 순서·정규화·freeze 확인")
        raise SystemExit(2)


if __name__ == "__main__":
    main()
