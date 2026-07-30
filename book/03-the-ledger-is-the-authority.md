# Chapter 3: The Ledger Is the Authority

![An append-only ledger recording authoritative financial history from which balances are derived](../images/chapters/chapter-03-the-ledger-is-the-authority.png)

## Learning objectives

After this chapter, you should be able to:

- explain why a financial institution records each change in money as a durable fact;
- distinguish authoritative ledger history from a derived balance;
- represent money exactly as integer cents rather than floating-point values;
- describe how immutability, sequence numbers, and simulated time make replay
  deterministic; and
- rebuild a current-balance projection by replaying a ledger from the beginning.

## Why ledgers exist

A balance answers a useful question: "How much does this history add up to now?"
It does not explain how the institution arrived there. Financial software needs a
permanent record of each change so that the result can be understood and rebuilt.
That record is the ledger.

This chapter's ledger contains only fictional identifiers, an exact amount, a
credit-or-debit direction, a description, a sequence number, and a simulated
posting time. Each entry is a fact about money. No entry initiates a deposit,
withdrawal, transfer, or payment; those are workflows for later chapters.

## Money without floating point

`Money` stores a positive integer number of cents. One thousand dollars is
`100_000` cents and fifty-five dollars and twenty-five cents is `5_525` cents.
Integer arithmetic is exact: it cannot introduce the binary rounding surprises
that floating-point values can. The entry type supplies the direction, so an entry
amount itself is always greater than zero.

This is a deliberately small choice for a single-currency lesson. Production
money types also need explicit currency and carefully defined rules for rounding,
limits, exchange, and serialization.

## Immutable history

`LedgerEntry` and `Money` are frozen values. Once created, their fields cannot be
assigned new values. `Ledger.append` accepts only the next contiguous sequence,
rejects duplicate identifiers, and prevents simulated posting time from moving
backward. The ledger exposes its entries as a tuple snapshot and provides no
update or delete operation.

Append-only does not mean "a list that callers promise not to edit." It means the
model permits one change: add the next valid fact. A correction in a real ledger
would be represented by additional facts, not by rewriting history, though this
chapter does not yet model corrections.

## Deterministic ordering and simulated posting time

Sequence numbers are the canonical replay order: `1`, `2`, `3`, without gaps or
duplicates. Posting times are nonnegative integers chosen by the simulation, not
wall-clock timestamps. The fixed teaching scenario uses `100`, `200`, and `300`.
There is no clock read, random identifier, database, network, or concurrent writer.
The same inputs therefore always produce the same ordered history and output.

## Replay

Replay begins at zero and visits every entry in sequence order:

```text
balance = 0
for each entry from sequence 1 onward:
    if Credit: balance = balance + amount_in_cents
    if Debit:  balance = balance - amount_in_cents
return balance
```

The algorithm validates contiguous ordering, changes only its local `balance`, and
does not mutate the ledger or any entry. Replaying an empty ledger produces zero.
Repeating a replay produces the identical integer result.

## Projection: current balance

A projection is a view computed from authoritative facts. This chapter has exactly
one projection: **current balance**. It starts at zero, adds credits, and subtracts
debits. The canonical ledger projects this result:

```text
100000 - 12000 - 5525 = 82475 cents = $824.75
```

There is no stored balance to synchronize with history. If a displayed result is
lost, replay recreates it. If projection code changes, the immutable history can be
replayed under the corrected rule. This is why the balance is useful but is not
authoritative.

## Try the deterministic timeline

```bash
docker compose run --rm lab bank-sim ledger
```

Expected output:

```text
Seq  Type      Amount
1    Credit    +$1,000.00
2    Debit       -$120.00
3    Debit        -$55.25
```

The timeline is stable because all data and ordering are fixed. Formatting also
works directly from cents rather than converting through floating point.

## Replay it step by step

```bash
docker compose run --rm lab bank-sim ledger-replay
```

Expected output:

```text
Ledger replay
1. Credit +$1,000.00 → $1,000.00
2. Debit -$120.00 → $880.00
3. Debit -$55.25 → $824.75

Final balance:
$824.75
```

Each line exposes the operation and running projection. The final number is not a
second source of truth; it is simply the last result of replay.

## Authoritative state and derived views

Treating a mutable balance field as authoritative loses the explanation behind the
number. A bug, partial update, or manual edit could change it without preserving
what happened. An immutable history retains the facts needed to recalculate and
inspect the view. Later systems may cache projections for performance, but a cache
does not become the authority merely because it is faster to read.

## Engineering lesson

> The ledger is authoritative because history can always be replayed. Every
> balance is a derived view of that history.

This distinction is foundational: facts are recorded once; questions about their
current meaning are answered by projections. Correctness is more important than
optimizing this first, intentionally straightforward replay.

## Limitations

The ledger is only an in-memory educational model. It has one fictional account
identifier and an intentionally currency-free money type. It provides no database,
persistence, recovery, concurrency, authentication, authorization, audit controls,
privacy controls, regulatory recordkeeping, transaction boundaries, or distributed
coordination. Restarting the process discards it.

It also implements no account lifecycle, deposits, withdrawals, transfers,
payments, ACH, wires, interest, loans, fraud detection, settlement, reconciliation,
holds, reserved funds, pending balance, or available balance. Debits may project a
negative current balance because overdraft policy is not this chapter's lesson.

## Next: richer balance views

Current balance answers only what posted ledger history sums to. Financial systems
often need to distinguish posted money from pending activity, holds, and funds that
are available to use. The next chapter will build those balance concepts without
changing the principle established here: derived views do not replace their
authoritative history.

## Debugging Laboratory

### Goal

Observe immutable ledger facts being replayed in order to derive, rather than store, a balance.

### Open the Source

Open `src/bank_sim/ledger.py`. Find `replay`, which validates sequence order and applies each entry's credit or debit direction.

### Set the Breakpoint

Set a breakpoint on `balance = 0` in `replay`. At this boundary `entries` already contains the three authoritative `LedgerEntry` objects, but `balance` does not exist until the highlighted initialization executes.

### Launch the Debugger

Select **Debug: Replay Chapter Ledger**. It runs `ledger-replay` over the fixed Chapter 3 ledger.

### Observe

Before stepping, inspect `entries`: the ordered, frozen entries are a 100000-cent credit, a 12000-cent debit, and a 5525-cent debit, with sequences 1, 2, and 3. They are authoritative history. There is not yet a `balance`, `expected_sequence`, `entry`, or `direction` local.

### Step Through

1. Step Over initialization: `balance` appears as `0`; history is unchanged.
2. Enter the loop. `expected_sequence` and `entry` appear for sequence 1. After direction and accumulation, balance is `100000`.
3. Repeat for sequences 2 and 3. The progression is exactly `0`, `100000`, `88000`, `82475`; each frozen entry remains unchanged.
4. Continue. The CLI independently renders the same history and final `$824.75` projection.

### Engineering Observation

The ledger contains immutable financial facts; balance is a reconstruction derived by replaying those facts. Because history is authoritative, the result can be reproduced and explained without trusting a mutable running total.
