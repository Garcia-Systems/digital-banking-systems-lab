"""Tests for the Chapter 2 member-application state machine."""

import pytest

from bank_sim.onboarding import (
    ApplicationEvent,
    ApplicationStatus,
    ApplicationValidationError,
    EligibilityStatus,
    IdentityVerificationStatus,
    InvalidApplicationTransition,
    MemberApplication,
    RejectionReason,
    failed_verification_onboarding,
    ineligible_onboarding,
    successful_onboarding,
)


def draft(region: str = "Hampton Roads") -> MemberApplication:
    return MemberApplication("HCCU-TEST", "Casey Sound", region)


def under_review(region: str = "Hampton Roads") -> MemberApplication:
    application = draft(region)
    application.submit()
    application.begin_review()
    return application


def test_valid_draft_creation() -> None:
    application = draft()
    assert application.status is ApplicationStatus.DRAFT
    assert application.eligibility_status is EligibilityStatus.NOT_EVALUATED
    assert (
        application.identity_verification_status
        is IdentityVerificationStatus.NOT_STARTED
    )
    assert application.rejection_reason is None


@pytest.mark.parametrize("application_id", ["", " ", "\t"])
def test_blank_identifier_is_rejected(application_id: str) -> None:
    with pytest.raises(ApplicationValidationError, match="identifier cannot be blank"):
        MemberApplication(application_id, "Casey Sound", "Hampton Roads")


@pytest.mark.parametrize("name", ["", " ", "\n"])
def test_blank_applicant_name_is_rejected(name: str) -> None:
    with pytest.raises(ApplicationValidationError, match="name cannot be blank"):
        MemberApplication("HCCU-TEST", name, "Hampton Roads")


def test_successful_submission() -> None:
    application = draft()
    application.submit()
    assert application.status is ApplicationStatus.SUBMITTED


def test_review_starts_only_after_submission() -> None:
    with pytest.raises(InvalidApplicationTransition, match="status is Draft"):
        draft().begin_review()


@pytest.mark.parametrize(
    ("region", "expected"),
    [
        ("Hampton Roads", EligibilityStatus.ELIGIBLE),
        ("Southeastern Virginia", EligibilityStatus.ELIGIBLE),
        ("Virginia Eastern Shore", EligibilityStatus.ELIGIBLE),
        ("Northern Virginia", EligibilityStatus.INELIGIBLE),
        ("hampton roads", EligibilityStatus.INELIGIBLE),
    ],
)
def test_eligibility_evaluation_is_deterministic(
    region: str, expected: EligibilityStatus
) -> None:
    application = under_review(region)
    assert application.evaluate_eligibility() is expected


def test_successful_identity_verification_is_recorded() -> None:
    application = under_review()
    application.record_identity_verification(IdentityVerificationStatus.PASSED)
    assert application.identity_verification_status is IdentityVerificationStatus.PASSED


def test_approval_requires_all_prerequisites() -> None:
    application = under_review()
    with pytest.raises(InvalidApplicationTransition, match="eligible status"):
        application.approve()
    application.evaluate_eligibility()
    with pytest.raises(InvalidApplicationTransition, match="passed identity"):
        application.approve()
    application.record_identity_verification(IdentityVerificationStatus.PASSED)
    application.approve()
    assert application.status is ApplicationStatus.APPROVED
    assert application.rejection_reason is None


def test_ineligible_application_is_rejected_with_reason() -> None:
    application = ineligible_onboarding()
    assert application.status is ApplicationStatus.REJECTED
    assert application.eligibility_status is EligibilityStatus.INELIGIBLE
    assert application.rejection_reason is RejectionReason.INELIGIBLE


def test_identity_verification_failure_is_rejected_with_reason() -> None:
    application = failed_verification_onboarding()
    assert application.status is ApplicationStatus.REJECTED
    assert application.identity_verification_status is IdentityVerificationStatus.FAILED
    assert application.rejection_reason is RejectionReason.IDENTITY_VERIFICATION_FAILED


def test_rejection_requires_a_reason() -> None:
    with pytest.raises(ApplicationValidationError, match="requires a reason"):
        under_review().reject(None)


def test_draft_cannot_be_approved_directly() -> None:
    with pytest.raises(InvalidApplicationTransition, match="status is Draft"):
        draft().approve()


@pytest.mark.parametrize("operation", ["submit", "begin_review", "reject"])
def test_changes_are_prevented_after_approval(operation: str) -> None:
    application = successful_onboarding()
    with pytest.raises(InvalidApplicationTransition, match="status is Approved"):
        if operation == "reject":
            application.reject(RejectionReason.INCOMPLETE_APPLICATION)
        else:
            getattr(application, operation)()


@pytest.mark.parametrize("operation", ["submit", "begin_review", "approve"])
def test_changes_are_prevented_after_rejection(operation: str) -> None:
    application = ineligible_onboarding()
    with pytest.raises(InvalidApplicationTransition, match="status is Rejected"):
        getattr(application, operation)()


def test_transition_history_has_stable_ordering() -> None:
    application = successful_onboarding()
    assert [record.sequence for record in application.history] == [1, 2, 3, 4, 5, 6]
    assert [record.event for record in application.history] == [
        ApplicationEvent.CREATED,
        ApplicationEvent.SUBMITTED,
        ApplicationEvent.REVIEW_STARTED,
        ApplicationEvent.ELIGIBILITY_EVALUATED,
        ApplicationEvent.IDENTITY_VERIFICATION_RECORDED,
        ApplicationEvent.APPROVED,
    ]
    assert isinstance(application.history, tuple)
