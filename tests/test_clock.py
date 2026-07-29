"""Focused tests for deterministic virtual time."""

import pytest

from bank_sim.clock import VirtualClock


def test_clock_starts_at_zero_by_default() -> None:
    assert VirtualClock().time == 0


def test_clock_accepts_nonnegative_initial_time() -> None:
    assert VirtualClock(4).time == 4


@pytest.mark.parametrize("value", [-1, 1.5, True])
def test_clock_rejects_invalid_initial_time(value: object) -> None:
    with pytest.raises(ValueError, match="nonnegative integer"):
        VirtualClock(value)  # type: ignore[arg-type]


def test_clock_advances_deterministically() -> None:
    clock = VirtualClock(2)
    assert clock.advance_by(3) == 5
    assert clock.advance_to(8) == 8
    assert clock.advance_by(0) == 8


def test_clock_cannot_move_backward() -> None:
    clock = VirtualClock(3)
    with pytest.raises(ValueError, match="backward"):
        clock.advance_to(2)


@pytest.mark.parametrize("operation", ["advance_by", "advance_to"])
def test_clock_rejects_invalid_advancement(operation: str) -> None:
    with pytest.raises(ValueError, match="nonnegative integer"):
        getattr(VirtualClock(), operation)(-1)
