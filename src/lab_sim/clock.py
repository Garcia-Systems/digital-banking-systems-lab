"""Deterministic integer virtual time.

The clock is advanced explicitly; it never reads wall-clock time or waits.  Time is
nonnegative and monotonic so a simulation can be repeated exactly.
"""


class VirtualClock:
    """A small monotonic clock measured in integer simulation units."""

    def __init__(self, initial_time: int = 0) -> None:
        self._validate_time(initial_time)
        self._time = initial_time

    @property
    def time(self) -> int:
        """Return the current simulated time."""
        return self._time

    def advance_to(self, new_time: int) -> int:
        """Advance to *new_time* and return it; moving backward is prohibited."""
        self._validate_time(new_time)
        if new_time < self._time:
            raise ValueError("virtual time cannot move backward")
        self._time = new_time
        return self._time

    def advance_by(self, amount: int) -> int:
        """Advance by a nonnegative integer amount and return the new time."""
        self._validate_time(amount)
        return self.advance_to(self._time + amount)

    @staticmethod
    def _validate_time(value: int) -> None:
        if type(value) is not int or value < 0:
            raise ValueError("virtual time must be a nonnegative integer")
