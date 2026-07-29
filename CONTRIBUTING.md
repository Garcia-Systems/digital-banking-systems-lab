# Contributing

Thank you for improving the Garcia Systems Laboratory Skeleton.

## Scope

Changes here must benefit unrelated educational simulation laboratories. Keep runtime code deterministic, synchronous, dependency-free, and separate from subject-specific behavior. Propose domain lessons in a repository created from this skeleton instead.

## Development

Use Python 3.13, create an isolated environment, and install `.[dev]`. Before opening a pull request, run:

```bash
pytest --cov=lab_sim --cov-branch --cov-report=term-missing
ruff check .
ruff format --check .
lab-sim doctor
python -m build
```

Docker equivalents are documented in the README. Add focused tests for contract changes and update prose whenever behavior changes.

## Pull requests

Keep changes narrow and commits reviewable. Explain the educational benefit, compatibility impact, and validation performed. Do not include generated caches, build output, external-service credentials, or production integrations.
