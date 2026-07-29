"""A deterministic, synchronous event scheduler.

Events execute chronologically, with insertion order breaking equal-time ties.
An event is removed before its callback runs and the clock first advances to its
scheduled time.  Exceptions propagate without retrying the failed event; later
events remain queued, and history contains only successfully completed callbacks.
"""

import heapq
from collections.abc import Callable
from dataclasses import dataclass, field

from lab_sim.clock import VirtualClock

Callback = Callable[[], None]


@dataclass(order=True, frozen=True)
class _Event:
    time: int
    order: int
    callback: Callback = field(compare=False, repr=False)


@dataclass(frozen=True)
class Execution:
    """A successfully completed event, identified by time and insertion order."""

    time: int
    order: int


class EventScheduler:
    """Schedule no-argument callbacks against a :class:`VirtualClock`."""

    def __init__(self, clock: VirtualClock | None = None) -> None:
        self.clock = clock if clock is not None else VirtualClock()
        self._queue: list[_Event] = []
        self._next_order = 0
        self._history: list[Execution] = []

    @property
    def pending(self) -> int:
        """Return the number of queued events."""
        return len(self._queue)

    @property
    def history(self) -> tuple[Execution, ...]:
        """Return an immutable snapshot of successful execution history."""
        return tuple(self._history)

    def schedule_at(self, time: int, callback: Callback) -> None:
        """Schedule *callback* at an integer time not earlier than the clock."""
        if type(time) is not int or time < 0:
            raise ValueError("event time must be a nonnegative integer")
        if time < self.clock.time:
            raise ValueError("cannot schedule an event in the past")
        if not callable(callback):
            raise TypeError("callback must be callable")
        heapq.heappush(self._queue, _Event(time, self._next_order, callback))
        self._next_order += 1

    def schedule_after(self, delay: int, callback: Callback) -> None:
        """Schedule *callback* after a nonnegative integer delay."""
        if type(delay) is not int or delay < 0:
            raise ValueError("event delay must be a nonnegative integer")
        self.schedule_at(self.clock.time + delay, callback)

    def run_next(self) -> bool:
        """Run one event, returning ``False`` when the queue is empty."""
        if not self._queue:
            return False
        event = heapq.heappop(self._queue)
        self.clock.advance_to(event.time)
        event.callback()
        self._history.append(Execution(event.time, event.order))
        return True

    def run(self) -> None:
        """Run queued events until none remain or a callback raises."""
        while self.run_next():
            pass
