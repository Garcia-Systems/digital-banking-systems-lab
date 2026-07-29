"""Reproducible balance projections over ledger and pending activity."""

from dataclasses import dataclass
from enum import Enum

from bank_sim.ledger import Ledger, Money, format_money, replay


class BalanceValidationError(ValueError):
    """Raised when pending activity cannot produce a reliable projection."""


class PendingTransactionType(Enum):
    """The direction in which pending activity affects available funds."""

    PENDING_DEBIT = "Pending Debit"
    PENDING_CREDIT = "Pending Credit"


@dataclass(frozen=True, slots=True)
class PendingTransaction:
    """An authorized transaction that has not become a ledger fact."""

    transaction_id: str
    amount: Money
    transaction_type: PendingTransactionType
    description: str
    sequence: int

    def __post_init__(self) -> None:
        for field_name in ("transaction_id", "description"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise BalanceValidationError(
                    f"{field_name.replace('_', ' ')} cannot be blank"
                )
        if not isinstance(self.amount, Money):
            raise BalanceValidationError("amount must be Money")
        if not isinstance(self.transaction_type, PendingTransactionType):
            raise BalanceValidationError("pending transaction type is not supported")
        if isinstance(self.sequence, bool) or not isinstance(self.sequence, int):
            raise BalanceValidationError("sequence must be an integer")
        if self.sequence <= 0:
            raise BalanceValidationError("sequence must be greater than zero")


@dataclass(frozen=True, slots=True)
class BalanceProjection:
    """A computed view, never an authoritative financial record."""

    current_balance: int
    pending_debits: int
    pending_credits: int
    available_balance: int


def project_balances(
    ledger: Ledger, pending: tuple[PendingTransaction, ...] | list[PendingTransaction]
) -> BalanceProjection:
    """Derive current, pending, and available balances without changing inputs."""
    if not isinstance(ledger, Ledger):
        raise BalanceValidationError("projection requires a Ledger")

    debits = 0
    credits = 0
    seen_ids: set[str] = set()
    for expected_sequence, transaction in enumerate(pending, start=1):
        if not isinstance(transaction, PendingTransaction):
            raise BalanceValidationError("pending activity must contain transactions")
        if transaction.sequence != expected_sequence:
            raise BalanceValidationError(
                "pending transactions require contiguous sequence order"
            )
        if transaction.transaction_id in seen_ids:
            raise BalanceValidationError(
                "pending transaction identifier must be unique"
            )
        seen_ids.add(transaction.transaction_id)
        if transaction.transaction_type is PendingTransactionType.PENDING_DEBIT:
            debits += transaction.amount.cents
        else:
            credits += transaction.amount.cents

    current = replay(ledger.entries)
    return BalanceProjection(current, debits, credits, current - debits + credits)


def chapter_pending_transactions() -> tuple[PendingTransaction, ...]:
    """Return fixed fictional pending activity in deterministic order."""
    return (
        PendingTransaction(
            "PT-0001",
            Money(6_000),
            PendingTransactionType.PENDING_DEBIT,
            "Gas Station",
            1,
        ),
        PendingTransaction(
            "PT-0002",
            Money(6_000),
            PendingTransactionType.PENDING_DEBIT,
            "Restaurant",
            2,
        ),
        PendingTransaction(
            "PT-0003", Money(2_500), PendingTransactionType.PENDING_CREDIT, "Payroll", 3
        ),
    )


def describe_balance(projection: BalanceProjection) -> str:
    """Render the four Chapter 4 balance figures."""
    return "\n".join(
        (
            f"Ledger Balance:     {format_money(projection.current_balance):>10}",
            f"Pending Debits:     {format_money(projection.pending_debits):>10}",
            f"Pending Credits:    {format_money(projection.pending_credits):>10}",
            f"Available Balance:  {format_money(projection.available_balance):>10}",
        )
    )


def describe_pending(pending: tuple[PendingTransaction, ...]) -> str:
    """Render pending transactions in their canonical sequence order."""
    lines: list[str] = []
    for transaction in pending:
        if lines:
            lines.append("")
        lines.extend(
            (
                transaction.transaction_type.value,
                transaction.description,
                format_money(transaction.amount.cents),
            )
        )
    return "\n".join(lines)
