"""Standard-form two-sided tabular CUSUM (Page 1954; Montgomery SQC ch.9).

Per-channel bank on a standardized multivariate stream + max-over-channels
statistic (channel bank chosen over Crosier's MCUSUM for fault isolation --
0804 plan §3.2).  No reset within a life (detection credit uses off->on
transitions of the thresholded statistic, not internal resets).
"""
import numpy as np


def cusum_two_sided(z, k=0.5):
    """One channel: standardized stream (T,) -> (C_plus, C_minus) each (T,)."""
    T = len(z)
    cp = np.zeros(T)
    cm = np.zeros(T)
    p = m = 0.0
    for t in range(T):
        p = max(0.0, p + z[t] - k)
        m = max(0.0, m - z[t] - k)
        cp[t] = p
        cm[t] = m
    return cp, cm


def cusum_bank(Z, k=0.5):
    """Standardized stream (T,d) -> statistic (T,) = max over channels and
    sides, plus the per-channel two-sided matrix (T,d) for isolation."""
    T, d = Z.shape
    per = np.zeros((T, d))
    for j in range(d):
        cp, cm = cusum_two_sided(Z[:, j], k=k)
        per[:, j] = np.maximum(cp, cm)
    return per.max(axis=1), per
