"""Tests for deposits as ledger-appending business operations."""

import pytest

from bank_sim.deposits import (
    DepositRequest,
    DepositStatus,
    DepositValidationError,
    post_deposit,
)
from bank_sim.ledger import EntryType, Ledger, replay


def request(deposit_id: str = "DEP-1", amount: int = 50_000) -> DepositRequest:
    return DepositRequest(deposit_id, "ACCOUNT-1", amount, "Cash deposit")


def test_successful_deposit_appends_credit_without_storing_a_balance() -> None:
    ledger = Ledger()
    deposit = post_deposit(ledger, request())

    assert deposit.status is DepositStatus.POSTED
    assert len(ledger.entries) == 1
    assert ledger.entries[0].entry_type is EntryType.CREDIT
    assert ledger.entries[0].amount.cents == 50_000
    assert replay(ledger.entries) == 50_000
    assert not hasattr(deposit, "balance")


def test_multiple_deposits_replay_exact_integer_cents_in_order() -> None:
    ledger = Ledger()
    running = []
    for identifier, amount in (("DEP-1", 50_000), ("DEP-2", 25_000), ("DEP-3", 7_550)):
        post_deposit(ledger, request(identifier, amount))
        running.append(replay(ledger.entries))

    assert running == [50_000, 75_000, 82_550]
    assert [entry.sequence for entry in ledger.entries] == [1, 2, 3]
    assert [entry.entry_id for entry in ledger.entries] == [
        "DEP-1-ENTRY",
        "DEP-2-ENTRY",
        "DEP-3-ENTRY",
    ]


@pytest.mark.parametrize(
    ("deposit_id", "account_id", "message"),
    [
        ("", "ACCOUNT-1", "deposit identifier cannot be blank"),
        ("DEP-1", "  ", "account identifier cannot be blank"),
    ],
)
def test_blank_identifiers_are_rejected(
    deposit_id: str, account_id: str, message: str
) -> None:
    with pytest.raises(DepositValidationError, match=message):
        DepositRequest(deposit_id, account_id, 100, "Deposit")


@pytest.mark.parametrize("amount", [0, -1])
def test_nonpositive_amount_is_rejected_without_a_ledger_entry(amount: int) -> None:
    ledger = Ledger()
    with pytest.raises(
        DepositValidationError, match="deposit amount must be greater than zero"
    ):
        post_deposit(ledger, request(amount=amount))
    assert ledger.entries == ()
