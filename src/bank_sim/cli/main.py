"""Command-line experiments for the laboratory."""

import argparse
from collections.abc import Sequence

from bank_sim import __version__
from bank_sim.institutions import (
    compare_institutions,
    describe_institution,
    harbor_community_credit_union,
)


def build_parser() -> argparse.ArgumentParser:
    """Build the command parser."""
    parser = argparse.ArgumentParser(prog="bank-sim")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("doctor", help="verify the laboratory environment")
    subparsers.add_parser("institution", help="describe the fictional institution")
    subparsers.add_parser(
        "compare-institutions", help="compare bank and credit-union ownership"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the laboratory command line."""
    args = build_parser().parse_args(argv)
    if args.command == "doctor":
        print("Digital Banking Systems Laboratory")
        print(f"Version {__version__}")
        print("Laboratory environment is ready.")
        return 0
    if args.command == "institution":
        print(describe_institution(harbor_community_credit_union()))
        return 0
    if args.command == "compare-institutions":
        print(compare_institutions())
        return 0
    return 2  # pragma: no cover - argparse rejects unknown commands
