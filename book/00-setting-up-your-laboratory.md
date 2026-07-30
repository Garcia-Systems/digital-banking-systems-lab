# Chapter 0: Setting Up Your Digital Banking Laboratory

![A digital banking laboratory combining a textbook, Python simulations, tests, and reproducible Docker tooling](../images/chapters/chapter-00-setting-up-your-digital-banking-laboratory.png)

## Purpose of the laboratory

The Digital Banking Systems Laboratory combines a written textbook, deterministic
Python simulations, command-line experiments, automated tests, and reproducible
development tooling. The examples take place at the fictional **Harbor Community
Credit Union** and are educational software, not a production banking platform.

Chapter 0 establishes a trustworthy environment before the learning sequence
introduces banking behavior. The laboratory should behave the same way for every
reader. Docker packages the Python version and development tools with the project
so the book can focus on banking systems rather than host-environment differences.

## Why the project uses Docker

A Python project depends on more than its source: a particular Python version,
package dependencies, pytest, Ruff, Build, Twine, and other development tools all
affect results. Installing and updating each tool separately on every host can
produce inconsistent behavior.

Docker supplies this project's Python 3.13 environment and dependencies. Docker
Compose provides the canonical `lab` command runner. Local development and GitHub
Actions therefore use the same environment. Docker is not merely a deployment
option here; it is part of the educational contract: every reader gets the same
tools, reproducible simulations, and fewer setup differences.

## What Docker does—and does not do

For this repository, Docker:

- supplies Python;
- installs the package and its development tools;
- runs commands in an isolated environment; and
- exposes local source edits through a bind mount.

It does **not** add a database, real payment network, external API, message broker,
or production banking platform. Volume I remains deterministic, in-memory,
single-process educational software.

## Required host tools

Install only these host tools:

- Git;
- Docker;
- Docker Compose through the `docker compose` command; and
- a code editor.

> You do not need to install Python, pip, pytest, Ruff, Build, or Twine on the host.

Confirm the host tools from a terminal:

```bash
git --version
docker --version
docker compose version
```

## Clone the repository

```bash
git clone https://github.com/Garcia-Systems/digital-banking-systems-lab.git
cd digital-banking-systems-lab
```

Run the remaining commands from this directory. The repository's Compose
configuration is `docker-compose.yml`, and its canonical service is `lab`.

## Build the image

```bash
docker compose build
```

The first build generally needs network access to download the Python 3.13 base
image and development packages. Docker caches completed layers, so later builds
normally reuse unchanged downloads. Changes to `Dockerfile` or `pyproject.toml`
generally require another build.

## Check the laboratory

```bash
docker compose run --rm lab bank-sim doctor
```

Current output is:

```text
Digital Banking Systems Laboratory
Version 1.0.0
Laboratory environment is ready.
```

`docker compose run` creates a one-off container, `--rm` removes that container
afterward, `lab` selects the service, and the rest is the command run inside it.

## Check CLI help and version

```bash
docker compose run --rm lab bank-sim --help
docker compose run --rm lab bank-sim --version
```

Help inventories the experiments. The version command prints `bank-sim 1.0.0`.

## Run the tests and coverage

Run the test suite:

```bash
docker compose run --rm lab pytest
```

Run the same branch-coverage command used by CI:

```bash
docker compose run --rm lab pytest \
  --cov=bank_sim \
  --cov-branch \
  --cov-report=term-missing \
  --cov-report=xml:coverage.xml
```

The XML report is written to `coverage.xml` in the host checkout because the
checkout is mounted into the container. Coverage data and reports are transient
generated files; regenerate them rather than treating them as source.

## Run linting and formatting checks

```bash
docker compose run --rm lab ruff check .
docker compose run --rm lab ruff format --check .
```

The second command only verifies formatting. When you deliberately want Ruff to
rewrite files, use:

```bash
docker compose run --rm lab ruff format .
```

Review formatting changes before committing them.

## Build and validate the package

Remove stale distributions, build fresh ones, and validate their metadata:

```bash
docker compose run --rm lab rm -rf build dist
docker compose run --rm lab python -m build
docker compose run --rm lab twine check dist/*
```

The `dist/` and possible `build/` directories are generated output in the mounted
checkout, not source files.

## Run the completed banking laboratory

Volume I is complete, so the environment can launch its capstone commands now:

```bash
docker compose run --rm lab bank-sim laboratory
docker compose run --rm lab bank-sim operational-summary
```

You do not need to understand the banking output yet. These commands simply prove
that the completed repository is executable; Chapters 1–18 introduce the concepts
in sequence.

## Determinism and virtual time

Financial-system behavior must be explainable. A simulation teaches most clearly
when the same inputs always create the same ordering and observations. The
laboratory represents virtual time as a nonnegative integer and advances it only
through explicit calls. Its scheduler runs callbacks synchronously in chronological
event order and uses insertion order to break equal-time ties.

No wall clock, sleep, thread, asynchronous runtime, network, database, or randomness
controls this foundation. Those boundaries keep causality visible; they do not
claim that real banking systems avoid distributed infrastructure. Read
`bank_sim.clock.VirtualClock` and `bank_sim.scheduler.EventScheduler`, then trace
their focused tests to see these contracts execute.

## GitHub Actions and Codecov

The CI workflow builds `docker-compose.yml` and runs the same `lab` service used
above. It performs Ruff linting and formatting verification, tests with branch
coverage, verifies `coverage.xml`, runs CLI help/version/capstone smoke checks,
compares repeated capstone output for determinism, builds distributions, and runs
Twine validation.

CI may upload `coverage.xml` to Codecov. Normal readers need no Codecov account,
token, or configuration to clone and use the laboratory. Repository owners who
enable uploads manage the `CODECOV_TOKEN` GitHub secret separately; an upload
failure is configured not to fail the laboratory validation job.

## Repository tour

```text
.github/workflows/   GitHub Actions workflows
book/                Chapters 0–18 of the textbook
docs/                Architecture, philosophy, roadmap, and CLI reference
src/bank_sim/        Deterministic simulation package and CLI
tests/               Focused and end-to-end automated tests
Dockerfile           Python 3.13 development image
docker-compose.yml   Canonical lab service and source mount
pyproject.toml       Package, dependency, test, coverage, and Ruff configuration
README.md            Project overview and Docker-first quick start
CONTRIBUTING.md      Contribution workflow
CHANGELOG.md         Published project history
```

## How source mounting works

`docker-compose.yml` maps `.:/workspace` and sets `/workspace` as the working
directory. A file saved in the local checkout is immediately visible at the same
relative path inside the container, so ordinary source or documentation edits do
not require rebuilding the image. Rebuild after dependency or Dockerfile changes.

The service runs as `${LAB_UID:-1000}:${LAB_GID:-1000}`. Generated files such as
`coverage.xml` and `dist/*` appear in the host checkout and normally use that mapped
identity.

## Troubleshooting

- **`docker: command not found`:** install Docker for the host operating system,
  reopen the terminal, and rerun `docker --version`.
- **Docker daemon unavailable:** start Docker Desktop or the Docker Engine service,
  then retry `docker compose build`.
- **`docker compose` unavailable:** install or enable the Compose v2 plugin. This
  project uses `docker compose`, not the legacy `docker-compose` executable.
- **Image or package download failure:** verify network/proxy access and retry the
  build. A completed cached layer does not need downloading again.
- **Wrong directory:** `cd` to the checkout containing `docker-compose.yml` before
  running Compose commands.
- **Source edits do not appear:** save the file, confirm the bind mount with
  `docker compose run --rm lab pwd`, and ensure you are editing this checkout.
- **Generated-file ownership:** set `LAB_UID` and `LAB_GID` to your numeric host
  identity if its IDs are not 1000, remove the affected generated files, and rerun.
- **Missing `coverage.xml`:** run the full coverage command above from the repository
  root; plain `pytest` intentionally does not create the XML report.
- **Host-Python results differ from Docker or CI:** treat the Docker Compose result
  as canonical and rebuild before investigating differences.
- **Stale image after dependencies change:** run `docker compose build` again (use
  `docker compose build --no-cache` only when normal cache invalidation is
  insufficient).

## Optional: running without Docker

This optional path is for readers who already manage Python development
environments. It is not required and is not more authoritative than Docker or CI.

```bash
python3.13 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1`. After activation,
the shorter `bank-sim`, `pytest`, `ruff`, `python -m build`, and `twine` commands are
available. If their results differ, reproduce the check through the `lab` service.

## Chapter summary

You have established a consistent Docker-based laboratory: the image supplies
Python and development tools, Compose runs commands through `lab`, the bind mount
exposes edits, and the same environment validates changes locally and in CI.

At this point in the book's learning sequence, banking behavior has not yet been
introduced. The completed checkout does contain the later Volume I implementation;
Chapter 0 simply keeps it outside the current teaching scope.

## Transition to Chapter 1

Chapter 1 begins the banking domain by distinguishing banks from credit unions and
introducing Harbor Community Credit Union as a member-owned institution.
