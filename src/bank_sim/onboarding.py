"""Deterministic member-application workflow for the fictional laboratory."""

from dataclasses import dataclass
from enum import Enum


class ApplicationValidationError(ValueError):
    """Raised when application data violates a domain invariant."""


class InvalidApplicationTransition(RuntimeError):
    """Raised when an operation is not allowed in the current workflow state."""


class ApplicationStatus(Enum):
    """States through which a membership application may progress."""

    DRAFT = "Draft"
    SUBMITTED = "Submitted"
    UNDER_REVIEW = "Under review"
    APPROVED = "Approved"
    REJECTED = "Rejected"


class EligibilityStatus(Enum):
    """Result of applying the fictional service-region rule."""

    NOT_EVALUATED = "Not evaluated"
    ELIGIBLE = "Eligible"
    INELIGIBLE = "Ineligible"


class IdentityVerificationStatus(Enum):
    """Simulated identity-verification outcome, not a production check."""

    NOT_STARTED = "Not started"
    PASSED = "Passed"
    FAILED = "Failed"


class RejectionReason(Enum):
    """Explicit reasons for a rejected application."""

    INCOMPLETE_APPLICATION = "Incomplete application"
    INELIGIBLE = "Ineligible"
    IDENTITY_VERIFICATION_FAILED = "Identity verification failed"


class ApplicationEvent(Enum):
    """Meaningful workflow facts retained in deterministic order."""

    CREATED = "Application created"
    SUBMITTED = "Application submitted"
    REVIEW_STARTED = "Review started"
    ELIGIBILITY_EVALUATED = "Eligibility evaluated"
    IDENTITY_VERIFICATION_RECORDED = "Identity verification recorded"
    APPROVED = "Application approved"
    REJECTED = "Application rejected"


@dataclass(frozen=True, slots=True)
class TransitionRecord:
    """An immutable, deterministically sequenced application event."""

    sequence: int
    event: ApplicationEvent
    detail: str


# A deliberately small fictional rule for this educational simulation.
ELIGIBLE_REGIONS = frozenset(
    {"Hampton Roads", "Southeastern Virginia", "Virginia Eastern Shore"}
)


class MemberApplication:
    """A membership application changed only through allowed domain operations."""

    __slots__ = (
        "_applicant_name",
        "_application_id",
        "_eligibility_status",
        "_history",
        "_identity_verification_status",
        "_rejection_reason",
        "_residential_region",
        "_status",
    )

    def __init__(
        self, application_id: str, applicant_name: str, residential_region: str
    ) -> None:
        self._application_id = self._required_text(
            application_id, "application identifier"
        )
        self._applicant_name = self._required_text(applicant_name, "applicant name")
        self._residential_region = self._required_text(
            residential_region, "residential region"
        )
        self._status = ApplicationStatus.DRAFT
        self._eligibility_status = EligibilityStatus.NOT_EVALUATED
        self._identity_verification_status = IdentityVerificationStatus.NOT_STARTED
        self._rejection_reason: RejectionReason | None = None
        self._history = [
            TransitionRecord(1, ApplicationEvent.CREATED, ApplicationStatus.DRAFT.value)
        ]

    @staticmethod
    def _required_text(value: str, field_name: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ApplicationValidationError(f"{field_name} cannot be blank")
        return value.strip()

    @property
    def application_id(self) -> str:
        return self._application_id

    @property
    def applicant_name(self) -> str:
        return self._applicant_name

    @property
    def residential_region(self) -> str:
        return self._residential_region

    @property
    def status(self) -> ApplicationStatus:
        return self._status

    @property
    def eligibility_status(self) -> EligibilityStatus:
        return self._eligibility_status

    @property
    def identity_verification_status(self) -> IdentityVerificationStatus:
        return self._identity_verification_status

    @property
    def rejection_reason(self) -> RejectionReason | None:
        return self._rejection_reason

    @property
    def history(self) -> tuple[TransitionRecord, ...]:
        """Return an immutable snapshot of the transition history."""
        return tuple(self._history)

    def _require_status(self, expected: ApplicationStatus, operation: str) -> None:
        if self._status is not expected:
            raise InvalidApplicationTransition(
                f"cannot {operation} application while status is {self._status.value}"
            )

    def _record(self, event: ApplicationEvent, detail: str) -> None:
        self._history.append(TransitionRecord(len(self._history) + 1, event, detail))

    def submit(self) -> None:
        self._require_status(ApplicationStatus.DRAFT, "submit")
        self._status = ApplicationStatus.SUBMITTED
        self._record(ApplicationEvent.SUBMITTED, self._status.value)

    def begin_review(self) -> None:
        self._require_status(ApplicationStatus.SUBMITTED, "begin review for")
        self._status = ApplicationStatus.UNDER_REVIEW
        self._record(ApplicationEvent.REVIEW_STARTED, self._status.value)

    def evaluate_eligibility(self) -> EligibilityStatus:
        """Apply the fixed, fictional service-region eligibility rule."""
        self._require_status(ApplicationStatus.UNDER_REVIEW, "evaluate eligibility for")
        if self._eligibility_status is not EligibilityStatus.NOT_EVALUATED:
            raise InvalidApplicationTransition("eligibility has already been evaluated")
        self._eligibility_status = (
            EligibilityStatus.ELIGIBLE
            if self._residential_region in ELIGIBLE_REGIONS
            else EligibilityStatus.INELIGIBLE
        )
        self._record(
            ApplicationEvent.ELIGIBILITY_EVALUATED,
            self._eligibility_status.value,
        )
        return self._eligibility_status

    def record_identity_verification(self, result: IdentityVerificationStatus) -> None:
        self._require_status(
            ApplicationStatus.UNDER_REVIEW, "record identity verification for"
        )
        if result is IdentityVerificationStatus.NOT_STARTED:
            raise ApplicationValidationError(
                "identity verification result must be Passed or Failed"
            )
        if (
            self._identity_verification_status
            is not IdentityVerificationStatus.NOT_STARTED
        ):
            raise InvalidApplicationTransition(
                "identity verification has already been recorded"
            )
        self._identity_verification_status = result
        self._record(ApplicationEvent.IDENTITY_VERIFICATION_RECORDED, result.value)

    def approve(self) -> None:
        self._require_status(ApplicationStatus.UNDER_REVIEW, "approve")
        if self._eligibility_status is not EligibilityStatus.ELIGIBLE:
            raise InvalidApplicationTransition("approval requires eligible status")
        if self._identity_verification_status is not IdentityVerificationStatus.PASSED:
            raise InvalidApplicationTransition(
                "approval requires passed identity verification"
            )
        self._status = ApplicationStatus.APPROVED
        self._rejection_reason = None
        self._record(ApplicationEvent.APPROVED, self._status.value)

    def reject(self, reason: RejectionReason | None) -> None:
        self._require_status(ApplicationStatus.UNDER_REVIEW, "reject")
        if reason is None:
            raise ApplicationValidationError("rejection requires a reason")
        if reason is RejectionReason.INELIGIBLE and (
            self._eligibility_status is not EligibilityStatus.INELIGIBLE
        ):
            raise InvalidApplicationTransition(
                "ineligible rejection requires ineligible status"
            )
        if reason is RejectionReason.IDENTITY_VERIFICATION_FAILED and (
            self._identity_verification_status is not IdentityVerificationStatus.FAILED
        ):
            raise InvalidApplicationTransition(
                "identity-verification rejection requires a failed result"
            )
        self._status = ApplicationStatus.REJECTED
        self._rejection_reason = reason
        self._record(ApplicationEvent.REJECTED, reason.value)


def successful_onboarding() -> MemberApplication:
    """Run the deterministic approved scenario for a fictional applicant."""
    application = MemberApplication("HCCU-0001", "Alex Harbor", "Hampton Roads")
    application.submit()
    application.begin_review()
    application.evaluate_eligibility()
    application.record_identity_verification(IdentityVerificationStatus.PASSED)
    application.approve()
    return application


def ineligible_onboarding() -> MemberApplication:
    """Run the deterministic ineligible scenario for a fictional applicant."""
    application = MemberApplication("HCCU-0002", "Morgan Bay", "Northern Virginia")
    application.submit()
    application.begin_review()
    application.evaluate_eligibility()
    application.reject(RejectionReason.INELIGIBLE)
    return application


def failed_verification_onboarding() -> MemberApplication:
    """Run the deterministic failed-verification scenario."""
    application = MemberApplication("HCCU-0003", "Taylor Shoal", "Hampton Roads")
    application.submit()
    application.begin_review()
    application.evaluate_eligibility()
    application.record_identity_verification(IdentityVerificationStatus.FAILED)
    application.reject(RejectionReason.IDENTITY_VERIFICATION_FAILED)
    return application


def describe_application(application: MemberApplication) -> str:
    """Render one application and its ordered workflow facts."""
    decision = application.status.value
    if application.rejection_reason is not None:
        decision = f"{decision} — {application.rejection_reason.value}"
    lines = [
        f"Application: {application.application_id}",
        f"Applicant: {application.applicant_name}",
        "State progression:",
    ]
    lines.extend(
        f"{record.sequence}. {record.event.value}: {record.detail}"
        for record in application.history
    )
    lines.extend(
        (
            f"Eligibility: {application.eligibility_status.value}",
            f"Identity verification: {application.identity_verification_status.value}",
            f"Final decision: {decision}",
        )
    )
    return "\n".join(lines)


def describe_onboarding_scenarios() -> str:
    """Render all Chapter 2 outcomes in stable order."""
    scenarios = (
        ("Approved application", successful_onboarding()),
        ("Ineligible application", ineligible_onboarding()),
        ("Identity-verification failure", failed_verification_onboarding()),
    )
    sections = ["Member onboarding outcomes"]
    for title, application in scenarios:
        sections.extend(("", title, describe_application(application)))
    return "\n".join(sections)
