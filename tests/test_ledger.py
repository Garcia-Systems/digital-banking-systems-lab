"""Tests for immutable ledger history and its one projection."""

from dataclasses import FrozenInstanceError

import pytest

from bank_sim.ledger import (
    EntryType,
    Ledger,
    LedgerEntry,
    LedgerValidationError,
    Money,
    replay,
)


def entry(sequence: int, cents: int, kind: EntryType = EntryType.CREDIT) -> LedgerEntry:
    return LedgerEntry(
        f"LE-{sequence}",
        "ACCOUNT-1",
        Money(cents),
        kind,
        "Test fact",
        sequence,
        sequence * 10,
    )


def test_money_and_entries_are_immutable() -> None:
    amount = Money(101)
    fact = entry(1, 101)
    with pytest.raises(FrozenInstanceError):
        amount.cents = 102  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        fact.description = "Changed"  # type: ignore[misc]


def test_ledger_is_append_only_and_returns_an_immutable_snapshot() -> None:
    ledger = Ledger()
    ledger.append(entry(1, 100))
    snapshot = ledger.entries
    assert isinstance(snapshot, tuple)
    assert not hasattr(ledger, "delete")
    assert not hasattr(ledger, "update")
    ledger.append(entry(2, 50))
    assert len(snapshot) == 1
    assert len(ledger.entries) == 2


def test_append_enforces_deterministic_order() -> None:
    ledger = Ledger()
    with pytest.raises(LedgerValidationError, match="sequence must be 1"):
        ledger.append(entry(2, 100))
    ledger.append(entry(1, 100))
    with pytest.raises(
        LedgerValidationError, match="posting time cannot move backward"
    ):
        ledger.append(LedgerEntry("LE-2", "A", Money(1), EntryType.CREDIT, "x", 2, 1))


@pytest.mark.parametrize(
    ("entries", "expected"),
    [
        ([], 0),
        ([entry(1, 100), entry(2, 225)], 325),
        ([entry(1, 100, EntryType.DEBIT)], -100),
        ([entry(1, 1000), entry(2, 125, EntryType.DEBIT), entry(3, 5)], 880),
    ],
)
def test_replay_projects_expected_current_balance(
    entries: list[LedgerEntry], expected: int
) -> None:
    assert replay(entries) == expected
    assert replay(entries) == expected


def test_integer_cent_precision_is_exact() -> None:
    entries = [entry(i, 1) for i in range(1, 101)]
    assert replay(entries) == 100


@pytest.mark.parametrize(
    "factory, message",
    [
        (lambda: Money(0), "greater than zero"),
        (lambda: Money(1.5), "integer cents"),
        (lambda: entry(0, 1), "sequence must be greater"),
        (
            lambda: LedgerEntry("", "A", Money(1), EntryType.CREDIT, "x", 1, 0),
            "entry id",
        ),
        (
            lambda: LedgerEntry("1", "", Money(1), EntryType.CREDIT, "x", 1, 0),
            "account id",
        ),
        (
            lambda: LedgerEntry("1", "A", Money(1), EntryType.CREDIT, "", 1, 0),
            "description",
        ),
        (
            lambda: LedgerEntry("1", "A", Money(1), EntryType.CREDIT, "x", 1, -1),
            "cannot be negative",
        ),
    ],
)
def test_invalid_entries_are_rejected(factory: object, message: str) -> None:
    with pytest.raises(LedgerValidationError, match=message):
        factory()  # type: ignore[operator]


def test_duplicate_identifier_is_rejected() -> None:
    ledger = Ledger()
    ledger.append(entry(1, 10))
    duplicate = LedgerEntry("LE-1", "A", Money(10), EntryType.CREDIT, "x", 2, 20)
    with pytest.raises(LedgerValidationError, match="unique"):
        ledger.append(duplicate)


def test_replay_rejects_out_of_order_history_without_mutating_it() -> None:
    entries = [entry(2, 10)]
    before = list(entries)
    with pytest.raises(LedgerValidationError, match="contiguous sequence"):
        replay(entries)
    assert entries == before
