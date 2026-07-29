"""Tests for the deterministic outbound ACH workflow."""

import pytest

from bank_sim.ach import (
    AchNetwork,
    AchTransferRequest,
    AchTransferStatus,
    AchValidationError,
)
from bank_sim.ledger import EntryType, Ledger, LedgerEntry, Money
from bank_sim.transfers import account_balance


def funded_network(cents: int = 100_000) -> AchNetwork:
    ledger = Ledger()
    ledger.append(
        LedgerEntry(
            "OPEN",
            "ACCOUNT-001",
            Money(cents),
            EntryType.CREDIT,
            "Opening balance",
            1,
            0,
        )
    )
    return AchNetwork(ledger)


def request(**changes: object) -> AchTransferRequest:
    values = {
        "transfer_id": "ACH-TEST-001",
        "source_account_id": "ACCOUNT-001",
        "destination_institution": "Blue Ridge National Bank",
        "destination_reference": "EXTERNAL-ACCOUNT-001",
        "amount_cents": 25_000,
        "description": "External transfer",
    }
    values.update(changes)
    return AchTransferRequest(**values)  # type: ignore[arg-type]


def test_valid_outbound_request_progresses_and_posts_once() -> None:
    network = funded_network()
    transfer = network.receive(request())
    network.scheduler.run()

    assert [event.status for event in transfer.history[:6]] == list(AchTransferStatus)[
        :6
    ]
    assert transfer.status is AchTransferStatus.COMPLETED
    assert network.submissions == ["ACH-TEST-001"]
    assert network.pending == []
    assert account_balance(network.ledger, "ACCOUNT-001") == 75_000
    assert len(network.ledger.entries) == 2


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"transfer_id": " "}, "transfer identifier cannot be blank"),
        ({"source_account_id": ""}, "source account identifier cannot be blank"),
        ({"destination_institution": ""}, "destination institution cannot be blank"),
        ({"destination_reference": ""}, "destination reference cannot be blank"),
        ({"amount_cents": 0}, "transfer amount cannot be zero"),
        ({"amount_cents": -1}, "transfer amount cannot be negative"),
    ],
)
def test_invalid_request_is_rejected_without_financial_effect(
    changes: dict[str, object], reason: str
) -> None:
    network = funded_network()
    transfer = network.receive(request(**changes))
    network.scheduler.run()

    assert transfer.status is AchTransferStatus.REJECTED
    assert transfer.rejection_reason == reason
    assert network.submissions == []
    assert network.pending == []
    assert len(network.ledger.entries) == 1
    assert account_balance(network.ledger, "ACCOUNT-001") == 100_000


def test_insufficient_available_funds_rejects_without_submission() -> None:
    network = funded_network(10_000)
    transfer = network.receive(request(amount_cents=15_000))
    network.scheduler.run()
    assert transfer.status is AchTransferStatus.REJECTED
    assert transfer.rejection_reason == "Insufficient available funds"
    assert network.submissions == []
    assert len(network.ledger.entries) == 1


def test_pending_debit_changes_available_before_current() -> None:
    network = funded_network()
    transfer = network.receive(request())
    assert network.scheduler.run_next()  # validated at T+1
    assert network.scheduler.run_next()  # pending at T+2
    assert transfer.status is AchTransferStatus.PENDING
    assert account_balance(network.ledger, "ACCOUNT-001") == 100_000
    assert network.available_balance("ACCOUNT-001") == 75_000
    assert len(network.ledger.entries) == 1


def test_virtual_time_and_event_order_are_deterministic() -> None:
    network = funded_network()
    transfer = network.receive(request())
    network.scheduler.run()
    assert [event.time for event in transfer.history] == [0, 1, 2, 3, 5, 10, 10]
    assert [execution.time for execution in network.scheduler.history] == [
        1,
        2,
        3,
        5,
        10,
    ]


def test_invalid_transitions_fail_immediately() -> None:
    network = funded_network()
    transfer = network.receive(request())
    with pytest.raises(AchValidationError, match="Received to Processing"):
        network.process(transfer)
    transfer.reject(0, "test rejection")
    with pytest.raises(AchValidationError, match="Rejected to Submitted"):
        network.submit(transfer)


def test_duplicate_completion_does_not_duplicate_debit() -> None:
    network = funded_network()
    transfer = network.receive(request())
    network.scheduler.run()
    with pytest.raises(AchValidationError, match="Completed to Completed"):
        network.complete(transfer)
    assert len(network.ledger.entries) == 2
    assert account_balance(network.ledger, "ACCOUNT-001") == 75_000
