# Garcia Systems Laboratory Skeleton

> **This repository is a reusable educational simulation foundation, not production business software.**

This project is the Chapter 0 starting point for Garcia Systems executable textbooks. An executable textbook combines explanation, runnable examples, and tests so readers can inspect claims rather than merely accept them. Deterministic simulations are useful because the same inputs always produce the same event order, state transitions, and observations, making lessons reproducible and failures explainable.

The skeleton supplies dependency-free runtime infrastructure for integer virtual time and synchronous event scheduling. It contains **no domain simulation yet**. Future laboratories should add their subject matter in later chapters without changing the stable foundation merely to suit one lesson.

## Quick start

Python 3.13 is required.

```bash
python -m pip install -e '.[dev]'
lab-sim doctor
pytest
ruff check .
ruff format --check .
```

The health check prints the project identity, package version, and readiness status. The sole command at this milestone is `lab-sim doctor`.

## Docker

```bash
docker compose -f docker-compose.yml build
docker compose -f docker-compose.yml run --rm lab lab-sim doctor
docker compose -f docker-compose.yml run --rm lab pytest
docker compose -f docker-compose.yml run --rm lab ruff check .
docker compose -f docker-compose.yml run --rm lab ruff format --check .
```

The Compose service bind-mounts the checkout for an immediate development loop and runs as a non-root user.

## Creating a laboratory

Copy this repository or use it as a GitHub template. Do not turn the skeleton itself into one permanent domain project. In the copy:

1. replace project identity, URLs, and introductory prose;
2. retain and test the virtual clock and scheduler as shared infrastructure;
3. introduce one major educational concept per new chapter;
4. place subject-specific code outside the infrastructure modules;
5. keep tests and prose synchronized with every lesson.

See [Chapter 0](book/00-setting-up-your-laboratory.md), the [documentation index](docs/README.md), and the [architecture principles](docs/architecture-principles.md).

## License and participation

Contributions follow [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). The project is available under the [MIT License](LICENSE).
