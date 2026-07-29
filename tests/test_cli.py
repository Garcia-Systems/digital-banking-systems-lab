"""Tests for the deliberately small command line."""

import pytest

from bank_sim.cli import main


def test_doctor_reports_identity_and_version(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["doctor"]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "Digital Banking Systems Laboratory",
        "Version 0.2.0",
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
