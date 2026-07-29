# Digital Banking Systems Laboratory Documentation

This documentation supports an executable textbook set at the fictional Harbor
Community Credit Union:

- [Architecture principles](architecture-principles.md) defines the boundaries that
  keep simulations deterministic and inspectable.
- [Design philosophy](design-philosophy.md) explains how prose, code, tests, and
  command-line experiments work together.
- [Roadmap](roadmap.md) outlines the planned progression of banking lessons.

Begin with [Chapter 0](../book/00-setting-up-your-laboratory.md) for the deterministic
laboratory foundation, then continue to
[Chapter 1: Bank or Credit Union?](../book/01-bank-or-credit-union.md) for the first
banking-domain model, then [Chapter 2: Member Onboarding](../book/02-member-onboarding.md)
for a validated person-level application workflow, and then
[Chapter 3: The Ledger Is the Authority](../book/03-the-ledger-is-the-authority.md)
for immutable money history and deterministic current-balance replay, and then
[Chapter 4: Understanding Balances](../book/04-understanding-balances.md) for
current, pending, and available projections, and then
[Chapter 5: Deposits](../book/05-deposits.md) for validated business requests that
append ledger history and change balances only through replay, and then
[Chapter 6: Withdrawals](../book/06-withdrawals.md) for approval against available
funds before successful requests append debit history, and then
[Chapter 7: Internal Transfers](../book/07-internal-transfers.md) for atomic paired
debit and credit entries with replay across two accounts, and then
[Chapter 8: ACH Transfers](../book/08-ach-transfers.md) for a pending-first,
deterministic outbound external-payment workflow.

Continue with [Chapter 9: ACH Returns](../book/09-ach-returns.md) for a separate
return workflow, append-only corrective credit, and replay preserving the debit.
Continue with
[Chapter 10: Settlement and Reconciliation](../book/10-settlement-and-reconciliation.md)
for independently produced settlement records, deterministic comparison, and
preserved exceptions.
Continue with [Chapter 11: Payment Queues](../book/11-payment-queues.md) for FIFO
ACH scheduling, deterministic worker capacity, backlog metrics, and unchanged
financial outcomes.
Continue with [Chapter 12: Worker Capacity](../book/12-worker-capacity.md) for
deterministic worker pools, throughput, utilization, and backlog reduction without
changing ledger history.
Continue with
[Chapter 13: Retries and Transient Failures](../book/13-retries-and-transient-failures.md)
for scripted operational failures, deterministic fixed-delay retries, bounded
recovery, and exactly one financial effect after success.
