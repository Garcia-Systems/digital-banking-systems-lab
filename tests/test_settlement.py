"""Settlement expectations and independent reconciliation."""

from dataclasses import FrozenInstanceError

import pytest

from bank_sim.ach import AchNetwork, AchTransferRequest
from bank_sim.ledger import EntryType, Ledger, LedgerEntry, Money
from bank_sim.settlement import (
    ExternalSettlementRecord,
    ExternalSettlementReport,
    ReconciliationStatus,
    SettlementDirection,
    SettlementRecord,
    chapter_settlement_records,
    reconcile,
    settlement_expectations,
)


def record(
    payment_id: str,
    amount: int = 10_000,
    direction: SettlementDirection = SettlementDirection.OUTBOUND,
) -> SettlementRecord:
    return SettlementRecord(f"S-{payment_id}", payment_id, amount, direction, 40)


def external(
    payment_id: str,
    amount: int = 10_000,
    direction: SettlementDirection = SettlementDirection.OUTBOUND,
    reference: str = "EXT-1",
) -> ExternalSettlementRecord:
    return ExternalSettlementRecord(reference, payment_id, amount, direction, 50)


def report(
    internal: tuple[SettlementRecord, ...], rows: tuple[ExternalSettlementRecord, ...]
):
    return reconcile(internal, ExternalSettlementReport(rows, 50), 51)


def test_completed_transfer_and_return_create_unique_expectations() -> None:
    rows = chapter_settlement_records()
    assert [(r.payment_id, r.direction, r.amount_cents) for r in rows] == [
        ("ACH-001", SettlementDirection.OUTBOUND, 25_000),
        ("RETURN-001", SettlementDirection.RETURN, 25_000),
    ]
    # Reprocessing the same workflow objects cannot duplicate an expectation.
    assert len({row.matching_key for row in rows}) == len(rows)


def test_pending_and_rejected_transfers_create_no_expectations() -> None:
    ledger = Ledger()
    ledger.append(LedgerEntry("OPEN", "A", Money(100), EntryType.CREDIT, "Open", 1, 0))
    network = AchNetwork(ledger)
    pending = network.receive(AchTransferRequest("PENDING", "A", "Bank", "Ref", 50, ""))
    rejected = network.receive(
        AchTransferRequest("REJECTED", "A", "Bank", "Ref", 0, "")
    )
    network.scheduler.run_next()  # pending validates
    network.scheduler.run_next()  # rejected rejects
    assert settlement_expectations([pending, rejected, pending], [], 40) == ()


@pytest.mark.parametrize(
    ("internal", "rows", "status"),
    [
        ((record("A"),), (external("A"),), ReconciliationStatus.MATCHED),
        ((record("A"),), (), ReconciliationStatus.MISSING_EXTERNALLY),
        ((), (external("A"),), ReconciliationStatus.UNEXPECTED_EXTERNALLY),
        ((record("A"),), (external("A", 9_900),), ReconciliationStatus.AMOUNT_MISMATCH),
        (
            (record("A"),),
            (external("A", direction=SettlementDirection.RETURN),),
            ReconciliationStatus.DIRECTION_MISMATCH,
        ),
    ],
)
def test_reconciliation_classifications(internal, rows, status) -> None:
    assert report(internal, rows).items[0].status is status


def test_duplicate_precedes_direction_and_amount_mismatch() -> None:
    result = report(
        (record("A"),),
        (
            external("A", 1, SettlementDirection.RETURN, "EXT-B"),
            external("A", 2, SettlementDirection.OUTBOUND, "EXT-A"),
        ),
    )
    item = result.items[0]
    assert item.status is ReconciliationStatus.DUPLICATE_EXTERNALLY
    assert item.external_reference == "EXT-A, EXT-B"


def test_integer_totals_signed_difference_and_stable_order() -> None:
    result = report(
        (record("B", 30_000), record("A", 12_500)),
        (
            external("B", 29_900, reference="EXT-B"),
            external("X", 8_000, reference="EXT-X"),
        ),
    )
    assert [item.payment_id for item in result.items] == ["A", "B", "X"]
    assert result.outbound_totals.internal_cents == 42_500
    assert result.outbound_totals.external_cents == 37_900
    assert result.outbound_totals.difference_cents == -4_600
    assert result.items[1].difference_cents == -100
    assert all(
        isinstance(value, int)
        for value in (
            result.outbound_totals.internal_cents,
            result.outbound_totals.external_cents,
        )
    )


def test_report_is_immutable_and_reconciliation_has_no_side_effects() -> None:
    internal = (record("A"),)
    rows = (external("A"),)
    result = report(internal, rows)
    with pytest.raises(FrozenInstanceError):
        result.completed_at = 52  # type: ignore[misc]
    assert internal == (record("A"),)
    assert rows == (external("A"),)


def test_reconciliation_does_not_modify_ach_or_ledger_history() -> None:
    ledger = Ledger()
    ledger.append(
        LedgerEntry("OPEN", "A", Money(20_000), EntryType.CREDIT, "Open", 1, 0)
    )
    network = AchNetwork(ledger)
    transfer = network.receive(
        AchTransferRequest("ACH-A", "A", "Bank", "Ref", 10_000, "ACH")
    )
    network.scheduler.run()
    entries_before = network.ledger.entries
    status_before = transfer.status
    history_before = transfer.history
    internal = settlement_expectations([transfer], [], 40)

    reconcile(internal, ExternalSettlementReport((), 50), 51)

    assert network.ledger.entries == entries_before
    assert transfer.status is status_before
    assert transfer.history == history_before
