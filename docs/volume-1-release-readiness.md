# Volume I Release Readiness

## Scope

This stabilization covers Volume I Chapters 0–18, source code, CLI, book, README,
tests, packaging configuration, Docker workflow, CI, determinism, and financial
invariants.

## Issues identified

The QA review found missing release-readiness and changelog documents, no top-level
version interface, stale Chapter 0 and README language, an incomplete roadmap, no
authoritative CLI completeness check, insufficient capstone CI smoke checks, and no
recorded full executable release validation.

## Corrections made

- Added `bank-sim --version`, sourced from `bank_sim.__version__`.
- Added parser-introspection tests for the complete unique command set, help,
  documentation coverage, and every default demonstration.
- Corrected Chapter 0's version output and historical framing; rewrote the README
  for completed Volume I; completed the roadmap through Chapter 18.
- Added the canonical CLI reference and changelog.
- Added CI smoke and repeated-output checks for both capstone interfaces.
- Strengthened Chapter 18 assertions for unique effects and dead-letter isolation.

## Financial invariants reviewed

The executable suite confirms that the ledger remains authoritative and balances are
replay-derived where designed. Successful unique operations have one effect; retries
and idempotent duplicate deliveries add none. Stale and duplicate ordering events
cannot alter newer financial state. `PAY-E` is dead-lettered without a payment entry.
Five successful payments produce five settlement records, reconciliation matches all
five with no exceptions, and replay derives the canonical final balance of **$850.00**.

## Determinism

The simulations use scripted inputs rather than randomness, explicit virtual time,
and stable sequence/insertion ordering. Local source-interface executions of
`laboratory` and `operational-summary` were each redirected twice and compared with
`diff -u`; both comparisons passed with no differences. The CI workflow performs the
same comparisons in Docker.

## Validation

Executed on 2026-07-29:

- Passed: `PYTHONPATH=src pytest` (283 tests).
- Passed: `PYTHONPATH=src pytest tests/test_cli.py tests/test_laboratory.py` (79 tests).
- Passed: `ruff check .` and `ruff format --check .`.
- Passed through a temporary source-interface launcher: `bank-sim --help`,
  `bank-sim --version`, `bank-sim laboratory`, `bank-sim operational-summary`, and
  all 39 parser subcommands under their default demonstrations.
- Passed: both requested repeated-output `diff -u` comparisons.
- Not run successfully: coverage, because the available host pytest lacks
  `pytest-cov`.
- Not run successfully: `python -m build` and `twine check dist/*`, because the host
  lacks `build`, Hatchling, and Twine and dependency download was denied (HTTP 403).
- Not run successfully: isolated wheel installation and installed-wheel CLI checks,
  because no wheel could be built.
- Not run successfully: `docker compose build` or Docker validations, because the
  environment has no `docker` executable.

CI remains configured to execute coverage, package/Twine validation, Docker smoke
checks, and deterministic comparisons in an environment that supplies Docker.

## Known limitations

The laboratory is deterministic, in memory, single-process, educational, and not
connected to real financial networks. It does not provide production security,
compliance, persistence, high availability, privacy, or operational controls.

## Deferred work

Volume II may address digital channels, durable/distributed operation, security
boundaries, observability, lending, fraud signals, analytics, and carefully evaluated
machine learning. None is part of this stabilization.

## Recommendation

**Not ready to tag v1.0.0**

The implemented stabilization and host-executable checks pass, but release tagging
must wait for CI or another equipped environment to pass the unexecuted package,
installed-wheel, coverage, and Docker validations.
