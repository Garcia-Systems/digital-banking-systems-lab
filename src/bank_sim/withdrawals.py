"""Deterministic withdrawal decisions made before immutable history is written."""

from dataclasses import dataclass
from enum import Enum

from bank_sim.balances import PendingTransaction, project_balances
from bank_sim.ledger import EntryType, Ledger, LedgerEntry, Money, format_money, replay


class WithdrawalValidationError(ValueError):
    """Raised when a withdrawal request violates an input invariant."""


class WithdrawalStatus(Enum):
    """The explicit states in the educational withdrawal workflow."""

    RECEIVED = "Received"
    POSTED = "Posted"
    REJECTED = "Rejected"


@dataclass(frozen=True, slots=True)
class WithdrawalRequest:
    """A request to withdraw a positive amount expressed as integer cents."""

    withdrawal_id: str
    account_id: str
    amount_cents: int
    description: str

    def __post_init__(self) -> None:
        for field_name in ("withdrawal_id", "account_id"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                label = field_name.replace("_id", " identifier")
                raise WithdrawalValidationError(f"{label} cannot be blank")
        if isinstance(self.amount_cents, bool) or not isinstance(
            self.amount_cents, int
        ):
            raise WithdrawalValidationError("withdrawal amount must be integer cents")
        if self.amount_cents <= 0:
            raise WithdrawalValidationError(
                "withdrawal amount must be greater than zero"
            )
        if not isinstance(self.description, str):
            raise WithdrawalValidationError("description must be text")


@dataclass(frozen=True, slots=True)
class Withdrawal:
    """A withdrawal decision; only a posted result has a corresponding entry."""

    withdrawal_id: str
    account_id: str
    amount_cents: int
    description: str
    status: WithdrawalStatus
    rejection_reason: str | None = None


INSUFFICIENT_FUNDS_REASON = "Insufficient available funds"


def process_withdrawal(
    ledger: Ledger,
    request: WithdrawalRequest,
    pending: tuple[PendingTransaction, ...] | list[PendingTransaction] = (),
) -> Withdrawal:
    """Reject against available funds or append one authoritative debit fact."""
    if not isinstance(ledger, Ledger):
        raise WithdrawalValidationError("withdrawal processing requires a Ledger")
    if not isinstance(request, WithdrawalRequest):
        raise WithdrawalValidationError(
            "withdrawal processing requires a WithdrawalRequest"
        )

    available = project_balances(ledger, pending).available_balance
    if request.amount_cents > available:
        return Withdrawal(
            request.withdrawal_id,
            request.account_id,
            request.amount_cents,
            request.description,
            WithdrawalStatus.REJECTED,
            INSUFFICIENT_FUNDS_REASON,
        )

    sequence = len(ledger.entries) + 1
    ledger.append(
        LedgerEntry(
            entry_id=f"{request.withdrawal_id}-ENTRY",
            account_id=request.account_id,
            amount=Money(request.amount_cents),
            entry_type=EntryType.DEBIT,
            description=request.description or "Withdrawal",
            sequence=sequence,
            posted_at=sequence,
        )
    )
    return Withdrawal(
        request.withdrawal_id,
        request.account_id,
        request.amount_cents,
        request.description,
        WithdrawalStatus.POSTED,
    )


def _opening_ledger(amount_cents: int) -> Ledger:
    ledger = Ledger()
    ledger.append(
        LedgerEntry(
            "OPENING-ENTRY",
            "HCCU-DEMO-001",
            Money(amount_cents),
            EntryType.CREDIT,
            "Opening balance",
            1,
            1,
        )
    )
    return ledger


def describe_withdrawal() -> str:
    """Show the fixed successful Chapter 6 request from validation through replay."""
    ledger = _opening_ledger(50_000)
    request = WithdrawalRequest(
        "WDR-0001", "HCCU-DEMO-001", 12_000, "Member withdrawal"
    )
    result = process_withdrawal(ledger, request)
    entry = ledger.entries[-1]
    return "\n".join(
        (
            f"Request: {request.withdrawal_id} | {request.account_id} | "
            f"{format_money(request.amount_cents)}",
            "Validation: Request valid; available funds sufficient",
            f"Status: {WithdrawalStatus.RECEIVED.value} → {result.status.value}",
            f"Ledger entry: {entry.entry_id} | {entry.entry_type.value} | "
            f"{format_money(entry.amount.cents)}",
            "Replay: opening credit, then posted debit",
            "",
            "Final balance:",
            format_money(replay(ledger.entries)),
        )
    )


def describe_withdrawals() -> str:
    """Show one posted and one rejected request followed by a single replay."""
    ledger = _opening_ledger(50_000)
    requests = (
        WithdrawalRequest("WDR-0001", "HCCU-DEMO-001", 12_000, "Withdrawal"),
        WithdrawalRequest("WDR-0002", "HCCU-DEMO-001", 40_000, "Withdrawal"),
    )
    lines: list[str] = []
    for request in requests:
        before = len(ledger.entries)
        result = process_withdrawal(ledger, request)
        if lines:
            lines.append("")
        lines.extend(
            (
                f"Request: {request.withdrawal_id} | "
                f"{format_money(request.amount_cents)}",
                f"Status: {WithdrawalStatus.RECEIVED.value} → {result.status.value}",
            )
        )
        if result.status is WithdrawalStatus.POSTED:
            lines.append(f"Ledger entry: {ledger.entries[-1].entry_id} | Debit")
        else:
            lines.extend(
                (
                    f"Reason: {result.rejection_reason}",
                    f"Ledger entries appended: {len(ledger.entries) - before}",
                )
            )
    lines.extend(("", "Final ledger replay:", format_money(replay(ledger.entries))))
    return "\n".join(lines)
