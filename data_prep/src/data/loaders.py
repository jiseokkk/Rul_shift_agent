"""원본 CMAPSSDataset_ft / CMAPSSDataset_pre 의 FD001/FD003 경로를 동작 동일하게 재구성.

원본과 같은 것
  - 입력 17 컬럼 선택 순서 (cmapss.MODEL_FEATURE_RAW_COLS)
  - z-score: mean/std 는 np.mean / np.std(ddof=0). std == 0 이면 나눗셈 생략 (op3 가 FD001 에서 상수)
  - RUL: real_rul = (T_u + final_rul) − time,  rul = min(max_rul, real_rul)
  - window: unit 별 time 오름차순, 길이 seq_len 슬라이딩. 행 수 < seq_len 이면 첫 행 edge pad.
    only_final(test) 이면 마지막 window 하나. 라벨은 window 마지막 행의 rul
  - 사전학습 마스킹: random.seed(529) 후 window 마다 random.random() 한 번,
    mask_p 미만 → 마지막 행 17 feature 전부 0, mask_p~mask_p+random_p → U(0,1) 17개 후 op2 = 0
  - 사전학습 도메인 라벨: 주 dataset(FD001) = 1, 파트너(FD003) = 0

원본과 다른 것 (계획서 §3)
  - exclude_units: hold-out unit 을 학습·정규화 통계에서 제외
  - 정규화 통계에서 test set 제외 (원본은 train+test 합쳐서 계산)
  - norm_params 를 파일로 저장/로드해 모든 추론이 같은 통계를 사용
  - FD003 id offset = 필터링된 FD001 train id 의 max (원본은 마지막 행의 id)
"""
from __future__ import annotations

import random
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset

from src.data import cmapss


# ---------------- 정규화 ----------------
def compute_norm_params(feature_mats: list[np.ndarray]) -> np.ndarray:
    """여러 feature 행렬을 이어붙여 (17, 2) [mean, std(ddof=0)]."""
    X = np.concatenate(feature_mats, axis=0)
    mean = np.mean(X, axis=0)
    std = np.std(X, axis=0)
    return np.stack([mean, std], axis=1)


def apply_zscore(X: np.ndarray, norm_params: np.ndarray) -> np.ndarray:
    """원본 z_score_normalization 과 동일: std==0 인 컬럼은 mean 만 뺌."""
    X = X.astype(np.float64) - norm_params[:, 0]
    std = norm_params[:, 1]
    nz = std != 0
    X[:, nz] = X[:, nz] / std[nz]
    return X


def save_norm_params(norm_params: np.ndarray, path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    np.save(path, norm_params)


def load_norm_params(path: str | Path) -> np.ndarray:
    arr = np.load(path)
    assert arr.shape == (len(cmapss.MODEL_FEATURE_NAMES), 2), arr.shape
    return arr


# ---------------- RUL ----------------
def add_rul(df: pd.DataFrame, max_rul: int | None, final_rul: np.ndarray | None = None) -> pd.DataFrame:
    """real_rul, rul 컬럼 추가. final_rul 은 unit id 오름차순 배열 (train 은 None → 0)."""
    df = df.copy()
    sizes = df.groupby("id").size().sort_index()
    if final_rul is None:
        final_rul = np.zeros(len(sizes))
    assert len(final_rul) == len(sizes), (len(final_rul), len(sizes))
    end = pd.Series(sizes.values + np.asarray(final_rul, dtype=float), index=sizes.index)
    df["real_rul"] = end.reindex(df["id"]).to_numpy() - df["time"].to_numpy()
    if max_rul is None:
        max_rul = 999999
    df["rul"] = np.minimum(df["real_rul"], max_rul)
    return df


# ---------------- window 생성 ----------------
def unit_windows(X: np.ndarray, seq_len: int, only_final: bool) -> np.ndarray:
    """(T, F) → (n_win, seq_len, F). 원본 gen_sequence 의 unit 처리와 동일."""
    T = X.shape[0]
    if T >= seq_len:
        if only_final:
            return X[T - seq_len:][None]
        idx = np.arange(T - seq_len + 1)[:, None] + np.arange(seq_len)[None, :]
        return X[idx]
    pad = np.pad(X, ((seq_len - T, 0), (0, 0)), "edge")
    return pad[None]


class FTDataset(Dataset):
    """미세조정/평가용. (X: (seq_len,17) float32, y: (1,) float32)."""

    def __init__(self, df: pd.DataFrame, norm_params: np.ndarray, seq_len: int, max_rul: int,
                 final_rul: np.ndarray | None = None, only_final: bool = False):
        df = add_rul(df, max_rul, final_rul)
        feats = apply_zscore(cmapss.feature_matrix(df), norm_params)
        seqs, labels, ids = [], [], []
        for uid in df["id"].unique():  # 원본: unique() 순서
            m = (df["id"] == uid).to_numpy()
            order = np.argsort(df.loc[m, "time"].to_numpy(), kind="mergesort")
            Xu = feats[m][order]
            ru = df.loc[m, "rul"].to_numpy()[order]
            w = unit_windows(np.concatenate([Xu, ru[:, None]], axis=1), seq_len, only_final)
            seqs.append(w[:, :, :-1])
            labels.append(w[:, -1, -1])
            ids.append(np.full(len(w), uid))
        self.X = np.concatenate(seqs).astype(np.float32)
        self.y = np.concatenate(labels).astype(np.float32)
        self.ids = np.concatenate(ids)
        self.df = df

    def __len__(self):
        return len(self.X)

    def __getitem__(self, i):
        return torch.from_numpy(self.X[i]), torch.tensor([self.y[i]], dtype=torch.float32)


class PreDataset(Dataset):
    """사전학습용. (X, y_rul: (1,) float, y_domain: (1,) long). 원본 gen_pre_sequence 재현."""

    MASK_SEED = 529  # 원본 gen_pre_sequence 내부 상수

    def __init__(self, df: pd.DataFrame, domain: np.ndarray, norm_params: np.ndarray, seq_len: int,
                 max_rul: int, mask_p: float, random_p: float):
        """df: 26 컬럼 (FD001−holdout + FD003, id 충돌 없음), domain: 행별 도메인 라벨."""
        df = add_rul(df, max_rul, None)
        feats = apply_zscore(cmapss.feature_matrix(df), norm_params)
        F = feats.shape[1]
        random.seed(self.MASK_SEED)
        seqs, y_rul, y_dom = [], [], []
        for uid in df["id"].unique():
            m = (df["id"] == uid).to_numpy()
            order = np.argsort(df.loc[m, "time"].to_numpy(), kind="mergesort")
            Xu = feats[m][order]
            ru = df.loc[m, "rul"].to_numpy()[order]
            du = domain[m][order]
            T = Xu.shape[0]
            if T >= seq_len:
                for i in range(0, T - seq_len + 1):
                    w = Xu[i:i + seq_len].copy()
                    self._mask_last_row(w, F, mask_p, random_p)
                    seqs.append(w)
                    y_rul.append(ru[i + seq_len - 1])
                    y_dom.append(du[i + seq_len - 1])
            else:
                w = Xu.copy()
                self._mask_last_row(w, F, mask_p, random_p)
                seqs.append(np.pad(w, ((seq_len - T, 0), (0, 0)), "edge"))
                y_rul.append(ru[-1])
                y_dom.append(du[-1])
        self.X = np.stack(seqs).astype(np.float32)
        self.y = np.asarray(y_rul, dtype=np.float32)
        self.d = np.asarray(y_dom, dtype=np.int64)

    @staticmethod
    def _mask_last_row(w: np.ndarray, F: int, mask_p: float, random_p: float) -> None:
        r = random.random()
        if r < mask_p:
            w[-1, :] = 0.0
        elif mask_p < r < mask_p + random_p:
            w[-1, :] = [random.random() for _ in range(F)]
            w[-1, 1] = 0.0  # 원본: data_array[-1, 2] = 0  (= op2)

    def __len__(self):
        return len(self.X)

    def __getitem__(self, i):
        return (torch.from_numpy(self.X[i]),
                torch.tensor([self.y[i]], dtype=torch.float32),
                torch.tensor([self.d[i]], dtype=torch.long))


# ---------------- 빌더 ----------------
def filter_units(df: pd.DataFrame, units: list[int]) -> pd.DataFrame:
    return df[df["id"].isin(units)].reset_index(drop=True)


def build_finetune(paths, cfg: dict, split: dict, norm_params: np.ndarray | None = None):
    """train(80 unit) FTDataset, test(test_FD00X, only_final) FTDataset, norm_params_ft.

    norm_params 가 None 이면 train 80 unit 으로 계산 (test 제외).
    """
    sub = cfg["sub_dataset"]
    train_df = filter_units(cmapss.load_raw(paths.raw_dir, "train", sub), split["train_units"])
    test_df = cmapss.load_raw(paths.raw_dir, "test", sub)
    rul = cmapss.load_rul(paths.raw_dir, sub)
    if norm_params is None:
        norm_params = compute_norm_params([cmapss.feature_matrix(train_df)])
    train_ds = FTDataset(train_df, norm_params, cfg["seq_len"], cfg["max_rul"])
    test_ds = FTDataset(test_df, norm_params, cfg["seq_len"], cfg["max_rul"], final_rul=rul, only_final=True)
    return train_ds, test_ds, norm_params


def build_pretrain(paths, cfg: dict, split: dict, norm_params: np.ndarray | None = None):
    """(FD001 − holdout, domain 1) + (FD003 train 전체, domain 0). norm_params_pre 는 둘의 train 통계."""
    sub, partner = cfg["sub_dataset"], cfg["pre_partner"]
    main_df = filter_units(cmapss.load_raw(paths.raw_dir, "train", sub), split["train_units"])
    part_df = cmapss.load_raw(paths.raw_dir, "train", partner)
    part_df["id"] = part_df["id"] + int(main_df["id"].max())  # 계획서 B-1: max 로 offset
    domain = np.concatenate([np.ones(len(main_df), dtype=int), np.zeros(len(part_df), dtype=int)])
    df = pd.concat([main_df, part_df], ignore_index=True)
    if norm_params is None:
        norm_params = compute_norm_params([cmapss.feature_matrix(df)])
    p = cfg["pretrain"]
    ds = PreDataset(df, domain, norm_params, cfg["seq_len"], cfg["max_rul"], p["mask_p"], p["random_p"])
    return ds, norm_params


def zero_std_columns(norm_params: np.ndarray) -> list[str]:
    return [n for n, s in zip(cmapss.MODEL_FEATURE_NAMES, norm_params[:, 1]) if s == 0]
