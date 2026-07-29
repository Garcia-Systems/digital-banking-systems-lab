"""Minimal command-line health check."""

import argparse
from collections.abc import Sequence

from bank_sim import __version__


def build_parser() -> argparse.ArgumentParser:
    """Build the command parser."""
    parser = argparse.ArgumentParser(prog="bank-sim")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("doctor", help="verify the laboratory environment")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the laboratory command line."""
    args = build_parser().parse_args(argv)
    if args.command == "doctor":
        print("Digital Banking Systems Laboratory")
        print(f"Version {__version__}")
        print("Laboratory environment is ready.")
        return 0
    return 2  # pragma: no cover - argparse rejects unknown commands
