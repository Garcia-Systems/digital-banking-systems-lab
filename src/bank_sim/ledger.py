"""An immutable history of money and its current-balance projection."""

from dataclasses import dataclass
from enum import Enum


class LedgerValidationError(ValueError):
    """Raised when ledger data violates a domain invariant."""


@dataclass(frozen=True, slots=True)
class Money:
    """An exact monetary magnitude represented as nonnegative integer cents."""

    cents: int

    def __post_init__(self) -> None:
        if isinstance(self.cents, bool) or not isinstance(self.cents, int):
            raise LedgerValidationError("money must be represented by integer cents")
        if self.cents <= 0:
            raise LedgerValidationError("ledger entry amount must be greater than zero")


class EntryType(Enum):
    """The direction in which an entry changes the balance projection."""

    CREDIT = "Credit"
    DEBIT = "Debit"


@dataclass(frozen=True, slots=True)
class LedgerEntry:
    """One immutable, deterministically ordered fact about money."""

    entry_id: str
    account_id: str
    amount: Money
    entry_type: EntryType
    description: str
    sequence: int
    posted_at: int
    original_transfer_id: str | None = None
    ach_return_id: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("entry_id", "account_id", "description"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise LedgerValidationError(
                    f"{field_name.replace('_', ' ')} cannot be blank"
                )
        if not isinstance(self.amount, Money):
            raise LedgerValidationError("amount must be Money")
        if not isinstance(self.entry_type, EntryType):
            raise LedgerValidationError("entry type is not supported")
        if isinstance(self.sequence, bool) or not isinstance(self.sequence, int):
            raise LedgerValidationError("sequence must be an integer")
        if self.sequence <= 0:
            raise LedgerValidationError("sequence must be greater than zero")
        if isinstance(self.posted_at, bool) or not isinstance(self.posted_at, int):
            raise LedgerValidationError("posting time must be an integer")
        if self.posted_at < 0:
            raise LedgerValidationError("posting time cannot be negative")
        for reference_name in ("original_transfer_id", "ach_return_id"):
            reference = getattr(self, reference_name)
            if reference is not None and (
                not isinstance(reference, str) or not reference.strip()
            ):
                raise LedgerValidationError(
                    f"{reference_name.replace('_', ' ')} cannot be blank"
                )


class Ledger:
    """An append-only in-memory collection of immutable ledger entries."""

    __slots__ = ("_entries", "_entry_ids")

    def __init__(self) -> None:
        self._entries: list[LedgerEntry] = []
        self._entry_ids: set[str] = set()

    @property
    def entries(self) -> tuple[LedgerEntry, ...]:
        """Return an immutable snapshot in canonical sequence order."""
        return tuple(self._entries)

    def append(self, entry: LedgerEntry) -> None:
        """Append the next fact; existing facts cannot be changed or removed."""
        if not isinstance(entry, LedgerEntry):
            raise LedgerValidationError("ledger accepts only LedgerEntry values")
        expected_sequence = len(self._entries) + 1
        if entry.sequence != expected_sequence:
            raise LedgerValidationError(
                f"sequence must be {expected_sequence}, received {entry.sequence}"
            )
        if entry.entry_id in self._entry_ids:
            raise LedgerValidationError("entry identifier must be unique")
        if self._entries and entry.posted_at < self._entries[-1].posted_at:
            raise LedgerValidationError("posting time cannot move backward")
        self._entries.append(entry)
        self._entry_ids.add(entry.entry_id)

    def append_batch(self, entries: tuple[LedgerEntry, ...]) -> None:
        """Validate and append a group of facts as one in-memory operation."""
        if not isinstance(entries, tuple) or not entries:
            raise LedgerValidationError("ledger batch must be a nonempty tuple")

        expected_sequence = len(self._entries) + 1
        known_ids = set(self._entry_ids)
        last_posted_at = self._entries[-1].posted_at if self._entries else 0
        for entry in entries:
            if not isinstance(entry, LedgerEntry):
                raise LedgerValidationError("ledger accepts only LedgerEntry values")
            if entry.sequence != expected_sequence:
                raise LedgerValidationError(
                    f"sequence must be {expected_sequence}, received {entry.sequence}"
                )
            if entry.entry_id in known_ids:
                raise LedgerValidationError("entry identifier must be unique")
            if entry.posted_at < last_posted_at:
                raise LedgerValidationError("posting time cannot move backward")
            known_ids.add(entry.entry_id)
            last_posted_at = entry.posted_at
            expected_sequence += 1

        self._entries.extend(entries)
        self._entry_ids.update(entry.entry_id for entry in entries)


def replay(entries: tuple[LedgerEntry, ...] | list[LedgerEntry]) -> int:
    """Project current balance in cents by replaying entries in sequence order."""
    balance = 0
    for expected_sequence, entry in enumerate(entries, start=1):
        if entry.sequence != expected_sequence:
            raise LedgerValidationError("replay requires contiguous sequence order")
        direction = 1 if entry.entry_type is EntryType.CREDIT else -1
        balance += direction * entry.amount.cents
    return balance


def chapter_ledger() -> Ledger:
    """Build the fixed Chapter 3 teaching ledger."""
    ledger = Ledger()
    for entry in (
        LedgerEntry(
            "LE-0001",
            "HCCU-DEMO-001",
            Money(100_000),
            EntryType.CREDIT,
            "Opening ledger fact",
            1,
            100,
        ),
        LedgerEntry(
            "LE-0002",
            "HCCU-DEMO-001",
            Money(12_000),
            EntryType.DEBIT,
            "First debit fact",
            2,
            200,
        ),
        LedgerEntry(
            "LE-0003",
            "HCCU-DEMO-001",
            Money(5_525),
            EntryType.DEBIT,
            "Second debit fact",
            3,
            300,
        ),
    ):
        ledger.append(entry)
    return ledger


def format_money(cents: int, *, show_sign: bool = False) -> str:
    """Format exact cents without converting through floating point."""
    sign = "-" if cents < 0 else "+" if show_sign else ""
    magnitude = abs(cents)
    dollars, remainder = divmod(magnitude, 100)
    return f"{sign}${dollars:,}.{remainder:02d}"


def describe_ledger(ledger: Ledger) -> str:
    """Render a deterministic ledger timeline."""
    lines = ["Seq  Type      Amount"]
    for entry in ledger.entries:
        signed_cents = (
            entry.amount.cents
            if entry.entry_type is EntryType.CREDIT
            else -entry.amount.cents
        )
        lines.append(
            f"{entry.sequence:<5}{entry.entry_type.value:<10}"
            f"{format_money(signed_cents, show_sign=True):>10}"
        )
    return "\n".join(lines)


def describe_replay(ledger: Ledger) -> str:
    """Render each uncomplicated replay step and its running balance."""
    lines = ["Ledger replay"]
    balance = 0
    for entry in ledger.entries:
        signed_cents = (
            entry.amount.cents
            if entry.entry_type is EntryType.CREDIT
            else -entry.amount.cents
        )
        balance += signed_cents
        lines.append(
            f"{entry.sequence}. {entry.entry_type.value} "
            f"{format_money(signed_cents, show_sign=True)} "
            f"→ {format_money(balance)}"
        )
    lines.extend(("", "Final balance:", format_money(balance)))
    return "\n".join(lines)
