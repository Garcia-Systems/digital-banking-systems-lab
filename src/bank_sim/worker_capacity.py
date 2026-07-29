"""Deterministic worker pools for queued payment work.

Workers only decide when accepted work runs.  The callback remains responsible for
all financial rules, keeping capacity separate from the ledger and ACH domains.
"""

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass

from bank_sim.ledger import EntryType, Ledger, LedgerEntry, Money
from bank_sim.payment_queues import PaymentType, QueuedPayment
from bank_sim.scheduler import EventScheduler
from bank_sim.transfers import account_balance


@dataclass(frozen=True, slots=True)
class CapacityConfiguration:
    """Fixed worker-pool settings for one repeatable run."""

    worker_count: int
    processing_time: int = 2

    def __post_init__(self) -> None:
        if type(self.worker_count) is not int or self.worker_count <= 0:
            raise ValueError("worker count must be a positive integer")
        if type(self.processing_time) is not int or self.processing_time <= 0:
            raise ValueError("processing time must be a positive integer")


@dataclass(frozen=True, slots=True)
class WorkerStatistics:
    """Measurements for one worker at the end of a run."""

    worker_id: str
    payments_completed: int
    total_busy_time: int
    utilization_percentage: int


@dataclass(frozen=True, slots=True)
class CapacityEvent:
    """One observable arrival, assignment, or completion."""

    time: int
    action: str
    payment_id: str
    worker_id: str | None
    queue_depth: int


@dataclass(frozen=True, slots=True)
class ThroughputMetrics:
    """Operational results calculated with deterministic integer arithmetic."""

    total_completion_time: int
    average_wait: int
    maximum_wait: int
    average_queue_depth_hundredths: int
    maximum_queue_depth: int
    payments_processed: int
    throughput_hundredths: int


class PaymentWorker:
    """A single deterministic simulated worker."""

    def __init__(self, worker_id: str) -> None:
        self.worker_id = worker_id
        self.current_payment: QueuedPayment | None = None
        self.payments_completed = 0
        self.total_busy_time = 0

    @property
    def is_busy(self) -> bool:
        return self.current_payment is not None


class WorkerPool:
    """Assign FIFO payment work to the lowest-numbered idle worker."""

    def __init__(
        self, scheduler: EventScheduler, configuration: CapacityConfiguration
    ) -> None:
        self.scheduler = scheduler
        self.configuration = configuration
        self.workers = tuple(
            PaymentWorker(f"worker-{number}")
            for number in range(1, configuration.worker_count + 1)
        )
        self._waiting: deque[QueuedPayment] = deque()
        self._completed: list[QueuedPayment] = []
        self._events: list[CapacityEvent] = []
        self._arrival_order = 0
        self._maximum_depth = 0
        self._depth_area = 0
        self._depth_last_changed = scheduler.clock.time
        self._first_arrival: int | None = None

    @property
    def completed(self) -> tuple[QueuedPayment, ...]:
        return tuple(self._completed)

    @property
    def events(self) -> tuple[CapacityEvent, ...]:
        return tuple(self._events)

    def _record_depth_until_now(self) -> None:
        now = self.scheduler.clock.time
        self._depth_area += len(self._waiting) * (now - self._depth_last_changed)
        self._depth_last_changed = now

    def enqueue(
        self, payment_id: str, payment_type: PaymentType, work: Callable[[], None]
    ) -> QueuedPayment:
        """Add already accepted work and immediately dispatch when possible."""
        if not payment_id.strip():
            raise ValueError("payment identifier cannot be blank")
        if not isinstance(payment_type, PaymentType):
            raise TypeError("payment type must be a PaymentType")
        if not callable(work):
            raise TypeError("payment work must be callable")
        now = self.scheduler.clock.time
        if self._first_arrival is None:
            self._first_arrival = now
        self._record_depth_until_now()
        item = QueuedPayment(
            payment_id,
            payment_type,
            now,
            len(self._waiting) + 1,
            self._arrival_order,
            work,
        )
        self._arrival_order += 1
        self._waiting.append(item)
        self._maximum_depth = max(self._maximum_depth, len(self._waiting))
        self._events.append(
            CapacityEvent(now, "arrived", payment_id, None, len(self._waiting))
        )
        self._dispatch()
        return item

    def _dispatch(self) -> None:
        for worker in self.workers:
            if not self._waiting:
                break
            if worker.is_busy:
                continue
            self._record_depth_until_now()
            item = self._waiting.popleft()
            item.processing_started_at = self.scheduler.clock.time
            worker.current_payment = item
            self._events.append(
                CapacityEvent(
                    self.scheduler.clock.time,
                    "assigned",
                    item.payment_id,
                    worker.worker_id,
                    len(self._waiting),
                )
            )
            self.scheduler.schedule_after(
                self.configuration.processing_time,
                lambda worker=worker: self._complete(worker),
            )

    def _complete(self, worker: PaymentWorker) -> None:
        item = worker.current_payment
        if item is None:  # pragma: no cover - internal invariant
            raise RuntimeError("idle worker cannot complete a payment")
        item._work()
        item.completed_at = self.scheduler.clock.time
        self._completed.append(item)
        worker.current_payment = None
        worker.payments_completed += 1
        worker.total_busy_time += self.configuration.processing_time
        self._events.append(
            CapacityEvent(
                self.scheduler.clock.time,
                "completed",
                item.payment_id,
                worker.worker_id,
                len(self._waiting),
            )
        )
        self._dispatch()

    @property
    def metrics(self) -> ThroughputMetrics:
        end = max((item.completed_at or 0 for item in self._completed), default=0)
        start = self._first_arrival or 0
        elapsed = end - start
        waits = [item.wait_duration or 0 for item in self._completed]
        count = len(self._completed)
        return ThroughputMetrics(
            elapsed,
            sum(waits) // count if count else 0,
            max(waits, default=0),
            self._depth_area * 100 // elapsed if elapsed else 0,
            self._maximum_depth,
            count,
            count * 100 // elapsed if elapsed else 0,
        )

    @property
    def worker_statistics(self) -> tuple[WorkerStatistics, ...]:
        elapsed = self.metrics.total_completion_time
        return tuple(
            WorkerStatistics(
                worker.worker_id,
                worker.payments_completed,
                worker.total_busy_time,
                worker.total_busy_time * 100 // elapsed if elapsed else 0,
            )
            for worker in self.workers
        )


@dataclass(frozen=True, slots=True)
class CapacityScenario:
    pool: WorkerPool
    ledger: Ledger

    @property
    def ledger_effects(self) -> tuple[tuple[str, str, int], ...]:
        return tuple(
            (entry.entry_id, entry.entry_type.value, entry.amount.cents)
            for entry in self.ledger.entries[1:]
        )


WORKLOAD = tuple(
    (f"PAY-{number:02}", EntryType.DEBIT if number % 2 else EntryType.CREDIT, 100)
    for number in range(1, 13)
)


def run_worker_capacity(worker_count: int) -> CapacityScenario:
    """Run the Chapter 12 burst workload with a fixed worker count."""
    scheduler = EventScheduler()
    pool = WorkerPool(scheduler, CapacityConfiguration(worker_count))
    ledger = Ledger()
    ledger.append(
        LedgerEntry("OPEN", "A", Money(10_000), EntryType.CREDIT, "Open", 1, 0)
    )

    def arrival(
        payment_id: str, entry_type: EntryType, amount: int
    ) -> Callable[[], None]:
        def arrive() -> None:
            def post() -> None:
                ledger.append(
                    LedgerEntry(
                        payment_id,
                        "A",
                        Money(amount),
                        entry_type,
                        "Capacity workload",
                        len(ledger.entries) + 1,
                        scheduler.clock.time,
                    )
                )

            pool.enqueue(payment_id, PaymentType.ACH_TRANSFER, post)

        return arrive

    for index, payment in enumerate(WORKLOAD):
        scheduler.schedule_at(index // 2, arrival(*payment))
    scheduler.run()
    return CapacityScenario(pool, ledger)


def _depth(value: int) -> str:
    return f"{value // 100}.{value % 100:02}"


def describe_worker_capacity(worker_count: int = 1) -> str:
    scenario = run_worker_capacity(worker_count)
    pool = scenario.pool
    lines = [
        f"Worker capacity | {worker_count} worker(s) | identical 12-payment workload"
    ]
    for event in pool.events:
        worker = f" -> {event.worker_id}" if event.worker_id else ""
        lines.append(
            f"T+{event.time:02} {event.action.capitalize():<9} {event.payment_id}"
            f"{worker:<12} | queue depth {event.queue_depth}"
        )
    lines.append("Worker utilization")
    for stats in pool.worker_statistics:
        lines.append(
            f"{stats.worker_id}: completed {stats.payments_completed} | busy "
            f"{stats.total_busy_time} | utilization {stats.utilization_percentage}%"
        )
    lines.append(
        "Completion order: " + ", ".join(item.payment_id for item in pool.completed)
    )
    lines.append(
        f"Average queue depth: {_depth(pool.metrics.average_queue_depth_hundredths)}"
    )
    return "\n".join(lines)


def describe_capacity_comparison() -> str:
    scenarios = tuple(run_worker_capacity(count) for count in (1, 2, 4))
    lines = ["Worker capacity comparison | identical 12-payment workload"]
    for count, scenario in zip((1, 2, 4), scenarios, strict=True):
        metrics = scenario.pool.metrics
        utilization = (
            sum(s.utilization_percentage for s in scenario.pool.worker_statistics)
            // count
        )
        lines.append(
            f"{count} worker(s): completion T+{metrics.total_completion_time} | "
            f"average wait {metrics.average_wait} | "
            f"longest wait {metrics.maximum_wait} | "
            f"average depth {_depth(metrics.average_queue_depth_hundredths)} | "
            f"max depth {metrics.maximum_queue_depth} | utilization {utilization}% | "
            f"processed {metrics.payments_processed}"
        )
    identical = len({scenario.ledger_effects for scenario in scenarios}) == 1
    balances = {account_balance(scenario.ledger, "A") for scenario in scenarios}
    lines.append(f"Identical ledger history: {'yes' if identical else 'no'}")
    lines.append(f"Identical final balance: {'yes' if len(balances) == 1 else 'no'}")
    return "\n".join(lines)
