"""Atomic internal transfers represented by coordinated immutable entries."""

from dataclasses import dataclass
from enum import Enum

from bank_sim.ledger import EntryType, Ledger, LedgerEntry, Money, format_money


class TransferValidationError(ValueError):
    """Raised when a transfer request violates an input invariant."""


class TransferStatus(Enum):
    """The explicit states in the internal-transfer workflow."""

    RECEIVED = "Received"
    POSTED = "Posted"
    REJECTED = "Rejected"


@dataclass(frozen=True, slots=True)
class TransferRequest:
    """A request to transfer positive integer cents between distinct accounts."""

    transfer_id: str
    source_account_id: str
    destination_account_id: str
    amount_cents: int
    description: str

    def __post_init__(self) -> None:
        for field_name in (
            "transfer_id",
            "source_account_id",
            "destination_account_id",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                label = field_name.replace("_id", " identifier").replace("_", " ")
                raise TransferValidationError(f"{label} cannot be blank")
        if self.source_account_id == self.destination_account_id:
            raise TransferValidationError(
                "source and destination accounts must be different"
            )
        if isinstance(self.amount_cents, bool) or not isinstance(
            self.amount_cents, int
        ):
            raise TransferValidationError("transfer amount must be integer cents")
        if self.amount_cents <= 0:
            raise TransferValidationError("transfer amount must be greater than zero")
        if not isinstance(self.description, str):
            raise TransferValidationError("description must be text")


@dataclass(frozen=True, slots=True)
class Transfer:
    """The workflow decision, separate from authoritative ledger history."""

    transfer_id: str
    source_account_id: str
    destination_account_id: str
    amount_cents: int
    description: str
    status: TransferStatus
    rejection_reason: str | None = None


@dataclass(frozen=True, slots=True)
class TransferResult:
    """A transfer decision and the paired entries created by that decision."""

    transfer: Transfer
    ledger_entries: tuple[LedgerEntry, ...]


INSUFFICIENT_FUNDS_REASON = "Insufficient available funds"


def account_balance(ledger: Ledger, account_id: str) -> int:
    """Replay one account from the shared ledger's canonical history."""
    balance = 0
    for entry in ledger.entries:
        if entry.account_id == account_id:
            direction = 1 if entry.entry_type is EntryType.CREDIT else -1
            balance += direction * entry.amount.cents
    return balance


def process_transfer(ledger: Ledger, request: TransferRequest) -> TransferResult:
    """Reject a request or atomically append its debit and credit entries."""
    if not isinstance(ledger, Ledger):
        raise TransferValidationError("transfer processing requires a Ledger")
    if not isinstance(request, TransferRequest):
        raise TransferValidationError("transfer processing requires a TransferRequest")

    if request.amount_cents > account_balance(ledger, request.source_account_id):
        transfer = Transfer(
            request.transfer_id,
            request.source_account_id,
            request.destination_account_id,
            request.amount_cents,
            request.description,
            TransferStatus.REJECTED,
            INSUFFICIENT_FUNDS_REASON,
        )
        return TransferResult(transfer, ())

    first_sequence = len(ledger.entries) + 1
    entries = (
        LedgerEntry(
            f"{request.transfer_id}-DEBIT",
            request.source_account_id,
            Money(request.amount_cents),
            EntryType.DEBIT,
            request.description or "Internal transfer",
            first_sequence,
            first_sequence,
        ),
        LedgerEntry(
            f"{request.transfer_id}-CREDIT",
            request.destination_account_id,
            Money(request.amount_cents),
            EntryType.CREDIT,
            request.description or "Internal transfer",
            first_sequence + 1,
            first_sequence + 1,
        ),
    )
    ledger.append_batch(entries)
    transfer = Transfer(
        request.transfer_id,
        request.source_account_id,
        request.destination_account_id,
        request.amount_cents,
        request.description,
        TransferStatus.POSTED,
    )
    return TransferResult(transfer, entries)


def _scenario_ledger(source_cents: int, destination_cents: int = 25_000) -> Ledger:
    ledger = Ledger()
    ledger.append_batch(
        (
            LedgerEntry(
                "SOURCE-OPEN",
                "ACCOUNT-SOURCE",
                Money(source_cents),
                EntryType.CREDIT,
                "Opening balance",
                1,
                1,
            ),
            LedgerEntry(
                "DESTINATION-OPEN",
                "ACCOUNT-DESTINATION",
                Money(destination_cents),
                EntryType.CREDIT,
                "Opening balance",
                2,
                2,
            ),
        )
    )
    return ledger


def describe_transfer() -> str:
    """Render the fixed successful transfer from request through both replays."""
    ledger = _scenario_ledger(100_000)
    request = TransferRequest(
        "TRF-0001",
        "ACCOUNT-SOURCE",
        "ACCOUNT-DESTINATION",
        15_000,
        "Internal transfer",
    )
    result = process_transfer(ledger, request)
    debit, credit = result.ledger_entries
    return "\n".join(
        (
            f"Request: {request.transfer_id} | {request.source_account_id} → "
            f"{request.destination_account_id} | {format_money(request.amount_cents)}",
            "Validation: Request valid; available funds sufficient",
            f"Status: {TransferStatus.RECEIVED.value} → {result.transfer.status.value}",
            f"Debit entry: {debit.entry_id} | {debit.account_id} | "
            f"{format_money(debit.amount.cents)}",
            f"Credit entry: {credit.entry_id} | {credit.account_id} | "
            f"{format_money(credit.amount.cents)}",
            "Replay: both account histories",
            "Source balance: "
            f"{format_money(account_balance(ledger, 'ACCOUNT-SOURCE'))}",
            "Destination balance: "
            f"{format_money(account_balance(ledger, 'ACCOUNT-DESTINATION'))}",
        )
    )


def describe_transfers() -> str:
    """Render successful, insufficient-funds, and invalid transfer scenarios."""
    success = describe_transfer()
    ledger = _scenario_ledger(5_000)
    insufficient = TransferRequest(
        "TRF-0002", "ACCOUNT-SOURCE", "ACCOUNT-DESTINATION", 10_000, "Transfer"
    )
    before = len(ledger.entries)
    rejected = process_transfer(ledger, insufficient)
    try:
        TransferRequest(
            "TRF-0003", "ACCOUNT-SOURCE", "ACCOUNT-SOURCE", 1_000, "Transfer"
        )
    except TransferValidationError as error:
        invalid_reason = str(error)
    return "\n\n".join(
        (
            "Successful transfer\n" + success,
            "Insufficient-funds transfer\n"
            f"Request: {insufficient.transfer_id} | "
            f"{format_money(insufficient.amount_cents)}\n"
            f"Status: Received → {rejected.transfer.status.value}\n"
            f"Reason: {rejected.transfer.rejection_reason}\n"
            f"Ledger entries appended: {len(ledger.entries) - before}",
            "Same-account transfer\n"
            "Request: TRF-0003 | ACCOUNT-SOURCE → ACCOUNT-SOURCE\n"
            "Status: Received → Rejected\n"
            f"Reason: {invalid_reason}\nLedger entries appended: 0",
        )
    )
