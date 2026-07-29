"""Command-line experiments for the laboratory."""

import argparse
from collections.abc import Sequence

from bank_sim import __version__
from bank_sim.ach import describe_ach, describe_ach_timeline
from bank_sim.ach_returns import describe_ach_return, describe_ach_return_timeline
from bank_sim.balances import (
    chapter_pending_transactions,
    describe_balance,
    describe_pending,
    project_balances,
)
from bank_sim.deposits import chapter_deposit_requests, describe_deposits
from bank_sim.institutions import (
    compare_institutions,
    describe_institution,
    harbor_community_credit_union,
)
from bank_sim.ledger import chapter_ledger, describe_ledger, describe_replay
from bank_sim.onboarding import (
    describe_application,
    describe_onboarding_scenarios,
    successful_onboarding,
)
from bank_sim.payment_queues import (
    describe_payment_capacity,
    describe_payment_queue,
)
from bank_sim.settlement import (
    describe_reconciliation,
    describe_reconciliation_exceptions,
    describe_settlement,
)
from bank_sim.transfers import describe_transfer, describe_transfers
from bank_sim.withdrawals import describe_withdrawal, describe_withdrawals


def build_parser() -> argparse.ArgumentParser:
    """Build the command parser."""
    parser = argparse.ArgumentParser(prog="bank-sim")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("doctor", help="verify the laboratory environment")
    subparsers.add_parser("institution", help="describe the fictional institution")
    subparsers.add_parser(
        "compare-institutions", help="compare bank and credit-union ownership"
    )
    subparsers.add_parser("member-apply", help="run one successful member application")
    subparsers.add_parser(
        "member-onboarding", help="show deterministic member-application outcomes"
    )
    subparsers.add_parser("ledger", help="show the immutable ledger timeline")
    subparsers.add_parser("ledger-replay", help="replay the ledger balance projection")
    subparsers.add_parser(
        "balance", help="show current, pending, and available balances"
    )
    subparsers.add_parser(
        "pending", help="show authorized transactions awaiting posting"
    )
    subparsers.add_parser("deposit", help="post one deposit and replay its balance")
    subparsers.add_parser("deposits", help="post several deposits with replay")
    subparsers.add_parser("withdrawal", help="approve one withdrawal and replay")
    subparsers.add_parser(
        "withdrawals", help="show approved and rejected withdrawal requests"
    )
    subparsers.add_parser("transfer", help="post one internal transfer and replay")
    subparsers.add_parser(
        "transfers", help="show posted and rejected internal transfers"
    )
    subparsers.add_parser("ach", help="run one outbound ACH transfer")
    subparsers.add_parser("ach-timeline", help="show the outbound ACH timeline")
    subparsers.add_parser("ach-return", help="return one completed outbound ACH")
    subparsers.add_parser(
        "ach-return-timeline", help="show the ACH transfer and return timeline"
    )
    subparsers.add_parser("settlement", help="show internal settlement expectations")
    subparsers.add_parser("reconcile", help="reconcile a matched external report")
    subparsers.add_parser(
        "reconciliation-exceptions", help="show settlement discrepancies"
    )
    subparsers.add_parser("payment-queue", help="run queued ACH work")
    subparsers.add_parser(
        "payment-capacity", help="compare deterministic worker capacities"
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
    if args.command == "member-apply":
        print(describe_application(successful_onboarding()))
        return 0
    if args.command == "member-onboarding":
        print(describe_onboarding_scenarios())
        return 0
    if args.command == "ledger":
        print(describe_ledger(chapter_ledger()))
        return 0
    if args.command == "ledger-replay":
        print(describe_replay(chapter_ledger()))
        return 0
    if args.command == "balance":
        projection = project_balances(chapter_ledger(), chapter_pending_transactions())
        print(describe_balance(projection))
        return 0
    if args.command == "pending":
        print(describe_pending(chapter_pending_transactions()))
        return 0
    if args.command == "deposit":
        print(describe_deposits(chapter_deposit_requests()[:1]))
        return 0
    if args.command == "deposits":
        print(describe_deposits(chapter_deposit_requests()))
        return 0
    if args.command == "withdrawal":
        print(describe_withdrawal())
        return 0
    if args.command == "withdrawals":
        print(describe_withdrawals())
        return 0
    if args.command == "transfer":
        print(describe_transfer())
        return 0
    if args.command == "transfers":
        print(describe_transfers())
        return 0
    if args.command == "ach":
        print(describe_ach())
        return 0
    if args.command == "ach-timeline":
        print(describe_ach_timeline())
        return 0
    if args.command == "ach-return":
        print(describe_ach_return())
        return 0
    if args.command == "ach-return-timeline":
        print(describe_ach_return_timeline())
        return 0
    if args.command == "settlement":
        print(describe_settlement())
        return 0
    if args.command == "reconcile":
        print(describe_reconciliation())
        return 0
    if args.command == "reconciliation-exceptions":
        print(describe_reconciliation_exceptions())
        return 0
    if args.command == "payment-queue":
        print(describe_payment_queue())
        return 0
    if args.command == "payment-capacity":
        print(describe_payment_capacity())
        return 0
    return 2  # pragma: no cover - argparse rejects unknown commands
