# Debugging a Banking Simulation

Debugging is introduced as a core learning mode in
[Chapter 0: Setting Up Your Digital Banking Laboratory](00-setting-up-your-laboratory.md#debugging-the-laboratory).
Start there for the beginner-friendly VS Code and Dev Container setup and the
explanation of debugger controls and state views. Chapter 5 contains the canonical
exercise that later chapters should follow.

Open the repository in VS Code and run **Dev Containers: Reopen in Container**.
The Dev Container terminal is the primary Run Mode environment: run `bank-sim ...`
directly because the terminal is already inside the reproducible environment.
Host-side Compose is an alternative for readers without VS Code and for validation
or troubleshooting; [Chapter 0](00-setting-up-your-laboratory.md#8-host-side-docker-compose-alternatives)
documents that boundary.

Run Mode answers **“What happened?”** Debug Mode answers **“How did it happen?”**
Both execute the same deterministic simulation; the debugger only lets you pause
and observe the banking objects along the way.

## Normal Run and Debug workflow

1. Open the repository in the Dev Container.
2. In its terminal, run the chapter's direct command and observe the CLI result.
3. Open **Run and Debug** and select the prepared chapter launch configuration.
4. Open the source named by the chapter and set its documented breakpoint at the
   recognizable operation (not a brittle line number).
5. Press **F5**.
6. Inspect **Variables**, **Call Stack**, and the execution flow at the pause.
7. Use Step Over, Step Into, Step Out, and Continue as directed by the chapter.
8. Compare the observed debugger state with the original CLI result.

This is one learning loop: direct Run Mode establishes what happened, then Debug
Mode reveals how it happened.

## Reusable Debugging Laboratory template

Use the following seven-part structure when adding a **Debugging Laboratory** to a
chapter. Replace every italicized prompt with details verified against the source
and `.vscode/launch.json`. A laboratory is not a second command-line walkthrough:
it must expose a state transition or invariant that Run Mode's output cannot show.

### Goal

*Name the banking or software-engineering concept the learner will observe. State
the lesson without describing debugger controls.*

### Open the Source

*Give the exact repository-relative path to the implementation and name the
relevant function or class. Briefly connect that code to the chapter's concept.*

### Set the Breakpoint

*Identify a stable function and a recognizable operation inside it rather than a
line number. Say what has and has not happened when execution pauses, and explain
why that boundary makes the hidden state meaningful.*

### Launch the Debugger

*Give the debugger configuration's exact name from `.vscode/launch.json`. Describe
the deterministic scenario it starts; do not repeat setup instructions from
Chapter 0 or create a new configuration merely for the prose.*

### Observe

*List the precise local variables, objects, attributes, or side-effect-free Watch
expressions to inspect before stepping. Give their expected values and distinguish
requests (intent), authoritative facts, workflow results, and derived views.*

### Step Through

*Give an intentional sequence of Step Over, Step Into, Step Out, and Continue
actions. For every transition, state what changes, what remains unchanged, and why
that difference demonstrates the chapter's engineering concept.*

### Engineering Observation

*Conclude with the system-design lesson rather than a recap of debugger controls.
Explain why a financial system benefits from the observed invariant and what risk
the design avoids.*

Chapter 5's [Debugging Laboratory](05-deposits.md#debugging-laboratory) is the
reference implementation. It demonstrates all seven parts against a small flow in
which intent becomes an immutable fact and a balance is subsequently derived.

## Assumptions for future chapters

Before applying the template across the book, verify these assumptions chapter by
chapter:

- an existing launch configuration reaches the chapter's real execution flow;
- the named source path, function, and variables still exist at the current
  revision;
- the breakpoint scope is verified explicitly: identify what exists before the
  highlighted line, what is created by executing it, what object state changed
  earlier, and what changes only later;
- the scenario is deterministic and its expected values agree with its tests;
- stepping into a helper reveals a useful domain rule rather than library or
  generated code; and
- the laboratory adds an internal observation that the chapter's CLI output does
  not already teach.

## Prepared launch configurations

The repository provides one convenient CLI entry point for every Chapter 1–18
Debugging Laboratory:

- **Debug: Compare Institutions**
- **Debug: Run Member Onboarding**
- **Debug: Replay Chapter Ledger**
- **Debug: Project Balances**
- **Debug: Post One Deposit**
- **Debug: Process Withdrawals**
- **Debug: Process Internal Transfers**
- **Debug: Run ACH Timeline**
- **Debug: Run ACH Return Timeline**
- **Debug: Reconcile Settlement**
- **Debug: Process Payment Queue**
- **Debug: Run Worker Capacity**
- **Debug: Run Retries**
- **Debug: Observe Duplicate Payments**
- **Debug: Process Idempotently**
- **Debug: Process Out-of-Order Events**
- **Debug: Isolate Dead Letters**
- **Debug: Run End-to-End Laboratory**

These names are the exact inventory in `.vscode/launch.json`. A launch
configuration is only a convenient entry point. The educational value comes from
choosing a meaningful breakpoint, verifying its scope, and observing a real state
transition with accurate before-and-after expectations. Chapter 5 remains the
reference implementation for the canonical seven-heading format.
