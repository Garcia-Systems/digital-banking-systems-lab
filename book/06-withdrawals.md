# Chapter 6: Withdrawals

## Learning objectives

By the end of this chapter, you will be able to:

- describe a withdrawal request and its approval states;
- explain how available funds determine approval or rejection;
- explain why validation must precede an immutable ledger append; and
- replay balances after successful and rejected requests.

## Withdrawal workflow

A `WithdrawalRequest` carries a withdrawal identifier, account identifier, amount
in integer cents, and description. Processing produces a `Withdrawal` whose status
is `Posted` or `Rejected`. `Received` names the request's initial workflow state.
The result describes a decision; the ledger remains the authority for money.

The intentionally small workflow is:

1. receive and validate the request;
2. derive available balance with the existing balance projection;
3. compare the requested amount with available funds;
4. reject without an append, or append one debit entry; and
5. replay the ledger.

## Validation before history

A blank withdrawal identifier, blank account identifier, zero amount, or negative
amount is rejected immediately. Amounts must be integer cents. These checks happen
before the ledger is touched. Invalid input is not a financial fact and therefore
must not become immutable financial history.

This ordering matters because an append-only ledger cannot repair a bad append by
editing or deleting it. A compensating entry would itself become history and would
misrepresent a request that should never have posted.

## Available balance checks

This chapter reuses the Chapter 4 projection. A request succeeds only when its
amount is less than or equal to available balance. For example, $120.00 requested
against $500.00 is posted and replay produces $380.00. Requesting exactly the
available amount is also allowed.

## Rejected requests

A $150.00 request against $100.00 is rejected deterministically with the reason
`Insufficient available funds`. The returned workflow state preserves that useful
decision, but no debit entry is appended. The ledger and its replayed balance remain
unchanged.

Rejection is not a debit followed by a correction. It is a decision made before
financial history exists.

## Ledger replay

Successful withdrawals append debit entries in deterministic sequence order. From
a $500.00 beginning balance, withdrawals of $50.00, $75.25, and $20.00 replay to
$354.75. Exact integer cents avoid floating-point rounding, and no object stores or
mutates a balance total.

A rejected withdrawal contributes no replay step. Replaying after rejection yields
the same result as replaying immediately before it.

## Deterministic CLI walkthroughs

Run a successful $120.00 withdrawal against $500.00:

```bash
bank-sim withdrawal
```

The output shows the request, validation, posted debit, replay, and final balance of
`$380.00`.

Run both a successful request and an insufficient-funds request:

```bash
bank-sim withdrawals
```

The rejected request reports `Insufficient available funds` and zero appended
entries. One final replay includes only the opening credit and successful debit.
Both commands use fixed identifiers, amounts, and ordering, so repeated runs match.

## Engineering lesson

> Immutable history should only record successful business operations. Failed
> requests belong in workflow state, not in the financial ledger.

Separating decision-making from recording prevents rejected activity from changing
balances and preserves an explainable ledger. Validation asks whether a business
operation may occur; append records that the approved operation did occur.

## Limitations

This simulation has no overdraft protection, credit line, fee, ATM, card hold,
cash dispensing, check, settlement, fraud detection, database, networking, or
background processing. It models only immediate educational decisions against an
existing balance projection and is not production banking software.

## Transition to internal transfers

An internal transfer will coordinate movement between two accounts while retaining
the same discipline: decide whether the complete operation is valid before writing
authoritative history. Transfers, including their atomicity and paired entries, are
intentionally deferred to a later chapter.
