"""Chapter 18's deterministic end-to-end banking operations laboratory.

The capstone composes the existing clock, queue, retry/DLQ, idempotency, ordering,
ledger, settlement, and reconciliation components.  It deliberately adds no new
infrastructure boundary: this module only scripts and reports one integrated run.
"""

from dataclasses import dataclass, replace

from bank_sim.dead_letters import (
    DeadLetterProcessor,
    DeadLetterQueue,
    WorkflowState,
)
from bank_sim.duplicates import PaymentDelivery
from bank_sim.idempotency import IdempotencyKey, IdempotentPaymentProcessor
from bank_sim.ledger import EntryType, Ledger, LedgerEntry, Money, format_money, replay
from bank_sim.ordering import OrderedEventProcessor, out_of_order_events
from bank_sim.payment_queues import PaymentQueue
from bank_sim.scheduler import EventScheduler
from bank_sim.settlement import (
    ExternalSettlementRecord,
    ExternalSettlementReport,
    ReconciliationReport,
    SettlementDirection,
    SettlementRecord,
    reconcile,
)


@dataclass(frozen=True, slots=True)
class LaboratoryStatistics:
    """Stable integer measurements from the complete operational run."""

    payments_received: int
    successful_payments: int
    retries: int
    duplicate_deliveries: int
    duplicate_requests_prevented: int
    out_of_order_events_detected: int
    stale_events: int
    dead_letter_entries: int
    settlement_records: int
    reconciled_records: int
    reconciliation_exceptions: int
    ledger_effects: int
    elapsed_time: int
    throughput_hundredths: int
    final_balance_cents: int


@dataclass(frozen=True, slots=True)
class PaymentOutcome:
    payment_id: str
    scenario: str
    outcome: str
    attempts: int
    ledger_effects: int


@dataclass(frozen=True, slots=True)
class LaboratoryResult:
    scheduler: EventScheduler
    queue: PaymentQueue
    ledger: Ledger
    dead_letters: DeadLetterQueue
    ordering: OrderedEventProcessor
    idempotency: IdempotentPaymentProcessor
    outcomes: tuple[PaymentOutcome, ...]
    settlements: tuple[SettlementRecord, ...]
    reconciliation: ReconciliationReport
    statistics: LaboratoryStatistics


def run_laboratory() -> LaboratoryResult:
    """Execute payments A-F from a clean state with no random inputs."""
    scheduler = EventScheduler()
    queue = PaymentQueue(scheduler, capacity=1)
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
    dead_letters = DeadLetterQueue()
    processor = DeadLetterProcessor(
        scheduler, queue, dead_letters, maximum_retries=2, retry_delay=2
    )
    idempotency = IdempotentPaymentProcessor(ledger)
    ordering = OrderedEventProcessor(ledger)

    def post(payment_id: str, amount_cents: int) -> None:
        ledger.append(
            LedgerEntry(
                f"{payment_id}-DEBIT",
                "HCCU-DEMO-001",
                Money(amount_cents),
                EntryType.DEBIT,
                "End-to-end laboratory payment",
                len(ledger.entries) + 1,
                scheduler.clock.time,
            )
        )

    # A: ordinary success. B: one transient failure and recovery.
    processor.submit("PAY-A", "REQ-A", lambda: post("PAY-A", 1_000))
    processor.submit(
        "PAY-B",
        "REQ-B",
        lambda: post("PAY-B", 2_000),
        transient_failures=("processor temporarily unavailable",),
    )

    # C: the same business request is delivered twice, but only the first posts.
    c_key = IdempotencyKey("IDEMPOTENCY-PAY-C")

    def payment_c(delivery_number: int) -> None:
        idempotency.process(
            PaymentDelivery("PAY-C", Money(3_000), delivery_number, 2, delivery_number),
            c_key,
        )

    processor.submit("PAY-C", "REQ-C", lambda: payment_c(1))
    queue.enqueue_ach_transfer("PAY-C-DUPLICATE", lambda: payment_c(2))

    # D: sequence 3 arrives first and is buffered; a duplicate and stale event
    # later prove that only the ordered completion can affect the ledger.
    d_events = tuple(
        replace(
            event,
            payment_id="PAY-D",
            event_id=event.event_id.replace("PAY-ORDER-001", "PAY-D"),
            amount=Money(4_000),
        )
        for event in out_of_order_events()
    )
    processor.submit(
        "PAY-D",
        "REQ-D",
        lambda: [ordering.receive(event) for event in d_events],
    )

    # E: all allowed retries are consumed, then the payment is isolated.
    processor.submit(
        "PAY-E",
        "REQ-E",
        lambda: post("PAY-E", 6_000),
        transient_failures=("network unavailable",) * 3,
        original_state=WorkflowState.PROCESSING,
    )

    # F: a transient worker failure and duplicate delivery occur together.
    f_key = IdempotencyKey("IDEMPOTENCY-PAY-F")

    def payment_f() -> None:
        for number in (1, 2):
            idempotency.process(
                PaymentDelivery("PAY-F", Money(5_000), number, 8, number), f_key
            )

    processor.submit(
        "PAY-F",
        "REQ-F",
        payment_f,
        transient_failures=("worker lease expired",),
    )
    scheduler.run()

    completed_ids = tuple(
        payment.payment_id for payment in processor.payments if payment.completed
    )
    settlements = tuple(
        SettlementRecord(
            f"SETTLEMENT-{payment_id}",
            payment_id,
            next(
                entry.amount.cents
                for entry in ledger.entries
                if entry.entry_id in (f"{payment_id}-DEBIT", f"{payment_id}-SETTLEMENT")
            ),
            SettlementDirection.OUTBOUND,
            scheduler.clock.time + 1,
        )
        for payment_id in sorted(completed_ids)
    )
    external = ExternalSettlementReport(
        tuple(
            ExternalSettlementRecord(
                f"EXTERNAL-{record.payment_id}",
                record.payment_id,
                record.amount_cents,
                record.direction,
                scheduler.clock.time + 2,
            )
            for record in settlements
        ),
        scheduler.clock.time + 2,
    )
    report = reconcile(settlements, external, scheduler.clock.time + 3)
    payment_by_id = {payment.payment_id: payment for payment in processor.payments}
    outcomes = (
        PaymentOutcome("PAY-A", "normal processing", "Completed", 1, 1),
        PaymentOutcome("PAY-B", "transient failure", "Completed", 2, 1),
        PaymentOutcome("PAY-C", "duplicate request", "Completed", 1, 1),
        PaymentOutcome("PAY-D", "out-of-order events", "Completed", 1, 1),
        PaymentOutcome("PAY-E", "retry exhaustion", "Dead letter", 3, 0),
        PaymentOutcome("PAY-F", "mixed retry + duplicate", "Completed", 2, 1),
    )
    ordering_stats = ordering.statistics
    idempotency_stats = idempotency.statistics
    elapsed = scheduler.clock.time
    stats = LaboratoryStatistics(
        payments_received=6,
        successful_payments=len(completed_ids),
        retries=sum(payment.retry_count for payment in processor.payments),
        duplicate_deliveries=idempotency_stats.duplicate_deliveries,
        duplicate_requests_prevented=idempotency_stats.duplicate_requests_prevented,
        out_of_order_events_detected=ordering_stats.out_of_order_events,
        stale_events=ordering_stats.stale_events,
        dead_letter_entries=len(dead_letters.entries),
        settlement_records=len(settlements),
        reconciled_records=report.matched_count,
        reconciliation_exceptions=report.exception_count,
        ledger_effects=len(ledger.entries) - 1,
        elapsed_time=elapsed,
        throughput_hundredths=len(completed_ids) * 100 // elapsed,
        final_balance_cents=replay(ledger.entries),
    )
    assert payment_by_id["PAY-E"].isolated
    return LaboratoryResult(
        scheduler,
        queue,
        ledger,
        dead_letters,
        ordering,
        idempotency,
        outcomes,
        settlements,
        report,
        stats,
    )


def describe_laboratory() -> str:
    """Render the full readable lifecycle timeline."""
    result = run_laboratory()
    stats = result.statistics
    lines = [
        "End-to-End Banking Operations Laboratory",
        "Receiving payments",
        "T+0 PAY-A..PAY-F | received, validated, and placed in FIFO queue",
        "Processing queue and worker execution",
    ]
    lines.extend(
        f"T+{event.time} {event.payment_id} | {event.action} | queue {event.queue_size}"
        for event in result.queue.events
        if event.action in ("arrived", "processing")
    )
    lines.extend(
        (
            "Retries",
            "PAY-B | transient failure -> retry 1 -> completed",
            "PAY-E | transient failures -> retries 1, 2 -> retry limit exceeded",
            "PAY-F | worker lease failure -> retry 1 -> completed",
            "Duplicate deliveries and idempotency",
            "PAY-C | 2 deliveries -> 1 stored result -> 1 ledger effect",
            "PAY-F | 2 deliveries -> 1 stored result -> 1 ledger effect",
            "Ordering validation",
            "PAY-D | future sequence buffered; ordered events drained safely",
            "PAY-D | duplicate event rejected; stale event detected",
            "Ledger updates",
        )
    )
    lines.extend(
        f"{entry.sequence}. {entry.entry_id} | {entry.entry_type.value} "
        f"{format_money(entry.amount.cents)} | T+{entry.posted_at}"
        for entry in result.ledger.entries
    )
    lines.append("Settlement")
    lines.extend(
        f"{record.payment_id} | {format_money(record.amount_cents)} | Outbound"
        for record in result.settlements
    )
    lines.extend(
        (
            "Reconciliation",
            f"Matched: {result.reconciliation.matched_count} | Exceptions: "
            f"{result.reconciliation.exception_count} | Reconciled",
            "Dead-letter queue",
        )
    )
    lines.extend(
        f"{entry.payment_id} | {entry.reason.name} | retries {entry.retry_count} | "
        f"isolated T+{entry.isolated_at}"
        for entry in result.dead_letters.entries
    )
    lines.extend(("Final operational summary", *_summary_lines(stats)))
    return "\n".join(lines)


def _summary_lines(stats: LaboratoryStatistics) -> tuple[str, ...]:
    return (
        f"Payments received: {stats.payments_received}",
        f"Successful payments: {stats.successful_payments}",
        f"Retries: {stats.retries}",
        f"Duplicate deliveries: {stats.duplicate_deliveries}",
        f"Duplicate requests prevented: {stats.duplicate_requests_prevented}",
        f"Out-of-order events detected: {stats.out_of_order_events_detected}",
        f"Stale events: {stats.stale_events}",
        f"Dead-letter entries: {stats.dead_letter_entries}",
        f"Settlement records: {stats.settlement_records}",
        f"Reconciliation: {stats.reconciled_records} matched, "
        f"{stats.reconciliation_exceptions} exceptions",
        f"Ledger effects: {stats.ledger_effects}",
        f"Final balance: {format_money(stats.final_balance_cents)}",
    )


def describe_operational_summary() -> str:
    """Render the concise throughput, reliability, and correctness report."""
    result = run_laboratory()
    stats = result.statistics
    lines = [
        "Operational Summary | deterministic end-to-end workload",
        f"Throughput: {stats.successful_payments} completions / "
        f"{stats.elapsed_time} time units ({stats.throughput_hundredths // 100}."
        f"{stats.throughput_hundredths % 100:02} per unit)",
        "Reliability",
        f"Retries: {stats.retries} | duplicates prevented: "
        f"{stats.duplicate_requests_prevented} | ordering alerts: "
        f"{stats.out_of_order_events_detected + stats.stale_events} | "
        f"dead letters: {stats.dead_letter_entries}",
        "Payment outcomes",
    ]
    lines.extend(
        f"{item.payment_id}: {item.outcome} | {item.scenario} | "
        f"attempts {item.attempts} | ledger effects {item.ledger_effects}"
        for item in result.outcomes
    )
    lines.extend(
        (
            "Financial correctness",
            f"Settlement: {stats.settlement_records} records | reconciliation: "
            f"{stats.reconciled_records} matched, "
            f"{stats.reconciliation_exceptions} exceptions",
            f"Ledger: {stats.ledger_effects} payment effects | final balance "
            f"{format_money(stats.final_balance_cents)} | authoritative and reconciled",
        )
    )
    return "\n".join(lines)
