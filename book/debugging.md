# Debugging a Banking Simulation

Debugging is introduced as a core learning mode in
[Chapter 0: Setting Up Your Digital Banking Laboratory](00-setting-up-your-laboratory.md#debugging-the-laboratory).
Start there for the beginner-friendly VS Code and Dev Container setup, the
explanation of debugger controls and state views, and the complete **Debug: Post
One Deposit** exercise.

Remember the environment boundary:

- From a host terminal, use `docker compose run --rm lab bank-sim ...`.
- From VS Code's Dev Container terminal, use `bank-sim ...` directly because that
  terminal is already inside the reproducible environment.

Run Mode answers **“What happened?”** Debug Mode answers **“How did it happen?”**
Both execute the same deterministic simulation; the debugger only lets you pause
and observe the banking objects along the way.
