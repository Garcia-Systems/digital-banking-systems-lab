"""Deterministic isolation of permanently unprocessable payment work.

The dead-letter queue records operational facts, not financial history.  It never
replays an entry or invokes payment work; later operator recovery is deliberately
outside this chapter.
"""

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

from bank_sim.ledger import EntryType, Ledger, LedgerEntry, Money, replay
from bank_sim.payment_queues import PaymentQueue, PaymentType
from bank_sim.scheduler import EventScheduler


class DeadLetterReason(Enum):
    """The small, typed set of permanent isolation reasons."""

    RETRY_LIMIT_EXCEEDED = "Retry limit exceeded"
    INVALID_WORKFLOW_STATE = "Invalid workflow state"
    INVALID_PAYMENT = "Invalid payment"
    STALE_EVENT = "Stale event"


class WorkflowState(Enum):
    """Workflow state captured when work leaves active processing."""

    RECEIVED = "Received"
    VALIDATED = "Validated"
    PROCESSING = "Processing"
    COMPLETED = "Completed"
    FAILED = "Failed"


@dataclass(frozen=True, slots=True)
class DeadLetterEntry:
    """An immutable diagnostic snapshot of isolated payment work."""

    payment_id: str
    request_id: str
    reason: DeadLetterReason
    retry_count: int
    isolated_at: int
    original_state: WorkflowState
    diagnostic_message: str


class DeadLetterQueue:
    """Append-only, insertion-ordered storage for permanent failures."""

    def __init__(self) -> None:
        self._entries: list[DeadLetterEntry] = []
        self._payment_ids: set[str] = set()

    @property
    def entries(self) -> tuple[DeadLetterEntry, ...]:
        return tuple(self._entries)

    def isolate(self, entry: DeadLetterEntry) -> bool:
        """Store a payment once, preserving deterministic insertion order."""
        if not isinstance(entry, DeadLetterEntry):
            raise TypeError("dead-letter entry is required")
        if entry.payment_id in self._payment_ids:
            return False
        self._payment_ids.add(entry.payment_id)
        self._entries.append(entry)
        return True


@dataclass(frozen=True, slots=True)
class DeadLetterStatistics:
    items_processed: int
    successful_payments: int
    retry_attempts: int
    dlq_entries: int
    dlq_reasons: tuple[tuple[DeadLetterReason, int], ...]
    active_queue_size: int
    dlq_size: int


@dataclass(slots=True)
class DeadLetterPayment:
    payment_id: str
    request_id: str
    original_state: WorkflowState
    attempts: int = 0
    retry_count: int = 0
    completed: bool = False
    isolated: bool = False


@dataclass(frozen=True, slots=True)
class ProcessingResult:
    time: int
    payment_id: str
    outcome: str
    attempt_number: int


class DeadLetterProcessor:
    """Coordinate bounded retries and permanent isolation around payment work."""

    def __init__(
        self,
        scheduler: EventScheduler,
        queue: PaymentQueue,
        dead_letters: DeadLetterQueue,
        *,
        maximum_retries: int = 2,
        retry_delay: int = 2,
    ) -> None:
        if type(maximum_retries) is not int or maximum_retries < 0:
            raise ValueError("maximum retries must be a nonnegative integer")
        if type(retry_delay) is not int or retry_delay <= 0:
            raise ValueError("retry delay must be a positive integer")
        self.scheduler = scheduler
        self.queue = queue
        self.dead_letters = dead_letters
        self.maximum_retries = maximum_retries
        self.retry_delay = retry_delay
        self._payments: list[DeadLetterPayment] = []
        self._results: list[ProcessingResult] = []
        self._pending_retries = 0

    @property
    def payments(self) -> tuple[DeadLetterPayment, ...]:
        return tuple(self._payments)

    @property
    def results(self) -> tuple[ProcessingResult, ...]:
        return tuple(self._results)

    def submit(
        self,
        payment_id: str,
        request_id: str,
        work: Callable[[], None],
        *,
        transient_failures: tuple[str, ...] = (),
        permanent_reason: DeadLetterReason | None = None,
        original_state: WorkflowState = WorkflowState.VALIDATED,
        diagnostic_message: str | None = None,
    ) -> DeadLetterPayment:
        """Submit scripted work; permanent rules take precedence over retries."""
        if not payment_id.strip() or not request_id.strip():
            raise ValueError("payment and request identifiers cannot be blank")
        if not callable(work):
            raise TypeError("payment work must be callable")
        if any(not reason.strip() for reason in transient_failures):
            raise ValueError("transient failure messages cannot be blank")
        if permanent_reason is not None and not isinstance(
            permanent_reason, DeadLetterReason
        ):
            raise TypeError("permanent reason must be a DeadLetterReason")
        payment = DeadLetterPayment(payment_id, request_id, original_state)
        self._payments.append(payment)
        self._enqueue_attempt(
            payment,
            work,
            transient_failures,
            permanent_reason,
            diagnostic_message,
        )
        return payment

    def _enqueue_attempt(
        self,
        payment: DeadLetterPayment,
        work: Callable[[], None],
        failures: tuple[str, ...],
        permanent_reason: DeadLetterReason | None,
        diagnostic: str | None,
    ) -> None:
        if payment.isolated or payment.completed:
            return

        def attempt() -> None:
            if payment.isolated or payment.completed:
                return
            payment.attempts += 1
            if permanent_reason is not None:
                self._isolate(
                    payment,
                    permanent_reason,
                    diagnostic or permanent_reason.value,
                )
                return
            if payment.attempts <= len(failures):
                message = failures[payment.attempts - 1]
                if payment.retry_count >= self.maximum_retries:
                    self._isolate(
                        payment, DeadLetterReason.RETRY_LIMIT_EXCEEDED, message
                    )
                    return
                payment.retry_count += 1
                self._results.append(
                    ProcessingResult(
                        self.scheduler.clock.time,
                        payment.payment_id,
                        "retry scheduled",
                        payment.attempts,
                    )
                )
                self._pending_retries += 1

                def retry() -> None:
                    self._pending_retries -= 1
                    self._enqueue_attempt(
                        payment, work, failures, permanent_reason, diagnostic
                    )

                self.scheduler.schedule_after(self.retry_delay, retry)
                return
            work()
            payment.completed = True
            self._results.append(
                ProcessingResult(
                    self.scheduler.clock.time,
                    payment.payment_id,
                    "succeeded",
                    payment.attempts,
                )
            )

        self.queue.enqueue(payment.payment_id, PaymentType.ACH_TRANSFER, attempt)

    def _isolate(
        self,
        payment: DeadLetterPayment,
        reason: DeadLetterReason,
        diagnostic: str,
    ) -> None:
        entry = DeadLetterEntry(
            payment.payment_id,
            payment.request_id,
            reason,
            payment.retry_count,
            self.scheduler.clock.time,
            payment.original_state,
            diagnostic,
        )
        if self.dead_letters.isolate(entry):
            payment.isolated = True
            self._results.append(
                ProcessingResult(
                    self.scheduler.clock.time,
                    payment.payment_id,
                    "moved to DLQ",
                    payment.attempts,
                )
            )

    @property
    def statistics(self) -> DeadLetterStatistics:
        reasons = tuple(
            (reason, sum(entry.reason is reason for entry in self.dead_letters.entries))
            for reason in DeadLetterReason
            if any(entry.reason is reason for entry in self.dead_letters.entries)
        )
        return DeadLetterStatistics(
            len(self._payments),
            sum(payment.completed for payment in self._payments),
            sum(payment.retry_count for payment in self._payments),
            len(self.dead_letters.entries),
            reasons,
            len(self.queue.queued) + self._pending_retries,
            len(self.dead_letters.entries),
        )


@dataclass(frozen=True, slots=True)
class DeadLetterScenario:
    processor: DeadLetterProcessor
    dead_letters: DeadLetterQueue
    ledger: Ledger


def run_dead_letter_scenario() -> DeadLetterScenario:
    """Run successful, exhausted, invalid-workflow, and stale-event work."""
    scheduler = EventScheduler()
    queue = PaymentQueue(scheduler)
    dead_letters = DeadLetterQueue()
    processor = DeadLetterProcessor(scheduler, queue, dead_letters)
    ledger = Ledger()
    ledger.append(
        LedgerEntry(
            "OPEN", "HCCU-DEMO-001", Money(100_000), EntryType.CREDIT, "Open", 1, 0
        )
    )

    def post(payment_id: str, amount: int) -> Callable[[], None]:
        def work() -> None:
            ledger.append(
                LedgerEntry(
                    payment_id,
                    "HCCU-DEMO-001",
                    Money(amount),
                    EntryType.DEBIT,
                    "Dead-letter chapter payment",
                    len(ledger.entries) + 1,
                    scheduler.clock.time,
                )
            )

        return work

    processor.submit("PAY-SUCCESS-001", "REQ-001", post("PAY-SUCCESS-001", 10_000))
    processor.submit(
        "PAY-EXHAUSTED",
        "REQ-002",
        post("PAY-EXHAUSTED", 20_000),
        transient_failures=("processor unavailable",) * 3,
        original_state=WorkflowState.PROCESSING,
    )
    processor.submit(
        "PAY-INVALID-WORKFLOW",
        "REQ-003",
        post("PAY-INVALID-WORKFLOW", 30_000),
        permanent_reason=DeadLetterReason.INVALID_WORKFLOW_STATE,
        original_state=WorkflowState.RECEIVED,
        diagnostic_message="PaymentCompleted arrived before PaymentValidated",
    )
    processor.submit(
        "PAY-STALE-EVENT",
        "REQ-004",
        post("PAY-STALE-EVENT", 40_000),
        permanent_reason=DeadLetterReason.STALE_EVENT,
        original_state=WorkflowState.COMPLETED,
        diagnostic_message="Event revision is older than completed payment state",
    )
    processor.submit("PAY-SUCCESS-002", "REQ-005", post("PAY-SUCCESS-002", 5_000))
    scheduler.run()
    return DeadLetterScenario(processor, dead_letters, ledger)


def describe_dead_letters() -> str:
    scenario = run_dead_letter_scenario()
    stats = scenario.processor.statistics
    lines = ["Dead-letter processing | mixed deterministic workload"]
    lines.extend(
        f"T+{result.time} {result.payment_id} | {result.outcome} | "
        f"attempt {result.attempt_number}"
        for result in scenario.processor.results
    )
    lines.append("Final statistics")
    lines.extend(
        (
            f"Items processed: {stats.items_processed}",
            f"Successful payments: {stats.successful_payments}",
            f"Retry attempts: {stats.retry_attempts}",
            f"DLQ entries: {stats.dlq_entries}",
            "DLQ reasons: "
            + ", ".join(
                f"{reason.name}={count}" for reason, count in stats.dlq_reasons
            ),
            f"Active queue size: {stats.active_queue_size}",
            f"DLQ size: {stats.dlq_size}",
            f"Final balance: {replay(scenario.ledger.entries)} cents",
        )
    )
    return "\n".join(lines)


def describe_dead_letter_report() -> str:
    entries = run_dead_letter_scenario().dead_letters.entries
    lines = ["Dead-letter queue report | insertion order"]
    lines.extend(
        f"{entry.payment_id} | {entry.reason.name} | retries {entry.retry_count} | "
        f"state {entry.original_state.value} | isolated T+{entry.isolated_at}"
        for entry in entries
    )
    lines.append(f"DLQ size: {len(entries)}")
    return "\n".join(lines)
