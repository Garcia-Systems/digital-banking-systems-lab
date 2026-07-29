"""Tests for the Chapter 1 financial-institution domain model."""

from dataclasses import FrozenInstanceError

import pytest

from bank_sim.institutions import (
    SHARED_SOFTWARE_CAPABILITIES,
    FinancialInstitution,
    InstitutionType,
    InstitutionValidationError,
    OwnershipModel,
    harbor_community_credit_union,
)


def make_institution(**changes: object) -> FinancialInstitution:
    values = {
        "name": "Example Bank",
        "institution_type": InstitutionType.BANK,
        "ownership_model": OwnershipModel.SHAREHOLDER_OWNED,
        "service_region": "Example region",
        "purpose": "Serve customers.",
    }
    values.update(changes)
    return FinancialInstitution(**values)  # type: ignore[arg-type]


def test_harbor_community_credit_union_identity_and_ownership() -> None:
    institution = harbor_community_credit_union()
    assert institution.name == "Harbor Community Credit Union"
    assert institution.institution_type is InstitutionType.CREDIT_UNION
    assert institution.ownership_model is OwnershipModel.MEMBER_OWNED
    assert institution.service_region == "Southeastern Virginia"


def test_financial_institution_is_immutable() -> None:
    institution = harbor_community_credit_union()
    with pytest.raises(FrozenInstanceError):
        institution.name = "Changed"  # type: ignore[misc]


@pytest.mark.parametrize("name", ["", " ", "\t\n"])
def test_blank_name_is_rejected(name: str) -> None:
    with pytest.raises(InstitutionValidationError, match="name cannot be blank"):
        make_institution(name=name)


@pytest.mark.parametrize("field", ["service_region", "purpose"])
def test_blank_descriptive_field_is_rejected(field: str) -> None:
    with pytest.raises(InstitutionValidationError, match="cannot be blank"):
        make_institution(**{field: " "})


def test_bank_cannot_be_member_owned() -> None:
    with pytest.raises(InstitutionValidationError, match="shareholder-owned"):
        make_institution(ownership_model=OwnershipModel.MEMBER_OWNED)


def test_credit_union_cannot_be_shareholder_owned() -> None:
    with pytest.raises(InstitutionValidationError, match="member-owned"):
        make_institution(
            institution_type=InstitutionType.CREDIT_UNION,
            ownership_model=OwnershipModel.SHAREHOLDER_OWNED,
        )


def test_shared_capabilities_have_stable_teaching_order() -> None:
    assert SHARED_SOFTWARE_CAPABILITIES == (
        "Customer or member records",
        "Account systems",
        "Transaction processing",
        "Digital banking",
        "Security",
        "Reporting",
    )
