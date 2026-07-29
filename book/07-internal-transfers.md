# Chapter 7: Internal Transfers

## Learning objectives

By the end of this chapter, you will be able to:

- identify the source and destination accounts in an internal transfer;
- distinguish the source debit from the destination credit;
- explain why both entries form one atomic business operation; and
- replay both account histories to derive their new balances.

## Transfer workflow

A `TransferRequest` names a transfer, two distinct accounts, an amount in integer
cents, and a description. Processing returns a `TransferResult`: its `Transfer`
records a `Received`, `Posted`, or `Rejected` workflow outcome, while its entry
tuple reports the immutable facts created for a posted transfer. The ledger—not
the workflow object—remains the authoritative financial record.

The deliberately small workflow is:

1. receive and validate the request;
2. replay the source account to determine available funds;
3. reject without writing if the funds are insufficient;
4. construct a source debit and destination credit;
5. atomically validate and append the pair; and
6. replay both account histories.

Blank identifiers, nonpositive amounts, and identical source and destination
accounts are invalid. They are rejected before ledger interaction. A request above
the source balance is rejected with `Insufficient available funds`, also without
an append.

## Coordinated ledger entries

A successful $150.00 transfer from an account holding $1,000.00 to one holding
$250.00 appends two facts. The source debit reduces its replayed balance to $850.00;
the destination credit increases its replayed balance to $400.00. No stored balance
is moved or edited.

Both entries carry deterministic identifiers derived from the transfer identifier
and occupy adjacent sequence positions. Their common business meaning comes from
the transfer workflow, while their debit and credit directions preserve each
account's financial history.

## Atomic business operations

The in-memory ledger's batch append validates the complete pair before mutating its
entry collection. Therefore either both entries exist or neither exists. A failure
in the prospective credit cannot leave behind its debit. Insufficient funds and
invalid requests never reach batch creation.

This is intentionally an educational, single-process definition of atomicity.
Production banking systems use database transactions or other durable transactional
mechanisms, plus operational controls, to enforce the same all-or-nothing property
across failures.

## Replay for both accounts

Account replay scans canonical ledger order and applies only facts belonging to the
requested account. Repeating the fixed scenario always produces source `$850.00`
and destination `$400.00`. Rejected scenarios add no facts, so replay is unchanged.

## Deterministic CLI walkthroughs

Run the successful scenario:

```bash
bank-sim transfer
```

The command displays the request, validation, paired debit and credit, replay, and
both resulting balances.

Run all three teaching outcomes:

```bash
bank-sim transfers
```

This adds a $100.00 request against $50.00 and a same-account request. Each is
rejected with a deterministic reason and reports zero appended entries. Fixed data,
integer cents, synchronous processing, and canonical sequence order keep every run
identical.

## Engineering lesson

> A transfer is not a single balance change. It is a coordinated set of immutable
> ledger entries that must succeed together.

Validation decides whether the entire business operation may occur. Atomic append
then records both consequences. Replay observes the resulting history; it does not
perform the transfer.

## Limitations

This laboratory has no database, concurrency, crash recovery, retries, overdrafts,
fees, settlement, reconciliation, fraud detection, notifications, or distributed
transactions. It models only a synchronous transfer between accounts represented
inside one in-memory institution and is not production banking software.

## Transition to external payments

Moving money outside an institution introduces payment rails, counterparties,
messages, settlement, failure handling, and reconciliation. ACH, wires, card
networks, and every other external payment mechanism remain intentionally
unimplemented for later chapters.
