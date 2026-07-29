# Chapter 5: Deposits

## Learning objectives

By the end of this chapter, you will be able to:

- describe a deposit request and its validation;
- explain why posting appends an immutable credit entry;
- replay the ledger after one or several deposits; and
- distinguish a workflow result from the authoritative ledger.

## Why deposits append history

A deposit is a business request to record money received for an account. It does
not assign a new balance. Assigning a total would discard how the account reached
that total and could overwrite the effects of other operations. Posting instead
adds a fact to the end of history. The existing replay rule then derives the new
balance from all facts, old and new.

The `DepositRequest` carries a deposit identifier, account identifier, amount in
integer cents, and description. A successful workflow returns a `Deposit` with
`Posted` status, but that object is only a workflow result. The immutable credit
entry in the ledger is authoritative.

## Validation

The boundary immediately rejects a blank deposit identifier, blank account
identifier, zero amount, or negative amount with a clear validation exception.
Amounts must be integer cents. Invalid input creates no ledger entry: the example
does not silently repair, round, or post it. Although the small state vocabulary
includes `Received`, `Posted`, and `Rejected`, invalid requests fail at the boundary
rather than becoming posted deposits.

## Immutable ledger interaction

For a valid request, posting:

1. receives and validates the request;
2. assigns the next deterministic ledger sequence;
3. appends one immutable credit entry;
4. reports the deposit as posted; and
5. replays ledger entries to display the balance.

There is no balance field to increment. Entry identifiers derive from deposit
identifiers, and example ordering and posting times derive from ledger sequence;
there is no clock, random input, external service, or background work.

## Replay after deposits

With an empty ledger, posting $500.00 appends a $500.00 credit. Replay starts at
$0.00, applies that fact, and returns $500.00. Posting $250.00 and $75.50 afterward
does not edit either previous fact. Replay applies all three credits in sequence
and returns $825.50, with exact integer-cent precision.

## Deterministic CLI walkthroughs

Run one request from receipt through replay:

```bash
bank-sim deposit
```

```text
Request: DEP-0001 | HCCU-DEMO-001 | $500.00
Status: Received → Posted
Ledger entry: DEP-0001-ENTRY | Credit | $500.00
Running balance: $500.00

Final balance:
$500.00
```

Run all three requests and observe replay after each append:

```bash
bank-sim deposits
```

The running balances are `$500.00`, `$750.00`, and `$825.50`, in that order.
Repeating either command produces identical output.

## Engineering lesson

> Business operations create ledger history. Ledger history creates balances.

This separation preserves an explainable audit trail and makes a balance
reproducible. A workflow can be retried, inspected, or improved without turning a
mutable cached total into the financial authority.

## Limitations and transition to withdrawals

This chapter implements only immediately posted educational deposits. It omits
checks, ACH, cash logistics, tellers, ATMs, mobile capture, holds, pending deposits,
settlement, reconciliation, fraud, notifications, databases, and external systems.
It is not production banking software.

The next lesson can introduce withdrawals. A withdrawal will require its own
validation and debit entry, while preserving the same invariant: business
operations append history, and replay—not direct balance mutation—produces the
balance.
