# Digital Banking Systems Laboratory

> **An executable textbook and educational simulation—not production banking software.**

The **Digital Banking Systems Laboratory** teaches modern banking software
engineering through deterministic simulations. Its fictional institution,
**Harbor Community Credit Union**, gives future lessons a consistent setting
without implying that this repository is a real financial system.

Each chapter will connect one business concept, one software-engineering concept,
one deterministic simulation, one command-line experiment, and one engineering
lesson. Readers can run the examples and tests, inspect every mechanism, and
repeat an experiment exactly rather than merely accepting claims in prose.

## Chapters 0–16

Chapter 0 introduced reusable simulation infrastructure:

- nonnegative integer virtual time advanced only by explicit calls;
- synchronous events executed chronologically, with insertion order breaking ties;
- no threads, asynchronous runtime, sleeping, network calls, database, or randomness.

Chapter 1's `0.2.0` release added immutable financial-institution identity and a
deterministic comparison of shareholder-owned banks and member-owned credit unions.
Chapter 2's `0.3.0` release adds a validated, deterministic membership-application
state machine with explicit decisions and ordered transition history. Chapter 3's
`0.4.0` release introduces immutable ledger entries, exact integer-cent money, and
a current balance derived by deterministic replay. Chapter 4's `0.5.0` release adds
current, pending, and available balance projections while keeping authorized pending
activity separate from ledger facts. Chapter 5's `0.6.0` release introduces
validated deposits that append credit entries and derives every updated balance by
ledger replay. Chapter 6's `0.7.0` release adds deterministic withdrawal approval:
only requests within available funds append debit entries, while rejected requests
leave the ledger unchanged. There are still deliberately no permanent members,
account lifecycle, external payments, settlement, or other payment workflows.
Chapter 7's `0.8.0` release adds internal transfers as atomic source-debit and
destination-credit pairs, with both account balances derived by replay. Chapter
8's `0.9.0` release adds a deterministic outbound ACH workflow whose pending debit
becomes one posted ledger debit only after simulated network completion.
Chapter 9's `0.10.0` release adds a separate ACH return workflow that preserves
that debit, appends one corrective credit, and derives the restored balance by replay.
Chapter 10's `0.11.0` release independently compares completed ACH settlement
expectations with a simulated external report and preserves reconciliation exceptions.
Chapter 11's `0.12.0` release schedules accepted ACH transfers and returns through
a deterministic FIFO queue and compares fixed worker capacities without changing
financial outcomes.
Chapter 12's `0.13.0` release adds deterministic payment-worker pools and compares
throughput, queue depth, wait time, and utilization while preserving ledger history.
Chapter 13's `0.14.0` release adds scripted transient failures, fixed-delay retries,
bounded attempts, and recovery statistics without duplicating ledger effects.
Chapter 14's `0.15.0` release scripts repeated request delivery and intentionally
shows how naïve processing creates duplicate financial effects. Duplicate prevention
is implemented by Chapter 15's `0.16.0` release with deterministic idempotency keys,
stored results, duplicate acknowledgements, and exactly one financial effect.
Chapter 16's `0.17.0` release adds deterministic event sequences, revision checks,
future-event buffering, and stale-event rejection without changing ledger truth.
Later chapters will introduce banking
concepts incrementally without pretending this educational environment has the
security, compliance, resilience, controls, or integrations required of production
banking software.

## Quick start

Python 3.13 is required.

```bash
python -m pip install -e '.[dev]'
bank-sim doctor
bank-sim institution
bank-sim compare-institutions
bank-sim member-apply
bank-sim member-onboarding
bank-sim ledger
bank-sim ledger-replay
bank-sim balance
bank-sim pending
bank-sim deposit
bank-sim deposits
bank-sim withdrawal
bank-sim withdrawals
bank-sim transfer
bank-sim transfers
bank-sim ach
bank-sim ach-timeline
bank-sim ach-return
bank-sim ach-return-timeline
bank-sim settlement
bank-sim reconcile
bank-sim reconciliation-exceptions
bank-sim payment-queue
bank-sim payment-capacity
bank-sim worker-capacity --workers 1
bank-sim capacity-comparison
bank-sim retries
bank-sim retry-timeline
bank-sim duplicates
bank-sim duplicate-timeline
bank-sim idempotency
bank-sim idempotency-comparison
bank-sim ordering
bank-sim out-of-order
pytest
ruff check .
ruff format --check .
```

The health check prints:

```text
Digital Banking Systems Laboratory
Version 0.17.0
Laboratory environment is ready.
```

## Docker

```bash
docker compose build
docker compose run --rm lab bank-sim doctor
docker compose run --rm lab bank-sim member-apply
docker compose run --rm lab bank-sim member-onboarding
docker compose run --rm lab bank-sim ledger
docker compose run --rm lab bank-sim ledger-replay
docker compose run --rm lab bank-sim balance
docker compose run --rm lab bank-sim pending
docker compose run --rm lab bank-sim deposit
docker compose run --rm lab bank-sim deposits
docker compose run --rm lab bank-sim withdrawal
docker compose run --rm lab bank-sim withdrawals
docker compose run --rm lab bank-sim transfer
docker compose run --rm lab bank-sim transfers
docker compose run --rm lab bank-sim ach
docker compose run --rm lab bank-sim ach-timeline
docker compose run --rm lab bank-sim ach-return
docker compose run --rm lab bank-sim ach-return-timeline
docker compose run --rm lab bank-sim settlement
docker compose run --rm lab bank-sim reconcile
docker compose run --rm lab bank-sim reconciliation-exceptions
docker compose run --rm lab bank-sim payment-queue
docker compose run --rm lab bank-sim payment-capacity
docker compose run --rm lab bank-sim worker-capacity --workers 1
docker compose run --rm lab bank-sim capacity-comparison
docker compose run --rm lab bank-sim retries
docker compose run --rm lab bank-sim retry-timeline
docker compose run --rm lab bank-sim duplicates
docker compose run --rm lab bank-sim duplicate-timeline
docker compose run --rm lab bank-sim idempotency
docker compose run --rm lab bank-sim idempotency-comparison
docker compose run --rm lab bank-sim ordering
docker compose run --rm lab bank-sim out-of-order
docker compose run --rm lab pytest
docker compose run --rm lab ruff check .
docker compose run --rm lab ruff format --check .
```

The Compose service bind-mounts the checkout for an immediate development loop and
runs as a non-root user.

## Learning path

The domain learning path begins with
[Chapter 1: Bank or Credit Union?](book/01-bank-or-credit-union.md), continues with
[Chapter 2: Member Onboarding](book/02-member-onboarding.md), then proceeds to
[Chapter 3: The Ledger Is the Authority](book/03-the-ledger-is-the-authority.md),
then [Chapter 4: Understanding Balances](book/04-understanding-balances.md), and
then [Chapter 5: Deposits](book/05-deposits.md), and then
[Chapter 6: Withdrawals](book/06-withdrawals.md).
[Chapter 7: Internal Transfers](book/07-internal-transfers.md) follows with atomic
paired ledger entries. [Chapter 8: ACH Transfers](book/08-ach-transfers.md) then
introduces delayed external-payment coordination.
[Chapter 9: ACH Returns](book/09-ach-returns.md) follows with append-only corrective
history.
[Chapter 10: Settlement and Reconciliation](book/10-settlement-and-reconciliation.md)
then separates external financial results from independent verification.
[Chapter 11: Payment Queues](book/11-payment-queues.md) adds FIFO waiting and
deterministic processing capacity while preserving financial results.
[Chapter 12: Worker Capacity](book/12-worker-capacity.md) introduces fixed worker
pools, utilization, and throughput comparisons.
[Chapter 13: Retries and Transient Failures](book/13-retries-and-transient-failures.md)
adds scripted failures, fixed retry scheduling, and bounded recovery without duplicate
financial effects.
[Chapter 14: Duplicate Payment Requests](book/14-duplicate-payment-requests.md)
then exposes how repeated delivery creates repeated ledger effects under intentionally
naïve processing. [Chapter 15: Idempotent Payment Processing](book/15-idempotent-payment-processing.md)
then recognizes repeated business identity before applying ledger effects.
[Chapter 16: Out-of-Order Events](book/16-out-of-order-events.md) validates event
sequence and freshness before allowing business effects. The path
will expand through digital banking channels, distributed financial systems,
lending and
loan servicing, fraud detection, analytics, machine learning, and reliable
operations. Every capability will arrive with the chapter that explains it.

This repository originated from Garcia Systems' reusable laboratory template. See
[Chapter 0](book/00-setting-up-your-laboratory.md), the
[documentation index](docs/README.md), and the
[architecture principles](docs/architecture-principles.md) for the adapted learning
foundation.

## License and participation

Contributions follow [CONTRIBUTING.md](CONTRIBUTING.md) and
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). The project is available under the
[MIT License](LICENSE).
