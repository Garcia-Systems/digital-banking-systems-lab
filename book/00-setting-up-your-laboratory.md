# Chapter 0: Setting Up Your Digital Banking Laboratory

## Learning objective

Establish a repeatable, trustworthy environment before introducing banking
behavior. By the end of this chapter, the package, tests, formatter, linter, build,
and container health check should all run.

## Why banking education begins with determinism

Financial-system behavior must be explainable. A simulation teaches most clearly
when a reader can repeat it: the same inputs should create the same ordering and
observations. This foundation represents time as a nonnegative integer and advances
it only through explicit calls. The scheduler runs callbacks synchronously in
chronological order and uses insertion order for ties.

Chapter 0 uses no wall clock, sleep, thread, asynchronous runtime, network,
database, or randomness. These boundaries keep causality visible; they are not a
claim that real banking systems avoid distributed infrastructure.

## Prepare Python

Install Python 3.13 and create an isolated environment:

```bash
python3.13 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
```

Confirm the environment:

```bash
bank-sim doctor
```

Expected output:

```text
Digital Banking Systems Laboratory
Version 0.1.0
Laboratory environment is ready.
```

## Check and package the foundation

```bash
pytest
ruff check .
ruff format --check .
python -m build
twine check dist/*
```

Alternatively, build and run the `lab` Compose service as shown in the README. Its
bind mount keeps local edits visible inside the container.

## Explore the contracts

Read `bank_sim.clock.VirtualClock`, then its focused tests. Next read
`bank_sim.scheduler.EventScheduler` and trace equal-time events, dynamically
scheduled events, and callback failures. These tests are executable statements of
the contracts, including chronological execution and insertion-order tie breaking.

## Before Chapter 1

Harbor Community Credit Union is currently only the fictional setting for the
curriculum. No financial institution, member, account, ledger, balance, deposit, or
transfer has been implemented. Later chapters will add banking behavior one concept
at a time, pairing each business idea with a software mechanism, simulation,
command-line experiment, and engineering lesson. This laboratory is educational
software and must not be used as production banking software.
