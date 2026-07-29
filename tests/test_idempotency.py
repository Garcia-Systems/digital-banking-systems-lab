import pytest

from bank_sim.duplicates import delivery
from bank_sim.idempotency import (
    CompletionStatus,
    IdempotencyConflictError,
    IdempotencyKey,
    IdempotentPaymentProcessor,
    idempotency_key_for,
    idempotency_scenarios,
    process_idempotently,
)
from bank_sim.ledger import EntryType, Ledger, LedgerEntry, Money, replay
from bank_sim.payment_queues import PaymentQueue
from bank_sim.retries import FinalOutcome, RetryScheduler
from bank_sim.scheduler import EventScheduler


def test_unique_request_creates_one_record_debit_and_balance_change() -> None:
    observation = process_idempotently(idempotency_scenarios()[0])

    assert len(observation.ledger.entries) == 2
    assert observation.ledger.entries[-1].entry_type is EntryType.DEBIT
    assert replay(observation.ledger.entries) == 75_000
    record = observation.processor.store.records[0]
    assert record.key == IdempotencyKey("IDEMPOTENCY-PAY-001")
    assert record.original_request_id == "PAY-001"
    assert record.first_processed_at == 1
    assert record.completion_status is CompletionStatus.COMPLETED
    assert record.result.ledger_entry_id == "PAY-001-DEBIT"
    assert record.duplicate_delivery_count == 0


@pytest.mark.parametrize(
    ("scenario_index", "deliveries", "duplicates"), ((1, 2, 1), (2, 3, 2))
)
def test_repeated_delivery_returns_original_result_without_another_effect(
    scenario_index: int, deliveries: int, duplicates: int
) -> None:
    observation = process_idempotently(idempotency_scenarios()[scenario_index])
    acknowledgements = observation.processor.acknowledgements

    assert len(acknowledgements) == deliveries
    assert acknowledgements[0].duplicate is False
    assert all(item.duplicate for item in acknowledgements[1:])
    assert all(item.result is acknowledgements[0].result for item in acknowledgements)
    assert len(observation.ledger.entries) == 2
    assert replay(observation.ledger.entries) == 75_000
    assert observation.processor.store.records[0].duplicate_delivery_count == duplicates


def test_mixed_workload_only_posts_unique_business_operations() -> None:
    observation = process_idempotently(idempotency_scenarios()[3])

    assert [entry.entry_id for entry in observation.ledger.entries[1:]] == [
        "PAY-001-DEBIT",
        "PAY-002-DEBIT",
        "PAY-003-DEBIT",
    ]
    assert replay(observation.ledger.entries) == 60_000
    assert observation.processor.statistics.unique_business_operations == 3


def test_statistics_separate_deliveries_from_financial_effects() -> None:
    stats = process_idempotently(idempotency_scenarios()[2]).processor.statistics

    assert stats.total_requests_received == 3
    assert stats.unique_business_operations == 1
    assert stats.duplicate_deliveries == 2
    assert stats.duplicate_requests_prevented == 2
    assert stats.stored_idempotency_records == 1
    assert stats.ledger_entries_created == 1


def test_key_reuse_for_different_payment_is_rejected_before_ledger_effect() -> None:
    ledger = Ledger()
    processor = IdempotentPaymentProcessor(ledger)
    key = IdempotencyKey("CUSTOMER-CHECKOUT-1")
    processor.process(delivery("PAY-A", 100, 1, 0, 1), key)

    with pytest.raises(IdempotencyConflictError):
        processor.process(delivery("PAY-B", 200, 1, 1, 2), key)

    assert len(ledger.entries) == 1


def test_retry_success_then_repeated_delivery_reuses_result() -> None:
    scheduler = EventScheduler()
    retries = RetryScheduler(scheduler, PaymentQueue(scheduler))
    ledger = Ledger()
    ledger.append(
        LedgerEntry(
            "OPEN", "HCCU-DEMO-001", Money(1_000), EntryType.CREDIT, "Open", 1, 0
        )
    )
    processor = IdempotentPaymentProcessor(ledger)
    request = delivery("PAY-RETRY", 250, 1, 0, 1)
    key = idempotency_key_for(request)

    retries.submit(
        "PAY-RETRY", ("processor unavailable",), lambda: processor.process(request, key)
    )
    scheduler.run()
    duplicate = processor.process(delivery("PAY-RETRY", 250, 2, 3, 2), key)

    assert retries.payments[0].final_outcome is FinalOutcome.SUCCEEDED
    assert retries.payments[0].attempts == 2
    assert duplicate.duplicate is True
    assert processor.statistics.ledger_entries_created == 1
    assert replay(ledger.entries) == 750


@pytest.mark.parametrize("value", ["", "   "])
def test_idempotency_key_must_not_be_blank(value: str) -> None:
    with pytest.raises(ValueError):
        IdempotencyKey(value)
