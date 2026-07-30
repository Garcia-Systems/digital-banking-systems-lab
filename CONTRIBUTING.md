# Contributing

Thank you for improving the Digital Banking Systems Laboratory.

## Scope

This project is an executable textbook, not production banking software. Keep
runtime behavior deterministic and synchronous. Introduce banking behavior only in
the chapter that teaches it, with matching prose and focused tests; Chapter 0 is
limited to the trustworthy laboratory foundation.

## Development

The VS Code Dev Container is the normal environment for interactive editing,
testing, and debugging. Run commands such as `pytest`, `ruff check .`, and
`bank-sim deposit` directly in its terminal. Use Git from the host repository
folder. The image supplies Python 3.13, the editable package, and `.[dev]`;
contributors do not need those tools installed on the host.

Before opening a pull request, use these host-side Compose commands for
reproducible, CI-equivalent validation:

```bash
docker compose build
docker compose run --rm lab pytest --cov=bank_sim --cov-branch \
  --cov-report=term-missing --cov-report=xml:coverage.xml
docker compose run --rm lab ruff check .
docker compose run --rm lab ruff format --check .
docker compose run --rm lab bank-sim doctor
docker compose run --rm lab rm -rf build dist
docker compose run --rm lab python -m build
docker compose run --rm lab twine check dist/*
```

Run `docker compose run --rm lab ruff format .` only when deliberately applying
formatting. A direct host-Python environment is an optional advanced workflow
documented in Chapter 0; Docker and CI results are canonical. Add focused tests for
contract changes and update prose whenever behavior changes.

## Pull requests

Keep changes narrow and commits reviewable. Explain the educational benefit,
compatibility impact, and validation performed. Do not include generated caches,
build output, external-service credentials, or production integrations.
