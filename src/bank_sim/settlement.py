"""Independent, deterministic settlement reconciliation for completed ACH work."""

from dataclasses import dataclass
from enum import Enum

from bank_sim.ach import AchTransfer, AchTransferStatus
from bank_sim.ach_returns import AchReturn, AchReturnStatus
from bank_sim.ledger import format_money


class SettlementDirection(Enum):
    OUTBOUND = "Outbound"
    RETURN = "Return"


class ReconciliationStatus(Enum):
    MATCHED = "Matched"
    MISSING_EXTERNALLY = "Missing externally"
    UNEXPECTED_EXTERNALLY = "Unexpected externally"
    AMOUNT_MISMATCH = "Amount mismatch"
    DIRECTION_MISMATCH = "Direction mismatch"
    DUPLICATE_EXTERNALLY = "Duplicate externally"


@dataclass(frozen=True, slots=True)
class SettlementRecord:
    record_id: str
    payment_id: str
    amount_cents: int
    direction: SettlementDirection
    expected_at: int

    @property
    def matching_key(self) -> tuple[str, SettlementDirection]:
        """The payment identifier and direction, never the amount, form the key."""
        return self.payment_id, self.direction


@dataclass(frozen=True, slots=True)
class ExternalSettlementRecord:
    external_reference: str
    payment_id: str
    amount_cents: int
    direction: SettlementDirection
    reported_at: int

    @property
    def matching_key(self) -> tuple[str, SettlementDirection]:
        return self.payment_id, self.direction


@dataclass(frozen=True, slots=True)
class ExternalSettlementReport:
    records: tuple[ExternalSettlementRecord, ...]
    received_at: int


@dataclass(frozen=True, slots=True)
class ReconciliationItem:
    payment_id: str
    status: ReconciliationStatus
    direction: SettlementDirection
    internal_amount_cents: int
    external_amount_cents: int
    external_reference: str = "-"
    details: str = ""

    @property
    def difference_cents(self) -> int:
        """External minus internal; a negative value means external reported less."""
        return self.external_amount_cents - self.internal_amount_cents


@dataclass(frozen=True, slots=True)
class DirectionTotals:
    internal_cents: int
    external_cents: int

    @property
    def difference_cents(self) -> int:
        return self.external_cents - self.internal_cents


@dataclass(frozen=True, slots=True)
class ReconciliationReport:
    items: tuple[ReconciliationItem, ...]
    status_totals: tuple[tuple[ReconciliationStatus, int], ...]
    outbound_totals: DirectionTotals
    return_totals: DirectionTotals
    completed_at: int

    @property
    def matched_count(self) -> int:
        return sum(item.status is ReconciliationStatus.MATCHED for item in self.items)

    @property
    def exception_count(self) -> int:
        return len(self.items) - self.matched_count


def settlement_expectations(
    transfers: tuple[AchTransfer, ...] | list[AchTransfer],
    returns: tuple[AchReturn, ...] | list[AchReturn],
    generated_at: int,
) -> tuple[SettlementRecord, ...]:
    """Derive unique expectations from completed domain workflows only."""
    records: dict[tuple[str, SettlementDirection], SettlementRecord] = {}
    for transfer in transfers:
        if transfer.status is AchTransferStatus.COMPLETED:
            payment_id = transfer.request.transfer_id
            record = SettlementRecord(
                f"SETTLEMENT-{payment_id}",
                payment_id,
                transfer.request.amount_cents,
                SettlementDirection.OUTBOUND,
                generated_at,
            )
            records[record.matching_key] = record
    for item in returns:
        if item.status is AchReturnStatus.COMPLETED:
            payment_id = item.request.return_id
            record = SettlementRecord(
                f"SETTLEMENT-{payment_id}",
                payment_id,
                item.request.amount_cents,
                SettlementDirection.RETURN,
                generated_at,
            )
            records[record.matching_key] = record
    return tuple(
        sorted(records.values(), key=lambda row: (row.payment_id, row.direction.value))
    )


def reconcile(
    internal: tuple[SettlementRecord, ...],
    external_report: ExternalSettlementReport,
    completed_at: int,
) -> ReconciliationReport:
    """Compare snapshots without mutating workflows, ledger, or expectations.

    Classification precedence for a shared payment identity is duplicate,
    direction mismatch, amount mismatch, then matched.
    """
    internal_by_id = {row.payment_id: row for row in internal}
    external_by_id: dict[str, list[ExternalSettlementRecord]] = {}
    for row in external_report.records:
        external_by_id.setdefault(row.payment_id, []).append(row)
    items: list[ReconciliationItem] = []
    for payment_id in sorted(set(internal_by_id) | set(external_by_id)):
        expected = internal_by_id.get(payment_id)
        actual = sorted(
            external_by_id.get(payment_id, []), key=lambda row: row.external_reference
        )
        if expected is None:
            for row in actual:
                items.append(
                    _item(row, None, ReconciliationStatus.UNEXPECTED_EXTERNALLY)
                )
        elif not actual:
            items.append(_item(None, expected, ReconciliationStatus.MISSING_EXTERNALLY))
        elif len(actual) > 1:
            refs = ", ".join(row.external_reference for row in actual)
            items.append(
                ReconciliationItem(
                    payment_id,
                    ReconciliationStatus.DUPLICATE_EXTERNALLY,
                    expected.direction,
                    expected.amount_cents,
                    sum(row.amount_cents for row in actual),
                    refs,
                    f"{len(actual)} external rows share this payment identity",
                )
            )
        else:
            row = actual[0]
            if row.direction is not expected.direction:
                status = ReconciliationStatus.DIRECTION_MISMATCH
            elif row.amount_cents != expected.amount_cents:
                status = ReconciliationStatus.AMOUNT_MISMATCH
            else:
                status = ReconciliationStatus.MATCHED
            items.append(_item(row, expected, status))
    items.sort(
        key=lambda item: (item.payment_id, item.status.value, item.external_reference)
    )
    status_totals = tuple(
        (status, sum(item.status is status for item in items))
        for status in ReconciliationStatus
    )
    return ReconciliationReport(
        tuple(items),
        status_totals,
        _totals(internal, external_report.records, SettlementDirection.OUTBOUND),
        _totals(internal, external_report.records, SettlementDirection.RETURN),
        completed_at,
    )


def _item(
    external: ExternalSettlementRecord | None,
    internal: SettlementRecord | None,
    status: ReconciliationStatus,
) -> ReconciliationItem:
    source = internal if internal is not None else external
    assert source is not None
    return ReconciliationItem(
        source.payment_id,
        status,
        source.direction,
        internal.amount_cents if internal else 0,
        external.amount_cents if external else 0,
        external.external_reference if external else "-",
        status.value,
    )


def _totals(
    internal: tuple[SettlementRecord, ...],
    external: tuple[ExternalSettlementRecord, ...],
    direction: SettlementDirection,
) -> DirectionTotals:
    return DirectionTotals(
        sum(row.amount_cents for row in internal if row.direction is direction),
        sum(row.amount_cents for row in external if row.direction is direction),
    )


def _completed_workflows() -> tuple[list[AchTransfer], list[AchReturn]]:
    """Build Chapter 10 records through the existing ACH domain workflows."""
    from bank_sim.ach import AchNetwork, AchTransferRequest
    from bank_sim.ach_returns import (
        AchReturnProcessor,
        AchReturnReason,
        AchReturnRequest,
    )
    from bank_sim.ledger import EntryType, Ledger, LedgerEntry, Money

    ledger = Ledger()
    ledger.append(
        LedgerEntry(
            "OPEN",
            "HCCU-DEMO-001",
            Money(100_000),
            EntryType.CREDIT,
            "Opening balance",
            1,
            0,
        )
    )
    network = AchNetwork(ledger)
    first = network.receive(
        AchTransferRequest(
            "ACH-001",
            "HCCU-DEMO-001",
            "Fictional Network Bank",
            "DEMO-001",
            25_000,
            "Settlement lesson",
        )
    )
    network.scheduler.run()
    network.scheduler.clock.advance_to(30)
    processor = AchReturnProcessor(network)
    returned = processor.receive(
        AchReturnRequest(
            "RETURN-001", "ACH-001", AchReturnReason.ACCOUNT_CLOSED, 25_000
        )
    )
    network.scheduler.run()
    return [first], [returned]


def chapter_settlement_records() -> tuple[SettlementRecord, ...]:
    transfers, returns = _completed_workflows()
    return settlement_expectations(transfers, returns, 40)


def describe_settlement() -> str:
    records = chapter_settlement_records()
    lines = ["Internal settlement expectations", f"Record count: {len(records)}"]
    lines.extend(
        f"{r.payment_id} | {r.direction.value} | "
        f"{format_money(r.amount_cents)} | T+{r.expected_at}"
        for r in records
    )
    return "\n".join(lines)


def _matched_report() -> tuple[
    tuple[SettlementRecord, ...], ExternalSettlementReport, ReconciliationReport
]:
    internal = chapter_settlement_records()
    external = ExternalSettlementReport(
        tuple(
            ExternalSettlementRecord(
                f"EXT-{index:03}", row.payment_id, row.amount_cents, row.direction, 50
            )
            for index, row in enumerate(internal, 1)
        ),
        50,
    )
    return internal, external, reconcile(internal, external, 51)


def describe_reconciliation() -> str:
    internal, external, report = _matched_report()
    return "\n".join(
        (
            "Settlement reconciliation",
            f"Internal records: {len(internal)}",
            f"External records: {len(external.records)}",
            f"Matched: {report.matched_count}",
            f"Exceptions: {report.exception_count}",
            *_totals_lines(report),
            "Final result: Reconciled",
        )
    )


def describe_reconciliation_exceptions() -> str:
    internal = (
        SettlementRecord(
            "S-ACH-002", "ACH-002", 12_500, SettlementDirection.OUTBOUND, 40
        ),
        SettlementRecord(
            "S-ACH-003", "ACH-003", 30_000, SettlementDirection.OUTBOUND, 40
        ),
        SettlementRecord(
            "S-ACH-004", "ACH-004", 5_000, SettlementDirection.OUTBOUND, 40
        ),
    )
    external = ExternalSettlementReport(
        (
            ExternalSettlementRecord(
                "EXT-003", "ACH-003", 29_900, SettlementDirection.OUTBOUND, 50
            ),
            ExternalSettlementRecord(
                "EXT-004-A", "ACH-004", 5_000, SettlementDirection.OUTBOUND, 50
            ),
            ExternalSettlementRecord(
                "EXT-004-B", "ACH-004", 5_000, SettlementDirection.OUTBOUND, 50
            ),
            ExternalSettlementRecord(
                "EXT-999", "ACH-EXTERNAL-999", 8_000, SettlementDirection.OUTBOUND, 50
            ),
        ),
        50,
    )
    report = reconcile(internal, external, 51)
    lines = ["Reconciliation exception report"]
    for item in report.items:
        lines.append(
            f"{item.payment_id} | {item.status.value} | {item.direction.value} | "
            f"Difference: {format_money(item.difference_cents)} | "
            f"External: {item.external_reference}"
        )
    lines.extend(
        (
            f"Matched: {report.matched_count}",
            f"Exceptions: {report.exception_count}",
            *_totals_lines(report),
        )
    )
    return "\n".join(lines)


def _totals_lines(report: ReconciliationReport) -> tuple[str, ...]:
    out, ret = report.outbound_totals, report.return_totals
    return (
        f"Outbound totals: internal {format_money(out.internal_cents)} | "
        f"external {format_money(out.external_cents)} | "
        f"difference {format_money(out.difference_cents)}",
        f"Return totals: internal {format_money(ret.internal_cents)} | "
        f"external {format_money(ret.external_cents)} | "
        f"difference {format_money(ret.difference_cents)}",
    )
