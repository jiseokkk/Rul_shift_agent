"""RUL 모델(ft_s529) 의 MC dropout 예측을 전 cycle · 전 시나리오에 대해 미리 뽑아 캐시로 저장한다.

에이전트 도구(rul_tool.mc_dropout) 의 기본 호출 결과. 라벨 생성에 쓰인 결정적 예측(data_prep/preds) 과는 별개다.

  python agent/scripts/build_mc_dropout.py                 # shift 4,880 + clean 20
  python agent/scripts/build_mc_dropout.py --T 50 --check  # --check: unit 1 을 두 번 돌려 재현성 확인

출력: agent/artifacts/mc_dropout/{shift|clean}/u{unit}/{scenario_id}.parquet
      컬럼 time, pass_00 .. pass_{T-1} (float32, 음수는 0 clip).  메타: T, seed, model, dropout_p
      각 cycle 의 값은 그 cycle 에서 끝나는 window 하나로만 계산되므로 미래 정보가 없다.
seed: derive_seed(base_seed, unit, "mc") 로 **unit 마다** 고정. 같은 unit 의 모든 시나리오(와 clean)가 같은 dropout 마스크를 쓴다.
      → τ_s 이전 cycle 은 입력이 같으므로 MC 결과도 바이트 단위로 같아져 프롬프트 캐시가 시나리오 간 공유된다.
      (배치가 항상 cycle 45~T_u 전체라 RNG 소비 순서가 같고, (cycle, pass) 별 마스크가 시나리오와 무관해진다.)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch

AGENT = Path(__file__).resolve().parents[1]
PREP = AGENT.parent / "data_prep"
sys.path.insert(0, str(PREP)); sys.path.insert(0, str(PREP / "scripts"))
from _bootstrap import setup  # noqa: E402
from src.common import derive_seed, read_parquet, write_parquet  # noqa: E402
from src.data import cmapss  # noqa: E402
from src.data.loaders import apply_zscore, load_norm_params, unit_windows  # noqa: E402
from src.model.infer_full import enable_determinism  # noqa: E402
from src.model.train_ft import load_ft_model  # noqa: E402

OUT = AGENT / "artifacts" / "mc_dropout"


def mc_predict(model, df: pd.DataFrame, norm, seq_len: int, T: int, seed: int, device) -> tuple[np.ndarray, np.ndarray]:
    df = df.sort_values("time").reset_index(drop=True)
    X = apply_zscore(cmapss.feature_matrix(df), norm)
    W = torch.from_numpy(unit_windows(X, seq_len, only_final=False).astype(np.float32)).to(device)
    model.eval()
    for m in model.modules():
        if isinstance(m, torch.nn.Dropout):
            m.train()  # dropout 층만 활성화. LayerNorm 등은 eval 유지
    g = torch.Generator(device=device).manual_seed(seed)
    torch.manual_seed(seed)  # F.dropout 은 전역 RNG 사용
    outs = []
    with torch.no_grad():
        for _ in range(T):
            outs.append(model(W).squeeze(1).clamp(min=0).cpu().numpy())
    model.eval()
    times = df["time"].to_numpy()[seq_len - 1:]
    return times.astype(int), np.stack(outs, axis=1).astype(np.float32)  # (n_cycle, T)


def save(times, P, path: Path, meta: dict):
    df = pd.DataFrame(P, columns=[f"pass_{i:02d}" for i in range(P.shape[1])])
    df.insert(0, "time", times)
    write_parquet(df, path, meta=meta)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--T", type=int, default=50)
    ap.add_argument("--base-seed", type=int, default=7)
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()

    paths, cfg = setup()
    enable_determinism()
    norm = load_norm_params(paths.norm_ft)
    base = cfg["finetune"]["base_seed"]
    model = load_ft_model(paths.ft_model(base), cfg)
    device = next(model.parameters()).device
    p_drop = [m.p for m in model.modules() if isinstance(m, torch.nn.Dropout)]
    seq_len = cfg["seq_len"]
    raw = cmapss.load_raw(paths.raw_dir, "train", cfg["sub_dataset"])
    idx = pd.read_csv(paths.scenario_index).drop_duplicates(["unit", "scenario_id"])
    meta_common = {"T": a.T, "model": f"ft_s{base}", "dropout_p": p_drop[0] if p_drop else None,
                   "base_seed": a.base_seed, "note": "dropout layers train(), others eval(); values clipped at 0"}
    print(f"model ft_s{base} device {device} dropout p={p_drop[:1]} T={a.T}  shift {len(idx)} + clean {idx.unit.nunique()}")

    if a.check:
        u = int(idx.unit.iloc[0]); sid = idx.scenario_id.iloc[0]
        sh = read_parquet(paths.shifted(u, sid)); s = derive_seed(a.base_seed, u, "mc")
        _, P1 = mc_predict(model, sh, norm, seq_len, a.T, s, device)
        _, P2 = mc_predict(model, sh, norm, seq_len, a.T, s, device)
        print(f"[check] u{u} {sid}: 두 번 실행 완전 일치 = {np.array_equal(P1, P2)}; pass 간 std 평균 {P1.std(1).mean():.3f}")
        return

    n_done = 0
    for u in sorted(idx.unit.unique()):
        u = int(u)
        out = OUT / "clean" / f"u{u}" / "clean.parquet"
        if a.overwrite or not out.exists():
            s = derive_seed(a.base_seed, u, "mc")
            t, P = mc_predict(model, cmapss.unit_frame(raw, u), norm, seq_len, a.T, s, device)
            save(t, P, out, {**meta_common, "unit": u, "scenario_id": "clean", "seed": s})
        for sid in idx.loc[idx.unit == u, "scenario_id"]:
            out = OUT / "shift" / f"u{u}" / f"{sid}.parquet"
            if not a.overwrite and out.exists():
                continue
            s = derive_seed(a.base_seed, u, "mc")
            t, P = mc_predict(model, read_parquet(paths.shifted(u, sid)), norm, seq_len, a.T, s, device)
            save(t, P, out, {**meta_common, "unit": u, "scenario_id": sid, "seed": s})
            n_done += 1
        print(f"unit {u} 완료 (누적 shift {n_done})")
    (OUT / "META.json").write_text(json.dumps({**meta_common, "n_shift": int(len(idx)), "n_clean": int(idx.unit.nunique())}, indent=2, ensure_ascii=False))
    print(f"→ {OUT}")


if __name__ == "__main__":
    main()
