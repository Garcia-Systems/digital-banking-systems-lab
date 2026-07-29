"""Tests for the deliberately small command line."""

import pytest

from bank_sim.cli import main


def test_doctor_reports_identity_and_version(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["doctor"]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "Digital Banking Systems Laboratory",
        "Version 0.9.0",
        "Laboratory environment is ready.",
    ]


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
