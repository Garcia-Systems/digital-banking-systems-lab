"""Tests for deterministic current, pending, and available projections."""

from dataclasses import FrozenInstanceError

import pytest

from bank_sim.balances import (
    BalanceValidationError,
    PendingTransaction,
    PendingTransactionType,
    chapter_pending_transactions,
    describe_pending,
    project_balances,
)
from bank_sim.ledger import EntryType, Ledger, LedgerEntry, Money, replay


def ledger_with(*amounts: tuple[int, EntryType]) -> Ledger:
    ledger = Ledger()
    for sequence, (cents, entry_type) in enumerate(amounts, start=1):
        ledger.append(
            LedgerEntry(
                f"LE-{sequence}",
                "ACCOUNT-1",
                Money(cents),
                entry_type,
                "Test fact",
                sequence,
                sequence,
            )
        )
    return ledger


def pending(
    sequence: int, cents: int, kind: PendingTransactionType
) -> PendingTransaction:
    return PendingTransaction(
        f"PT-{sequence}", Money(cents), kind, f"Pending {sequence}", sequence
    )


def test_current_balance_is_derived_by_replaying_ledger() -> None:
    ledger = ledger_with((10_000, EntryType.CREDIT), (1_501, EntryType.DEBIT))
    projection = project_balances(ledger, [])
    assert projection.current_balance == replay(ledger.entries) == 8_499


def test_pending_debit_reduces_only_available_balance() -> None:
    projection = project_balances(
        ledger_with((10_000, EntryType.CREDIT)),
        [pending(1, 2_345, PendingTransactionType.PENDING_DEBIT)],
    )
    assert projection.pending_debits == 2_345
    assert projection.current_balance == 10_000
    assert projection.available_balance == 7_655


def test_pending_credit_increases_only_available_balance() -> None:
    projection = project_balances(
        ledger_with((10_000, EntryType.CREDIT)),
        [pending(1, 125, PendingTransactionType.PENDING_CREDIT)],
    )
    assert projection.pending_credits == 125
    assert projection.current_balance == 10_000
    assert projection.available_balance == 10_125


def test_multiple_pending_transactions_are_combined_in_integer_cents() -> None:
    transactions = [
        pending(1, 1, PendingTransactionType.PENDING_DEBIT),
        pending(2, 2, PendingTransactionType.PENDING_DEBIT),
        pending(3, 4, PendingTransactionType.PENDING_CREDIT),
    ]
    projection = project_balances(ledger_with((101, EntryType.CREDIT)), transactions)
    assert projection.pending_debits == 3
    assert projection.pending_credits == 4
    assert projection.available_balance == 102


def test_empty_pending_queue_leaves_available_equal_to_current() -> None:
    projection = project_balances(ledger_with((500, EntryType.CREDIT)), ())
    assert projection.pending_debits == projection.pending_credits == 0
    assert projection.available_balance == projection.current_balance == 500


def test_pending_activity_never_changes_ledger_or_replay() -> None:
    ledger = ledger_with((500, EntryType.CREDIT))
    before = ledger.entries
    before_balance = replay(before)
    project_balances(ledger, [pending(1, 200, PendingTransactionType.PENDING_DEBIT)])
    assert ledger.entries == before
    assert replay(ledger.entries) == before_balance


def test_pending_transactions_and_projection_are_immutable() -> None:
    transaction = pending(1, 100, PendingTransactionType.PENDING_DEBIT)
    projection = project_balances(ledger_with((500, EntryType.CREDIT)), [transaction])
    with pytest.raises(FrozenInstanceError):
        transaction.description = "Changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        projection.available_balance = 0  # type: ignore[misc]


def test_pending_display_preserves_deterministic_sequence() -> None:
    transactions = chapter_pending_transactions()
    assert [item.sequence for item in transactions] == [1, 2, 3]
    assert describe_pending(transactions) == describe_pending(transactions)
    assert describe_pending(transactions).splitlines() == [
        "Pending Debit",
        "Gas Station",
        "$60.00",
        "",
        "Pending Debit",
        "Restaurant",
        "$60.00",
        "",
        "Pending Credit",
        "Payroll",
        "$25.00",
    ]


def test_out_of_order_or_duplicate_pending_activity_is_rejected() -> None:
    ledger = ledger_with((100, EntryType.CREDIT))
    with pytest.raises(BalanceValidationError, match="contiguous sequence"):
        project_balances(ledger, [pending(2, 1, PendingTransactionType.PENDING_DEBIT)])
    duplicate = pending(1, 1, PendingTransactionType.PENDING_DEBIT)
    second = PendingTransaction(
        duplicate.transaction_id,
        Money(1),
        PendingTransactionType.PENDING_CREDIT,
        "Duplicate",
        2,
    )
    with pytest.raises(BalanceValidationError, match="unique"):
        project_balances(ledger, [duplicate, second])
