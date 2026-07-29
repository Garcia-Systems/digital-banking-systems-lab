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

Chapter 4 derives current, pending, and available balances. Authorized pending
transactions remain separate from the authoritative ledger, and the deterministic
available-balance rule demonstrates why institutions show multiple balances. It
intentionally defers posting, settlement, and all payment workflows.

Chapter 5 introduces the first ledger-appending business operation. Valid deposits
append immutable credit entries, and replay after each append derives the updated
balance. It intentionally defers withdrawals, payment rails, pending deposits,
settlement, reconciliation, and operational concerns.

Chapter 6 introduces withdrawal approval. Valid requests are checked against the
available-balance projection before debit entries are appended; invalid and
insufficient-funds requests leave the ledger unchanged. It intentionally defers
overdrafts, fees, transfers, payment rails, fraud detection, and settlement.

Chapter 7 introduces internal transfers. Valid, sufficiently funded requests append
a source debit and destination credit as one atomic in-memory operation, then replay
both accounts. It intentionally defers external institutions, ACH, wires, payment
networks, settlement, retries, reconciliation, and distributed transactions.

Chapter 8 introduces outbound ACH credits as delayed workflows. A validated request
places a pending debit, advances through a simulated network on virtual time, and
posts exactly one source debit at completion. It intentionally defers ACH returns,
real payment formats and integrations, settlement, reconciliation, and complete
retry and idempotency infrastructure.

Chapter 9 introduces deterministic ACH returns. A return references one completed
outbound transfer and appends a full corrective credit without editing the original
debit. Production return rules, settlement, reconciliation, and generalized
idempotency remain deferred.

Chapter 10 introduces settlement expectations derived from completed ACH transfers
and returns, and reconciliation against an independently constructed external
report. Stable classification and totals expose missing, unexpected, mismatched,
and duplicate records without changing workflows or ledger history. Operational
exception resolution and real network settlement remain deferred.

Chapter 11 introduces a deterministic FIFO queue for accepted ACH transfers and
returns. Fixed per-minute worker capacity changes backlog and completion latency
without changing ordered ledger outcomes. Retries, failures, dead-letter queues,
distributed workers, and load balancing remain deferred.

Chapter 12 introduces deterministic worker pools and compares throughput, wait time,
utilization, and backlog under fixed capacities without changing ledger outcomes.

Chapter 13 introduces scripted transient failures, fixed-delay retries, and bounded
attempts. Successful recovery creates one financial effect, while exhausted work
creates none.

Chapter 14 introduces scripted duplicate request delivery caused by client retry,
network duplication, and queue replay. Its isolated naïve processor intentionally
creates duplicate ledger effects so Chapter 15 can motivate idempotent processing.

Chapter 15 introduces deterministic idempotency keys and an in-memory result store.
Repeated deliveries return the original completed result while exactly one unique
business operation appends exactly one ledger debit. Distributed storage,
expiration, and consensus remain deferred.

Chapter 16 introduces scripted out-of-order delivery, per-payment sequences and
revisions, deterministic future-event buffering, and explicit stale and duplicate
rejection before ledger effects. Distributed ordering protocols remain deferred.

Chapter 17 introduces a deterministic dead-letter queue for retry exhaustion,
invalid workflow states, invalid payments, and stale events. Isolation stops future
automatic retries and preserves diagnostic context without modifying financial
history. Manual replay, operator approval, and automatic recovery remain deferred.

Future chapters are planned to progress incrementally through:

1. account opening;
2. additional external-payment behavior;
3. digital banking channels and their operational boundaries;
4. distributed financial systems and failure handling;
5. lending and loan servicing;
6. fraud signals, controls, and explainable detection;
7. analytics and carefully evaluated machine learning; and
8. observability, reliability, and operations.

The sequence may evolve as the textbook grows, but every chapter must connect one
business concept, one software-engineering concept, one deterministic simulation,
one command-line experiment, and one engineering lesson. Models appear only when
their lessons arrive; placeholders do not substitute for explanations.
