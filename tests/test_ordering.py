"""Focused tests for deterministic out-of-order event validation."""

from dataclasses import replace

import pytest

from bank_sim.ledger import replay
from bank_sim.ordering import (
    EventRevision,
    EventSequence,
    OrderedEventProcessor,
    PaymentEventType,
    ProcessingDecision,
    ordering_ledger,
    out_of_order_events,
    payment_events,
    process_events,
)


def test_correct_order_processes_every_event_and_one_financial_effect() -> None:
    processor = process_events(payment_events())

    assert [result.decision for result in processor.results] == [
        ProcessingDecision.PROCESSED
    ] * 4
    assert processor.payment_state("PAY-ORDER-001") == "PaymentCompleted"
    assert [entry.entry_id for entry in processor.ledger.entries] == [
        "OPEN",
        "PAY-ORDER-001-SETTLEMENT",
    ]
    assert replay(processor.ledger.entries) == 75_000


def test_reversed_delivery_is_buffered_then_drained_in_sequence() -> None:
    processor = process_events(payment_events(arrival=(3, 2, 1, 4)))

    assert [result.decision for result in processor.results] == [
        ProcessingDecision.BUFFERED,
        ProcessingDecision.BUFFERED,
        ProcessingDecision.PROCESSED,
        ProcessingDecision.PROCESSED,
        ProcessingDecision.PROCESSED,
        ProcessingDecision.PROCESSED,
    ]
    processed_sequences = [
        result.event.sequence.value
        for result in processor.results
        if result.decision is ProcessingDecision.PROCESSED
    ]
    assert processed_sequences == [1, 2, 3, 4]
    assert processor.statistics.out_of_order_events == 2
    assert processor.statistics.buffered_events == 2


def test_late_superseded_event_is_stale_and_cannot_change_ledger() -> None:
    processor = process_events(payment_events())
    late = replace(payment_events()[1], event_id="LATE-VALIDATION", arrival_order=5)
    entries_before = processor.ledger.entries

    result = processor.receive(late)[0]

    assert result.decision is ProcessingDecision.STALE
    assert processor.ledger.entries == entries_before
    assert replay(processor.ledger.entries) == 75_000


def test_duplicate_old_event_is_not_reapplied() -> None:
    processor = process_events(payment_events())
    old_event = replace(payment_events()[0], arrival_order=5)

    result = processor.receive(old_event)[0]

    assert result.decision is ProcessingDecision.DUPLICATE
    assert processor.statistics.duplicate_events == 1
    assert processor.statistics.ledger_entries_created == 1
    assert replay(processor.ledger.entries) == 75_000


def test_out_of_order_scenario_statistics_are_exact() -> None:
    processor = process_events(out_of_order_events())

    assert processor.statistics.events_received == 6
    assert processor.statistics.events_processed == 4
    assert processor.statistics.stale_events == 1
    assert processor.statistics.out_of_order_events == 2
    assert processor.statistics.buffered_events == 2
    assert processor.statistics.rejected_events == 2
    assert processor.statistics.duplicate_events == 1
    assert processor.statistics.ledger_entries_created == 1


def test_mixed_payments_keep_independent_ordering_and_ledger_history() -> None:
    processor = OrderedEventProcessor(ordering_ledger())
    mixed = (
        payment_events("PAY-A", 10_000, (3, 1, 2, 4))[0],
        payment_events("PAY-B", 5_000, (1, 2, 3, 4))[0],
        payment_events("PAY-A", 10_000, (3, 1, 2, 4))[1],
        *payment_events("PAY-B", 5_000, (1, 2, 3, 4))[1:],
        *payment_events("PAY-A", 10_000, (3, 1, 2, 4))[2:],
    )
    for event in mixed:
        processor.receive(event)

    assert processor.payment_state("PAY-A") == "PaymentCompleted"
    assert processor.payment_state("PAY-B") == "PaymentCompleted"
    assert processor.statistics.ledger_entries_created == 2
    assert {entry.entry_id for entry in processor.ledger.entries[1:]} == {
        "PAY-A-SETTLEMENT",
        "PAY-B-SETTLEMENT",
    }
    assert replay(processor.ledger.entries) == 85_000


def test_same_scenario_replays_identically() -> None:
    first = process_events(out_of_order_events())
    second = process_events(out_of_order_events())

    assert first.results == second.results
    assert first.statistics == second.statistics
    assert first.ledger.entries == second.ledger.entries


@pytest.mark.parametrize("wrapper", [EventSequence, EventRevision])
@pytest.mark.parametrize("value", [0, -1, True])
def test_order_values_must_be_positive_integers(wrapper: type, value: int) -> None:
    with pytest.raises(ValueError):
        wrapper(value)


def test_event_type_must_match_sequence() -> None:
    with pytest.raises(ValueError):
        replace(payment_events()[0], event_type=PaymentEventType.COMPLETED)
