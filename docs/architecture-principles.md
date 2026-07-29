# Architecture Principles

1. **Deterministic first.** Identical inputs must lead to identical observations.
2. **Reproducibility.** Examples and tests must work without timing luck or external services.
3. **Simulation over production integration.** Model a concept locally instead of connecting production infrastructure.
4. **Educational clarity over optimization.** Prefer direct, readable code to clever performance techniques.
5. **Explicit state.** State and transitions must be visible and deliberately owned.
6. **Inspectable behavior.** Readers should be able to trace an outcome from code and tests.
7. **One major concept per chapter.** Each lesson should have a narrow learning objective.
8. **No hidden dependencies.** Requirements and inputs must be declared and observable.
9. **Dependency-free runtime code where practical.** Development tooling must not leak into the package contract.
10. **No randomness unless a lesson explicitly introduces controlled randomness.** Any such lesson must seed and explain it.
11. **No concurrency unless a lesson explicitly teaches concurrency.** The reusable scheduler remains synchronous.
12. **Separate reusable laboratory infrastructure from domain behavior.** The clock and scheduler are long-lived foundations; copies add subject code elsewhere.

These constraints make examples small enough to reason about and stable enough to serve as executable documentation.
