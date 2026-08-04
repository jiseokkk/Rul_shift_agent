"""Standard-form PCA monitoring: Hotelling T^2 (retained subspace) + SPE/Q
residual statistic (Jackson & Mudholkar 1979; Qin 2003).

Fit on clean-train cycle vectors (restandardized), retain components to reach
ev_target explained variance.  Thresholds are NOT the parametric UCLs -- the
0804 protocol calibrates all thresholds as u20 quantiles (plan §4.2), so this
module only produces scores.
"""
import numpy as np

EV_TARGET = 0.90


class PCAMonitor:
    def __init__(self, X_train, ev_target=EV_TARGET):
        self.mean = X_train.mean(axis=0)
        Xc = X_train - self.mean
        U, S, Vt = np.linalg.svd(Xc, full_matrices=False)
        lam = S ** 2 / (len(Xc) - 1)               # component variances
        evr = lam / lam.sum()
        self.n_comp = int(np.searchsorted(np.cumsum(evr), ev_target) + 1)
        self.P = Vt[: self.n_comp].T               # (d,a) loadings
        self.lam = lam[: self.n_comp]
        self.ev_captured = float(np.cumsum(evr)[self.n_comp - 1])

    def scores(self, X):
        """X (N,d) -> (t2 (N,), spe (N,))."""
        Xc = X - self.mean
        t = Xc @ self.P                             # (N,a)
        t2 = ((t ** 2) / self.lam).sum(axis=1)
        recon = t @ self.P.T
        spe = ((Xc - recon) ** 2).sum(axis=1)
        return t2, spe
