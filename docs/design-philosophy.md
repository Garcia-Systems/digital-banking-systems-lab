# Design Philosophy

An executable textbook treats prose, code, and tests as one teaching artifact. Prose states a claim, implementation makes the mechanism inspectable, and tests demonstrate the claim repeatedly.

## Small mechanisms, strong contracts

The reusable layer contains only virtual time, event ordering, and environment verification. It avoids speculative frameworks. A future laboratory can build a focused lesson on these mechanisms without inheriting unrelated abstractions.

## Virtual rather than real time

Wall-clock behavior makes education slow and flaky. Explicit integer time lets a reader advance a scenario instantly and observe exact boundaries. Synchronous callbacks keep causal order visible.

## Tests as demonstrations

Focused tests document normal behavior, boundaries, and failures. A callback that raises is removed, its exception remains visible, and later work stays queued. Stating and testing this behavior is more valuable than hiding it behind recovery policy.

## A template, not a monolith

Each subject starts from a copy or GitHub template. The copy should adopt its own identity and learning path while preserving the simple infrastructure contracts. Improvements that benefit every future laboratory belong here; subject features do not.
