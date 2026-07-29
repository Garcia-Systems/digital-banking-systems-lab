"""Tests for Chapter 13 deterministic retry processing."""

import pytest

from bank_sim.cli import main
from bank_sim.ledger import EntryType, Ledger, LedgerEntry, Money
from bank_sim.payment_queues import PaymentQueue
from bank_sim.retries import (
    FinalOutcome,
    RetryPolicy,
    RetryScheduler,
    run_retry_scenario,
)
from bank_sim.scheduler import EventScheduler


def run_script(script: tuple[str, ...], maximum_retries: int = 3):
    scheduler = EventScheduler()
    queue = PaymentQueue(scheduler)
    retry_scheduler = RetryScheduler(
        scheduler, queue, RetryPolicy(maximum_retries=maximum_retries)
    )
    effects: list[str] = []
    payment = retry_scheduler.submit(
        "PAY-TEST", script, lambda: effects.append("posted")
    )
    scheduler.run()
    return payment, retry_scheduler, effects


@pytest.mark.parametrize(
    ("script", "attempts"),
    [((), 1), (("temporary",), 2), (("first", "second"), 3)],
)
def test_successful_scenarios_post_once(script: tuple[str, ...], attempts: int) -> None:
    payment, retries, effects = run_script(script)

    assert payment.attempts == attempts
    assert payment.final_outcome is FinalOutcome.SUCCEEDED
    assert effects == ["posted"]
    assert retries.statistics.permanent_failures == 0


def test_retry_exhaustion_respects_limit_and_has_no_financial_effect() -> None:
    payment, retries, effects = run_script(("unavailable",) * 10)

    assert payment.attempts == 4
    assert payment.final_outcome is FinalOutcome.PERMANENTLY_FAILED
    assert effects == []
    assert retries.statistics.total_retries == 3


def test_retry_schedule_is_fixed_and_reproducible() -> None:
    first = run_script(("first", "second"))[1]
    second = run_script(("first", "second"))[1]

    assert first.attempts == second.attempts
    assert [attempt.attempted_at for attempt in first.attempts] == [1, 4, 7]
    assert [attempt.scheduled_retry_time for attempt in first.attempts] == [3, 6, None]


@pytest.mark.parametrize("maximum", [-1, True])
def test_invalid_retry_limits_are_rejected(maximum: int) -> None:
    with pytest.raises(ValueError, match="maximum retries"):
        RetryPolicy(maximum_retries=maximum)


def test_mixed_workload_statistics_and_ledger_are_correct() -> None:
    scenario = run_retry_scenario()
    stats = scenario.retries.statistics

    assert stats.total_payments == 4
    assert stats.total_retries == 6
    assert stats.successful_recoveries == 2
    assert stats.permanent_failures == 1
    assert stats.average_attempts_hundredths == 250
    assert stats.maximum_attempts == 4
    assert stats.retry_queue_size == 0
    assert [entry.entry_id for entry in scenario.ledger.entries] == [
        "OPEN",
        "PAY-IMMEDIATE",
        "PAY-ONE-RETRY",
        "PAY-MULTIPLE",
    ]


def test_success_after_retries_creates_exactly_one_ledger_entry() -> None:
    scheduler = EventScheduler()
    queue = PaymentQueue(scheduler)
    retries = RetryScheduler(scheduler, queue)
    ledger = Ledger()

    def post() -> None:
        ledger.append(
            LedgerEntry("PAY-1", "A", Money(100), EntryType.DEBIT, "Payment", 1, 0)
        )

    retries.submit("PAY-1", ("timeout", "unavailable"), post)
    scheduler.run()

    assert len(ledger.entries) == 1
    assert ledger.entries[0].entry_id == "PAY-1"


@pytest.mark.parametrize("command", ["retries", "retry-timeline"])
def test_retry_cli_output_is_deterministic(
    command: str, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main([command]) == 0
    first = capsys.readouterr().out
    assert "PAY-EXHAUSTED" in first
    assert main([command]) == 0
    assert capsys.readouterr().out == first
