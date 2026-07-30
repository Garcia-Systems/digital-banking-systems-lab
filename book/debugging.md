# Debugging a Banking Simulation

Debugging is introduced as a core learning mode in
[Chapter 0: Setting Up Your Digital Banking Laboratory](00-setting-up-your-laboratory.md#debugging-the-laboratory).
Start there for the beginner-friendly VS Code and Dev Container setup and the
explanation of debugger controls and state views. Chapter 5 contains the canonical
exercise that later chapters should follow.

Remember the environment boundary:

- From a host terminal, use `docker compose run --rm lab bank-sim ...`.
- From VS Code's Dev Container terminal, use `bank-sim ...` directly because that
  terminal is already inside the reproducible environment.

Run Mode answers **“What happened?”** Debug Mode answers **“How did it happen?”**
Both execute the same deterministic simulation; the debugger only lets you pause
and observe the banking objects along the way.

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
- the chosen pause occurs before the state transition, so the before and after
  states can both be observed;
- the scenario is deterministic and its expected values agree with its tests;
- stepping into a helper reveals a useful domain rule rather than library or
  generated code; and
- the laboratory adds an internal observation that the chapter's CLI output does
  not already teach.

At present the repository has one prepared configuration, **Debug: Post One
Deposit**. Other chapters may therefore require separately reviewed debugger
configurations before they can adopt the pattern; this documentation task does not
add or rename any configuration.
