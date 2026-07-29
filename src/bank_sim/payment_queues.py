"""Deterministic FIFO scheduling for already accepted ACH work.

The queue deliberately knows nothing about balances or ledger entries.  A caller
validates a payment first and supplies the domain callback that performs it.
"""

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum

from bank_sim.ledger import EntryType, Ledger, LedgerEntry, Money, format_money
from bank_sim.scheduler import EventScheduler
from bank_sim.transfers import account_balance

PaymentWork = Callable[[], None]


class PaymentType(Enum):
    """The payment workflows that Chapter 11 may schedule."""

    ACH_TRANSFER = "ACH transfer"
    ACH_RETURN = "ACH return"


@dataclass(slots=True)
class QueuedPayment:
    """One accepted payment and its deterministic queue timestamps."""

    payment_id: str
    payment_type: PaymentType
    queued_at: int
    queue_position: int
    arrival_order: int
    _work: PaymentWork = field(repr=False)
    processing_started_at: int | None = None
    completed_at: int | None = None

    @property
    def wait_duration(self) -> int | None:
        """Return integer time spent waiting, once processing has begun."""
        if self.processing_started_at is None:
            return None
        return self.processing_started_at - self.queued_at


@dataclass(frozen=True, slots=True)
class QueueStatistics:
    """An immutable snapshot of queue measurements."""

    total_processed: int
    average_wait: int
    longest_wait: int
    maximum_queue_depth: int
    remaining_queued_items: int


@dataclass(frozen=True, slots=True)
class QueueEvent:
    """One observable queue event used by the CLI and tests."""

    time: int
    action: str
    payment_id: str
    queue_size: int


class QueueWorker:
    """Process at most ``capacity`` FIFO items per simulated minute."""

    def __init__(self, queue: "PaymentQueue", capacity: int) -> None:
        if type(capacity) is not int or capacity <= 0:
            raise ValueError("worker capacity must be a positive integer")
        self.queue = queue
        self.capacity = capacity
        self._tick_scheduled = False

    def wake(self) -> None:
        """Ensure that the next one-minute processing tick is scheduled."""
        if self._tick_scheduled:
            return
        self._tick_scheduled = True
        self.queue.scheduler.schedule_after(1, self._process_tick)

    def _process_tick(self) -> None:
        self._tick_scheduled = False
        for _ in range(min(self.capacity, len(self.queue._waiting))):
            item = self.queue._waiting.popleft()
            now = self.queue.scheduler.clock.time
            item.processing_started_at = now
            self.queue._events.append(
                QueueEvent(now, "processing", item.payment_id, len(self.queue._waiting))
            )
            item._work()
            item.completed_at = now
            self.queue._completed.append(item)
            self.queue._events.append(
                QueueEvent(now, "completed", item.payment_id, len(self.queue._waiting))
            )
        if self.queue._waiting:
            self.wake()


class PaymentQueue:
    """A synchronous, in-memory FIFO queue driven by an event scheduler."""

    def __init__(self, scheduler: EventScheduler, capacity: int = 1) -> None:
        self.scheduler = scheduler
        self._waiting: deque[QueuedPayment] = deque()
        self._completed: list[QueuedPayment] = []
        self._events: list[QueueEvent] = []
        self._next_order = 0
        self._maximum_depth = 0
        self.worker = QueueWorker(self, capacity)

    @property
    def queued(self) -> tuple[QueuedPayment, ...]:
        return tuple(self._waiting)

    @property
    def completed(self) -> tuple[QueuedPayment, ...]:
        return tuple(self._completed)

    @property
    def events(self) -> tuple[QueueEvent, ...]:
        return tuple(self._events)

    def enqueue(
        self,
        payment_id: str,
        payment_type: PaymentType,
        work: PaymentWork,
        *,
        accepted: bool = True,
    ) -> QueuedPayment | None:
        """Append accepted work; rejected work is never represented in the queue."""
        if not accepted:
            return None
        if not isinstance(payment_id, str) or not payment_id.strip():
            raise ValueError("payment identifier cannot be blank")
        if not isinstance(payment_type, PaymentType):
            raise TypeError("payment type must be a PaymentType")
        if not callable(work):
            raise TypeError("payment work must be callable")
        item = QueuedPayment(
            payment_id,
            payment_type,
            self.scheduler.clock.time,
            len(self._waiting) + 1,
            self._next_order,
            work,
        )
        self._next_order += 1
        self._waiting.append(item)
        self._maximum_depth = max(self._maximum_depth, len(self._waiting))
        self._events.append(
            QueueEvent(
                self.scheduler.clock.time,
                "arrived",
                payment_id,
                len(self._waiting),
            )
        )
        self.worker.wake()
        return item

    def enqueue_ach_transfer(
        self, payment_id: str, work: PaymentWork, *, accepted: bool = True
    ) -> QueuedPayment | None:
        return self.enqueue(
            payment_id, PaymentType.ACH_TRANSFER, work, accepted=accepted
        )

    def enqueue_ach_return(
        self, payment_id: str, work: PaymentWork, *, accepted: bool = True
    ) -> QueuedPayment | None:
        return self.enqueue(payment_id, PaymentType.ACH_RETURN, work, accepted=accepted)

    @property
    def statistics(self) -> QueueStatistics:
        waits = [item.wait_duration for item in self._completed]
        completed_waits = [wait for wait in waits if wait is not None]
        total = len(completed_waits)
        return QueueStatistics(
            total,
            sum(completed_waits) // total if total else 0,
            max(completed_waits, default=0),
            self._maximum_depth,
            len(self._waiting),
        )


@dataclass(frozen=True, slots=True)
class CapacityResult:
    capacity: int
    final_balance: int
    ledger_effects: tuple[tuple[str, str, int], ...]
    final_completion: int
    queue_after_first_minute: int
    statistics: QueueStatistics


def run_capacity_scenario(capacity: int) -> tuple[PaymentQueue, Ledger]:
    """Run the same alternating transfer/return workload at one capacity."""
    scheduler = EventScheduler()
    queue = PaymentQueue(scheduler, capacity)
    ledger = Ledger()
    ledger.append(
        LedgerEntry("OPEN", "A", Money(100_000), EntryType.CREDIT, "Open", 1, 0)
    )

    def post(entry_id: str, entry_type: EntryType, amount: int) -> PaymentWork:
        def work() -> None:
            ledger.append(
                LedgerEntry(
                    entry_id,
                    "A",
                    Money(amount),
                    entry_type,
                    "Queued ACH work",
                    len(ledger.entries) + 1,
                    scheduler.clock.time,
                )
            )

        return work

    workload = (
        ("ACH-001", PaymentType.ACH_TRANSFER, EntryType.DEBIT, 10_000),
        ("ACH-002", PaymentType.ACH_TRANSFER, EntryType.DEBIT, 20_000),
        ("RETURN-001", PaymentType.ACH_RETURN, EntryType.CREDIT, 10_000),
        ("ACH-003", PaymentType.ACH_TRANSFER, EntryType.DEBIT, 5_000),
        ("RETURN-002", PaymentType.ACH_RETURN, EntryType.CREDIT, 20_000),
        ("RETURN-003", PaymentType.ACH_RETURN, EntryType.CREDIT, 5_000),
    )

    def arrival(
        payment_id: str,
        payment_type: PaymentType,
        entry_type: EntryType,
        amount: int,
    ) -> PaymentWork:
        def enqueue_work() -> None:
            queue.enqueue(
                payment_id,
                payment_type,
                post(payment_id, entry_type, amount),
            )

        return enqueue_work

    for index, (payment_id, payment_type, entry_type, amount) in enumerate(workload):
        scheduler.schedule_at(
            0 if index < 2 else 1,
            arrival(payment_id, payment_type, entry_type, amount),
        )
    scheduler.run()
    return queue, ledger


def capacity_result(capacity: int) -> CapacityResult:
    queue, ledger = run_capacity_scenario(capacity)
    effects = tuple(
        (entry.entry_id, entry.entry_type.value, entry.amount.cents)
        for entry in ledger.entries[1:]
    )
    return CapacityResult(
        capacity,
        account_balance(ledger, "A"),
        effects,
        queue.completed[-1].completed_at or 0,
        next(
            event.queue_size
            for event in reversed(queue.events)
            if event.time == 1 and event.action == "completed"
        ),
        queue.statistics,
    )


def describe_payment_queue() -> str:
    queue, ledger = run_capacity_scenario(2)
    lines = ["Payment queue | capacity 2 payments/minute"]
    for event in queue.events:
        lines.append(
            f"T+{event.time} {event.action.capitalize():<10} "
            f"{event.payment_id:<10} | queue size {event.queue_size}"
        )
    stats = queue.statistics
    lines.extend(
        (
            "Final statistics",
            f"Total processed: {stats.total_processed}",
            f"Average wait: {stats.average_wait} minute(s)",
            f"Longest wait: {stats.longest_wait} minute(s)",
            f"Maximum queue depth: {stats.maximum_queue_depth}",
            f"Remaining queued items: {stats.remaining_queued_items}",
            f"Final balance: {format_money(account_balance(ledger, 'A'))}",
        )
    )
    return "\n".join(lines)


def describe_payment_capacity() -> str:
    results = tuple(capacity_result(value) for value in (1, 2, 4))
    lines = ["Payment capacity comparison | identical workload"]
    for result in results:
        stats = result.statistics
        lines.append(
            f"Capacity {result.capacity}: completed T+{result.final_completion} | "
            f"average wait {stats.average_wait} | longest wait "
            f"{stats.longest_wait} | queued after T+1 "
            f"{result.queue_after_first_minute} | "
            f"max depth {stats.maximum_queue_depth} | "
            f"final balance {result.final_balance} cents"
        )
    identical = len({result.ledger_effects for result in results}) == 1
    lines.append(f"Identical ledger outcomes: {'yes' if identical else 'no'}")
    return "\n".join(lines)
