# Chapter 0: Setting Up Your Laboratory

## Learning objective

Establish a repeatable environment before introducing any subject-specific behavior. By the end of this chapter, the package, tests, formatter, linter, and container health check should all run.

## Why begin with determinism?

A simulation teaches most clearly when a reader can repeat it. This foundation therefore represents time as a nonnegative integer and advances it only through explicit calls. The scheduler runs callbacks synchronously in chronological order and uses insertion order for ties. It does not consult a clock outside the simulation, sleep, create threads, or choose random outcomes.

## Prepare Python

Install Python 3.13 and create an isolated environment:

```bash
python3.13 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
```

Confirm the environment:

```bash
lab-sim doctor
```

Expected output:

```text
Garcia Systems Laboratory Skeleton
Version 0.1.0
Laboratory environment is ready.
```

## Check the foundation

```bash
pytest
ruff check .
ruff format --check .
```

Alternatively, build and run the `lab` Compose service as shown in the project README. Bind mounting keeps local edits visible inside the container.

## Explore the contracts

Read `lab_sim.clock.VirtualClock`, then its focused tests. Next read `lab_sim.scheduler.EventScheduler` and trace equal-time events, dynamically scheduled events, and callback failures. The tests are executable statements of the contracts.

## Before Chapter 1

A laboratory created from this skeleton may add its own Chapter 1. This repository intentionally does not. First customize identity and learning goals, keep reusable infrastructure separate from subject behavior, and verify all checks remain green.
