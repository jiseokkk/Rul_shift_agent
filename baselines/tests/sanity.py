"""§3.4 validation: synthetic sanity + cross-checks against published values.

1. CUSUM ARL0 Monte Carlo vs Montgomery (SQC, Table 9.4 / Hawkins):
   two-sided tabular CUSUM, k=0.5: h=4 -> ARL0 ~ 168, h=5 -> ARL0 ~ 465.
2. CUSUM mean-shift sanity: 1-sigma step detected with small delay; max-bank
   isolates the shifted channel.
3. PCA directionality: shift along the retained loading direction raises T^2
   (SPE flat); shift orthogonal to the subspace raises SPE (T^2 flat).

Run:  PYTHONPATH=/home/iai4/Desktop <python> -m han.Rul_shift_agent.baselines.tests.sanity
Writes baselines/tests/results_sanity.json.
"""
import json
import os

import numpy as np

from han.Rul_shift_agent.baselines.cusum.core import cusum_two_sided, cusum_bank
from han.Rul_shift_agent.baselines.pca.core import PCAMonitor

OUT = os.path.join(os.path.dirname(__file__), "results_sanity.json")
res = {}


def arl0_mc(h, k=0.5, n_runs=4000, horizon=5000, seed=0):
    rng = np.random.default_rng(seed)
    lengths = []
    for _ in range(n_runs):
        z = rng.normal(size=horizon)
        p = m = 0.0
        t_hit = horizon
        for t in range(horizon):
            p = max(0.0, p + z[t] - k)
            m = max(0.0, m - z[t] - k)
            if p > h or m > h:
                t_hit = t + 1
                break
        lengths.append(t_hit)
    return float(np.mean(lengths))


# -- 1. ARL0 cross-check ----------------------------------------------------
published = {4.0: 168.0, 5.0: 465.0}
res["arl0"] = {}
ok = True
for h, ref in published.items():
    got = arl0_mc(h)
    rel = abs(got - ref) / ref
    res["arl0"][f"h={h}"] = {"mc": round(got, 1), "published": ref,
                             "rel_err": round(rel, 3)}
    ok &= rel < 0.10
res["arl0"]["pass"] = ok
assert ok, f"ARL0 mismatch: {res['arl0']}"

# -- 2. mean-shift sanity ---------------------------------------------------
# NOTE h=8 (not 5): a 6-channel max-bank divides the per-channel ARL0 by ~d,
# so h=5 (ARL0=465 single-channel) gives family-wise ARL0 < the 150-point
# pre-onset stretch -- pre-onset alarms would be EXPECTED, not a bug.
rng = np.random.default_rng(1)
T, d, onset = 300, 6, 150
Z = rng.normal(size=(T, d))
Z[onset:, 2] += 1.0                       # 1-sigma step on channel 2
stat, per = cusum_bank(Z, k=0.5)
h = 8.0
hits = np.where(stat > h)[0]
first = int(hits[0]) if len(hits) else None
pre_fa = bool((stat[:onset] > h).any())
iso = int(per[first].argmax()) if first is not None else None
res["mean_shift"] = {"first_alarm": first, "onset": onset,
                     "delay": first - onset if first else None,
                     "pre_onset_fa": pre_fa, "isolated_channel": iso,
                     "pass": bool(first and 0 < first - onset < 40
                                  and not pre_fa and iso == 2)}
assert res["mean_shift"]["pass"], res["mean_shift"]

# -- 3. PCA directionality --------------------------------------------------
rng = np.random.default_rng(2)
n, dim = 600, 10
# factor model: 2 strong latent factors + small residual noise
F = rng.normal(size=(n, 2))
L = rng.normal(size=(2, dim))
X = F @ L + 0.1 * rng.normal(size=(n, dim))
mon = PCAMonitor(X, ev_target=0.90)
t2c, spec_ = mon.scores(X)
v_in = mon.P[:, 0]                                   # retained direction
# orthogonal-to-subspace direction
Q = np.eye(dim) - mon.P @ mon.P.T
v_out = Q @ rng.normal(size=dim)
v_out /= np.linalg.norm(v_out)
shift_in = X + 8.0 * v_in
shift_out = X + 8.0 * v_out
t2i, spei = mon.scores(shift_in)
t2o, speo = mon.scores(shift_out)
res["pca_direction"] = {
    "n_comp": mon.n_comp, "ev_captured": round(mon.ev_captured, 3),
    "t2_ratio_in": round(float(t2i.mean() / t2c.mean()), 2),
    "spe_ratio_in": round(float(spei.mean() / spec_.mean()), 2),
    "t2_ratio_out": round(float(t2o.mean() / t2c.mean()), 2),
    "spe_ratio_out": round(float(speo.mean() / speo.mean()
                                 and speo.mean() / spec_.mean()), 2),
}
res["pca_direction"]["pass"] = bool(
    res["pca_direction"]["t2_ratio_in"] > 5
    and res["pca_direction"]["spe_ratio_in"] < 2
    and res["pca_direction"]["spe_ratio_out"] > 5
    and res["pca_direction"]["t2_ratio_out"] < 2)
assert res["pca_direction"]["pass"], res["pca_direction"]

with open(OUT, "w") as f:
    json.dump(res, f, indent=1)
print(json.dumps(res, indent=1))
print("ALL SANITY CHECKS PASSED")
