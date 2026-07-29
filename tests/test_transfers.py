"""Tests for coordinated internal-transfer ledger entries."""

import pytest

from bank_sim.ledger import EntryType, Ledger, LedgerEntry, LedgerValidationError, Money
from bank_sim.transfers import (
    INSUFFICIENT_FUNDS_REASON,
    TransferRequest,
    TransferStatus,
    TransferValidationError,
    account_balance,
    process_transfer,
)


def funded_ledger(source: int = 100_000, destination: int = 25_000) -> Ledger:
    ledger = Ledger()
    ledger.append_batch(
        (
            LedgerEntry(
                "OPEN-S", "SOURCE", Money(source), EntryType.CREDIT, "Open", 1, 1
            ),
            LedgerEntry(
                "OPEN-D",
                "DESTINATION",
                Money(destination),
                EntryType.CREDIT,
                "Open",
                2,
                2,
            ),
        )
    )
    return ledger


def request(identifier: str = "TRF-1", amount: int = 15_000) -> TransferRequest:
    return TransferRequest(identifier, "SOURCE", "DESTINATION", amount, "Transfer")


def test_successful_transfer_appends_pair_and_replays_both_accounts() -> None:
    ledger = funded_ledger()
    result = process_transfer(ledger, request())

    assert result.transfer.status is TransferStatus.POSTED
    assert [entry.entry_type for entry in result.ledger_entries] == [
        EntryType.DEBIT,
        EntryType.CREDIT,
    ]
    assert account_balance(ledger, "SOURCE") == 85_000
    assert account_balance(ledger, "DESTINATION") == 40_000


def test_transfer_pair_has_deterministic_identifiers_and_order() -> None:
    ledger = funded_ledger()
    result = process_transfer(ledger, request())
    assert [entry.sequence for entry in result.ledger_entries] == [3, 4]
    assert [entry.entry_id for entry in result.ledger_entries] == [
        "TRF-1-DEBIT",
        "TRF-1-CREDIT",
    ]


def test_insufficient_funds_rejects_without_entries() -> None:
    ledger = funded_ledger(source=5_000)
    before = ledger.entries
    result = process_transfer(ledger, request(amount=10_000))
    assert result.transfer.status is TransferStatus.REJECTED
    assert result.transfer.rejection_reason == INSUFFICIENT_FUNDS_REASON
    assert result.ledger_entries == ()
    assert ledger.entries == before


def test_batch_validation_is_atomic_when_second_entry_is_invalid() -> None:
    ledger = funded_ledger()
    before = ledger.entries
    entries = (
        LedgerEntry("ONE", "SOURCE", Money(100), EntryType.DEBIT, "Pair", 3, 3),
        LedgerEntry(
            "OPEN-S", "DESTINATION", Money(100), EntryType.CREDIT, "Pair", 4, 4
        ),
    )
    with pytest.raises(LedgerValidationError, match="identifier must be unique"):
        ledger.append_batch(entries)
    assert ledger.entries == before


@pytest.mark.parametrize("amount", [0, -1])
def test_nonpositive_amount_is_rejected(amount: int) -> None:
    with pytest.raises(TransferValidationError, match="greater than zero"):
        request(amount=amount)


@pytest.mark.parametrize(
    ("transfer_id", "source", "destination", "message"),
    [
        ("", "SOURCE", "DESTINATION", "transfer identifier cannot be blank"),
        ("TRF", " ", "DESTINATION", "source account identifier cannot be blank"),
        ("TRF", "SOURCE", "", "destination account identifier cannot be blank"),
    ],
)
def test_blank_identifiers_are_rejected(
    transfer_id: str, source: str, destination: str, message: str
) -> None:
    with pytest.raises(TransferValidationError, match=message):
        TransferRequest(transfer_id, source, destination, 100, "Transfer")


def test_same_account_is_rejected_before_ledger_write() -> None:
    ledger = funded_ledger()
    before = ledger.entries
    with pytest.raises(TransferValidationError, match="must be different"):
        process_transfer(
            ledger, TransferRequest("TRF", "SOURCE", "SOURCE", 100, "Transfer")
        )
    assert ledger.entries == before
