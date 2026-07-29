"""Deterministic retries for transiently failing queued payment work.

The retry scheduler controls *when* an accepted callback is attempted.  It does not
own payment validation or ledger rules, and it calls the financial callback only
after the scenario's explicit failure script has been consumed.
"""

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

from bank_sim.ledger import EntryType, Ledger, LedgerEntry, Money
from bank_sim.payment_queues import PaymentQueue, PaymentType
from bank_sim.scheduler import EventScheduler


class TransientFailure(RuntimeError):
    """An operational failure that may be safe to retry."""


class FinalOutcome(Enum):
    """The terminal result of retry processing."""

    SUCCEEDED = "succeeded"
    PERMANENTLY_FAILED = "permanently failed"


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """A fixed retry limit and simulated delay."""

    maximum_retries: int = 3
    retry_delay: int = 2

    def __post_init__(self) -> None:
        if type(self.maximum_retries) is not int or self.maximum_retries < 0:
            raise ValueError("maximum retries must be a nonnegative integer")
        if type(self.retry_delay) is not int or self.retry_delay <= 0:
            raise ValueError("retry delay must be a positive integer")


@dataclass(frozen=True, slots=True)
class RetryAttempt:
    """One completed attempt and, when applicable, its next retry time."""

    payment_id: str
    attempt_number: int
    attempted_at: int
    succeeded: bool
    retry_reason: str | None
    scheduled_retry_time: int | None
    remaining_retries: int


@dataclass(frozen=True, slots=True)
class RetryEvent:
    """One stable event exposed by retry timelines."""

    time: int
    action: str
    payment_id: str
    attempt_number: int | None = None


@dataclass(slots=True)
class RetryPayment:
    """An accepted payment with an explicit sequence of transient failures."""

    payment_id: str
    failure_script: tuple[str, ...]
    attempts: int = 0
    final_outcome: FinalOutcome | None = None


@dataclass(frozen=True, slots=True)
class RetryStatistics:
    """Deterministic retry measurements; averages are stored as hundredths."""

    total_payments: int
    total_retries: int
    successful_recoveries: int
    permanent_failures: int
    average_attempts_hundredths: int
    maximum_attempts: int
    retry_queue_size: int


class RetryScheduler:
    """Submit attempts to a payment queue and schedule fixed-delay retries."""

    def __init__(
        self,
        scheduler: EventScheduler,
        queue: PaymentQueue,
        policy: RetryPolicy = RetryPolicy(),
    ) -> None:
        self.scheduler = scheduler
        self.queue = queue
        self.policy = policy
        self._payments: list[RetryPayment] = []
        self._attempts: list[RetryAttempt] = []
        self._events: list[RetryEvent] = []
        self._pending_retries = 0

    @property
    def payments(self) -> tuple[RetryPayment, ...]:
        return tuple(self._payments)

    @property
    def attempts(self) -> tuple[RetryAttempt, ...]:
        return tuple(self._attempts)

    @property
    def events(self) -> tuple[RetryEvent, ...]:
        return tuple(self._events)

    def submit(
        self, payment_id: str, failure_script: tuple[str, ...], work: Callable[[], None]
    ) -> RetryPayment:
        """Queue a payment whose first scripted reasons cause transient failures."""
        if not payment_id.strip():
            raise ValueError("payment identifier cannot be blank")
        if not callable(work):
            raise TypeError("payment work must be callable")
        if any(not reason.strip() for reason in failure_script):
            raise ValueError("failure reasons cannot be blank")
        payment = RetryPayment(payment_id, failure_script)
        self._payments.append(payment)
        self._events.append(RetryEvent(self.scheduler.clock.time, "queued", payment_id))
        self._enqueue_attempt(payment, work)
        return payment

    def _enqueue_attempt(self, payment: RetryPayment, work: Callable[[], None]) -> None:
        def attempt() -> None:
            payment.attempts += 1
            number = payment.attempts
            if number <= len(payment.failure_script):
                reason = payment.failure_script[number - 1]
                retries_used = number - 1
                remaining = self.policy.maximum_retries - retries_used
                if remaining > 0:
                    retry_time = self.scheduler.clock.time + self.policy.retry_delay
                    self._attempts.append(
                        RetryAttempt(
                            payment.payment_id,
                            number,
                            self.scheduler.clock.time,
                            False,
                            reason,
                            retry_time,
                            remaining,
                        )
                    )
                    self._events.append(
                        RetryEvent(
                            self.scheduler.clock.time,
                            "failed",
                            payment.payment_id,
                            number,
                        )
                    )
                    self._pending_retries += 1

                    def retry() -> None:
                        self._pending_retries -= 1
                        self._events.append(
                            RetryEvent(
                                self.scheduler.clock.time,
                                "retry scheduled",
                                payment.payment_id,
                                number + 1,
                            )
                        )
                        self._enqueue_attempt(payment, work)

                    self.scheduler.schedule_at(retry_time, retry)
                    return
                payment.final_outcome = FinalOutcome.PERMANENTLY_FAILED
                self._attempts.append(
                    RetryAttempt(
                        payment.payment_id,
                        number,
                        self.scheduler.clock.time,
                        False,
                        reason,
                        None,
                        0,
                    )
                )
                self._events.append(
                    RetryEvent(
                        self.scheduler.clock.time,
                        "permanently failed",
                        payment.payment_id,
                        number,
                    )
                )
                return

            work()
            payment.final_outcome = FinalOutcome.SUCCEEDED
            self._attempts.append(
                RetryAttempt(
                    payment.payment_id,
                    number,
                    self.scheduler.clock.time,
                    True,
                    None,
                    None,
                    self.policy.maximum_retries - (number - 1),
                )
            )
            self._events.append(
                RetryEvent(
                    self.scheduler.clock.time, "succeeded", payment.payment_id, number
                )
            )

        self.queue.enqueue(payment.payment_id, PaymentType.ACH_TRANSFER, attempt)

    @property
    def statistics(self) -> RetryStatistics:
        count = len(self._payments)
        total_attempts = sum(payment.attempts for payment in self._payments)
        return RetryStatistics(
            count,
            sum(max(payment.attempts - 1, 0) for payment in self._payments),
            sum(
                payment.attempts > 1 and payment.final_outcome is FinalOutcome.SUCCEEDED
                for payment in self._payments
            ),
            sum(
                payment.final_outcome is FinalOutcome.PERMANENTLY_FAILED
                for payment in self._payments
            ),
            total_attempts * 100 // count if count else 0,
            max((payment.attempts for payment in self._payments), default=0),
            self._pending_retries,
        )


@dataclass(frozen=True, slots=True)
class RetryScenario:
    retries: RetryScheduler
    ledger: Ledger


RETRY_WORKLOAD = (
    ("PAY-IMMEDIATE", ()),
    ("PAY-ONE-RETRY", ("processor unavailable",)),
    ("PAY-MULTIPLE", ("connection reset", "processor unavailable")),
    ("PAY-EXHAUSTED", ("service unavailable",) * 4),
)


def run_retry_scenario() -> RetryScenario:
    """Run the Chapter 13 mixed workload with scripted failures."""
    scheduler = EventScheduler()
    queue = PaymentQueue(scheduler)
    retries = RetryScheduler(scheduler, queue)
    ledger = Ledger()
    ledger.append(
        LedgerEntry("OPEN", "A", Money(10_000), EntryType.CREDIT, "Open", 1, 0)
    )

    def post(payment_id: str) -> Callable[[], None]:
        def work() -> None:
            ledger.append(
                LedgerEntry(
                    payment_id,
                    "A",
                    Money(100),
                    EntryType.DEBIT,
                    "Retried payment",
                    len(ledger.entries) + 1,
                    scheduler.clock.time,
                )
            )

        return work

    for payment_id, script in RETRY_WORKLOAD:
        retries.submit(payment_id, script, post(payment_id))
    scheduler.run()
    return RetryScenario(retries, ledger)


def describe_retries() -> str:
    scenario = run_retry_scenario()
    lines = ["Deterministic payment retries", "Payments"]
    for payment in scenario.retries.payments:
        failures = sum(
            not item.succeeded
            for item in scenario.retries.attempts
            if item.payment_id == payment.payment_id
        )
        summary = f"{payment.payment_id}: attempts {payment.attempts}"
        lines.append(
            f"{summary} | failures {failures} | retries "
            f"{max(payment.attempts - 1, 0)} | {payment.final_outcome.value}"
        )
    stats = scenario.retries.statistics
    lines.extend(
        (
            "Retry statistics",
            f"Total retries: {stats.total_retries}",
            f"Successful recoveries: {stats.successful_recoveries}",
            f"Permanent failures: {stats.permanent_failures}",
            "Average attempts: "
            f"{stats.average_attempts_hundredths // 100}."
            f"{stats.average_attempts_hundredths % 100:02}",
            f"Maximum attempts: {stats.maximum_attempts}",
            f"Retry queue size: {stats.retry_queue_size}",
        )
    )
    return "\n".join(lines)


def describe_retry_timeline() -> str:
    scenario = run_retry_scenario()
    lines = ["Deterministic retry timeline"]
    for event in scenario.retries.events:
        attempt = f" | attempt {event.attempt_number}" if event.attempt_number else ""
        lines.append(f"T+{event.time} {event.payment_id} | {event.action}{attempt}")
    return "\n".join(lines)
