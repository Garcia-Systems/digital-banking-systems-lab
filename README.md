# Digital Banking Systems Laboratory

> **This repository is an executable educational laboratory, not production banking software.**

The Digital Banking Systems Laboratory teaches modern financial-software engineering through deterministic simulations. It follows **Harbor Community Credit Union**, a fictional member-owned institution serving families and businesses across southeastern Virginia.

Each chapter connects a business capability to its software representation, a reproducible simulation, a command-line experiment, and an engineering lesson. Readers learn how financial institutions represent money, derive balances, move funds, secure digital channels, reconcile distributed systems, service loans, detect fraud, and use analytics and machine learning responsibly.

Chapter 0 establishes the dependency-light simulation foundation: integer virtual time, synchronous event scheduling, tests, Docker support, linting, formatting, and reproducible execution. Banking-domain behavior begins in later chapters so the shared infrastructure remains stable and understandable.

## Guiding principle

> **Every business is a system. Every software system is an executable model of that business. By building deterministic simulations, we can understand both the business and the engineering that supports it.**

## Educational contract

Every chapter introduces:

1. one business concept;
2. one software-engineering concept;
3. one deterministic simulation;
4. one command-line experiment;
5. one engineering lesson.

## Quick start

Python 3.13 is required.

```bash
python -m pip install -e '.[dev]'
bank-sim doctor
pytest
ruff check .
ruff format --check .
```

The health check prints the project identity, package version, and readiness status. At the Chapter 0 milestone, `bank-sim doctor` is the sole domain-facing command.

## Docker

```bash
docker compose -f docker-compose.yml build
docker compose -f docker-compose.yml run --rm lab bank-sim doctor
docker compose -f docker-compose.yml run --rm lab pytest
docker compose -f docker-compose.yml run --rm lab ruff check .
docker compose -f docker-compose.yml run --rm lab ruff format --check .
```

The Compose service bind-mounts the checkout for an immediate development loop and runs as a non-root user.

## Planned learning path

The laboratory grows from core banking into payments, digital channels, distributed financial systems, lending, fraud and compliance, analytics, machine learning, and institutional operations.

The opening chapters will establish:

- the difference between banks and credit unions;
- members, accounts, and onboarding;
- an immutable ledger as the authority for money;
- current, available, and pending balances;
- deposits, withdrawals, and internal transfers.

Later chapters will add ACH, wires, debit cards, bill pay, online and mobile banking, APIs, authentication, authorization, settlement, reconciliation, lending, fraud controls, reporting, forecasting, and operational resilience.

## Repository layout

```text
book/       Executable-textbook chapters
docs/       Architecture and contributor documentation
src/        Deterministic simulation code
tests/      Executable behavioral contracts
examples/   Focused runnable scenarios
reports/    Generated experiment reports
diagrams/   System and timeline diagrams
```

Subject-specific code should remain separate from reusable clock and scheduler infrastructure. Tests, prose, CLI behavior, and examples should evolve together.

See [Chapter 0](book/00-setting-up-your-laboratory.md), the [documentation index](docs/README.md), and the [architecture principles](docs/architecture-principles.md).

## License and participation

Contributions follow [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). The project is available under the [MIT License](LICENSE).
