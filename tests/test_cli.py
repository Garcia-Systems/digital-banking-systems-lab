"""Tests for the command line and its authoritative command inventory."""

import argparse
import subprocess
import sys
from pathlib import Path

import pytest

from bank_sim import __version__
from bank_sim.cli import main
from bank_sim.cli.main import build_parser

EXPECTED_COMMANDS = {
    "doctor",
    "institution",
    "compare-institutions",
    "member-apply",
    "member-onboarding",
    "ledger",
    "ledger-replay",
    "balance",
    "pending",
    "deposit",
    "deposits",
    "withdrawal",
    "withdrawals",
    "transfer",
    "transfers",
    "ach",
    "ach-timeline",
    "ach-return",
    "ach-return-timeline",
    "settlement",
    "reconcile",
    "reconciliation-exceptions",
    "payment-queue",
    "payment-capacity",
    "worker-capacity",
    "capacity-comparison",
    "retries",
    "retry-timeline",
    "duplicates",
    "duplicate-timeline",
    "idempotency",
    "idempotency-comparison",
    "ordering",
    "out-of-order",
    "dead-letter",
    "dead-letter-report",
    "laboratory",
    "operational-summary",
}


def command_names() -> list[str]:
    """Introspect the parser rather than maintaining a second implementation list."""
    action = next(
        action
        for action in build_parser()._actions
        if isinstance(action, argparse._SubParsersAction)
    )
    return list(action.choices)


def test_version_and_help_work_without_a_subcommand(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as version_exit:
        main(["--version"])
    assert version_exit.value.code == 0
    assert capsys.readouterr().out == f"bank-sim {__version__}\n"

    with pytest.raises(SystemExit) as help_exit:
        main(["--help"])
    assert help_exit.value.code == 0
    assert "usage: bank-sim" in capsys.readouterr().out


def test_cli_module_supports_debugger_launch() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "bank_sim.cli", "deposit"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "Ledger entry: DEP-0001-ENTRY | Credit | $500.00" in result.stdout


def test_command_inventory_is_complete_unique_documented_and_in_help(
    capsys: pytest.CaptureFixture[str],
) -> None:
    commands = command_names()
    assert set(commands) == EXPECTED_COMMANDS
    assert len(commands) == len(set(commands))

    with pytest.raises(SystemExit) as help_exit:
        main(["--help"])
    assert help_exit.value.code == 0
    help_output = capsys.readouterr().out
    reference = Path("docs/cli-reference.md").read_text()
    for command in commands:
        assert command in help_output
        assert f"`{command}`" in reference


@pytest.mark.parametrize("command", sorted(EXPECTED_COMMANDS))
def test_every_command_default_demonstration_succeeds(
    command: str, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main([command]) == 0
    assert capsys.readouterr().out


def test_doctor_reports_identity_and_version(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["doctor"]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "Digital Banking Systems Laboratory",
        "Version 1.0.0",
        "Laboratory environment is ready.",
    ]


@pytest.mark.parametrize(
    "document",
    [Path("README.md"), Path("book/00-setting-up-your-laboratory.md")],
)
def test_setup_documents_describe_the_dev_container_workflow(document: Path) -> None:
    """Keep setup aligned with direct Dev Container and host-side workflows."""
    text = document.read_text()
    lines = set(text.splitlines())

    direct_commands = {
        "bank-sim --help",
        "bank-sim institution",
        "pytest",
        "ruff check .",
    }
    host_docker_commands = {
        "docker compose build",
        "docker compose run --rm lab bank-sim institution",
    }

    assert direct_commands <= lines
    assert host_docker_commands <= lines
    clone_command = (
        "git clone https://github.com/Garcia-Systems/digital-banking-systems-lab.git"
    )
    assert clone_command in lines

    lower_text = text.lower()
    assert "dev container terminal" in lower_text
    assert "host" in lower_text and "git" in lower_text
    assert "host-side" in lower_text and "compose" in lower_text
    assert (
        "docker supplies" in lower_text or "docker is the reproducibility" in lower_text
    )


def test_chapter_zero_includes_host_repository_maintenance() -> None:
    """Keep Git maintenance on the host side of the Chapter 0 boundary."""
    text = Path("book/00-setting-up-your-laboratory.md").read_text()
    lines = set(text.splitlines())

    assert {"git status", "git pull"} <= lines
    assert "Git is normally used outside the Dev Container" in text


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        (
            "settlement",
            [
                "Internal settlement expectations",
                "Record count: 2",
                "ACH-001 | Outbound | $250.00 | T+40",
                "RETURN-001 | Return | $250.00 | T+40",
            ],
        ),
        (
            "reconcile",
            [
                "Settlement reconciliation",
                "Internal records: 2",
                "External records: 2",
                "Matched: 2",
                "Exceptions: 0",
                "Outbound totals: internal $250.00 | external $250.00 | "
                "difference $0.00",
                "Return totals: internal $250.00 | external $250.00 | difference $0.00",
                "Final result: Reconciled",
            ],
        ),
        (
            "reconciliation-exceptions",
            [
                "Reconciliation exception report",
                "ACH-002 | Missing externally | Outbound | Difference: -$125.00 | "
                "External: -",
                "ACH-003 | Amount mismatch | Outbound | Difference: -$1.00 | "
                "External: EXT-003",
                "ACH-004 | Duplicate externally | Outbound | Difference: $50.00 | "
                "External: EXT-004-A, EXT-004-B",
                "ACH-EXTERNAL-999 | Unexpected externally | Outbound | "
                "Difference: $80.00 | External: EXT-999",
                "Matched: 0",
                "Exceptions: 4",
                "Outbound totals: internal $475.00 | external $479.00 | "
                "difference $4.00",
                "Return totals: internal $0.00 | external $0.00 | difference $0.00",
            ],
        ),
    ],
)
def test_settlement_commands_are_deterministic(
    command: str, expected: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    assert main([command]) == 0
    first = capsys.readouterr().out
    assert first.splitlines() == expected
    assert main([command]) == 0
    assert capsys.readouterr().out == first


@pytest.mark.parametrize("arguments", [[], ["unknown"]])
def test_invalid_command_exits_with_helpful_error(arguments: list[str]) -> None:
    with pytest.raises(SystemExit) as error:
        main(arguments)
    assert error.value.code == 2


def test_institution_output_is_deterministic(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["institution"]) == 0
    first_output = capsys.readouterr().out
    assert main(["institution"]) == 0
    assert capsys.readouterr().out == first_output
    assert first_output.splitlines() == [
        "Harbor Community Credit Union",
        "Institution type: Credit union",
        "Ownership model: Member-owned",
        "Service region: Southeastern Virginia",
        "Purpose: Serve families and businesses by strengthening the financial "
        "well-being of our members and community.",
    ]


def test_comparison_output_is_deterministic(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["compare-institutions"]) == 0
    first_output = capsys.readouterr().out
    assert main(["compare-institutions"]) == 0
    assert capsys.readouterr().out == first_output
    assert first_output.splitlines() == [
        "Institution ownership comparison",
        "",
        "Tidewater Regional Bank",
        "Type: Bank",
        "Ownership: Shareholder-owned",
        "Primary stakeholders: Customers and shareholders",
        "Organizational purpose: Serve customers while sustaining a strong "
        "institution and creating long-term shareholder value.",
        "",
        "Harbor Community Credit Union",
        "Type: Credit union",
        "Ownership: Member-owned",
        "Primary stakeholders: Members",
        "Organizational purpose: Serve families and businesses by strengthening "
        "the financial well-being of our members and community.",
        "",
        "Shared software capabilities:",
        "- Customer or member records",
        "- Account systems",
        "- Transaction processing",
        "- Digital banking",
        "- Security",
        "- Reporting",
    ]


def test_member_apply_output_is_deterministic(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["member-apply"]) == 0
    output = capsys.readouterr().out
    assert output.splitlines() == [
        "Application: HCCU-0001",
        "Applicant: Alex Harbor",
        "State progression:",
        "1. Application created: Draft",
        "2. Application submitted: Submitted",
        "3. Review started: Under review",
        "4. Eligibility evaluated: Eligible",
        "5. Identity verification recorded: Passed",
        "6. Application approved: Approved",
        "Eligibility: Eligible",
        "Identity verification: Passed",
        "Final decision: Approved",
    ]
    assert main(["member-apply"]) == 0
    assert capsys.readouterr().out == output


def test_member_onboarding_output_has_stable_multiple_outcomes(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["member-onboarding"]) == 0
    output = capsys.readouterr().out
    assert output.count("Final decision: Approved") == 1
    assert output.count("Final decision: Rejected — Ineligible") == 1
    assert output.count("Final decision: Rejected — Identity verification failed") == 1
    assert output.index("Approved application") < output.index("Ineligible application")
    assert output.index("Ineligible application") < output.index(
        "Identity-verification failure"
    )
    assert main(["member-onboarding"]) == 0
    assert capsys.readouterr().out == output


def test_ledger_output_is_deterministic(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["ledger"]) == 0
    output = capsys.readouterr().out
    assert output.splitlines() == [
        "Seq  Type      Amount",
        "1    Credit    +$1,000.00",
        "2    Debit       -$120.00",
        "3    Debit        -$55.25",
    ]
    assert main(["ledger"]) == 0
    assert capsys.readouterr().out == output


def test_ledger_replay_output_is_deterministic(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["ledger-replay"]) == 0
    output = capsys.readouterr().out
    assert output.splitlines() == [
        "Ledger replay",
        "1. Credit +$1,000.00 → $1,000.00",
        "2. Debit -$120.00 → $880.00",
        "3. Debit -$55.25 → $824.75",
        "",
        "Final balance:",
        "$824.75",
    ]
    assert main(["ledger-replay"]) == 0
    assert capsys.readouterr().out == output


def test_payment_queue_output_is_deterministic(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["payment-queue"]) == 0
    output = capsys.readouterr().out
    assert output.startswith("Payment queue | capacity 2 payments/minute\n")
    assert "T+0 Arrived    ACH-001" in output
    assert "T+1 Processing ACH-001" in output
    assert "Total processed: 6" in output
    assert "Maximum queue depth: 6" in output
    assert "Remaining queued items: 0" in output
    assert main(["payment-queue"]) == 0
    assert capsys.readouterr().out == output


def test_payment_capacity_output_is_deterministic(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["payment-capacity"]) == 0
    output = capsys.readouterr().out
    assert output.splitlines() == [
        "Payment capacity comparison | identical workload",
        "Capacity 1: completed T+6 | average wait 2 | longest wait 5 | "
        "queued after T+1 5 | max depth 6 | final balance 100000 cents",
        "Capacity 2: completed T+3 | average wait 1 | longest wait 2 | "
        "queued after T+1 4 | max depth 6 | final balance 100000 cents",
        "Capacity 4: completed T+2 | average wait 0 | longest wait 1 | "
        "queued after T+1 2 | max depth 6 | final balance 100000 cents",
        "Identical ledger outcomes: yes",
    ]
    assert main(["payment-capacity"]) == 0
    assert capsys.readouterr().out == output


def test_balance_output_is_deterministic(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["balance"]) == 0
    output = capsys.readouterr().out
    assert output.splitlines() == [
        "Ledger Balance:        $824.75",
        "Pending Debits:        $120.00",
        "Pending Credits:        $25.00",
        "Available Balance:     $729.75",
    ]
    assert main(["balance"]) == 0
    assert capsys.readouterr().out == output


def test_pending_output_is_deterministic(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["pending"]) == 0
    output = capsys.readouterr().out
    assert output.splitlines() == [
        "Pending Debit",
        "Gas Station",
        "$60.00",
        "",
        "Pending Debit",
        "Restaurant",
        "$60.00",
        "",
        "Pending Credit",
        "Payroll",
        "$25.00",
    ]
    assert main(["pending"]) == 0
    assert capsys.readouterr().out == output


def test_deposit_output_shows_request_entry_and_replayed_balance(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["deposit"]) == 0
    output = capsys.readouterr().out
    assert output.splitlines() == [
        "Request: DEP-0001 | HCCU-DEMO-001 | $500.00",
        "Status: Received → Posted",
        "Ledger entry: DEP-0001-ENTRY | Credit | $500.00",
        "Running balance: $500.00",
        "",
        "Final balance:",
        "$500.00",
    ]
    assert main(["deposit"]) == 0
    assert capsys.readouterr().out == output


def test_deposits_output_replays_each_deposit_deterministically(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["deposits"]) == 0
    output = capsys.readouterr().out
    assert "Running balance: $500.00" in output
    assert "Running balance: $750.00" in output
    assert "Running balance: $825.50" in output
    assert output.endswith("Final balance:\n$825.50\n")
    assert main(["deposits"]) == 0
    assert capsys.readouterr().out == output


def test_withdrawal_output_shows_validation_entry_and_replay(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["withdrawal"]) == 0
    output = capsys.readouterr().out
    assert output.splitlines() == [
        "Request: WDR-0001 | HCCU-DEMO-001 | $120.00",
        "Validation: Request valid; available funds sufficient",
        "Status: Received → Posted",
        "Ledger entry: WDR-0001-ENTRY | Debit | $120.00",
        "Replay: opening credit, then posted debit",
        "",
        "Final balance:",
        "$380.00",
    ]
    assert main(["withdrawal"]) == 0
    assert capsys.readouterr().out == output


def test_withdrawals_output_includes_rejection_without_ledger_append(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["withdrawals"]) == 0
    output = capsys.readouterr().out
    assert "Status: Received → Posted" in output
    assert "Status: Received → Rejected" in output
    assert "Reason: Insufficient available funds" in output
    assert "Ledger entries appended: 0" in output
    assert output.endswith("Final ledger replay:\n$380.00\n")
    assert main(["withdrawals"]) == 0
    assert capsys.readouterr().out == output


def test_transfer_output_shows_coordinated_entries_and_both_balances(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["transfer"]) == 0
    output = capsys.readouterr().out
    assert "Debit entry: TRF-0001-DEBIT | ACCOUNT-SOURCE | $150.00" in output
    assert "Credit entry: TRF-0001-CREDIT | ACCOUNT-DESTINATION | $150.00" in output
    assert output.endswith("Source balance: $850.00\nDestination balance: $400.00\n")
    assert main(["transfer"]) == 0
    assert capsys.readouterr().out == output


def test_transfers_output_contains_all_deterministic_outcomes(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["transfers"]) == 0
    output = capsys.readouterr().out
    assert "Successful transfer" in output
    assert "Reason: Insufficient available funds" in output
    assert "Reason: source and destination accounts must be different" in output
    assert output.count("Ledger entries appended: 0") == 2
    assert main(["transfers"]) == 0
    assert capsys.readouterr().out == output


def test_ach_output_is_deterministic(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["ach"]) == 0
    output = capsys.readouterr().out
    assert output.splitlines() == [
        "ACH transfer: ACH-0001",
        "Source account: HCCU-DEMO-001",
        "Destination institution: Blue Ridge National Bank",
        "Destination reference: EXTERNAL-ACCOUNT-001",
        "Amount: $250.00",
        "Initial current balance: $1,000.00",
        "Initial available balance: $1,000.00",
        "Final status: Completed",
        "Final current balance: $750.00",
        "Final available balance: $750.00",
        "Ledger effect: ACH-0001-DEBIT | Debit | $250.00",
    ]
    assert main(["ach"]) == 0
    assert capsys.readouterr().out == output


def test_ach_timeline_output_is_deterministic(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["ach-timeline"]) == 0
    output = capsys.readouterr().out
    assert output.splitlines() == [
        "T+0    ACH transfer received",
        "T+1    Transfer validated",
        "T+2    Funds marked pending",
        "T+3    Submitted to ACH network",
        "T+5    Network processing",
        "T+10   Transfer completed",
        "T+10   Ledger debit posted",
    ]
    assert main(["ach-timeline"]) == 0
    assert capsys.readouterr().out == output


def test_ach_return_output_is_deterministic(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["ach-return"]) == 0
    output = capsys.readouterr().out
    assert output.splitlines() == [
        "Original source balance: $1,000.00",
        "Outbound ACH amount: $250.00",
        "Balance after outbound posting: $750.00",
        "Return reason: Account closed",
        "Corrective ledger entry: RETURN-0001-CREDIT | Credit | $250.00",
        "Final balance: $1,000.00",
        "Preserved entries:",
        "- ACH-0001-DEBIT | Debit | $250.00",
        "- RETURN-0001-CREDIT | Credit | $250.00",
    ]
    assert main(["ach-return"]) == 0
    assert capsys.readouterr().out == output


def test_ach_return_timeline_output_is_deterministic(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["ach-return-timeline"]) == 0
    output = capsys.readouterr().out
    assert output.splitlines() == [
        "T+0    ACH transfer received",
        "T+1    Transfer validated",
        "T+2    Funds marked pending",
        "T+3    Submitted to ACH network",
        "T+5    Network processing",
        "T+10   Transfer completed",
        "T+10   Ledger debit posted",
        "T+30   ACH return received",
        "T+31   ACH return validated",
        "T+32   ACH return processing",
        "T+35   ACH return completed",
        "T+35   Corrective credit posted",
    ]
    assert main(["ach-return-timeline"]) == 0
    assert capsys.readouterr().out == output


def test_idempotency_output_is_deterministic(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["idempotency"]) == 0
    output = capsys.readouterr().out
    assert output.splitlines() == [
        "Idempotent payment processing | protection enabled",
        "Initial balance: $1,000.00",
        "Delivery 1: PAY-001 | key IDEMPOTENCY-PAY-001 | original processed",
        "Delivery 2: PAY-001 | key IDEMPOTENCY-PAY-001 | duplicate acknowledged; "
        "original result returned",
        "Delivery 3: PAY-001 | key IDEMPOTENCY-PAY-001 | duplicate acknowledged; "
        "original result returned",
        "Deliveries: 3",
        "Original processing: 1",
        "Duplicate acknowledgements: 2",
        "Final balance: $750.00",
        "Ledger entry count: 1",
        "Financial effect: exactly one debit of $250.00",
    ]
    assert main(["idempotency"]) == 0
    assert capsys.readouterr().out == output


def test_idempotency_comparison_output_is_deterministic(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["idempotency-comparison"]) == 0
    output = capsys.readouterr().out
    assert output.splitlines() == [
        "Duplicate processing comparison | identical triple-delivery workload",
        "Workload: 3 deliveries | key IDEMPOTENCY-PAY-001 | payment $250.00",
        "Chapter 14 | naïve duplicate processing",
        "Ledger debits: 3",
        "Final balance: $250.00 | INCORRECT",
        "Chapter 15 | idempotent processing",
        "Ledger debits: 1",
        "Duplicate requests prevented: 2",
        "Final balance: $750.00 | CORRECT",
        "Result: duplicate deliveries produced exactly one financial effect.",
    ]
    assert main(["idempotency-comparison"]) == 0
    assert capsys.readouterr().out == output


@pytest.mark.parametrize(
    ("command", "expected_lines"),
    [
        (
            "ordering",
            [
                "Payment event ordering | correct delivery",
                "Expected order: 1 -> 2 -> 3 -> 4",
                "Sequence 1 | PaymentReceived | processed",
                "Sequence 2 | PaymentValidated | processed",
                "Sequence 3 | PaymentQueued | processed",
                "Sequence 4 | PaymentCompleted | processed",
                "Final payment state: PaymentCompleted",
                "Final balance: $750.00",
                "Financial effect: exactly one settlement debit",
            ],
        ),
        (
            "out-of-order",
            [
                "Payment event ordering | out-of-order delivery",
                "Expected order: 1 -> 2 -> 3 -> 4",
                "Arrival order: 3 -> 2 -> 1 -> 4 -> 4 (duplicate) -> 2 (late)",
                "Processing decisions:",
                "Arrival 1 | sequence 3 | buffered: waiting for an earlier event",
                "Arrival 2 | sequence 2 | buffered: waiting for an earlier event",
                "Arrival 3 | sequence 1 | processed",
                "Arrival 2 | sequence 2 | processed",
                "Arrival 1 | sequence 3 | processed",
                "Arrival 4 | sequence 4 | processed",
                "Arrival 5 | sequence 4 | rejected: event already processed",
                "Arrival 6 | sequence 2 | rejected: stale revision",
                "Stale events detected: 1",
                "Out-of-order events detected: 2",
                "Buffered events: 2",
                "Duplicate events: 1",
                "Rejected events: 2",
                "Final payment state: PaymentCompleted",
                "Final balance: $750.00",
                "Ledger settlement entries: 1",
                "Financial outcome: correct; stale and duplicate events had no effect",
            ],
        ),
    ],
)
def test_ordering_commands_are_deterministic(
    command: str, expected_lines: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    assert main([command]) == 0
    first = capsys.readouterr().out
    assert first.splitlines() == expected_lines
    assert main([command]) == 0
    assert capsys.readouterr().out == first
