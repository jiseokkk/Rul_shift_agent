"""12.4 규칙 케이스 — 사전 alarm 지속, late, warm-up, TN, FAR 분모.

규칙을 바꿀 때는 docs/research_plan_v2.md 12.4 와 이 테스트를 함께 고친다.
"""
from agent_rul.evaluation import classify, metrics
from agent_rul.evaluation.classify import to_events

D = 5
WARM = 4


def _dec(start: int, pattern: str) -> list[dict]:
    """'NNFFN' 문자열 → 판정 리스트. N=NORMAL, F=FAULT, E=ERROR."""
    m = {"N": "NORMAL", "F": "FAULT", "E": "ERROR"}
    return [{"cycle": start + i, "sensor_status": m[ch]} for i, ch in enumerate(pattern)]


def _gt(faulty: bool, t_f=None, alpha=1.0, life=59) -> dict:
    return {"is_faulty": faulty, "t_f": t_f, "alpha": alpha if faulty else 0.0,
            "life_cycles": life, "scenario_id": "x", "unit": 11}


# --------------------------------------------------------------------- events
def test_events_merge_consecutive():
    ev = to_events(_dec(100, "NNFFFNN"))
    assert len(ev) == 1 and ev[0].onset == 102 and ev[0].end == 104


def test_normal_splits_events():
    ev = to_events(_dec(100, "FFNFF"))
    assert [(e.onset, e.end) for e in ev] == [(100, 101), (103, 104)]


def test_error_does_not_split_event():
    ev = to_events(_dec(100, "FEF"))
    assert len(ev) == 1 and ev[0].onset == 100 and ev[0].end == 102


# ------------------------------------------------------------------- TP / FN
def test_tp_within_tolerance():
    ev = to_events(_dec(99, "NNNFF"))
    r = classify.classify_scenario("s", ev, _gt(True, 100), D)
    assert (r.tp, r.fn, r.fp, r.delay) == (1, 0, 0, 2)


def test_tp_at_exact_boundary():
    r = classify.classify_scenario("s", to_events(_dec(105, "F")), _gt(True, 100), D)
    assert r.tp == 1 and r.delay == 5


def test_late_detection_is_fn():
    r = classify.classify_scenario("s", to_events(_dec(100, "NNNNNNNFF")), _gt(True, 100), D)
    assert (r.tp, r.fn, r.late) == (0, 1, True)
    assert "late_detection" in r.notes


def test_no_alarm_is_fn():
    r = classify.classify_scenario("s", to_events(_dec(100, "NNNNN")), _gt(True, 100), D)
    assert (r.tp, r.fn, r.fp, r.late) == (0, 1, 0, False)
    assert "no_alarm" in r.notes


# ------------------------------------------------------------------------ FP
def test_pre_onset_alarm_spanning_tf_is_fp_only():
    r = classify.classify_scenario("s", to_events(_dec(97, "FFFFFFF")), _gt(True, 100), D)
    assert (r.tp, r.fp, r.fn) == (0, 1, 1)
    assert "pre_onset_alarm_spans_tf" in r.notes


def test_pre_onset_alarm_then_separate_tp():
    r = classify.classify_scenario("s", to_events(_dec(95, "FFNNNFF")), _gt(True, 100), D)
    assert (r.tp, r.fp, r.fn, r.delay) == (1, 1, 0, 0)


def test_events_after_tp_ignored():
    r = classify.classify_scenario("s", to_events(_dec(100, "FFNNFF")), _gt(True, 100), D)
    assert (r.tp, r.fp, r.fn) == (1, 0, 0)


def test_clean_alarms_all_fp():
    r = classify.classify_scenario("c", to_events(_dec(5, "NNFFNNFN")), _gt(False), D)
    assert (r.fp, r.tn, r.tp, r.fn) == (2, 0, 0, 0)


def test_clean_no_alarm_is_tn():
    r = classify.classify_scenario("c", to_events(_dec(5, "NNNNN")), _gt(False), D)
    assert (r.tn, r.fp) == (1, 0)


# ------------------------------------------------------- warm-up / FAR 분모
def test_warmup_cycles_never_reach_classification():
    dec = _dec(5, "FF")
    assert min(r["cycle"] for r in dec) > WARM
    assert to_events(dec)[0].onset == 5


def test_clean_monitored_cycles_formula():
    gts = {"c1": _gt(False, life=59), "f1": _gt(True, 27, life=59)}
    n = classify.clean_monitored_cycles(gts, {"c1": 59, "f1": 59}, WARM)
    assert n == (59 - 4) + (27 - 5)


def test_metrics_aggregate_basic():
    results = [
        classify.classify_scenario("f1", to_events(_dec(100, "NNFF")), _gt(True, 100), D),
        classify.classify_scenario("f2", to_events(_dec(100, "NNNNN")), _gt(True, 100), D),
        classify.classify_scenario("c1", to_events(_dec(5, "NFN")), _gt(False), D),
    ]
    m = metrics.aggregate(results, clean_monitored=100)
    assert (m["TP"], m["FP"], m["FN"], m["TN"]) == (1, 1, 1, 0)
    assert m["precision"] == 0.5 and m["recall"] == 0.5 and m["f1"] == 0.5
    assert m["MDD"] == 2.0
    assert m["FAR_1000"] == 10.0


def test_subsample_period():
    rows = _dec(5, "N" * 10)                      # cycle 5..14
    sub = metrics.subsample_decisions(rows, S=3, warm_up=WARM)
    assert [r["cycle"] for r in sub] == [5, 8, 11, 14]
