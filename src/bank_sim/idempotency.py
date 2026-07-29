"""Deterministic, in-memory idempotency before payment ledger effects."""

from dataclasses import dataclass
from enum import Enum

from bank_sim.duplicates import (
    DuplicatePaymentScenario,
    PaymentDelivery,
    client_retry_scenario,
    network_duplicate_scenario,
    process_naively,
    queue_replay_scenario,
)
from bank_sim.ledger import EntryType, Ledger, LedgerEntry, Money, format_money, replay


@dataclass(frozen=True, slots=True)
class IdempotencyKey:
    """Client-supplied identity for one intended business operation."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value.strip():
            raise ValueError("idempotency key cannot be blank")


class CompletionStatus(Enum):
    """Terminal state retained by the teaching store."""

    COMPLETED = "completed"


@dataclass(frozen=True, slots=True)
class PaymentProcessingResult:
    """Stable business result returned for original and duplicate deliveries."""

    original_request_id: str
    ledger_entry_id: str
    amount: Money
    processed_at: int


@dataclass(slots=True)
class IdempotencyRecord:
    """Completed operation and duplicate count remembered under one key."""

    key: IdempotencyKey
    original_request_id: str
    first_processed_at: int
    completion_status: CompletionStatus
    result: PaymentProcessingResult
    duplicate_delivery_count: int = 0


class IdempotencyConflictError(ValueError):
    """Raised when a key is reused for a different business request."""


class IdempotencyStore:
    """Process-local store with no expiration, persistence, or synchronization."""

    def __init__(self) -> None:
        self._records: dict[IdempotencyKey, IdempotencyRecord] = {}

    def get(self, key: IdempotencyKey) -> IdempotencyRecord | None:
        """Return the completed record for ``key``, if one exists."""
        return self._records.get(key)

    def remember(self, record: IdempotencyRecord) -> None:
        """Remember a newly completed operation exactly once."""
        if record.key in self._records:
            raise ValueError("idempotency record already exists")
        self._records[record.key] = record

    @property
    def records(self) -> tuple[IdempotencyRecord, ...]:
        """Expose records in deterministic insertion order."""
        return tuple(self._records.values())


@dataclass(frozen=True, slots=True)
class IdempotentAcknowledgement:
    """One response, including whether an earlier result was reused."""

    delivery: PaymentDelivery
    key: IdempotencyKey
    result: PaymentProcessingResult
    duplicate: bool


@dataclass(frozen=True, slots=True)
class IdempotencyStatistics:
    """Measurements separating transport deliveries from business effects."""

    total_requests_received: int
    unique_business_operations: int
    duplicate_deliveries: int
    duplicate_requests_prevented: int
    stored_idempotency_records: int
    ledger_entries_created: int


class IdempotentPaymentProcessor:
    """Resolve business identity before appending a financial ledger fact."""

    def __init__(self, ledger: Ledger, store: IdempotencyStore | None = None) -> None:
        self.ledger = ledger
        self.store = store if store is not None else IdempotencyStore()
        self._acknowledgements: list[IdempotentAcknowledgement] = []
        self._ledger_entries_created = 0

    def process(
        self, delivery: PaymentDelivery, key: IdempotencyKey
    ) -> IdempotentAcknowledgement:
        """Return the stored result or apply and remember one new debit."""
        if not isinstance(delivery, PaymentDelivery):
            raise TypeError("payment delivery is required")
        if not isinstance(key, IdempotencyKey):
            raise TypeError("idempotency key is required")

        record = self.store.get(key)
        if record is not None:
            result = record.result
            if (
                result.original_request_id != delivery.original_request_id
                or result.amount != delivery.amount
            ):
                raise IdempotencyConflictError(
                    "idempotency key cannot identify a different payment"
                )
            record.duplicate_delivery_count += 1
            acknowledgement = IdempotentAcknowledgement(delivery, key, result, True)
            self._acknowledgements.append(acknowledgement)
            return acknowledgement

        processed_at = delivery.arrived_at + 1
        entry_id = f"{delivery.original_request_id}-DEBIT"
        self.ledger.append(
            LedgerEntry(
                entry_id,
                "HCCU-DEMO-001",
                delivery.amount,
                EntryType.DEBIT,
                "Idempotently processed payment",
                len(self.ledger.entries) + 1,
                processed_at,
            )
        )
        result = PaymentProcessingResult(
            delivery.original_request_id, entry_id, delivery.amount, processed_at
        )
        self.store.remember(
            IdempotencyRecord(
                key,
                delivery.original_request_id,
                processed_at,
                CompletionStatus.COMPLETED,
                result,
            )
        )
        self._ledger_entries_created += 1
        acknowledgement = IdempotentAcknowledgement(delivery, key, result, False)
        self._acknowledgements.append(acknowledgement)
        return acknowledgement

    @property
    def acknowledgements(self) -> tuple[IdempotentAcknowledgement, ...]:
        return tuple(self._acknowledgements)

    @property
    def statistics(self) -> IdempotencyStatistics:
        duplicates = sum(item.duplicate for item in self._acknowledgements)
        return IdempotencyStatistics(
            len(self._acknowledgements),
            len(self.store.records),
            duplicates,
            duplicates,
            len(self.store.records),
            self._ledger_entries_created,
        )


@dataclass(frozen=True, slots=True)
class IdempotencyObservation:
    scenario: DuplicatePaymentScenario
    processor: IdempotentPaymentProcessor
    ledger: Ledger


def idempotency_key_for(delivery: PaymentDelivery) -> IdempotencyKey:
    """Derive the fixed key carried by every delivery of a scripted request."""
    return IdempotencyKey(f"IDEMPOTENCY-{delivery.original_request_id}")


def process_idempotently(
    scenario: DuplicatePaymentScenario, initial_balance_cents: int = 100_000
) -> IdempotencyObservation:
    """Run one Chapter 14 delivery script through Chapter 15 protection."""
    ledger = Ledger()
    ledger.append(
        LedgerEntry(
            "OPEN",
            "HCCU-DEMO-001",
            Money(initial_balance_cents),
            EntryType.CREDIT,
            "Opening balance",
            1,
            0,
        )
    )
    processor = IdempotentPaymentProcessor(ledger)
    for item in scenario.sequence.deliveries:
        processor.process(item, idempotency_key_for(item))
    return IdempotencyObservation(scenario, processor, ledger)


def describe_idempotency() -> str:
    """Show three deliveries producing one stored result and financial effect."""
    observation = process_idempotently(network_duplicate_scenario())
    processor = observation.processor
    lines = [
        "Idempotent payment processing | protection enabled",
        "Initial balance: $1,000.00",
    ]
    for acknowledgement in processor.acknowledgements:
        item = acknowledgement.delivery
        outcome = (
            "duplicate acknowledged; original result returned"
            if acknowledgement.duplicate
            else "original processed"
        )
        lines.append(
            f"Delivery {item.delivery_number}: {item.original_request_id} | "
            f"key {acknowledgement.key.value} | {outcome}"
        )
    stats = processor.statistics
    lines.extend(
        (
            f"Deliveries: {stats.total_requests_received}",
            "Original processing: 1",
            f"Duplicate acknowledgements: {stats.duplicate_deliveries}",
            f"Final balance: {format_money(replay(observation.ledger.entries))}",
            f"Ledger entry count: {stats.ledger_entries_created}",
            "Financial effect: exactly one debit of $250.00",
        )
    )
    return "\n".join(lines)


def describe_idempotency_comparison() -> str:
    """Contrast Chapter 14 naïve behavior with Chapter 15 for one workload."""
    scenario = network_duplicate_scenario()
    naive = process_naively(scenario)
    protected = process_idempotently(scenario)
    stats = protected.processor.statistics
    return "\n".join(
        (
            "Duplicate processing comparison | identical triple-delivery workload",
            "Workload: 3 deliveries | key IDEMPOTENCY-PAY-001 | payment $250.00",
            "Chapter 14 | naïve duplicate processing",
            f"Ledger debits: {naive.statistics.financial_operations_performed}",
            f"Final balance: {format_money(replay(naive.ledger.entries))} | INCORRECT",
            "Chapter 15 | idempotent processing",
            f"Ledger debits: {stats.ledger_entries_created}",
            f"Duplicate requests prevented: {stats.duplicate_requests_prevented}",
            "Final balance: "
            f"{format_money(replay(protected.ledger.entries))} | CORRECT",
            "Result: duplicate deliveries produced exactly one financial effect.",
        )
    )


def idempotency_scenarios() -> tuple[DuplicatePaymentScenario, ...]:
    """Return the unique, duplicate, triple, and mixed teaching workloads."""
    from bank_sim.duplicates import no_duplicates_scenario

    return (
        no_duplicates_scenario(),
        client_retry_scenario(),
        network_duplicate_scenario(),
        queue_replay_scenario(),
    )
