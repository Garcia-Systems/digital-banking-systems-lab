"""Tests for Chapter 14's intentionally naïve duplicate processing."""

import pytest

from bank_sim.cli import main
from bank_sim.duplicates import (
    client_retry_scenario,
    duplicate_scenarios,
    network_duplicate_scenario,
    no_duplicates_scenario,
    process_naively,
    queue_replay_scenario,
)
from bank_sim.ledger import replay


def test_unique_request_delivery_has_one_financial_effect() -> None:
    observation = process_naively(no_duplicates_scenario())

    assert observation.statistics.deliveries_received == 1
    assert observation.statistics.duplicate_deliveries == 0
    assert observation.statistics.duplicate_financial_operations == 0
    assert replay(observation.ledger.entries) == 75_000


def test_duplicate_delivery_is_processed_twice_in_naive_demonstration() -> None:
    observation = process_naively(client_retry_scenario())

    assert [item.delivery.original_request_id for item in observation.attempts] == [
        "PAY-001",
        "PAY-001",
    ]
    assert len(observation.ledger.entries) == 3
    assert replay(observation.ledger.entries) == 50_000


def test_multiple_duplicate_deliveries_each_create_a_financial_effect() -> None:
    observation = process_naively(network_duplicate_scenario())

    assert observation.statistics.duplicate_deliveries == 2
    assert observation.statistics.financial_operations_performed == 3
    assert observation.statistics.duplicate_financial_operations == 2
    assert replay(observation.ledger.entries) == 25_000


def test_mixed_workload_statistics_are_exact_integer_measurements() -> None:
    stats = process_naively(queue_replay_scenario()).statistics

    assert stats.deliveries_received == 4
    assert stats.unique_payment_identifiers == 3
    assert stats.duplicate_deliveries == 1
    assert stats.financial_operations_performed == 4
    assert stats.duplicate_financial_operations == 1
    assert stats.duplicate_percentage_hundredths == 2_500


def test_delivery_order_and_arrival_times_are_scripted_and_deterministic() -> None:
    first = duplicate_scenarios()
    second = duplicate_scenarios()

    assert first == second
    mixed = first[-1].sequence.deliveries
    assert [item.delivery_order for item in mixed] == [1, 2, 3, 4]
    assert [item.arrived_at for item in mixed] == [0, 2, 4, 6]


@pytest.mark.parametrize("command", ["duplicates", "duplicate-timeline"])
def test_duplicate_cli_output_is_deterministic(
    command: str, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main([command]) == 0
    first = capsys.readouterr().out
    assert main([command]) == 0
    assert capsys.readouterr().out == first
    assert "Chapter 15" in first


def test_duplicate_timeline_exposes_incorrect_five_hundred_dollar_balance(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["duplicate-timeline"]) == 0

    assert capsys.readouterr().out.splitlines() == [
        "Duplicate payment timeline | naïve processing",
        "Initial balance: $1,000.00",
        "T+0 Payment request received | PAY-001",
        "T+1 Payment processed | debit $250.00",
        "T+3 Duplicate request received | PAY-001",
        "T+4 Payment processed again | debit $250.00",
        "Single-delivery balance would be: $750.00",
        "Naïve duplicate-delivery balance: $500.00",
        "INCORRECT: the customer intended one payment, but two financial effects "
        "occurred.",
        "Chapter 15 will eliminate the second financial effect with idempotent "
        "processing.",
    ]
