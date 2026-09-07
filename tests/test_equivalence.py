"""배치 → 스트림 전환 등가성 (실제 데이터가 있을 때만).

1) test_stream_equals_batch_real_data
   같은 머신에서 새 코드로 배치(전체 window 한 번에) 와 스트림(window 하나씩, cycle 하나씩) 을
   계산해 **정확히** 같은지 본다. 리팩터링 자체의 정합성. 환경에 무관.

2) test_*_match_old_artifacts / test_prompts_identical_to_sent
   예전 02/03/04 산출물(artifacts/eda, artifacts/rul, results/rep1_seed42/prompts)과 비교.
   KNN 이웃 검색의 거리 동률(tie) 처리가 sklearn 버전에 따라 달라 z_w 가 1e-3 수준으로 흔들릴 수
   있으므로, 산출물을 만든 머신(Linux, LLMshift env)에서 AGENT_RUL_STRICT_EQUIV=1 로 돌려야
   의미가 있다. 그 외 환경에서는 차이 요약만 출력하고 skip 한다.

프롬프트가 바이트 단위로 같으면 판정 캐시 키가 같아서 기존 판정이 그대로 재사용된다.
"""
import glob
import os

import numpy as np
import pytest

from agent_rul import data
from agent_rul.agent import prompts
from agent_rul.config import PROJECT_ROOT, load_config
from agent_rul.reference import calibration
from agent_rul.tools import eda
from agent_rul.tools.rul import rul_context
from agent_rul.utils import read_csv

OLD_EDA = os.path.join(PROJECT_ROOT, "artifacts", "eda")
OLD_RUL = os.path.join(PROJECT_ROOT, "artifacts", "rul")
OLD_PROMPTS = os.path.join(PROJECT_ROOT, "results", "rep1_seed42", "prompts")
STRICT = os.environ.get("AGENT_RUL_STRICT_EQUIV", "") == "1"


def _cfg():
    try:
        return load_config()
    except (FileNotFoundError, OSError) as e:
        pytest.skip(f"데이터 없음: {e}")


def _soft_fail(msg: str):
    if STRICT:
        pytest.fail(msg)
    pytest.skip("[non-strict] " + msg)


@pytest.fixture(scope="module")
def streamed():
    cfg = _cfg()
    from agent_rul.reference import build
    ref = build.load_all(cfg)
    tool = eda.EDATool(cfg, ref)
    out = {}
    for sid in cfg.scenarios:
        sc = data.load_scenario(cfg.paths.corrupted_root, sid)
        tool.reset(sid, sc["unit"])
        for c, seq in data.stream(sc):
            for win in data.split_windows(seq, cfg.samples_per_window):
                tool.observe_window(c, win)
            tool.end_cycle(c)
        out[sid] = {"scenario": sc, "cycles": list(tool.cycles),
                    "aggs": {c: tool.aggs[c] for c in tool.cycles},
                    "windows": {c: tool.windows[c] for c in tool.cycles},
                    "evidence": {c: tool.evidence(c) for c in tool.cycles if tool.is_decision_cycle(c)}}
    return cfg, ref, out


# =========================================================================== #
# 1. 스트림 == 배치 (같은 머신, 새 코드)
# =========================================================================== #
def test_stream_equals_batch_real_data(streamed):
    cfg, ref, out = streamed
    cal_arr = calibration.as_arrays(ref["calibration"])
    g_arr = calibration.global_as_arrays(ref["global"])
    for sid, s in out.items():
        used, aggs = [], []
        for c, seq in data.stream(s["scenario"]):
            win = data.split_windows(seq, cfg.samples_per_window)
            if len(win) == 0:
                continue
            ws = eda.compute_window_stats(win, ref["knn"], cal_arr, cfg.n_sensors, g_arr)
            aggs.append(eda.aggregate_cycle(ws, cal_arr["q95"], cfg.min_windows_short_flight))
            used.append(c)
            for k in ("z_w", "std_ratio", "t2", "contrib_frac"):
                np.testing.assert_array_equal(s["windows"][c][k], ws[k].astype(np.float32),
                                              err_msg=f"{sid} cycle {c} {k}")
        eda.fill_contrasts(aggs, cfg.L_c)
        assert used == s["cycles"], sid
        # einsum/BLAS 가 배치 크기(window 1개 vs n_w 개)에 따라 1e-14 수준으로 다를 수 있다.
        # 프롬프트는 소수 1~2자리로 반올림하므로 영향 없음.
        for c, agg in zip(used, aggs):
            for col in eda.SENSOR_COLS:
                np.testing.assert_allclose(s["aggs"][c]["sensor"][col], agg["sensor"][col],
                                           rtol=1e-9, atol=1e-12, err_msg=f"{sid} cycle {c} {col}")
            a, b = s["aggs"][c]["cycle"], agg["cycle"]
            assert (a["n_windows"], a["short_flight"]) == (b["n_windows"], b["short_flight"])
            assert np.isclose(a["t2_median"], b["t2_median"], rtol=1e-9)
            assert np.isclose(a["t2_max"], b["t2_max"], rtol=1e-9)


def test_decision_cycles_rule_unchanged(streamed):
    """판정 대상 = warm-up 이후 & 이전 cycle L_c 개 (예전 EDATool.decision_cycles 와 동일)."""
    cfg, ref, out = streamed
    for sid, s in out.items():
        cycles = s["cycles"]
        expected = [c for i, c in enumerate(cycles) if c > cfg.warm_up and i >= cfg.L_c]
        assert sorted(s["evidence"]) == expected, sid


# =========================================================================== #
# 2. 예전 산출물과 비교 (산출물을 만든 머신에서 STRICT 로)
# =========================================================================== #
def test_window_arrays_match_old_artifacts(streamed):
    cfg, ref, out = streamed
    if not os.path.isdir(OLD_EDA):
        pytest.skip("artifacts/eda 없음")
    worst = 0.0
    for sid, s in out.items():
        z = np.load(os.path.join(OLD_EDA, sid, "window.npz"))
        assert list(z["cycles"].astype(int)) == s["cycles"], sid
        b = z["window_bounds"]
        for i, c in enumerate(s["cycles"]):
            lo, hi = int(b[i]), int(b[i + 1])
            for k in ("z_w", "std_ratio", "t2", "contrib_frac"):
                worst = max(worst, float(np.abs(s["windows"][c][k] - z[k][lo:hi]).max()))
    if worst > 1e-5:
        _soft_fail(f"예전 window.npz 와 최대 |diff| = {worst:.3g} (KNN tie / sklearn 버전 차이 가능)")


def test_prompts_identical_to_sent(streamed):
    """재생성한 runtime input == 실제 LLM 에 보낸 텍스트 (판정 캐시 재사용의 전제)."""
    cfg, ref, out = streamed
    if not os.path.isdir(OLD_RUL) or not os.path.isdir(OLD_PROMPTS):
        pytest.skip("artifacts/rul 또는 results/rep1_seed42/prompts 없음")
    n, mism = 0, []
    for sid, s in out.items():
        preds = {int(r["cycle"]): {"rul": float(r["rul"])}
                 for r in read_csv(os.path.join(OLD_RUL, f"{sid}.csv"))}
        for c, ev in s["evidence"].items():
            p = os.path.join(OLD_PROMPTS, f"{sid}_{c}.txt")
            if not os.path.exists(p):
                continue
            with open(p, "r", encoding="utf-8") as f:
                sent = f.read()
            n += 1
            if prompts.format_input(ev, rul_context(preds, c, cfg.L_c)) != sent:
                mism.append((sid, c))
    assert n > 0
    if mism:
        _soft_fail(f"{len(mism)}/{n} 프롬프트 불일치 (예: {mism[:3]})")
    print(f"\n[equivalence] {n} prompts byte-identical")


def test_old_prompt_cycles_covered(streamed):
    """예전 run 이 판정한 cycle 은 새 규칙에서도 전부 판정 대상이다."""
    cfg, ref, out = streamed
    if not os.path.isdir(OLD_PROMPTS):
        pytest.skip("results/rep1_seed42/prompts 없음")
    for sid, s in out.items():
        old = {int(os.path.basename(p)[len(sid) + 1:-4])
               for p in glob.glob(os.path.join(OLD_PROMPTS, f"{sid}_*.txt"))}
        new = set(s["evidence"])
        assert old <= new, f"{sid}: 예전 판정 cycle 이 새 규칙에서 빠짐: {sorted(old - new)}"
