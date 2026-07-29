# Chapter 14: Duplicate Payment Requests

## Learning objectives

This chapter explains why a financial institution can receive one payment request
more than once and why retries alone cannot guarantee one financial result. You will
observe repeated delivery, distinguish deliveries from intended business operations,
measure duplicate financial effects, and identify the need for idempotent processing.

> **A payment request may be delivered multiple times, even when the customer
> intended to pay only once.**

The laboratory intentionally demonstrates financially incorrect behavior in this
isolated chapter. It does not represent a safe production implementation.

## Why duplicate requests occur

A customer or application can submit one instruction, yet distributed components
cannot always agree about what happened. Three fixed scenarios illustrate common
causes:

* **Client retry:** processing succeeds, but confirmation does not reach the client.
  Unable to distinguish failure from a lost response, the client sends the identical
  request again.
* **Network duplicate:** the simulated transport repeats delivery of the same request.
* **Queue replay:** a queued payment is accidentally delivered again by the scripted
  scenario.

These do not imply that the customer intended several payments. They mean that an
original business operation had several deliveries.

## Retries versus duplicates

Chapter 13 retried attempts *inside one accepted request*. Its financial callback ran
only after a scripted transient failure and stopped after success. Chapter 14 models
a different boundary: the entire request arrives again as apparently new work.

Retry limits answer how often one local operation should be attempted after failure.
They do not establish whether two separately received messages represent the same
customer intent. Therefore retry logic alone is insufficient to prevent duplicate
financial processing.

## Network uncertainty and repeated delivery

A timeout describes what one participant observed, not what another participant did.
The receiver may have posted a payment immediately before its response disappeared.
The sender sees uncertainty and may reasonably retry. At-least-once-style delivery
also favors eventually delivering work, even if doing so repeats it.

The simulation uses no real network, queue, wall clock, or randomness. Each cause and
arrival is explicit in a `DeliverySequence`, making uncertainty reproducible without
pretending that distributed timing is predictable in production.

## Naïve processing and duplicate financial effects

`process_naively` processes every `PaymentDelivery` independently. Each delivery
creates a distinct ledger entry so the existing ledger's requirement for unique
entry identifiers remains intact. The original request identifier stays the same,
exposing that several entries came from one intended business operation.

This is intentionally wrong. With an initial balance of **$1,000.00** and one intended
payment of **$250.00**, a single delivery produces **$750.00**. Delivering the same
request twice makes the naïve processor debit twice and produce **$500.00**. The
customer intended one payment, but the institution performed two financial operations.

The demonstration does not silently recognize, reject, or suppress the second
delivery. Prevention belongs entirely to Chapter 15.

## Deterministic demonstrations

The chapter scripts four repeatable workloads:

1. **No duplicates:** one request is delivered once and the outcome is correct.
2. **One duplicate:** a client retry delivers one request twice.
3. **Multiple duplicates:** the network delivers one request three times.
4. **Mixed workload:** three unique payment identifiers arrive in four deliveries
   because one queued request is replayed.

`PaymentDelivery` records original request identifier, delivery number, simulated
arrival time, and delivery order. `DeliveryAttempt` records processing time, result,
and the resulting ledger entry. `DuplicateStatistics` reports deliveries received,
unique payment identifiers, duplicate deliveries, financial operations performed,
duplicate financial operations, and duplicate percentage. Percentages use integer
hundredths rather than floating-point arithmetic.

## CLI walkthroughs

Observe every workload:

```bash
docker compose run --rm lab bank-sim duplicates
```

The observation report displays every delivery and debit, then contrasts requests
received, unique business operations, and financial operations performed. Its warning
is deliberate: every delivery is processed and duplicate effects remain visible.

Inspect the canonical timeline:

```bash
docker compose run --rm lab bank-sim duplicate-timeline
```

```text
T+0 Payment request received
T+1 Payment processed
T+3 Duplicate request received
T+4 Payment processed again
```

The output contrasts the correct single-delivery balance of `$750.00` with the
incorrect duplicate-delivery balance of `$500.00`.

## Engineering lesson

**Delivery is not business intent.** A distributed system cannot assume every
request is unique. Reliable retry and repeated-delivery mechanisms may improve the
chance that work arrives, but without a way to recognize an already processed
business operation, naïve processing can repeat the movement of money.

## Limitations

This is an in-memory, synchronous, deterministic teaching model. Its delivery causes
and timestamps are scripted. It provides no real transport, durable queue, parallel
consumer, response loss, message ordering guarantee, or exactly-once delivery. It
also deliberately provides no request hash, idempotency key, duplicate suppression,
distributed lock, consensus, or duplicate correction.

## Transition to idempotent processing

Chapter 15 will introduce idempotent processing so repeated deliveries of one
business operation can produce one financial effect. Until then, the incorrect
second debit remains visible: observing the risk before solving it is the purpose of
this chapter.
