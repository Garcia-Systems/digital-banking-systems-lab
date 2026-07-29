"""Tests for append-only ACH return correction."""

import pytest

from bank_sim.ach import AchNetwork, AchTransferRequest
from bank_sim.ach_returns import (
    AchReturnProcessor,
    AchReturnReason,
    AchReturnRequest,
    AchReturnStatus,
    AchReturnValidationError,
)
from bank_sim.ledger import EntryType, Ledger, LedgerEntry, Money
from bank_sim.transfers import account_balance


def setup_network(*, complete: bool = True) -> tuple[AchNetwork, object]:
    ledger = Ledger()
    ledger.append(
        LedgerEntry("OPEN", "A", Money(100_000), EntryType.CREDIT, "Open", 1, 0)
    )
    network = AchNetwork(ledger)
    transfer = network.receive(
        AchTransferRequest("ACH-1", "A", "Fictional Bank", "REF-1", 25_000, "ACH")
    )
    if complete:
        network.scheduler.run()
        network.scheduler.clock.advance_to(30)
    return network, transfer


def return_request(**changes: object) -> AchReturnRequest:
    values = {
        "return_id": "RET-1",
        "original_transfer_id": "ACH-1",
        "reason": AchReturnReason.ACCOUNT_CLOSED,
        "amount_cents": 25_000,
    }
    values.update(changes)
    return AchReturnRequest(**values)  # type: ignore[arg-type]


def test_valid_return_appends_correction_and_preserves_original_debit() -> None:
    network, _ = setup_network()
    original_debit = network.ledger.entries[1]
    processor = AchReturnProcessor(network)
    item = processor.receive(return_request())
    network.scheduler.run()

    assert item.status is AchReturnStatus.COMPLETED
    assert item.completed_at == 35
    assert item.corrective_entry_id == "RET-1-CREDIT"
    assert network.ledger.entries[1] is original_debit
    assert network.ledger.entries[1].entry_type is EntryType.DEBIT
    correction = network.ledger.entries[2]
    assert correction.entry_type is EntryType.CREDIT
    assert correction.amount.cents == 25_000
    assert correction.original_transfer_id == "ACH-1"
    assert correction.ach_return_id == "RET-1"
    assert account_balance(network.ledger, "A") == 100_000
    assert [event.time for event in item.history] == [30, 31, 32, 35, 35]


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"return_id": " "}, "return identifier cannot be blank"),
        ({"original_transfer_id": ""}, "original transfer identifier cannot be blank"),
        ({"original_transfer_id": "MISSING"}, "original ACH transfer does not exist"),
        ({"amount_cents": 24_999}, "return amount must match original transfer amount"),
    ],
)
def test_invalid_return_is_rejected_without_ledger_effect(
    changes: dict[str, object], reason: str
) -> None:
    network, _ = setup_network()
    processor = AchReturnProcessor(network)
    item = processor.receive(return_request(**changes))
    network.scheduler.run()
    assert item.status is AchReturnStatus.REJECTED
    assert item.rejection_reason == reason
    assert len(network.ledger.entries) == 2
    assert account_balance(network.ledger, "A") == 75_000


def test_premature_return_is_rejected_and_pending_state_is_preserved() -> None:
    network, transfer = setup_network(complete=False)
    processor = AchReturnProcessor(network)
    item = processor.receive(return_request())
    # Return validation and transfer validation share T+1; insertion order is stable.
    assert network.scheduler.run_next()
    assert network.scheduler.run_next()
    assert item.status is AchReturnStatus.REJECTED
    assert item.rejection_reason == "original ACH transfer is not completed"
    assert transfer.status.value == "Validated"
    assert len(network.ledger.entries) == 1


def test_duplicate_request_and_completion_do_not_duplicate_credit() -> None:
    network, _ = setup_network()
    processor = AchReturnProcessor(network)
    first = processor.receive(return_request())
    assert processor.receive(return_request()) is first
    network.scheduler.run()
    with pytest.raises(AchReturnValidationError, match="Completed to Completed"):
        processor.complete(first)
    assert len(network.ledger.entries) == 3
    assert account_balance(network.ledger, "A") == 100_000


def test_second_return_for_transfer_is_rejected() -> None:
    network, _ = setup_network()
    processor = AchReturnProcessor(network)
    first = processor.receive(return_request())
    network.scheduler.run()
    second = processor.receive(return_request(return_id="RET-2"))
    network.scheduler.run()
    assert first.status is AchReturnStatus.COMPLETED
    assert second.status is AchReturnStatus.REJECTED
    assert second.rejection_reason == "original ACH transfer already has a return"
    assert len(network.ledger.entries) == 3


def test_invalid_return_transitions_fail_immediately() -> None:
    network, _ = setup_network()
    processor = AchReturnProcessor(network)
    item = processor.receive(return_request())
    with pytest.raises(AchReturnValidationError, match="Received to Processing"):
        processor.process(item)
    item.reject(30, "invalid")
    with pytest.raises(AchReturnValidationError, match="Rejected to Completed"):
        processor.complete(item)
