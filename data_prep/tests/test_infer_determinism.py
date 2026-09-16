"""무작위 초기화 모델로도 추론 루틴 자체의 결정성과 window 정렬을 검증한다 (학습 weight 불필요)."""
import numpy as np
import pandas as pd
import torch

from src.common import load_yaml
from src.data import cmapss
from src.data.loaders import FTDataset, add_rul, apply_zscore, compute_norm_params, unit_windows
from src.model.infer_full import determinism_check, enable_determinism, infer_unit
from src.model.nets import build_ft


def synth(T=120, unit=3):
    rng = np.random.default_rng(1)
    df = pd.DataFrame({"id": unit, "time": np.arange(1, T + 1)})
    for c in cmapss.RAW_COLUMNS[2:]:
        df[c] = rng.normal(0, 1, T).cumsum()
    df["op3"] = 100.0
    return df[cmapss.RAW_COLUMNS]


def test_infer_twice_identical():
    enable_determinism()
    cfg = load_yaml("model_FD001")
    torch.manual_seed(0)
    model = build_ft(cfg).eval()
    u = synth()
    norm = compute_norm_params([cmapss.feature_matrix(u)])
    assert determinism_check(model, u, norm, cfg["seq_len"])


def test_infer_alignment_and_true_rul():
    cfg = load_yaml("model_FD001")
    torch.manual_seed(0)
    model = build_ft(cfg).eval()
    u = synth(T=120)
    norm = compute_norm_params([cmapss.feature_matrix(u)])
    out = infer_unit(model, u, norm, cfg["seq_len"], with_true=True)
    assert out["time"].iloc[0] == cfg["seq_len"] and out["time"].iloc[-1] == 120
    assert len(out) == 120 - cfg["seq_len"] + 1
    assert out["rul_true"].iloc[-1] == 0 and out["rul_true"].iloc[0] == 120 - cfg["seq_len"]
    assert (out["pred"] >= 0).all()


def test_infer_matches_dataset_windows():
    """infer_full 의 window 가 FTDataset(원본 gen_sequence 재현) 과 같은 예측을 내야 한다."""
    cfg = load_yaml("model_FD001")
    torch.manual_seed(0)
    model = build_ft(cfg).eval()
    u = synth(T=90)
    norm = compute_norm_params([cmapss.feature_matrix(u)])
    ds = FTDataset(u, norm, cfg["seq_len"], cfg["max_rul"])
    with torch.no_grad():
        p_ds = model(torch.from_numpy(ds.X)).squeeze(1).numpy()
    p_ds[p_ds < 0] = 0
    out = infer_unit(model, u, norm, cfg["seq_len"])
    assert np.allclose(out["pred"].to_numpy(), p_ds, atol=1e-6)
    # 라벨(rul) 도 동일 규칙: 마지막 window 의 rul = 0, 첫 window 의 rul = min(125, 90−45)
    assert ds.y[-1] == 0 and ds.y[0] == min(cfg["max_rul"], 90 - cfg["seq_len"])


def test_zscore_skips_zero_std():
    X = np.array([[1.0, 5.0], [3.0, 5.0]])
    npar = compute_norm_params([X])
    assert npar[1, 1] == 0
    Z = apply_zscore(X, npar)
    assert np.allclose(Z[:, 0], [-1, 1]) and np.allclose(Z[:, 1], [0, 0])


def test_edge_pad_short_unit():
    X = np.arange(10, dtype=float)[:, None]
    W = unit_windows(X, seq_len=12, only_final=True)
    assert W.shape == (1, 12, 1) and W[0, 0, 0] == 0 and W[0, 2, 0] == 0 and W[0, -1, 0] == 9


def test_add_rul_clip():
    u = synth(T=200)
    d = add_rul(u, max_rul=125)
    assert d["real_rul"].iloc[0] == 199 and d["rul"].iloc[0] == 125 and d["rul"].iloc[-1] == 0
