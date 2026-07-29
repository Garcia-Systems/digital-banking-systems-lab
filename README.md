# Digital Banking Systems Laboratory

> **An executable textbook and deterministic banking systems laboratory—not production banking software.**

The laboratory teaches banking software engineering through repeatable simulations
set at the fictional **Harbor Community Credit Union**. Each chapter connects a
business concept, a software-engineering concept, executable code, a command-line
experiment, and tests. This educational repository is not a real financial system.

## Volume I complete: Chapters 0–18

Volume I begins with the deterministic laboratory foundation in
[Chapter 0](book/00-setting-up-your-laboratory.md), proceeds through institution,
onboarding, ledger, balances, money movement, ACH, settlement, queues, capacity,
and reliability, and culminates in
[Chapter 18: End-to-End Banking Operations Laboratory](book/18-end-to-end-banking-operations-laboratory.md).
The [documentation index](docs/README.md) links the complete Chapter 0–18 sequence;
the [roadmap](docs/roadmap.md) summarizes every chapter. The
[CLI reference](docs/cli-reference.md) is the canonical command inventory.

## Requirements and installation

Local execution requires Python 3.13 or newer. Docker validation requires Docker
Engine with the Compose v2 (`docker compose`) plugin.

```bash
python3.13 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
```

## Local validation

```bash
pytest
pytest --cov=bank_sim --cov-branch --cov-report=term-missing
ruff check .
ruff format --check .
rm -rf build dist
python -m build
twine check dist/*
bank-sim --help
bank-sim --version
bank-sim laboratory
bank-sim operational-summary
```

`bank-sim doctor` reports the installed package identity and environment status.
See the [CLI reference](docs/cli-reference.md) for all deterministic experiments.

## Docker validation

The canonical Compose service is `lab`; it bind-mounts the checkout and runs as a
non-root user.

```bash
docker compose build
docker compose run --rm lab pytest
docker compose run --rm lab pytest --cov=bank_sim --cov-branch --cov-report=term-missing
docker compose run --rm lab ruff check .
docker compose run --rm lab ruff format --check .
docker compose run --rm lab sh -c 'rm -rf build dist && python -m build'
docker compose run --rm lab sh -c 'twine check dist/*'
docker compose run --rm lab bank-sim --help
docker compose run --rm lab bank-sim --version
docker compose run --rm lab bank-sim laboratory
docker compose run --rm lab bank-sim operational-summary
```

## Intentional limitations

Volume I is deterministic, in memory, single-process, and educational. It has no
connection to real financial networks and does not provide production security,
compliance, durability, availability, privacy, or operational controls.

## Volume II preview

Volume II is planned to explore digital channels, durable and distributed financial
systems, security boundaries, and operational observability. Later topics may include
lending, fraud signals, analytics, and machine learning; these capabilities are
deferred and do not exist in Volume I.

## License and participation

Contributions follow [CONTRIBUTING.md](CONTRIBUTING.md) and
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). The project is available under the
[MIT License](LICENSE).
