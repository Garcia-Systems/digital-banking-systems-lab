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

## Chapters 0–6

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
account lifecycle, transfers, payments, settlement, or other money-movement workflows.
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
pytest
ruff check .
ruff format --check .
```

The health check prints:

```text
Digital Banking Systems Laboratory
Version 0.7.0
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
The path then proceeds to account opening and internal transfers. It
will then expand through payments and digital
banking channels, distributed financial systems and reconciliation, lending and
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
