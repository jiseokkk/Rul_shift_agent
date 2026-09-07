"""window 분할 경계 (설계서 2.2)."""
import numpy as np

from agent_rul import data


def _seq(n, p=18):
    return np.arange(n * p, dtype=np.float32).reshape(n, p)


def test_exact_multiple():
    w = data.split_windows(_seq(90), 30)
    assert w.shape == (3, 30, 18)
    assert np.allclose(w[0, 0], _seq(90)[0])
    assert np.allclose(w[1, 0], _seq(90)[30])
    assert np.allclose(w[2, -1], _seq(90)[89])


def test_tail_dropped():
    """꼬리 샘플(< 1 window)은 버린다."""
    w = data.split_windows(_seq(95), 30)
    assert w.shape == (3, 30, 18)
    assert data.n_windows(95, 30) == 3


def test_too_short_returns_empty():
    w = data.split_windows(_seq(29), 30)
    assert w.shape == (0, 30, 18)
    assert data.n_windows(29, 30) == 0


def test_no_cycle_boundary_crossing():
    """cycle 두 개를 따로 나눈 결과가 이어붙인 것과 다르다 (경계 유지 확인)."""
    a, b = _seq(50), _seq(50) + 1000
    wa, wb = data.split_windows(a, 30), data.split_windows(b, 30)
    assert len(wa) == 1 and len(wb) == 1
    assert len(data.split_windows(np.concatenate([a, b]), 30)) == 3


def test_window_index():
    assert list(data.window_index(95, 30)) == [0, 30, 60]


def test_stream_yields_cycles_in_order():
    sc = {"cycles": np.array([3, 4, 5]), "series": [_seq(10), _seq(20), _seq(30)]}
    out = list(data.stream(sc))
    assert [c for c, _ in out] == [3, 4, 5]
    assert [len(s) for _, s in out] == [10, 20, 30]
