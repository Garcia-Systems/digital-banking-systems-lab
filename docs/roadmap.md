# Learning Roadmap

Chapter 0 establishes deterministic virtual time, synchronous scheduling, tooling,
and packaging. It implements no banking-domain behavior.

Chapter 1 introduces immutable financial-institution identity. It compares a
shareholder-owned bank with the fictional member-owned Harbor Community Credit
Union while keeping their shared high-level software needs visible. It intentionally
does not implement those capabilities.

Chapter 2 introduces the first person-level workflow: a membership application
with explicit submission, review, eligibility, simulated identity-verification,
and decision states. It preserves ordered transition history while intentionally
deferring permanent members, accounts, and all money movement.

Chapter 3 introduces the first representation of money: immutable, append-only
ledger entries using exact integer cents. A deterministic replay derives only the
current balance, establishing that ledger history—not a balance—is authoritative.
It intentionally defers business workflows and richer balance views.

Future chapters are planned to progress incrementally through:

1. account opening and richer balance concepts, including pending activity, holds,
   and available funds;
2. controlled movement of funds and payment processing;
3. digital banking channels and their operational boundaries;
4. distributed financial systems, reconciliation, and failure handling;
5. lending and loan servicing;
6. fraud signals, controls, and explainable detection;
7. analytics and carefully evaluated machine learning; and
8. observability, reliability, and operations.

The sequence may evolve as the textbook grows, but every chapter must connect one
business concept, one software-engineering concept, one deterministic simulation,
one command-line experiment, and one engineering lesson. Models appear only when
their lessons arrive; placeholders do not substitute for explanations.
