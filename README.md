# Digital Banking Systems Laboratory

> **An executable textbook and deterministic banking systems laboratory—not production banking software.**

The laboratory teaches banking software engineering through repeatable simulations
set at the fictional **Harbor Community Credit Union**. Each chapter connects a
business concept, software-engineering concept, executable code, command-line
experiment, and tests. Volume I contains Chapters 0–18 and culminates in the
[end-to-end laboratory](book/18-end-to-end-banking-operations-laboratory.md).

## Dev Container quick start

Git, Docker with Compose v2, Visual Studio Code, and its Dev Containers extension
are the supported host tools. Docker supplies Python 3.13, the package, and all
development tools beneath the Dev Container; no host Python toolchain is required.

```bash
# Host terminal
git clone https://github.com/Garcia-Systems/digital-banking-systems-lab.git
cd digital-banking-systems-lab
# Optional initial pre-build (VS Code can also build it when reopening)
docker compose build
```

Open the repository in VS Code, run **Dev Containers: Reopen in Container**, wait
for initialization, and then use direct commands in the Dev Container terminal:

```bash
bank-sim --help
bank-sim institution
pytest
ruff check .
```

The host checkout is mounted into the container, so edits are immediately visible.
Use Git from a normal host terminal; use the Dev Container for simulations, tests,
linting, packaging, and debugging. See [Chapter 0](book/00-setting-up-your-laboratory.md)
for guided setup and troubleshooting, and the [debugging guide](book/debugging.md)
for the learning workflow.

## Host-side Compose alternatives and validation

Docker Compose remains available to readers without VS Code and for independent,
CI-equivalent, or troubleshooting checks. Run these from the host repository
folder, not from inside the current Dev Container:

```bash
docker compose run --rm lab bank-sim institution
docker compose run --rm lab pytest
docker compose run --rm lab ruff check .
docker compose run --rm lab python -m build
```

Maintainers can use the complete CI-equivalent Compose command set in
[CONTRIBUTING.md](CONTRIBUTING.md). The [CLI reference](docs/cli-reference.md)
inventories all deterministic experiments.

## Optional host-Python workflow

Experienced readers may manage a Python 3.13 virtual environment and install
`.[dev]` directly. This is secondary to the Docker-backed Dev Container. The
commands are documented at the end of Chapter 0.

## Intentional limitations

Volume I is deterministic, in memory, single-process, and educational. It has no
connection to real financial networks and does not provide production security,
compliance, durability, availability, privacy, or operational controls. Volume II
topics are planned but are not implemented here.

## License and participation

Contributions follow [CONTRIBUTING.md](CONTRIBUTING.md) and
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). The project is available under the
[MIT License](LICENSE).
