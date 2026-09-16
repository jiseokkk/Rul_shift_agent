"""B-0: 원본 저장소를 그대로 실행해 FD001 RMSE ≈ 11.85 / Score ≈ 214 를 확인.

기본: 저장소에 포함된 pre_FD0013.pt 로 Transformer_ft_serialatten.py 만 실행 (README Step 2).
--with-pretrain: Transformer_pre.py 도 실행. 이때 원본이 ./pre_FD0013.pt 를 덮어쓰므로
  실행 전 백업하고 끝나면 복원한다 (RUL/ 수정 금지 원칙). 새 weight 는 models/ 에 보관.
원본 스크립트가 RUL/two_phase/result/ 에 csv 를 쓰는 것은 막을 수 없다.

결과 → models/FD001/reproduce_metrics.json["original"], reports/B_reproduction.md
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from datetime import datetime

from _bootstrap import setup, load_json, save_json
from src.common import git_commit_hash

PAT = re.compile(r"test_loss\s*=\s*([0-9.]+)\s+score\s*=\s*([0-9.]+)")


def run(cmd, cwd, log_path):
    print(f"$ {' '.join(cmd)}   (cwd={cwd})")
    with open(log_path, "w", encoding="utf-8") as f:
        proc = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                encoding="utf-8", errors="replace")
        tail = []
        for line in proc.stdout:
            f.write(line)
            tail.append(line)
            if len(tail) > 30:
                tail.pop(0)
        proc.wait()
    return proc.returncode, "".join(tail)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--with-pretrain", action="store_true")
    ap.add_argument("--python", default=sys.executable)
    ap.add_argument("--expect-rmse", type=float, default=11.85)
    ap.add_argument("--tol", type=float, default=1.0, help="|RMSE − 기대| 허용")
    a = ap.parse_args()

    paths, cfg = setup()
    repo = paths.rul_repo
    assert (repo / "Transformer_ft_serialatten.py").exists(), f"원본 저장소가 {repo} 에 없음 (configs/paths.yaml 확인)"
    paths.models_dir.mkdir(parents=True, exist_ok=True)
    paths.reports_dir.mkdir(parents=True, exist_ok=True)
    result = {"date": datetime.now().isoformat(timespec="seconds"), "commit": git_commit_hash(repo)}

    if a.with_pretrain:
        pre = repo / "pre_FD0013.pt"
        backup = paths.models_dir / "orig_pre_FD0013.pt.bak"
        shutil.copy2(pre, backup)
        rc, tail = run([a.python, "Transformer_pre.py"], repo, paths.reports_dir / "log_00_pretrain.txt")
        result["pretrain_rc"] = rc
        shutil.copy2(pre, paths.models_dir / "orig_repro_pre_FD0013.pt")
        shutil.copy2(backup, pre)  # 원본 복원
        backup.unlink()

    rc, tail = run([a.python, "Transformer_ft_serialatten.py"], repo, paths.reports_dir / "log_00_finetune.txt")
    result["finetune_rc"] = rc
    m = PAT.search(tail)
    if not m:
        print(tail)
        if "Attempting to deserialize object on a CUDA device" in tail:
            print("힌트: 원본 pre_FD0013.pt 는 CUDA 에서 저장됐고 원본 코드는 map_location 없이 torch.load 하므로\n"
                  "      GPU 가 있는 머신에서 실행해야 한다 (RUL/ 은 수정 금지). 이 단계만 GPU 에서 돌리고 나머지는 어디서든 가능.")
        raise SystemExit("원본 출력에서 'test_loss = X   score = Y' 를 찾지 못함 (reports/log_00_finetune.txt 확인)")
    result["rmse"], result["score"] = float(m.group(1)), float(m.group(2))
    ok = abs(result["rmse"] - a.expect_rmse) <= a.tol
    result["ok"] = bool(ok)

    metrics = load_json(paths.reproduce_metrics) if paths.reproduce_metrics.exists() else {}
    metrics["original"] = result
    save_json(metrics, paths.reproduce_metrics)

    rep = paths.reports_dir / "B_reproduction.md"
    txt = rep.read_text(encoding="utf-8") if rep.exists() else "# Phase B — 재현 확인\n\n"
    txt += (f"\n## B-0 원본 그대로 실행 ({result['date']})\n"
            f"- commit: `{result['commit']}`\n- RMSE = {result['rmse']:.2f}, Score = {result['score']:.2f} "
            f"(기대 {a.expect_rmse} ± {a.tol}) → {'OK' if ok else 'MISMATCH'}\n")
    rep.write_text(txt, encoding="utf-8")
    print(f"RMSE={result['rmse']:.2f} Score={result['score']:.2f} → {'OK' if ok else 'MISMATCH: 여기서 멈추고 원인 확인'}")
    raise SystemExit(0 if ok else 2)


if __name__ == "__main__":
    main()
