"""Integration tests for Chapter 18's complete operational workflow."""

import pytest

from bank_sim.cli import main
from bank_sim.dead_letters import DeadLetterReason
from bank_sim.laboratory import (
    describe_laboratory,
    describe_operational_summary,
    run_laboratory,
)
from bank_sim.ledger import replay


def test_complete_deterministic_workflow_and_mixed_workload() -> None:
    first = run_laboratory()
    second = run_laboratory()

    assert first.statistics == second.statistics
    assert first.outcomes == second.outcomes
    assert first.ledger.entries == second.ledger.entries
    assert [outcome.outcome for outcome in first.outcomes] == [
        "Completed",
        "Completed",
        "Completed",
        "Completed",
        "Dead letter",
        "Completed",
    ]


def test_retry_and_dead_letter_integration() -> None:
    result = run_laboratory()

    assert result.statistics.retries == 4
    assert result.dead_letters.entries[0].payment_id == "PAY-E"
    assert (
        result.dead_letters.entries[0].reason is DeadLetterReason.RETRY_LIMIT_EXCEEDED
    )
    assert result.dead_letters.entries[0].retry_count == 2


def test_idempotency_integration_has_exactly_one_effect_per_business_request() -> None:
    result = run_laboratory()

    assert result.idempotency.statistics.duplicate_deliveries == 2
    assert result.idempotency.statistics.duplicate_requests_prevented == 2
    assert [entry.entry_id for entry in result.ledger.entries].count("PAY-C-DEBIT") == 1
    assert [entry.entry_id for entry in result.ledger.entries].count("PAY-F-DEBIT") == 1


def test_ordering_validation_integration_is_safe() -> None:
    result = run_laboratory()

    assert result.ordering.statistics.out_of_order_events == 2
    assert result.ordering.statistics.stale_events == 1
    assert result.ordering.statistics.duplicate_events == 1
    assert result.ordering.payment_state("PAY-D") == "PaymentCompleted"
    assert [entry.entry_id for entry in result.ledger.entries].count(
        "PAY-D-SETTLEMENT"
    ) == 1


def test_settlement_reconciliation_and_financial_correctness() -> None:
    result = run_laboratory()

    assert [record.payment_id for record in result.settlements] == [
        "PAY-A",
        "PAY-B",
        "PAY-C",
        "PAY-D",
        "PAY-F",
    ]
    assert result.reconciliation.matched_count == 5
    assert result.reconciliation.exception_count == 0
    assert result.statistics.ledger_effects == 5
    assert (
        result.statistics.final_balance_cents == replay(result.ledger.entries) == 85_000
    )


def test_deterministic_statistics_are_exact() -> None:
    stats = run_laboratory().statistics

    assert (
        stats.payments_received,
        stats.successful_payments,
        stats.retries,
        stats.duplicate_deliveries,
        stats.duplicate_requests_prevented,
        stats.out_of_order_events_detected,
        stats.stale_events,
        stats.dead_letter_entries,
        stats.settlement_records,
        stats.reconciled_records,
        stats.reconciliation_exceptions,
        stats.elapsed_time,
        stats.throughput_hundredths,
    ) == (6, 5, 4, 2, 2, 2, 1, 1, 5, 5, 0, 12, 41)


@pytest.mark.parametrize(
    ("command", "heading"),
    [
        ("laboratory", "End-to-End Banking Operations Laboratory"),
        ("operational-summary", "Operational Summary"),
    ],
)
def test_cli_output_is_deterministic(
    command: str, heading: str, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main([command]) == 0
    first = capsys.readouterr().out
    assert heading in first
    assert main([command]) == 0
    assert capsys.readouterr().out == first


def test_renderers_are_stable_and_cover_final_isolation() -> None:
    assert describe_laboratory() == describe_laboratory()
    assert "PAY-E | RETRY_LIMIT_EXCEEDED" in describe_laboratory()
    assert describe_operational_summary() == describe_operational_summary()
    assert "final balance $850.00" in describe_operational_summary()
