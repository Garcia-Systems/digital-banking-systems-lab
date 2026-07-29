# Contributing

Thank you for improving the Digital Banking Systems Laboratory.

## Scope

This project is an executable textbook, not production banking software. Keep
runtime behavior deterministic and synchronous. Introduce banking behavior only in
the chapter that teaches it, with matching prose and focused tests; Chapter 0 is
limited to the trustworthy laboratory foundation.

## Development

Use Python 3.13, create an isolated environment, and install `.[dev]`. Before
opening a pull request, run:

```bash
pytest --cov=bank_sim --cov-branch --cov-report=term-missing
ruff check .
ruff format --check .
bank-sim doctor
python -m build
twine check dist/*
```

Docker equivalents are documented in the README. Add focused tests for contract
changes and update prose whenever behavior changes.

## Pull requests

Keep changes narrow and commits reviewable. Explain the educational benefit,
compatibility impact, and validation performed. Do not include generated caches,
build output, external-service credentials, or production integrations.
