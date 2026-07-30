# CLI Reference

Run CLI examples directly in the Dev Container terminal:

```bash
bank-sim institution
bank-sim deposit
bank-sim laboratory
```

These commands do not require Python or `bank-sim` to be installed on the host.
Readers not using VS Code, or those performing host-side validation, can use the
generic alternative `docker compose run --rm lab bank-sim <command>` from the host
repository folder. `--help` and `--version` are top-level interfaces and do not
require a subcommand. Every subcommand below runs a deterministic default
experiment without additional arguments.

## Foundation and institution

- `doctor` — verify the laboratory environment and package version.
- `institution` — describe Harbor Community Credit Union.
- `compare-institutions` — compare bank and credit-union ownership.

## Member onboarding

- `member-apply` — run one successful membership application.
- `member-onboarding` — show the complete set of application outcomes.

## Ledger and balances

- `ledger` — display immutable ledger history.
- `ledger-replay` — derive a balance by replay.
- `balance` — show ledger, pending, and available balances.
- `pending` — display transactions awaiting posting.

## Money movement

- `deposit` / `deposits` — post one or several deposits.
- `withdrawal` / `withdrawals` — demonstrate approval and rejection.
- `transfer` / `transfers` — demonstrate atomic internal transfers.

## ACH, settlement, and reconciliation

- `ach` / `ach-timeline` — run and inspect an outbound ACH transfer.
- `ach-return` / `ach-return-timeline` — run and inspect an ACH return.
- `settlement` — show internal settlement expectations.
- `reconcile` — reconcile a matching external report.
- `reconciliation-exceptions` — classify discrepancies.

## Queues and capacity

- `payment-queue` — process FIFO ACH work.
- `payment-capacity` — compare fixed queue capacities.
- `worker-capacity` — run a worker pool (optionally select `--workers`).
- `capacity-comparison` — compare worker-pool throughput.

## Reliability

- `retries` / `retry-timeline` — demonstrate bounded transient-failure recovery.
- `duplicates` / `duplicate-timeline` — expose naïve duplicate effects.
- `idempotency` / `idempotency-comparison` — prevent and compare duplicate effects.

## Ordering and isolation

- `ordering` — process correctly ordered events.
- `out-of-order` — buffer future events and reject stale events.
- `dead-letter` — isolate permanently failed payments.
- `dead-letter-report` — inspect isolated work.

## Capstone

- `laboratory` — run the complete Volume I operations laboratory.
- `operational-summary` — report its concise operational and financial results.
