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

## Chapter 0: a trustworthy foundation

This initial `0.1.0` release contains only reusable simulation infrastructure:

- nonnegative integer virtual time advanced only by explicit calls;
- synchronous events executed chronologically, with insertion order breaking ties;
- no threads, asynchronous runtime, sleeping, network calls, database, or randomness.

There are deliberately no accounts, members, ledgers, balances, deposits,
transfers, or other banking-domain models yet. Later chapters will introduce
banking concepts incrementally without pretending this educational environment has
the security, compliance, resilience, controls, or integrations required of
production banking software.

## Quick start

Python 3.13 is required.

```bash
python -m pip install -e '.[dev]'
bank-sim doctor
pytest
ruff check .
ruff format --check .
```

The health check prints:

```text
Digital Banking Systems Laboratory
Version 0.1.0
Laboratory environment is ready.
```

## Docker

```bash
docker compose build
docker compose run --rm lab bank-sim doctor
docker compose run --rm lab pytest
docker compose run --rm lab ruff check .
docker compose run --rm lab ruff format --check .
```

The Compose service bind-mounts the checkout for an immediate development loop and
runs as a non-root user.

## Learning path

The planned progression begins with representing money, deriving balances, and
moving funds in core banking. It will then expand through payments and digital
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
