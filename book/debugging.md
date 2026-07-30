# Debugging a Banking Simulation

Docker remains the official execution environment for the laboratory. The normal
way to run the single-deposit experiment is:

```bash
docker compose run --rm lab bank-sim deposit
```

This **run mode** shows the completed experiment and answers, “What happened?” The
optional VS Code **debug mode** uses the same Docker image and source code, but lets
you observe the experiment one statement at a time and answers, “How did it
happen?” Neither workflow requires Python on the host.

## Open the laboratory in its container

1. Install [Visual Studio Code](https://code.visualstudio.com/) and its **Dev
   Containers** extension.
2. Open this repository in VS Code.
3. Open the Command Palette and choose **Dev Containers: Reopen in Container**.
   VS Code builds and starts the existing `lab` Compose service, mounts the
   repository at `/workspace`, and installs its Python debugging extensions in the
   container.
4. Wait for the container to finish opening. Tests and CLI commands remain
   available in its terminal, such as `pytest` and `bank-sim deposit`.

The checked-in configuration selects the container's `/usr/local/bin/python`.
There is no host interpreter or extra runtime `debugpy` dependency to install;
VS Code provides its debugger inside the development container.

## Debug one deposit

This first exercise follows one request as it becomes an immutable credit entry
and changes the replayed account balance.

1. Open `src/bank_sim/deposits.py` and locate `post_deposit`.
2. Set a breakpoint on its first meaningful operation, the assignment to
   `sequence`.
3. Open **Run and Debug** and select **Debug: Post One Deposit**.
4. Press **F5**. When execution pauses, inspect `request`, `ledger`, and
   `ledger.entries` in the Variables view. The ledger is initially empty.
5. Use **Step Over** to construct and append the `LedgerEntry`. Observe that
   `ledger.entries` now contains a credit whose amount came from
   `request.amount_cents`.
6. Use **Step Into** on `ledger.append(...)` to explore the ledger invariant checks,
   then **Step Out** to return to `post_deposit`.
7. Use **Continue** to finish. The integrated terminal displays the same request,
   posted status, ledger entry, and final balance as run mode.

While paused, the Variables view explains current state and the Call Stack shows
how the CLI reached the deposit workflow. **Step Over** runs the current statement,
**Step Into** follows a called function, **Step Out** finishes the current function,
and **Continue** runs until the next breakpoint or completion.

The launch entry runs the real `bank_sim.cli` module with the `deposit`
argument—the same implementation and argument selected by `bank-sim deposit`.
Debugging changes only how execution is observed; the simulation inputs and
deterministic behavior are unchanged.
