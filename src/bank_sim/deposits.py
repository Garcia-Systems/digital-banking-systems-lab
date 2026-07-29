"""A small, deterministic workflow that posts deposits to the ledger."""

from dataclasses import dataclass
from enum import Enum

from bank_sim.ledger import EntryType, Ledger, LedgerEntry, Money, format_money, replay


class DepositValidationError(ValueError):
    """Raised when a deposit request violates a business invariant."""


class DepositStatus(Enum):
    """The explicit states in the educational deposit workflow."""

    RECEIVED = "Received"
    POSTED = "Posted"
    REJECTED = "Rejected"


@dataclass(frozen=True, slots=True)
class DepositRequest:
    """Input requesting that positive integer cents be deposited to an account."""

    deposit_id: str
    account_id: str
    amount_cents: int
    description: str

    def __post_init__(self) -> None:
        for field_name in ("deposit_id", "account_id"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                label = field_name.replace("_id", " identifier")
                raise DepositValidationError(f"{label} cannot be blank")
        if isinstance(self.amount_cents, bool) or not isinstance(
            self.amount_cents, int
        ):
            raise DepositValidationError("deposit amount must be integer cents")
        if self.amount_cents <= 0:
            raise DepositValidationError("deposit amount must be greater than zero")
        if not isinstance(self.description, str):
            raise DepositValidationError("description must be text")


@dataclass(frozen=True, slots=True)
class Deposit:
    """A workflow result; the corresponding ledger entry remains authoritative."""

    deposit_id: str
    account_id: str
    amount_cents: int
    description: str
    status: DepositStatus


def post_deposit(ledger: Ledger, request: DepositRequest) -> Deposit:
    """Append the request as a credit and return its posted workflow result."""
    if not isinstance(ledger, Ledger):
        raise DepositValidationError("deposit posting requires a Ledger")
    if not isinstance(request, DepositRequest):
        raise DepositValidationError("deposit posting requires a DepositRequest")

    sequence = len(ledger.entries) + 1
    ledger.append(
        LedgerEntry(
            entry_id=f"{request.deposit_id}-ENTRY",
            account_id=request.account_id,
            amount=Money(request.amount_cents),
            entry_type=EntryType.CREDIT,
            description=request.description or "Deposit",
            sequence=sequence,
            posted_at=sequence,
        )
    )
    return Deposit(
        request.deposit_id,
        request.account_id,
        request.amount_cents,
        request.description,
        DepositStatus.POSTED,
    )


def chapter_deposit_requests() -> tuple[DepositRequest, ...]:
    """Return the fixed Chapter 5 requests in their canonical order."""
    return (
        DepositRequest("DEP-0001", "HCCU-DEMO-001", 50_000, "Initial deposit"),
        DepositRequest("DEP-0002", "HCCU-DEMO-001", 25_000, "Second deposit"),
        DepositRequest("DEP-0003", "HCCU-DEMO-001", 7_550, "Third deposit"),
    )


def describe_deposits(requests: tuple[DepositRequest, ...]) -> str:
    """Post requests to a new ledger and show each request, fact, and projection."""
    ledger = Ledger()
    lines: list[str] = []
    for request in requests:
        deposit = post_deposit(ledger, request)
        entry = ledger.entries[-1]
        if lines:
            lines.append("")
        lines.extend(
            (
                f"Request: {request.deposit_id} | {request.account_id} | "
                f"{format_money(request.amount_cents)}",
                f"Status: {DepositStatus.RECEIVED.value} → {deposit.status.value}",
                f"Ledger entry: {entry.entry_id} | {entry.entry_type.value} | "
                f"{format_money(entry.amount.cents)}",
                f"Running balance: {format_money(replay(ledger.entries))}",
            )
        )
    lines.extend(("", "Final balance:", format_money(replay(ledger.entries))))
    return "\n".join(lines)
