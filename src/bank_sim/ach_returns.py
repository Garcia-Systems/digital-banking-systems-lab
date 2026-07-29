"""Deterministic corrections for completed outbound ACH transfers."""

from dataclasses import dataclass, field
from enum import Enum

from bank_sim.ach import AchNetwork, AchTransferStatus
from bank_sim.ledger import EntryType, LedgerEntry, Money, format_money
from bank_sim.transfers import account_balance


class AchReturnValidationError(ValueError):
    """Raised when an ACH return transition is not permitted."""


class AchReturnReason(Enum):
    """Simplified teaching reasons, not production NACHA return codes."""

    ACCOUNT_CLOSED = "Account closed"
    INVALID_ACCOUNT = "Invalid account"
    INSUFFICIENT_FUNDS_AT_RECEIVING_INSTITUTION = (
        "Insufficient funds at receiving institution"
    )
    UNAUTHORIZED = "Unauthorized"


class AchReturnStatus(Enum):
    RECEIVED = "Received"
    VALIDATED = "Validated"
    PROCESSING = "Processing"
    COMPLETED = "Completed"
    REJECTED = "Rejected"


@dataclass(frozen=True, slots=True)
class AchReturnRequest:
    return_id: str
    original_transfer_id: str
    reason: AchReturnReason
    amount_cents: int


@dataclass(frozen=True, slots=True)
class AchReturnEvent:
    time: int
    status: AchReturnStatus
    description: str


_ALLOWED_TRANSITIONS = {
    AchReturnStatus.RECEIVED: {
        AchReturnStatus.VALIDATED,
        AchReturnStatus.REJECTED,
    },
    AchReturnStatus.VALIDATED: {AchReturnStatus.PROCESSING},
    AchReturnStatus.PROCESSING: {AchReturnStatus.COMPLETED},
    AchReturnStatus.COMPLETED: set(),
    AchReturnStatus.REJECTED: set(),
}


@dataclass(slots=True)
class AchReturn:
    request: AchReturnRequest
    received_at: int
    status: AchReturnStatus = field(init=False, default=AchReturnStatus.RECEIVED)
    completed_at: int | None = field(init=False, default=None)
    corrective_entry_id: str | None = field(init=False, default=None)
    rejection_reason: str | None = field(init=False, default=None)
    _history: list[AchReturnEvent] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._history = [
            AchReturnEvent(self.received_at, self.status, "ACH return received")
        ]

    @property
    def history(self) -> tuple[AchReturnEvent, ...]:
        return tuple(self._history)

    def transition(self, status: AchReturnStatus, time: int, description: str) -> None:
        if status not in _ALLOWED_TRANSITIONS[self.status]:
            raise AchReturnValidationError(
                f"cannot transition ACH return from {self.status.value} "
                f"to {status.value}"
            )
        self.status = status
        self._history.append(AchReturnEvent(time, status, description))

    def reject(self, time: int, reason: str) -> None:
        self.transition(AchReturnStatus.REJECTED, time, "ACH return rejected")
        self.rejection_reason = reason


class AchReturnProcessor:
    """Coordinates returns without mutating transfer or prior ledger history."""

    def __init__(self, network: AchNetwork) -> None:
        self.network = network
        self.returns: dict[str, AchReturn] = {}
        self._returns_by_transfer: dict[str, AchReturn] = {}

    def receive(self, request: AchReturnRequest) -> AchReturn:
        existing = self.returns.get(request.return_id)
        if existing is not None:
            return existing
        item = AchReturn(request, self.network.scheduler.clock.time)
        self.returns[request.return_id] = item
        self.network.scheduler.schedule_after(1, lambda: self.validate(item))
        return item

    def validate(self, item: AchReturn) -> None:
        reason = self._invalid_reason(item.request)
        if reason is not None:
            item.reject(self.network.scheduler.clock.time, reason)
            return
        item.transition(
            AchReturnStatus.VALIDATED,
            self.network.scheduler.clock.time,
            "ACH return validated",
        )
        self._returns_by_transfer[item.request.original_transfer_id] = item
        self.network.scheduler.schedule_after(1, lambda: self.process(item))

    def process(self, item: AchReturn) -> None:
        item.transition(
            AchReturnStatus.PROCESSING,
            self.network.scheduler.clock.time,
            "ACH return processing",
        )
        self.network.scheduler.schedule_after(3, lambda: self.complete(item))

    def complete(self, item: AchReturn) -> None:
        """Append one full corrective credit after the guarded transition."""
        item.transition(
            AchReturnStatus.COMPLETED,
            self.network.scheduler.clock.time,
            "ACH return completed",
        )
        request = item.request
        entry_id = f"{request.return_id}-CREDIT"
        self.network.ledger.append(
            LedgerEntry(
                entry_id,
                self.network.transfers[
                    request.original_transfer_id
                ].request.source_account_id,
                Money(request.amount_cents),
                EntryType.CREDIT,
                "ACH return credit",
                len(self.network.ledger.entries) + 1,
                self.network.scheduler.clock.time,
                request.original_transfer_id,
                request.return_id,
            )
        )
        item.completed_at = self.network.scheduler.clock.time
        item.corrective_entry_id = entry_id
        item._history.append(
            AchReturnEvent(
                self.network.scheduler.clock.time,
                AchReturnStatus.COMPLETED,
                "Corrective credit posted",
            )
        )

    def _invalid_reason(self, request: AchReturnRequest) -> str | None:
        if not isinstance(request.return_id, str) or not request.return_id.strip():
            return "return identifier cannot be blank"
        if (
            not isinstance(request.original_transfer_id, str)
            or not request.original_transfer_id.strip()
        ):
            return "original transfer identifier cannot be blank"
        if not isinstance(request.reason, AchReturnReason):
            return "return reason is not supported"
        if isinstance(request.amount_cents, bool) or not isinstance(
            request.amount_cents, int
        ):
            return "return amount must be integer cents"
        transfer = self.network.transfers.get(request.original_transfer_id)
        if transfer is None:
            return "original ACH transfer does not exist"
        if transfer.status is not AchTransferStatus.COMPLETED:
            return "original ACH transfer is not completed"
        if request.amount_cents != transfer.request.amount_cents:
            return "return amount must match original transfer amount"
        if request.original_transfer_id in self._returns_by_transfer:
            return "original ACH transfer already has a return"
        return None


def chapter_ach_return_scenario() -> tuple[AchReturnProcessor, AchReturn, int, int]:
    """Run Chapter 9's fixed full-return scenario."""
    from bank_sim.ach import chapter_ach_scenario

    network, _, original_balance, _ = chapter_ach_scenario()
    balance_after_outbound = account_balance(network.ledger, "HCCU-DEMO-001")
    network.scheduler.clock.advance_to(30)
    processor = AchReturnProcessor(network)
    item = processor.receive(
        AchReturnRequest(
            "RETURN-0001",
            "ACH-0001",
            AchReturnReason.ACCOUNT_CLOSED,
            25_000,
        )
    )
    network.scheduler.run()
    return processor, item, original_balance, balance_after_outbound


def describe_ach_return() -> str:
    processor, item, original_balance, after_outbound = chapter_ach_return_scenario()
    request = item.request
    entries = processor.network.ledger.entries
    final_balance = account_balance(processor.network.ledger, "HCCU-DEMO-001")
    return "\n".join(
        (
            f"Original source balance: {format_money(original_balance)}",
            f"Outbound ACH amount: {format_money(request.amount_cents)}",
            f"Balance after outbound posting: {format_money(after_outbound)}",
            f"Return reason: {request.reason.value}",
            f"Corrective ledger entry: {item.corrective_entry_id} | Credit | "
            f"{format_money(request.amount_cents)}",
            f"Final balance: {format_money(final_balance)}",
            "Preserved entries:",
            f"- {entries[1].entry_id} | Debit | "
            f"{format_money(entries[1].amount.cents)}",
            f"- {entries[2].entry_id} | Credit | "
            f"{format_money(entries[2].amount.cents)}",
        )
    )


def describe_ach_return_timeline() -> str:
    processor, item, _, _ = chapter_ach_return_scenario()
    transfer = processor.network.transfers[item.request.original_transfer_id]
    events = [*transfer.history, *item.history]
    return "\n".join(f"T+{event.time:<4} {event.description}" for event in events)
