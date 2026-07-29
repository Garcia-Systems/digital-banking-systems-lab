"""Tests for withdrawal decisions made before ledger appends."""

import pytest

from bank_sim.ledger import EntryType, Ledger, LedgerEntry, Money, replay
from bank_sim.withdrawals import (
    INSUFFICIENT_FUNDS_REASON,
    WithdrawalRequest,
    WithdrawalStatus,
    WithdrawalValidationError,
    process_withdrawal,
)


def funded_ledger(amount: int = 50_000) -> Ledger:
    ledger = Ledger()
    ledger.append(
        LedgerEntry("OPEN", "ACCOUNT-1", Money(amount), EntryType.CREDIT, "Open", 1, 1)
    )
    return ledger


def request(identifier: str = "WDR-1", amount: int = 12_000) -> WithdrawalRequest:
    return WithdrawalRequest(identifier, "ACCOUNT-1", amount, "Withdrawal")


def test_successful_withdrawal_appends_debit_and_replays_balance() -> None:
    ledger = funded_ledger()
    result = process_withdrawal(ledger, request())

    assert result.status is WithdrawalStatus.POSTED
    assert result.rejection_reason is None
    assert ledger.entries[-1].entry_type is EntryType.DEBIT
    assert ledger.entries[-1].amount.cents == 12_000
    assert replay(ledger.entries) == 38_000


def test_insufficient_funds_rejection_does_not_change_ledger_or_replay() -> None:
    ledger = funded_ledger(10_000)
    entries_before = ledger.entries

    result = process_withdrawal(ledger, request(amount=15_000))

    assert result.status is WithdrawalStatus.REJECTED
    assert result.rejection_reason == INSUFFICIENT_FUNDS_REASON
    assert ledger.entries == entries_before
    assert replay(ledger.entries) == 10_000


def test_multiple_withdrawals_replay_exact_integer_cents_in_order() -> None:
    ledger = funded_ledger()
    for identifier, amount in (
        ("WDR-1", 5_000),
        ("WDR-2", 7_525),
        ("WDR-3", 2_000),
    ):
        assert process_withdrawal(ledger, request(identifier, amount)).status is (
            WithdrawalStatus.POSTED
        )

    assert replay(ledger.entries) == 35_475
    assert [entry.sequence for entry in ledger.entries] == [1, 2, 3, 4]
    assert [entry.entry_id for entry in ledger.entries[1:]] == [
        "WDR-1-ENTRY",
        "WDR-2-ENTRY",
        "WDR-3-ENTRY",
    ]


@pytest.mark.parametrize("amount", [0, -1])
def test_nonpositive_amount_is_rejected_before_ledger_interaction(amount: int) -> None:
    ledger = funded_ledger()
    entries_before = ledger.entries
    with pytest.raises(
        WithdrawalValidationError, match="withdrawal amount must be greater than zero"
    ):
        process_withdrawal(ledger, request(amount=amount))
    assert ledger.entries == entries_before


@pytest.mark.parametrize(
    ("withdrawal_id", "account_id", "message"),
    [
        ("", "ACCOUNT-1", "withdrawal identifier cannot be blank"),
        ("WDR-1", "  ", "account identifier cannot be blank"),
    ],
)
def test_blank_identifiers_are_rejected(
    withdrawal_id: str, account_id: str, message: str
) -> None:
    with pytest.raises(WithdrawalValidationError, match=message):
        WithdrawalRequest(withdrawal_id, account_id, 100, "Withdrawal")


def test_request_for_exact_available_balance_is_approved() -> None:
    ledger = funded_ledger(12_345)
    assert process_withdrawal(ledger, request(amount=12_345)).status is (
        WithdrawalStatus.POSTED
    )
    assert replay(ledger.entries) == 0
