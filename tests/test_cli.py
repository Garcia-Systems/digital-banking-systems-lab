"""Tests for the deliberately small command line."""

import pytest

from bank_sim.cli import main


def test_doctor_reports_identity_and_version(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["doctor"]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "Digital Banking Systems Laboratory",
        "Version 0.3.0",
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
