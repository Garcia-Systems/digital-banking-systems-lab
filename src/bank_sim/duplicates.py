"""Scripted duplicate delivery observed without duplicate prevention.

This module deliberately processes every delivery.  It is an isolated educational
demonstration of the incorrect financial result that Chapter 15 will prevent.
"""

from dataclasses import dataclass
from enum import Enum

from bank_sim.ledger import EntryType, Ledger, LedgerEntry, Money, format_money, replay


class ProcessingResult(Enum):
    """The result recorded for one received delivery."""

    PROCESSED = "Payment processed"


@dataclass(frozen=True, slots=True)
class PaymentDelivery:
    """One scripted arrival of an original payment request."""

    original_request_id: str
    amount: Money
    delivery_number: int
    arrived_at: int
    delivery_order: int

    def __post_init__(self) -> None:
        if not self.original_request_id.strip():
            raise ValueError("original request identifier cannot be blank")
        if type(self.delivery_number) is not int or self.delivery_number <= 0:
            raise ValueError("delivery number must be a positive integer")
        if type(self.arrived_at) is not int or self.arrived_at < 0:
            raise ValueError("arrival time must be a nonnegative integer")
        if type(self.delivery_order) is not int or self.delivery_order <= 0:
            raise ValueError("delivery order must be a positive integer")


@dataclass(frozen=True, slots=True)
class DeliveryAttempt:
    """The observable processing result for a received delivery."""

    delivery: PaymentDelivery
    processed_at: int
    result: ProcessingResult
    ledger_entry_id: str


@dataclass(frozen=True, slots=True)
class DeliverySequence:
    """A deterministic, explicitly ordered delivery script."""

    deliveries: tuple[PaymentDelivery, ...]

    def __post_init__(self) -> None:
        orders = tuple(item.delivery_order for item in self.deliveries)
        if orders != tuple(range(1, len(self.deliveries) + 1)):
            raise ValueError("deliveries must have contiguous delivery order")
        if any(
            current.arrived_at > following.arrived_at
            for current, following in zip(self.deliveries, self.deliveries[1:])
        ):
            raise ValueError("delivery arrival times cannot move backward")


@dataclass(frozen=True, slots=True)
class DuplicatePaymentScenario:
    """A named reason and script for receiving payment requests repeatedly."""

    name: str
    cause: str
    sequence: DeliverySequence


@dataclass(frozen=True, slots=True)
class DuplicateStatistics:
    """Integer measurements of deliveries and their incorrect financial effects."""

    deliveries_received: int
    unique_payment_identifiers: int
    duplicate_deliveries: int
    financial_operations_performed: int
    duplicate_financial_operations: int
    duplicate_percentage_hundredths: int


@dataclass(frozen=True, slots=True)
class DuplicateObservation:
    """The ledger and observations produced by deliberately naïve processing."""

    scenario: DuplicatePaymentScenario
    attempts: tuple[DeliveryAttempt, ...]
    ledger: Ledger
    statistics: DuplicateStatistics


def delivery(
    request_id: str, amount_cents: int, number: int, arrived_at: int, order: int
) -> PaymentDelivery:
    """Construct one concise item for a scenario script."""
    return PaymentDelivery(request_id, Money(amount_cents), number, arrived_at, order)


def no_duplicates_scenario() -> DuplicatePaymentScenario:
    return DuplicatePaymentScenario(
        "No duplicates",
        "Each request is delivered once.",
        DeliverySequence((delivery("PAY-001", 25_000, 1, 0, 1),)),
    )


def client_retry_scenario() -> DuplicatePaymentScenario:
    return DuplicatePaymentScenario(
        "Client retry",
        "The client never receives confirmation and sends the identical request again.",
        DeliverySequence(
            (
                delivery("PAY-001", 25_000, 1, 0, 1),
                delivery("PAY-001", 25_000, 2, 3, 2),
            )
        ),
    )


def network_duplicate_scenario() -> DuplicatePaymentScenario:
    return DuplicatePaymentScenario(
        "Network duplicate",
        "The simulated network delivers the same request three times.",
        DeliverySequence(
            tuple(
                delivery("PAY-001", 25_000, number, number - 1, number)
                for number in range(1, 4)
            )
        ),
    )


def queue_replay_scenario() -> DuplicatePaymentScenario:
    return DuplicatePaymentScenario(
        "Queue replay",
        "The scenario accidentally delivers queued payment PAY-002 twice.",
        DeliverySequence(
            (
                delivery("PAY-001", 25_000, 1, 0, 1),
                delivery("PAY-002", 10_000, 1, 2, 2),
                delivery("PAY-002", 10_000, 2, 4, 3),
                delivery("PAY-003", 5_000, 1, 6, 4),
            )
        ),
    )


def duplicate_scenarios() -> tuple[DuplicatePaymentScenario, ...]:
    """Return the fixed Chapter 14 no-, one-, multiple-, and mixed-duplicate scripts."""
    return (
        no_duplicates_scenario(),
        client_retry_scenario(),
        network_duplicate_scenario(),
        queue_replay_scenario(),
    )


def process_naively(
    scenario: DuplicatePaymentScenario, initial_balance_cents: int = 100_000
) -> DuplicateObservation:
    """Process every delivery independently, intentionally creating duplicates."""
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
    attempts: list[DeliveryAttempt] = []
    for item in scenario.sequence.deliveries:
        processed_at = item.arrived_at + 1
        entry_id = f"{item.original_request_id}-DELIVERY-{item.delivery_number}"
        ledger.append(
            LedgerEntry(
                entry_id,
                "HCCU-DEMO-001",
                item.amount,
                EntryType.DEBIT,
                "Naively processed payment delivery",
                len(ledger.entries) + 1,
                processed_at,
            )
        )
        attempts.append(
            DeliveryAttempt(item, processed_at, ProcessingResult.PROCESSED, entry_id)
        )

    deliveries = len(attempts)
    unique = len({attempt.delivery.original_request_id for attempt in attempts})
    duplicates = deliveries - unique
    stats = DuplicateStatistics(
        deliveries,
        unique,
        duplicates,
        deliveries,
        duplicates,
        duplicates * 10_000 // deliveries if deliveries else 0,
    )
    return DuplicateObservation(scenario, tuple(attempts), ledger, stats)


def describe_duplicates() -> str:
    """Show every scripted workload and expose naïve duplicate ledger effects."""
    lines = [
        "Duplicate payment requests | observation mode",
        "WARNING: naïve processing below is intentionally financially incorrect.",
    ]
    for scenario in duplicate_scenarios():
        observation = process_naively(scenario)
        stats = observation.statistics
        lines.extend(("", scenario.name, scenario.cause))
        for attempt in observation.attempts:
            item = attempt.delivery
            lines.append(
                f"Delivery {item.delivery_order}: {item.original_request_id} "
                f"#{item.delivery_number} at T+{item.arrived_at} | "
                f"debit {format_money(item.amount.cents)} | processed"
            )
        lines.extend(
            (
                f"Deliveries received: {stats.deliveries_received}",
                f"Unique business operations: {stats.unique_payment_identifiers}",
                f"Duplicate requests: {stats.duplicate_deliveries}",
                "Financial operations performed: "
                f"{stats.financial_operations_performed}",
                "Duplicate financial operations: "
                f"{stats.duplicate_financial_operations}",
                "Duplicate percentage: "
                f"{stats.duplicate_percentage_hundredths // 100}."
                f"{stats.duplicate_percentage_hundredths % 100:02}%",
                f"Final balance: {format_money(replay(observation.ledger.entries))}",
            )
        )
    lines.extend(
        (
            "",
            "Every delivery was processed; no duplicate was suppressed.",
            "Chapter 15 will introduce idempotent processing to prevent the extra "
            "financial effect.",
        )
    )
    return "\n".join(lines)


def describe_duplicate_timeline() -> str:
    """Render the canonical $1,000 minus two deliveries of one $250 request."""
    observation = process_naively(client_retry_scenario())
    lines = [
        "Duplicate payment timeline | naïve processing",
        "Initial balance: $1,000.00",
    ]
    for attempt in observation.attempts:
        item = attempt.delivery
        label = (
            "Payment request received"
            if item.delivery_number == 1
            else "Duplicate request received"
        )
        processed = (
            "Payment processed"
            if item.delivery_number == 1
            else "Payment processed again"
        )
        lines.extend(
            (
                f"T+{item.arrived_at} {label} | {item.original_request_id}",
                f"T+{attempt.processed_at} {processed} | debit $250.00",
            )
        )
    lines.extend(
        (
            "Single-delivery balance would be: $750.00",
            "Naïve duplicate-delivery balance: "
            f"{format_money(replay(observation.ledger.entries))}",
            "INCORRECT: the customer intended one payment, but two financial effects "
            "occurred.",
            "Chapter 15 will eliminate the second financial effect with idempotent "
            "processing.",
        )
    )
    return "\n".join(lines)
