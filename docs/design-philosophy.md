# Design Philosophy

An executable textbook treats prose, code, and tests as one teaching artifact. Prose states a claim, implementation makes the mechanism inspectable, and tests demonstrate the claim repeatedly.

## Small mechanisms, strong contracts

Chapter 0 contains only virtual time, event ordering, and environment verification. It avoids speculative frameworks. Future banking chapters can build focused lessons on these mechanisms without inheriting unrelated abstractions.

## Virtual rather than real time

Wall-clock behavior makes education slow and flaky. Explicit integer time lets a reader advance a scenario instantly and observe exact boundaries. Synchronous callbacks keep causal order visible.

## Tests as demonstrations

Focused tests document normal behavior, boundaries, and failures. A callback that raises is removed, its exception remains visible, and later work stays queued. Stating and testing this behavior is more valuable than hiding it behind recovery policy.

## An incremental textbook, not a production monolith

Harbor Community Credit Union provides a consistent fictional setting, not a claim of production readiness. Banking models should appear only when their business and engineering lessons are explained, while the simple infrastructure contracts remain stable.
