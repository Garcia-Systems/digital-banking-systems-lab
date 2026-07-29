"""Tests for deterministic Chapter 11 payment queues."""

import pytest

from bank_sim.payment_queues import (
    PaymentQueue,
    PaymentType,
    capacity_result,
    run_capacity_scenario,
)
from bank_sim.scheduler import EventScheduler


def test_fifo_order_and_same_time_tie_breaking() -> None:
    scheduler = EventScheduler()
    queue = PaymentQueue(scheduler, capacity=1)
    performed: list[str] = []

    for payment_id in ("ACH-1", "RETURN-1", "ACH-2"):
        scheduler.schedule_at(
            4,
            lambda payment_id=payment_id: queue.enqueue(
                payment_id,
                PaymentType.ACH_RETURN
                if payment_id.startswith("RETURN")
                else PaymentType.ACH_TRANSFER,
                lambda payment_id=payment_id: performed.append(payment_id),
            ),
        )

    scheduler.run()

    assert performed == ["ACH-1", "RETURN-1", "ACH-2"]
    assert [item.arrival_order for item in queue.completed] == [0, 1, 2]
    assert [item.queue_position for item in queue.completed] == [1, 2, 3]
    assert [item.completed_at for item in queue.completed] == [5, 6, 7]


def test_rejected_payment_never_enters_queue() -> None:
    scheduler = EventScheduler()
    queue = PaymentQueue(scheduler)

    assert queue.enqueue_ach_transfer("REJECTED", lambda: None, accepted=False) is None
    assert queue.queued == ()
    assert queue.events == ()
    assert scheduler.pending == 0


def test_heavy_load_grows_then_drains_with_integer_statistics() -> None:
    queue, _ = run_capacity_scenario(1)

    assert queue.queued == ()
    assert [item.wait_duration for item in queue.completed] == [1, 2, 2, 3, 4, 5]
    assert queue.statistics.total_processed == 6
    assert queue.statistics.average_wait == 2
    assert queue.statistics.longest_wait == 5
    assert queue.statistics.maximum_queue_depth == 6
    assert queue.statistics.remaining_queued_items == 0


def test_light_load_never_builds_a_backlog() -> None:
    scheduler = EventScheduler()
    queue = PaymentQueue(scheduler, capacity=1)
    for arrival in (0, 3, 6):
        scheduler.schedule_at(
            arrival,
            lambda arrival=arrival: queue.enqueue_ach_transfer(
                f"ACH-{arrival}", lambda: None
            ),
        )

    scheduler.run()

    assert queue.statistics.maximum_queue_depth == 1
    assert [item.wait_duration for item in queue.completed] == [1, 1, 1]


def test_capacities_change_latency_not_financial_results() -> None:
    results = [capacity_result(capacity) for capacity in (1, 2, 4)]

    assert len({result.ledger_effects for result in results}) == 1
    assert {result.final_balance for result in results} == {100_000}
    assert [result.final_completion for result in results] == [6, 3, 2]
    assert [result.statistics.average_wait for result in results] == [2, 1, 0]
    assert [result.statistics.longest_wait for result in results] == [5, 2, 1]
    assert [result.queue_after_first_minute for result in results] == [5, 4, 2]


@pytest.mark.parametrize("capacity", [0, -1, True, 1.5])
def test_capacity_must_be_a_positive_integer(capacity: object) -> None:
    with pytest.raises(ValueError, match="positive integer"):
        PaymentQueue(EventScheduler(), capacity=capacity)  # type: ignore[arg-type]
