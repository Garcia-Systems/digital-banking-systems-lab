"""Stable identity and ownership models for financial institutions."""

from dataclasses import dataclass
from enum import Enum


class InstitutionValidationError(ValueError):
    """Raised when an institution violates a domain invariant."""


class InstitutionType(Enum):
    """The organizational kind of a financial institution."""

    BANK = "Bank"
    CREDIT_UNION = "Credit union"


class OwnershipModel(Enum):
    """The group that owns a financial institution."""

    SHAREHOLDER_OWNED = "Shareholder-owned"
    MEMBER_OWNED = "Member-owned"


_REQUIRED_OWNERSHIP = {
    InstitutionType.BANK: OwnershipModel.SHAREHOLDER_OWNED,
    InstitutionType.CREDIT_UNION: OwnershipModel.MEMBER_OWNED,
}


@dataclass(frozen=True, slots=True)
class FinancialInstitution:
    """Immutable identifying information and organizational purpose."""

    name: str
    institution_type: InstitutionType
    ownership_model: OwnershipModel
    service_region: str
    purpose: str

    def __post_init__(self) -> None:
        for field_name in ("name", "service_region", "purpose"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                readable_name = field_name.replace("_", " ")
                raise InstitutionValidationError(f"{readable_name} cannot be blank")

        required = _REQUIRED_OWNERSHIP.get(self.institution_type)
        if required is None:
            raise InstitutionValidationError("institution type is not supported")
        if self.ownership_model is not required:
            raise InstitutionValidationError(
                f"{self.institution_type.value} must be {required.value.lower()}"
            )


SHARED_SOFTWARE_CAPABILITIES = (
    "Customer or member records",
    "Account systems",
    "Transaction processing",
    "Digital banking",
    "Security",
    "Reporting",
)
"""Capabilities in stable display order; no capability is implemented here."""


def harbor_community_credit_union() -> FinancialInstitution:
    """Create the canonical fictional institution used by the laboratory."""
    return FinancialInstitution(
        name="Harbor Community Credit Union",
        institution_type=InstitutionType.CREDIT_UNION,
        ownership_model=OwnershipModel.MEMBER_OWNED,
        service_region="Southeastern Virginia",
        purpose=(
            "Serve families and businesses by strengthening the financial "
            "well-being of our members and community."
        ),
    )


def fictional_shareholder_bank() -> FinancialInstitution:
    """Create a fictional bank for the ownership comparison."""
    return FinancialInstitution(
        name="Tidewater Regional Bank",
        institution_type=InstitutionType.BANK,
        ownership_model=OwnershipModel.SHAREHOLDER_OWNED,
        service_region="Southeastern Virginia",
        purpose=(
            "Serve customers while sustaining a strong institution and creating "
            "long-term shareholder value."
        ),
    )


def describe_institution(institution: FinancialInstitution) -> str:
    """Render stable, readable identifying information."""
    return "\n".join(
        (
            institution.name,
            f"Institution type: {institution.institution_type.value}",
            f"Ownership model: {institution.ownership_model.value}",
            f"Service region: {institution.service_region}",
            f"Purpose: {institution.purpose}",
        )
    )


def compare_institutions() -> str:
    """Render the deterministic Chapter 1 ownership comparison."""
    bank = fictional_shareholder_bank()
    credit_union = harbor_community_credit_union()
    lines = ["Institution ownership comparison"]
    for institution, stakeholders in (
        (bank, "Customers and shareholders"),
        (credit_union, "Members"),
    ):
        lines.extend(
            (
                "",
                institution.name,
                f"Type: {institution.institution_type.value}",
                f"Ownership: {institution.ownership_model.value}",
                f"Primary stakeholders: {stakeholders}",
                f"Organizational purpose: {institution.purpose}",
            )
        )
    lines.extend(("", "Shared software capabilities:"))
    lines.extend(f"- {capability}" for capability in SHARED_SOFTWARE_CAPABILITIES)
    return "\n".join(lines)
