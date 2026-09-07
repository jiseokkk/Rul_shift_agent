"""Operating-condition-aware Local Reference — 샘플 단위 KNN (설계서 3.3, 3.4).

핵심 규칙 (설계서 3.4): KNN 질의에는 **운전조건 W 만** 쓴다. 센서값 X 를 쓰면
주입된 fault 가 정상 reference 검색 자체를 오염시킨다.

  W' = (W - mu_train) / sigma_train  →  KD-tree  →  가장 가까운 K개
  E[x_j | W_j] = K개 이웃의 센서값 평균
  residual r_j = x_j - E[x_j | W_j]

KD-tree 는 pickle 하지 않고 (train W', train Xs, 표준화 파라미터)만 npz 로 저장한 뒤
load 시 다시 만든다 (40만×4 트리 구축은 1초 내외).
"""
from __future__ import annotations

import numpy as np
from sklearn.neighbors import KDTree


class KNNReference:
    """W-conditioned 정상 센서 기댓값 검색기 (deterministic)."""

    def __init__(self, w_train_std: np.ndarray, xs_train: np.ndarray,
                 w_mean: np.ndarray, w_std: np.ndarray, K: int,
                 query_chunk: int = 4000, leaf_size: int = 40):
        self.w_mean = np.asarray(w_mean, dtype=np.float64)
        self.w_std = np.asarray(w_std, dtype=np.float64)
        self.xs_train = np.asarray(xs_train, dtype=np.float32)
        self.K = int(K)
        self.query_chunk = int(query_chunk)
        self._w_train_std = np.asarray(w_train_std, dtype=np.float64)
        self.tree = KDTree(self._w_train_std, leaf_size=leaf_size)

    @classmethod
    def fit(cls, pool: np.ndarray, n_sensors: int, K: int,
            query_chunk: int = 4000) -> "KNNReference":
        """pool: (M,18) pooled clean-train 샘플 (앞 n_sensors 열 = X_s)."""
        xs = np.asarray(pool[:, :n_sensors], dtype=np.float32)
        w = np.asarray(pool[:, n_sensors:], dtype=np.float64)
        w_mean, w_std = w.mean(axis=0), w.std(axis=0) + 1e-12
        return cls((w - w_mean) / w_std, xs, w_mean, w_std, K, query_chunk)

    def standardize(self, w: np.ndarray) -> np.ndarray:
        return (np.asarray(w, dtype=np.float64) - self.w_mean) / self.w_std

    def expected_xs(self, w_query: np.ndarray, K: int | None = None) -> np.ndarray:
        """(N,4) 운전조건 → (N,n_sensors) 이웃 평균 센서값 E[x|W]. 청크 단위 질의."""
        K = self.K if K is None else int(K)
        wq = self.standardize(w_query)
        out = np.empty((len(wq), self.xs_train.shape[1]), dtype=np.float32)
        for lo in range(0, len(wq), self.query_chunk):
            hi = min(lo + self.query_chunk, len(wq))
            idx = self.tree.query(wq[lo:hi], k=K, return_distance=False)
            out[lo:hi] = self.xs_train[idx].mean(axis=1)
        return out

    def pooled_stats(self, w_query: np.ndarray, K: int | None = None) -> dict:
        """이웃 전체를 pooling 한 통계 (설계서 5.4 보조 정보, 진단용)."""
        K = self.K if K is None else int(K)
        wq = self.standardize(w_query)
        idx = self.tree.query(wq, k=K, return_distance=False)
        nb = self.xs_train[idx].reshape(-1, self.xs_train.shape[1])
        q75, q25 = np.percentile(nb, [75, 25], axis=0)
        return {"mean": nb.mean(axis=0), "median": np.median(nb, axis=0),
                "std": nb.std(axis=0), "iqr": q75 - q25, "n_pooled": int(len(nb))}

    def residuals(self, seq: np.ndarray, n_sensors: int, K: int | None = None,
                  ) -> np.ndarray:
        """(T,18) 시계열 → (T,n_sensors) residual r = x - E[x|W]."""
        seq = np.asarray(seq, dtype=np.float32)
        exp = self.expected_xs(seq[:, n_sensors:], K)
        return seq[:, :n_sensors] - exp

    def save(self, path: str) -> None:
        np.savez_compressed(
            path, w_train_std=self._w_train_std.astype(np.float32),
            xs_train=self.xs_train, w_mean=self.w_mean, w_std=self.w_std,
            K=np.int32(self.K), query_chunk=np.int32(self.query_chunk))

    @classmethod
    def load(cls, path: str) -> "KNNReference":
        z = np.load(path)
        return cls(z["w_train_std"].astype(np.float64), z["xs_train"],
                   z["w_mean"], z["w_std"], int(z["K"]), int(z["query_chunk"]))
