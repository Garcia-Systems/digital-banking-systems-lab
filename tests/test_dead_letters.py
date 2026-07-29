"""Focused tests for Chapter 17 deterministic dead-letter isolation."""

import pytest

from bank_sim.cli import main
from bank_sim.dead_letters import (
    DeadLetterEntry,
    DeadLetterProcessor,
    DeadLetterQueue,
    DeadLetterReason,
    WorkflowState,
    run_dead_letter_scenario,
)
from bank_sim.ledger import replay
from bank_sim.payment_queues import PaymentQueue
from bank_sim.scheduler import EventScheduler


def test_successful_processing_leaves_dlq_empty() -> None:
    scheduler = EventScheduler()
    queue = PaymentQueue(scheduler)
    dead_letters = DeadLetterQueue()
    processor = DeadLetterProcessor(scheduler, queue, dead_letters)
    effects: list[str] = []

    payment = processor.submit("PAY-1", "REQ-1", lambda: effects.append("posted"))
    scheduler.run()

    assert payment.completed
    assert effects == ["posted"]
    assert dead_letters.entries == ()


def test_retry_exhaustion_is_inserted_once_and_never_retries_again() -> None:
    scheduler = EventScheduler()
    queue = PaymentQueue(scheduler)
    dead_letters = DeadLetterQueue()
    processor = DeadLetterProcessor(scheduler, queue, dead_letters, maximum_retries=2)
    effects: list[str] = []
    payment = processor.submit(
        "PAY-1",
        "REQ-1",
        lambda: effects.append("posted"),
        transient_failures=("down",) * 9,
    )

    scheduler.run()
    attempts_after_isolation = payment.attempts
    scheduler.run()

    assert payment.isolated
    assert payment.retry_count == 2
    assert attempts_after_isolation == payment.attempts == 3
    assert effects == []
    assert dead_letters.entries[0].reason is DeadLetterReason.RETRY_LIMIT_EXCEEDED
    assert processor.statistics.active_queue_size == 0


def test_permanent_failure_preserves_inspection_context() -> None:
    scheduler = EventScheduler()
    dead_letters = DeadLetterQueue()
    processor = DeadLetterProcessor(scheduler, PaymentQueue(scheduler), dead_letters)
    processor.submit(
        "PAY-BAD",
        "REQ-BAD",
        lambda: None,
        permanent_reason=DeadLetterReason.INVALID_PAYMENT,
        original_state=WorkflowState.RECEIVED,
        diagnostic_message="amount failed validation",
    )
    scheduler.run()

    assert dead_letters.entries == (
        DeadLetterEntry(
            "PAY-BAD",
            "REQ-BAD",
            DeadLetterReason.INVALID_PAYMENT,
            0,
            1,
            WorkflowState.RECEIVED,
            "amount failed validation",
        ),
    )


def test_mixed_workload_is_ordered_and_financially_correct() -> None:
    scenario = run_dead_letter_scenario()

    assert [entry.payment_id for entry in scenario.dead_letters.entries] == [
        "PAY-INVALID-WORKFLOW",
        "PAY-STALE-EVENT",
        "PAY-EXHAUSTED",
    ]
    assert [entry.entry_id for entry in scenario.ledger.entries] == [
        "OPEN",
        "PAY-SUCCESS-001",
        "PAY-SUCCESS-002",
    ]
    assert replay(scenario.ledger.entries) == 85_000

    stats = scenario.processor.statistics
    assert stats.items_processed == 5
    assert stats.successful_payments == 2
    assert stats.retry_attempts == 2
    assert stats.dlq_entries == stats.dlq_size == 3
    assert stats.active_queue_size == 0
    assert stats.dlq_reasons == (
        (DeadLetterReason.RETRY_LIMIT_EXCEEDED, 1),
        (DeadLetterReason.INVALID_WORKFLOW_STATE, 1),
        (DeadLetterReason.STALE_EVENT, 1),
    )


def test_dlq_rejects_duplicate_isolation_without_mutating_history() -> None:
    queue = DeadLetterQueue()
    entry = DeadLetterEntry(
        "PAY-1",
        "REQ-1",
        DeadLetterReason.STALE_EVENT,
        0,
        1,
        WorkflowState.COMPLETED,
        "old revision",
    )

    assert queue.isolate(entry)
    assert not queue.isolate(entry)
    assert queue.entries == (entry,)


@pytest.mark.parametrize("command", ["dead-letter", "dead-letter-report"])
def test_dead_letter_cli_output_is_deterministic(
    command: str, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main([command]) == 0
    first = capsys.readouterr().out
    assert "PAY-EXHAUSTED" in first
    assert main([command]) == 0
    assert capsys.readouterr().out == first
