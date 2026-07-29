# Chapter 15: Idempotent Payment Processing

## Learning objectives

This chapter answers two related questions. **Business:** how can an institution
accept duplicate payment requests without charging a customer repeatedly?
**Engineering:** how can software distinguish another delivery of existing customer
intent from a new operation? You will use idempotency keys, return stored results,
and verify exactly one financial effect under safe retries.

> **Reliable payment systems allow duplicate requests while ensuring that money
> moves exactly once.**

## Why retries create duplicate requests

A sender that times out does not know whether the receiver failed or completed the
payment and lost the response. Retrying is therefore reasonable, and a network or
queue may also redeliver work. Transport reliability cannot promise that each
message arrives only once. Business correctness must tolerate this uncertainty.

## Review of Chapter 14

Chapter 14 deliberately treated every delivery as new. Three deliveries of one
`$250.00` payment appended three debit entries. Starting from `$1,000.00`, naïve
processing ended at `$250.00`, although the customer intended a final balance of
`$750.00`. That unsafe demonstration remains available for comparison; Chapter 15
does not redesign or conceal it.

## Business identity versus request delivery

A delivery is a transport event. A business operation is customer intent. Delivery
numbers and arrival times can change while the operation remains the same. The
client supplies a deterministic `IdempotencyKey` for that intent, and every retry or
redelivery carries the same key. A genuinely new payment receives a new key.

The key is not merely the transport's message identifier. The simulation derives
`IDEMPOTENCY-PAY-001` for all deliveries of `PAY-001`. Reusing a key with another
request identifier or amount is rejected rather than silently returning an
unrelated result.

## In-memory idempotency store

`IdempotencyStore` maps each key to one `IdempotencyRecord`. A completed record
retains the original request identifier, first processing time, completion status,
stored `PaymentProcessingResult`, and duplicate-delivery count. Insertion order
makes inspection deterministic.

The store lookup occurs **before** the ledger append. For a new key,
`IdempotentPaymentProcessor` appends one debit and remembers its completed result.
For an existing matching key, it skips financial processing and returns the same
result object. The ledger remains the authority for money; the idempotency layer
only decides whether this business operation was already processed.

## Duplicate acknowledgement

A repeated delivery is valid input, not necessarily an error. It receives an
`IdempotentAcknowledgement` marked as a duplicate and containing the original
result, including the original ledger entry identifier and processing time. Thus a
client can safely retry an uncertain request and still learn the outcome.

## Preserving financial correctness

The canonical deterministic scenario begins at `$1,000.00` and delivers the same
`$250.00` request three times:

1. delivery 1 finds no record, appends one debit, and stores the result;
2. delivery 2 finds the record and returns that result;
3. delivery 3 also returns that result.

The final balance is `$750.00` and the payment creates exactly one ledger entry.
Repeated acknowledgements do not mean repeated balance changes.

## Deterministic examples and statistics

Focused scenarios cover one unique request, two deliveries, three deliveries, a
mixed workload, and a transient failure followed by success and redelivery. The
processor reports total requests received, unique business operations, duplicate
deliveries, duplicate requests prevented, stored records, and ledger entries
created. Counts use integers and all arrival and processing times are scripted.

In the triple-delivery example the measurements are three received requests, one
unique operation, two duplicates prevented, one stored record, and one debit.

## CLI walkthroughs

Run protected processing:

```console
docker compose run --rm lab bank-sim idempotency
```

The report shows all three deliveries, their shared key, original processing,
duplicate acknowledgements, the `$750.00` final balance, and one ledger debit.

Compare the same workload under both approaches:

```console
docker compose run --rm lab bank-sim idempotency-comparison
```

Chapter 14 produces three debits and `$250.00`; Chapter 15 produces one debit and
`$750.00`. Because the workload is identical, the changed outcome comes from the
idempotency decision rather than a different delivery script.

## Retry compatibility

Chapter 13's scheduler can retry a transient failure before invoking successful
payment work. On success the idempotent processor creates the record and debit.
Any later delivery consults that record and returns the completed result. The retry
scheduler still controls *when* work is attempted; idempotency controls *whether*
that business intent may create a financial effect.

## Engineering lesson

**Reliable payment systems allow duplicate requests while ensuring that money moves
exactly once.** Idempotency protects business correctness even when transport
reliability cannot be guaranteed. Safe retries require a stable business identity,
an early lookup, and a stored result—not an assumption of exactly-once delivery.

## Limitations

This teaching store lives in one process, retains records forever, and has no
database, Redis, expiration, distributed lock, cross-region replication, or
consensus. It models synchronous decisions and does not solve races between
processes. The simulation also omits dead-letter queues and production security,
authentication, recovery, and audit controls.

## Transition to out-of-order events

Idempotency answers whether an operation has already produced its business result;
it does not decide whether events arrived in a meaningful order. The next chapter
can preserve the one-effect guarantee while examining out-of-order events as a
separate coordination problem.
