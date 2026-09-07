"""판정 시계열 → Alarm Event → TP / FP / FN / TN 분류 (설계서 12.3, 12.4).

규칙을 바꿀 때는 docs/research_plan_v2.md 12.4 를 함께 고친다 (CLAUDE.md 규칙 7).

Event (12.3)
    연속된 FAULT 판정 하나 = Event, onset = 첫 FAULT cycle. NORMAL 이 나온 뒤 다시 FAULT 면 새 Event.
    ERROR cycle(판정 실패)은 FAULT 도 NORMAL 도 아니므로 연속성을 끊지 않고 건너뛴다
    (NORMAL 로 보면 Event 가 인위적으로 쪼개지고, FAULT 로 보면 없는 알람을 만든다. FailRate 로 따로 보고).

분류 (12.4)
    TP  : faulty 에서 t_f <= onset <= t_f + D 인 **첫** Event. trajectory 당 최대 1개. d = onset - t_f.
          TP 이후 Event 는 어느 분류에도 넣지 않는다.
    FP  : clean 의 모든 Event + faulty 에서 onset < t_f 인 Event.
          t_f 이전에 시작해 t_f 를 넘겨 지속되는 Event 도 FP 로만 센다 (TP 후보 제외).
    FN  : faulty 에 TP 가 없는 경우. trajectory 당 최대 1개.
          Alarm 없음 / 늦은 탐지(t_f + D 이후에만) → Late / 사전 Alarm 지속 → FP 와 FN 동시
    TN  : clean 에서 Event 가 0개. trajectory 당 1개.
warm-up cycle 은 애초에 판정하지 않으므로 Event 에 들어오지 않는다.
"""
from __future__ import annotations

from dataclasses import dataclass, field


# =========================================================================== #
# Event
# =========================================================================== #
@dataclass
class AlarmEvent:
    onset: int          # 첫 FAULT cycle
    end: int            # 마지막 연속 FAULT cycle
    n_cycles: int       # Event 를 구성한 FAULT 판정 수

    def covers(self, cycle: int) -> bool:
        return self.onset <= cycle <= self.end


def to_events(decisions: list[dict]) -> list[AlarmEvent]:
    """decisions: [{'cycle': int, 'sensor_status': 'NORMAL'|'FAULT'|'ERROR'}, ...]"""
    rows = sorted(decisions, key=lambda r: int(r["cycle"]))
    events: list[AlarmEvent] = []
    cur: AlarmEvent | None = None
    for r in rows:
        st, c = r["sensor_status"], int(r["cycle"])
        if st == "FAULT":
            if cur is None:
                cur = AlarmEvent(onset=c, end=c, n_cycles=1)
            else:
                cur.end = c
                cur.n_cycles += 1
        elif st == "NORMAL":
            if cur is not None:
                events.append(cur)
                cur = None
        # ERROR: 아무것도 하지 않음 (연속성 유지)
    if cur is not None:
        events.append(cur)
    return events


def fail_cycles(decisions: list[dict]) -> list[int]:
    return [int(r["cycle"]) for r in decisions if r["sensor_status"] == "ERROR"]


# =========================================================================== #
# 분류
# =========================================================================== #
@dataclass
class ScenarioResult:
    scenario_id: str
    is_faulty: bool
    alpha: float = 0.0
    t_f: int | None = None
    tp: int = 0
    fp: int = 0
    fn: int = 0
    tn: int = 0
    late: bool = False
    delay: int | None = None          # TP 의 d = onset - t_f
    n_events: int = 0
    n_fail_cycles: int = 0
    n_eval_cycles: int = 0
    notes: list[str] = field(default_factory=list)


def classify_scenario(scenario_id: str, events: list[AlarmEvent], gt: dict, D: int,
                      n_fail_cycles: int = 0, n_eval_cycles: int = 0) -> ScenarioResult:
    r = ScenarioResult(scenario_id=scenario_id, is_faulty=gt["is_faulty"],
                       alpha=gt.get("alpha", 0.0), t_f=gt.get("t_f"),
                       n_events=len(events), n_fail_cycles=n_fail_cycles,
                       n_eval_cycles=n_eval_cycles)

    if not gt["is_faulty"]:                              # clean
        if events:
            r.fp = len(events)
        else:
            r.tn = 1
        return r

    t_f = int(gt["t_f"])
    hi = t_f + int(D)

    pre = [e for e in events if e.onset < t_f]           # 전부 FP
    r.fp = len(pre)
    if any(e.end >= t_f for e in pre):
        r.notes.append("pre_onset_alarm_spans_tf")

    in_window = [e for e in events if t_f <= e.onset <= hi]
    if in_window:
        tp_event = min(in_window, key=lambda e: e.onset)
        r.tp = 1
        r.delay = int(tp_event.onset - t_f)
        return r                                         # TP 이후 Event 는 분류하지 않는다

    r.fn = 1
    if any(e.onset > hi for e in events):
        r.late = True
        r.notes.append("late_detection")
    elif not events:
        r.notes.append("no_alarm")
    return r


def classify_all(per_scenario_events: dict[str, list[AlarmEvent]], gts: dict[str, dict],
                 D: int, fail_counts: dict[str, int] | None = None,
                 eval_counts: dict[str, int] | None = None) -> list[ScenarioResult]:
    fail_counts = fail_counts or {}
    eval_counts = eval_counts or {}
    return [classify_scenario(sid, ev, gts[sid], D, fail_counts.get(sid, 0), eval_counts.get(sid, 0))
            for sid, ev in per_scenario_events.items()]


def clean_monitored_cycles(gts: dict[str, dict], cycle_counts: dict[str, int], warm_up: int) -> int:
    """FAR 분모 (설계서 13): sum_clean (cycle 수 - warm_up) + sum_faulty (t_f - (warm_up + 1))."""
    total = 0
    for sid, gt in gts.items():
        n = int(cycle_counts.get(sid, 0))
        if not gt["is_faulty"]:
            total += max(0, n - warm_up)
        else:
            total += max(0, int(gt["t_f"]) - (warm_up + 1))
    return total
