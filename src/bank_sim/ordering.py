"""Deterministic validation of payment events before business effects."""

from dataclasses import dataclass
from enum import Enum

from bank_sim.ledger import EntryType, Ledger, LedgerEntry, Money, format_money, replay


@dataclass(frozen=True, slots=True, order=True)
class EventSequence:
    """Position of an event in one payment's workflow."""

    value: int

    def __post_init__(self) -> None:
        if (
            not isinstance(self.value, int)
            or isinstance(self.value, bool)
            or self.value < 1
        ):
            raise ValueError("event sequence must be a positive integer")


@dataclass(frozen=True, slots=True, order=True)
class EventRevision:
    """Version used to prevent older facts from replacing newer state."""

    value: int

    def __post_init__(self) -> None:
        if (
            not isinstance(self.value, int)
            or isinstance(self.value, bool)
            or self.value < 1
        ):
            raise ValueError("event revision must be a positive integer")


class PaymentEventType(Enum):
    RECEIVED = "PaymentReceived"
    VALIDATED = "PaymentValidated"
    QUEUED = "PaymentQueued"
    COMPLETED = "PaymentCompleted"


_EVENT_FOR_SEQUENCE = {
    1: PaymentEventType.RECEIVED,
    2: PaymentEventType.VALIDATED,
    3: PaymentEventType.QUEUED,
    4: PaymentEventType.COMPLETED,
}


@dataclass(frozen=True, slots=True)
class PaymentEvent:
    """One scripted event with distinct creation and delivery positions."""

    payment_id: str
    event_id: str
    sequence: EventSequence
    revision: EventRevision
    event_type: PaymentEventType
    creation_order: int
    arrival_order: int
    amount: Money

    def __post_init__(self) -> None:
        if not self.payment_id.strip() or not self.event_id.strip():
            raise ValueError("payment and event identifiers cannot be blank")
        if self.creation_order < 1 or self.arrival_order < 1:
            raise ValueError("creation and arrival order must be positive")
        if self.sequence.value != self.revision.value:
            raise ValueError(
                "the teaching workflow uses matching sequence and revision"
            )
        if _EVENT_FOR_SEQUENCE.get(self.sequence.value) is not self.event_type:
            raise ValueError("event type does not match its workflow sequence")


class ProcessingDecision(Enum):
    PROCESSED = "processed"
    BUFFERED = "buffered: waiting for an earlier event"
    STALE = "rejected: stale revision"
    DUPLICATE = "rejected: event already processed"
    REJECTED = "rejected: conflicting buffered event"


@dataclass(frozen=True, slots=True)
class EventProcessingResult:
    event: PaymentEvent
    decision: ProcessingDecision
    expected_sequence: int


@dataclass(slots=True)
class _PaymentOrderingState:
    last_sequence: int = 0
    last_revision: int = 0
    final_state: str = "Not started"
    amount: Money | None = None


@dataclass(frozen=True, slots=True)
class OrderingStatistics:
    events_received: int
    events_processed: int
    stale_events: int
    out_of_order_events: int
    buffered_events: int
    rejected_events: int
    duplicate_events: int
    ledger_entries_created: int


class OrderedEventProcessor:
    """Buffer future events and apply only the next fresh workflow fact."""

    def __init__(self, ledger: Ledger) -> None:
        self.ledger = ledger
        self._states: dict[str, _PaymentOrderingState] = {}
        self._buffers: dict[str, dict[int, PaymentEvent]] = {}
        self._processed_event_ids: set[str] = set()
        self._results: list[EventProcessingResult] = []
        self._events_received = 0
        self._out_of_order = 0
        self._buffered = 0
        self._ledger_entries_created = 0

    def receive(self, event: PaymentEvent) -> tuple[EventProcessingResult, ...]:
        """Receive one delivery, recording its decision and any deterministic drain."""
        if not isinstance(event, PaymentEvent):
            raise TypeError("payment event is required")
        self._events_received += 1
        before = len(self._results)
        state = self._states.setdefault(event.payment_id, _PaymentOrderingState())
        expected = state.last_sequence + 1

        if event.event_id in self._processed_event_ids:
            self._record(event, ProcessingDecision.DUPLICATE, expected)
        elif (
            event.sequence.value <= state.last_sequence
            or event.revision.value <= state.last_revision
        ):
            self._record(event, ProcessingDecision.STALE, expected)
        elif event.sequence.value > expected:
            buffer = self._buffers.setdefault(event.payment_id, {})
            if event.sequence.value in buffer:
                self._record(event, ProcessingDecision.REJECTED, expected)
            else:
                buffer[event.sequence.value] = event
                self._out_of_order += 1
                self._buffered += 1
                self._record(event, ProcessingDecision.BUFFERED, expected)
        else:
            self._apply(event, state)
            self._drain(event.payment_id, state)
        return tuple(self._results[before:])

    def _record(
        self, event: PaymentEvent, decision: ProcessingDecision, expected: int
    ) -> None:
        self._results.append(EventProcessingResult(event, decision, expected))

    def _apply(self, event: PaymentEvent, state: _PaymentOrderingState) -> None:
        expected = state.last_sequence + 1
        if state.amount is not None and state.amount != event.amount:
            self._record(event, ProcessingDecision.REJECTED, expected)
            return
        state.amount = event.amount
        state.last_sequence = event.sequence.value
        state.last_revision = event.revision.value
        state.final_state = event.event_type.value
        self._processed_event_ids.add(event.event_id)
        if event.event_type is PaymentEventType.COMPLETED:
            self.ledger.append(
                LedgerEntry(
                    f"{event.payment_id}-SETTLEMENT",
                    "HCCU-DEMO-001",
                    event.amount,
                    EntryType.DEBIT,
                    "Ordered payment settlement",
                    len(self.ledger.entries) + 1,
                    event.arrival_order,
                )
            )
            self._ledger_entries_created += 1
        self._record(event, ProcessingDecision.PROCESSED, expected)

    def _drain(self, payment_id: str, state: _PaymentOrderingState) -> None:
        buffer = self._buffers.setdefault(payment_id, {})
        while state.last_sequence + 1 in buffer:
            event = buffer.pop(state.last_sequence + 1)
            self._apply(event, state)

    @property
    def results(self) -> tuple[EventProcessingResult, ...]:
        return tuple(self._results)

    def payment_state(self, payment_id: str) -> str:
        state = self._states.get(payment_id)
        return state.final_state if state is not None else "Not started"

    @property
    def statistics(self) -> OrderingStatistics:
        decisions = [result.decision for result in self._results]
        return OrderingStatistics(
            self._events_received,
            decisions.count(ProcessingDecision.PROCESSED),
            decisions.count(ProcessingDecision.STALE),
            self._out_of_order,
            self._buffered,
            decisions.count(ProcessingDecision.STALE)
            + decisions.count(ProcessingDecision.DUPLICATE)
            + decisions.count(ProcessingDecision.REJECTED),
            decisions.count(ProcessingDecision.DUPLICATE),
            self._ledger_entries_created,
        )


def payment_events(
    payment_id: str = "PAY-ORDER-001",
    amount_cents: int = 25_000,
    arrival: tuple[int, ...] = (1, 2, 3, 4),
) -> tuple[PaymentEvent, ...]:
    """Create one workflow in the requested delivery order."""
    return tuple(
        PaymentEvent(
            payment_id,
            f"{payment_id}-EVENT-{sequence}",
            EventSequence(sequence),
            EventRevision(sequence),
            _EVENT_FOR_SEQUENCE[sequence],
            sequence,
            arrival_order,
            Money(amount_cents),
        )
        for arrival_order, sequence in enumerate(arrival, start=1)
    )


def ordering_ledger() -> Ledger:
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
    return ledger


def process_events(events: tuple[PaymentEvent, ...]) -> OrderedEventProcessor:
    processor = OrderedEventProcessor(ordering_ledger())
    for event in events:
        processor.receive(event)
    return processor


def describe_ordering() -> str:
    processor = process_events(payment_events())
    lines = [
        "Payment event ordering | correct delivery",
        "Expected order: 1 -> 2 -> 3 -> 4",
    ]
    lines.extend(
        f"Sequence {item.event.sequence.value} | "
        f"{item.event.event_type.value} | {item.decision.value}"
        for item in processor.results
    )
    lines.extend(
        (
            f"Final payment state: {processor.payment_state('PAY-ORDER-001')}",
            f"Final balance: {format_money(replay(processor.ledger.entries))}",
            "Financial effect: exactly one settlement debit",
        )
    )
    return "\n".join(lines)


def out_of_order_events() -> tuple[PaymentEvent, ...]:
    events = list(payment_events(arrival=(3, 2, 1, 4)))
    completion = events[-1]
    events.append(
        PaymentEvent(
            completion.payment_id,
            completion.event_id,
            completion.sequence,
            completion.revision,
            completion.event_type,
            completion.creation_order,
            5,
            completion.amount,
        )
    )
    events.append(
        PaymentEvent(
            "PAY-ORDER-001",
            "PAY-ORDER-001-LATE-VALIDATED",
            EventSequence(2),
            EventRevision(2),
            PaymentEventType.VALIDATED,
            2,
            6,
            Money(25_000),
        )
    )
    return tuple(events)


def describe_out_of_order() -> str:
    events = out_of_order_events()
    processor = process_events(events)
    stats = processor.statistics
    lines = [
        "Payment event ordering | out-of-order delivery",
        "Expected order: 1 -> 2 -> 3 -> 4",
        "Arrival order: 3 -> 2 -> 1 -> 4 -> 4 (duplicate) -> 2 (late)",
        "Processing decisions:",
    ]
    lines.extend(
        f"Arrival {item.event.arrival_order} | "
        f"sequence {item.event.sequence.value} | {item.decision.value}"
        for item in processor.results
    )
    lines.extend(
        (
            f"Stale events detected: {stats.stale_events}",
            f"Out-of-order events detected: {stats.out_of_order_events}",
            f"Buffered events: {stats.buffered_events}",
            f"Duplicate events: {stats.duplicate_events}",
            f"Rejected events: {stats.rejected_events}",
            f"Final payment state: {processor.payment_state('PAY-ORDER-001')}",
            f"Final balance: {format_money(replay(processor.ledger.entries))}",
            "Ledger settlement entries: 1",
            "Financial outcome: correct; stale and duplicate events had no effect",
        )
    )
    return "\n".join(lines)
