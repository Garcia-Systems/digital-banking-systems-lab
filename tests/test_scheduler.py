"""Focused tests for deterministic synchronous event scheduling."""

import pytest

from bank_sim.clock import VirtualClock
from bank_sim.scheduler import EventScheduler, Execution


def test_events_run_chronologically_with_insertion_order_ties() -> None:
    observed: list[str] = []
    scheduler = EventScheduler()
    scheduler.schedule_at(3, lambda: observed.append("third"))
    scheduler.schedule_at(1, lambda: observed.append("first"))
    scheduler.schedule_at(3, lambda: observed.append("fourth"))
    scheduler.schedule_at(2, lambda: observed.append("second"))

    scheduler.run()

    assert observed == ["first", "second", "third", "fourth"]
    assert scheduler.clock.time == 3
    assert scheduler.pending == 0
    assert scheduler.history == (
        Execution(1, 1),
        Execution(2, 3),
        Execution(3, 0),
        Execution(3, 2),
    )


def test_callback_can_schedule_an_event() -> None:
    observed: list[int] = []
    scheduler = EventScheduler(VirtualClock(5))

    def first() -> None:
        observed.append(scheduler.clock.time)
        scheduler.schedule_after(2, lambda: observed.append(scheduler.clock.time))

    scheduler.schedule_after(1, first)
    scheduler.run()
    assert observed == [6, 8]


def test_repeated_runs_are_deterministic() -> None:
    def execute() -> tuple[list[int], tuple[Execution, ...]]:
        observed: list[int] = []
        scheduler = EventScheduler()
        for time in (4, 1, 4, 2):
            scheduler.schedule_at(time, lambda time=time: observed.append(time))
        scheduler.run()
        return observed, scheduler.history

    assert execute() == execute()


def test_callback_failure_contract() -> None:
    observed: list[str] = []
    scheduler = EventScheduler()
    scheduler.schedule_at(1, lambda: observed.append("ok"))

    def fail() -> None:
        raise RuntimeError("callback failed")

    scheduler.schedule_at(2, fail)
    scheduler.schedule_at(3, lambda: observed.append("later"))

    with pytest.raises(RuntimeError, match="callback failed"):
        scheduler.run()

    assert scheduler.clock.time == 2
    assert scheduler.pending == 1
    assert scheduler.history == (Execution(1, 0),)
    scheduler.run()
    assert observed == ["ok", "later"]


def test_run_next_reports_an_empty_queue() -> None:
    assert EventScheduler().run_next() is False


@pytest.mark.parametrize("time", [-1, 1.5, True])
def test_invalid_event_times_are_rejected(time: object) -> None:
    with pytest.raises(ValueError, match="nonnegative integer"):
        EventScheduler().schedule_at(time, lambda: None)  # type: ignore[arg-type]


def test_past_events_and_invalid_callbacks_are_rejected() -> None:
    scheduler = EventScheduler(VirtualClock(2))
    with pytest.raises(ValueError, match="past"):
        scheduler.schedule_at(1, lambda: None)
    with pytest.raises(TypeError, match="callable"):
        scheduler.schedule_at(2, None)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="nonnegative integer"):
        scheduler.schedule_after(-1, lambda: None)
