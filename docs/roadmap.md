# Learning Roadmap

## Volume I — Completed

Volume I follows one consistent sequence of Chapters 0–18:

0. **Setting Up Your Digital Banking Laboratory** — deterministic virtual time,
   synchronous scheduling, tooling, packaging, and containers.
1. **Bank or Credit Union?** — institution identity and ownership comparison.
2. **Member Onboarding** — validated applications and explicit decisions.
3. **The Ledger Is the Authority** — immutable entries and replay-derived balance.
4. **Understanding Balances** — current, pending, and available projections.
5. **Deposits** — validated credit posting.
6. **Withdrawals** — funds checks and debit posting.
7. **Internal Transfers** — atomic paired account entries.
8. **ACH Transfers** — delayed external-payment workflow.
9. **ACH Returns** — append-only corrective credits.
10. **Settlement and Reconciliation** — independent records and exception classes.
11. **Payment Queues** — deterministic FIFO work and capacity.
12. **Worker Capacity** — pools, throughput, utilization, and backlog.
13. **Retries and Transient Failures** — bounded recovery without duplicate effects.
14. **Duplicate Payment Requests** — intentionally naïve duplicate processing.
15. **Idempotent Payment Processing** — one effect for repeated delivery.
16. **Out-of-Order Events** — sequence validation, buffering, and stale rejection.
17. **Dead-Letter Queues** — bounded permanent-failure isolation.
18. **End-to-End Banking Operations Laboratory** — an integrated workload combining
    queues, workers, retries, duplicates, idempotency, ordering, dead-letter
    isolation, settlement, and reconciliation.

## Volume II — Planned

Future work may explore account lifecycle, additional payment rails, digital banking
channels, durable and distributed operations, authentication and authorization,
security and compliance controls, observability, lending, fraud signals, analytics,
and carefully evaluated machine learning. None of these planned topics is implemented
or implied as production-ready by Volume I.

The sequence may evolve, but each lesson should connect a business concept, a
software-engineering concept, a deterministic simulation, a command-line experiment,
and an engineering lesson.
