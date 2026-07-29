"""A deliberately small, deterministic outbound ACH workflow."""

from dataclasses import dataclass, field
from enum import Enum

from bank_sim.balances import PendingTransaction, PendingTransactionType
from bank_sim.ledger import EntryType, Ledger, LedgerEntry, Money, format_money
from bank_sim.scheduler import EventScheduler
from bank_sim.transfers import account_balance


class AchValidationError(ValueError):
    """Raised when ACH input or a workflow transition is invalid."""


class AchDirection(Enum):
    """The only ACH direction taught in this chapter."""

    OUTBOUND_CREDIT = "Outbound credit"


class AchTransferStatus(Enum):
    """Observable stages of an outbound transfer."""

    RECEIVED = "Received"
    VALIDATED = "Validated"
    PENDING = "Pending"
    SUBMITTED = "Submitted"
    PROCESSING = "Processing"
    COMPLETED = "Completed"
    REJECTED = "Rejected"


@dataclass(frozen=True, slots=True)
class AchTransferRequest:
    """Fictional payment instructions; never real banking credentials."""

    transfer_id: str
    source_account_id: str
    destination_institution: str
    destination_reference: str
    amount_cents: int
    description: str


@dataclass(frozen=True, slots=True)
class AchProcessingEvent:
    """One timestamped observation in workflow history."""

    time: int
    status: AchTransferStatus
    description: str


_ALLOWED_TRANSITIONS = {
    AchTransferStatus.RECEIVED: {
        AchTransferStatus.VALIDATED,
        AchTransferStatus.REJECTED,
    },
    AchTransferStatus.VALIDATED: {AchTransferStatus.PENDING},
    AchTransferStatus.PENDING: {AchTransferStatus.SUBMITTED},
    AchTransferStatus.SUBMITTED: {AchTransferStatus.PROCESSING},
    AchTransferStatus.PROCESSING: {AchTransferStatus.COMPLETED},
    AchTransferStatus.COMPLETED: set(),
    AchTransferStatus.REJECTED: set(),
}


@dataclass(slots=True)
class AchTransfer:
    """A stateful payment workflow with guarded transitions."""

    request: AchTransferRequest
    direction: AchDirection = AchDirection.OUTBOUND_CREDIT
    status: AchTransferStatus = field(init=False, default=AchTransferStatus.RECEIVED)
    rejection_reason: str | None = field(init=False, default=None)
    _history: list[AchProcessingEvent] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._history = [
            AchProcessingEvent(0, AchTransferStatus.RECEIVED, "ACH transfer received")
        ]

    @property
    def history(self) -> tuple[AchProcessingEvent, ...]:
        return tuple(self._history)

    def transition(
        self, status: AchTransferStatus, time: int, description: str
    ) -> None:
        """Apply an allowed transition or fail immediately."""
        if status not in _ALLOWED_TRANSITIONS[self.status]:
            raise AchValidationError(
                f"cannot transition ACH transfer from {self.status.value} "
                f"to {status.value}"
            )
        self.status = status
        self._history.append(AchProcessingEvent(time, status, description))

    def reject(self, time: int, reason: str) -> None:
        self.transition(AchTransferStatus.REJECTED, time, "Transfer rejected")
        self.rejection_reason = reason


class AchNetwork:
    """In-memory coordination across fixed virtual-time stages."""

    def __init__(self, ledger: Ledger, scheduler: EventScheduler | None = None) -> None:
        self.ledger = ledger
        self.scheduler = scheduler if scheduler is not None else EventScheduler()
        self.pending: list[PendingTransaction] = []
        self.submissions: list[str] = []

    def receive(self, request: AchTransferRequest) -> AchTransfer:
        """Receive instructions and schedule their deterministic validation."""
        transfer = AchTransfer(request)
        self.scheduler.schedule_at(1, lambda: self._validate(transfer))
        return transfer

    def _validate(self, transfer: AchTransfer) -> None:
        reason = _invalid_reason(transfer.request)
        if reason is None and transfer.request.amount_cents > self.available_balance(
            transfer.request.source_account_id
        ):
            reason = "Insufficient available funds"
        if reason is not None:
            transfer.reject(self.scheduler.clock.time, reason)
            return
        transfer.transition(AchTransferStatus.VALIDATED, 1, "Transfer validated")
        self.scheduler.schedule_at(2, lambda: self._mark_pending(transfer))

    def _mark_pending(self, transfer: AchTransfer) -> None:
        transfer.transition(AchTransferStatus.PENDING, 2, "Funds marked pending")
        self.pending.append(
            PendingTransaction(
                transfer.request.transfer_id,
                Money(transfer.request.amount_cents),
                PendingTransactionType.PENDING_DEBIT,
                transfer.request.description or "Outbound ACH credit",
                len(self.pending) + 1,
            )
        )
        self.scheduler.schedule_at(3, lambda: self.submit(transfer))

    def submit(self, transfer: AchTransfer) -> None:
        transfer.transition(AchTransferStatus.SUBMITTED, 3, "Submitted to ACH network")
        self.submissions.append(transfer.request.transfer_id)
        self.scheduler.schedule_at(5, lambda: self.process(transfer))

    def process(self, transfer: AchTransfer) -> None:
        transfer.transition(AchTransferStatus.PROCESSING, 5, "Network processing")
        self.scheduler.schedule_at(10, lambda: self.complete(transfer))

    def complete(self, transfer: AchTransfer) -> None:
        """Complete once, clear the hold, and append exactly one debit."""
        transfer.transition(AchTransferStatus.COMPLETED, 10, "Transfer completed")
        self.pending = [
            item
            for item in self.pending
            if item.transaction_id != transfer.request.transfer_id
        ]
        self.ledger.append(
            LedgerEntry(
                f"{transfer.request.transfer_id}-DEBIT",
                transfer.request.source_account_id,
                Money(transfer.request.amount_cents),
                EntryType.DEBIT,
                transfer.request.description or "Outbound ACH credit",
                len(self.ledger.entries) + 1,
                10,
            )
        )
        transfer._history.append(
            AchProcessingEvent(10, AchTransferStatus.COMPLETED, "Ledger debit posted")
        )

    def available_balance(self, account_id: str) -> int:
        held = sum(
            item.amount.cents
            for item in self.pending
            if item.transaction_type is PendingTransactionType.PENDING_DEBIT
        )
        return account_balance(self.ledger, account_id) - held


def _invalid_reason(request: AchTransferRequest) -> str | None:
    for value, reason in (
        (request.transfer_id, "transfer identifier cannot be blank"),
        (request.source_account_id, "source account identifier cannot be blank"),
        (request.destination_institution, "destination institution cannot be blank"),
        (request.destination_reference, "destination reference cannot be blank"),
    ):
        if not isinstance(value, str) or not value.strip():
            return reason
    if isinstance(request.amount_cents, bool) or not isinstance(
        request.amount_cents, int
    ):
        return "transfer amount must be integer cents"
    if request.amount_cents == 0:
        return "transfer amount cannot be zero"
    if request.amount_cents < 0:
        return "transfer amount cannot be negative"
    if not isinstance(request.description, str):
        return "description must be text"
    return None


def chapter_ach_scenario() -> tuple[AchNetwork, AchTransfer, int, int]:
    """Run the fixed Chapter 8 successful scenario."""
    ledger = Ledger()
    ledger.append(
        LedgerEntry(
            "ACH-OPEN",
            "HCCU-DEMO-001",
            Money(100_000),
            EntryType.CREDIT,
            "Opening balance",
            1,
            0,
        )
    )
    network = AchNetwork(ledger)
    transfer = network.receive(
        AchTransferRequest(
            "ACH-0001",
            "HCCU-DEMO-001",
            "Blue Ridge National Bank",
            "EXTERNAL-ACCOUNT-001",
            25_000,
            "External transfer",
        )
    )
    initial_current = account_balance(ledger, "HCCU-DEMO-001")
    initial_available = network.available_balance("HCCU-DEMO-001")
    network.scheduler.run()
    return network, transfer, initial_current, initial_available


def describe_ach() -> str:
    network, transfer, initial_current, initial_available = chapter_ach_scenario()
    request = transfer.request
    final_current = account_balance(network.ledger, request.source_account_id)
    final_available = network.available_balance(request.source_account_id)
    return "\n".join(
        (
            f"ACH transfer: {request.transfer_id}",
            f"Source account: {request.source_account_id}",
            f"Destination institution: {request.destination_institution}",
            f"Destination reference: {request.destination_reference}",
            f"Amount: {format_money(request.amount_cents)}",
            f"Initial current balance: {format_money(initial_current)}",
            f"Initial available balance: {format_money(initial_available)}",
            f"Final status: {transfer.status.value}",
            f"Final current balance: {format_money(final_current)}",
            f"Final available balance: {format_money(final_available)}",
            f"Ledger effect: {request.transfer_id}-DEBIT | Debit | "
            f"{format_money(request.amount_cents)}",
        )
    )


def describe_ach_timeline() -> str:
    _, transfer, _, _ = chapter_ach_scenario()
    return "\n".join(
        f"T+{event.time:<4} {event.description}" for event in transfer.history
    )
