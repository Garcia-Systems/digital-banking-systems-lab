"""Tests for Chapter 12 deterministic worker capacity."""

import pytest

from bank_sim.cli import main
from bank_sim.worker_capacity import (
    CapacityConfiguration,
    run_worker_capacity,
)


def test_single_worker_builds_and_eventually_drains_backlog() -> None:
    scenario = run_worker_capacity(1)

    assert [item.completed_at for item in scenario.pool.completed] == list(
        range(2, 25, 2)
    )
    assert scenario.pool.metrics.maximum_queue_depth == 9
    assert scenario.pool.metrics.payments_processed == 12
    assert scenario.pool.worker_statistics[0].utilization_percentage == 100


def test_multiple_workers_have_reproducible_assignments() -> None:
    first = run_worker_capacity(2)
    second = run_worker_capacity(2)
    assignments = [
        (event.payment_id, event.worker_id)
        for event in first.pool.events
        if event.action == "assigned"
    ]

    assert assignments == [
        (f"PAY-{number:02}", f"worker-{1 if number % 2 else 2}")
        for number in range(1, 13)
    ]
    assert first.pool.events == second.pool.events


def test_capacity_changes_metrics_not_financial_history() -> None:
    scenarios = [run_worker_capacity(count) for count in (1, 2, 4, 8)]

    assert len({scenario.ledger_effects for scenario in scenarios}) == 1
    assert [scenario.pool.metrics.total_completion_time for scenario in scenarios] == [
        24,
        12,
        7,
        7,
    ]
    assert [scenario.pool.metrics.maximum_wait for scenario in scenarios] == [
        17,
        5,
        0,
        0,
    ]
    assert [scenario.pool.metrics.maximum_queue_depth for scenario in scenarios] == [
        9,
        6,
        2,
        1,
    ]
    assert all(scenario.pool.metrics.payments_processed == 12 for scenario in scenarios)


def test_queue_depth_throughput_and_utilization_use_integer_math() -> None:
    scenario = run_worker_capacity(2)

    assert scenario.pool.metrics.average_queue_depth_hundredths == 250
    assert scenario.pool.metrics.throughput_hundredths == 100
    assert [stats.total_busy_time for stats in scenario.pool.worker_statistics] == [
        12,
        12,
    ]
    assert [
        stats.utilization_percentage for stats in scenario.pool.worker_statistics
    ] == [100, 100]


@pytest.mark.parametrize("worker_count", [0, -1, True])
def test_invalid_worker_count_is_rejected(worker_count: int) -> None:
    with pytest.raises(ValueError, match="worker count"):
        CapacityConfiguration(worker_count)


def test_worker_capacity_cli_is_deterministic(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["worker-capacity", "--workers", "2"]) == 0
    output = capsys.readouterr().out
    assert "Worker capacity | 2 worker(s)" in output
    assert "T+00 Assigned  PAY-01 -> worker-1" in output
    assert "worker-1: completed 6 | busy 12 | utilization 100%" in output
    assert main(["worker-capacity", "--workers", "2"]) == 0
    assert capsys.readouterr().out == output


def test_capacity_comparison_cli_is_deterministic(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["capacity-comparison"]) == 0
    output = capsys.readouterr().out
    assert output.count("processed 12") == 3
    assert "1 worker(s): completion T+24" in output
    assert "4 worker(s): completion T+7" in output
    assert "Identical ledger history: yes" in output
    assert main(["capacity-comparison"]) == 0
    assert capsys.readouterr().out == output
