# Digital Banking Systems Laboratory

> **An executable textbook and deterministic banking systems laboratory—not production banking software.**

The laboratory teaches banking software engineering through repeatable simulations
set at the fictional **Harbor Community Credit Union**. Each chapter connects a
business concept, software-engineering concept, executable code, command-line
experiment, and tests. Volume I contains Chapters 0–18 and culminates in the
[end-to-end laboratory](book/18-end-to-end-banking-operations-laboratory.md).

## Docker-first quick start

Git, Docker with Compose v2, and an editor are the only host requirements. Docker
supplies Python 3.13, the package, and all development tools; the `lab` Compose
service is the canonical command runner locally and in CI.

```bash
git clone https://github.com/Garcia-Systems/digital-banking-systems-lab.git
cd digital-banking-systems-lab
docker compose build
docker compose run --rm lab bank-sim doctor
```

You do not need Python, pip, pytest, Ruff, Build, or Twine on the host. See
[Chapter 0](book/00-setting-up-your-laboratory.md) for beginner-friendly setup,
source-mount and troubleshooting guidance, and a complete first debugging exercise
inside the VS Code Dev Container. The shorter [debugging guide](book/debugging.md)
points returning readers back to that foundational lesson.

## Run and validate through Compose

```bash
# Tests and the same branch-coverage report used by CI
docker compose run --rm lab pytest
docker compose run --rm lab pytest --cov=bank_sim --cov-branch \
  --cov-report=term-missing --cov-report=xml:coverage.xml

# Lint, verify formatting, or deliberately format
docker compose run --rm lab ruff check .
docker compose run --rm lab ruff format --check .
docker compose run --rm lab ruff format .

# Clean, build, and validate distributions
docker compose run --rm lab rm -rf build dist
docker compose run --rm lab python -m build
docker compose run --rm lab twine check dist/*

# CLI and capstone smoke checks
docker compose run --rm lab bank-sim --help
docker compose run --rm lab bank-sim --version
docker compose run --rm lab bank-sim laboratory
docker compose run --rm lab bank-sim operational-summary
```

The bind-mounted checkout makes local edits visible to the container. The
[CLI reference](docs/cli-reference.md) inventories all deterministic experiments,
and the [documentation index](docs/README.md) links the full learning sequence.

## Optional host-Python workflow

Experienced readers may manage a Python 3.13 virtual environment and install
`.[dev]` directly. This is optional; Docker Compose remains the canonical and
CI-aligned result. The commands are documented at the end of Chapter 0.

## Intentional limitations

Volume I is deterministic, in memory, single-process, and educational. It has no
connection to real financial networks and does not provide production security,
compliance, durability, availability, privacy, or operational controls. Volume II
topics are planned but are not implemented here.

## License and participation

Contributions follow [CONTRIBUTING.md](CONTRIBUTING.md) and
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). The project is available under the
[MIT License](LICENSE).
