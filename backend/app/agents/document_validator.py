import re
from collections import Counter
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.models.claims import ClaimDocument, ClaimSubmission, DocumentQuality, DocumentType
from app.models.policy import PolicyTerms

DOCUMENT_TYPE_LABELS: dict[DocumentType, str] = {
    DocumentType.PRESCRIPTION: "Prescription",
    DocumentType.HOSPITAL_BILL: "Bill",
    DocumentType.PHARMACY_BILL: "Pharmacy bill",
    DocumentType.LAB_REPORT: "Lab report",
    DocumentType.DIAGNOSTIC_REPORT: "Diagnostic report",
    DocumentType.DENTAL_REPORT: "Dental report",
    DocumentType.DISCHARGE_SUMMARY: "Discharge summary",
}


class ActionRequired(StrEnum):
    REUPLOAD = "REUPLOAD"


class DocumentValidationResult(BaseModel):
    passed: bool
    stage: str = "DOCUMENT_VALIDATION"
    decision: None = None
    action_required: ActionRequired | None = None
    messages: list[str] = Field(default_factory=list)
    checks: list[dict[str, Any]] = Field(default_factory=list)


def _normalize_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.lower().strip())


def _patient_name_from_doc(doc: ClaimDocument) -> str | None:
    if doc.patient_name_on_doc:
        return doc.patient_name_on_doc.strip()
    if doc.content and doc.content.get("patient_name"):
        return str(doc.content["patient_name"]).strip()
    return None


class DocumentValidator:
    def __init__(self, policy: PolicyTerms, *, confidence_threshold: float = 0.7) -> None:
        self._policy = policy
        self._confidence_threshold = confidence_threshold

    def validate(self, submission: ClaimSubmission) -> DocumentValidationResult:
        checks: list[dict[str, Any]] = []

        type_check = self._check_document_types(submission)
        checks.append(type_check)
        if not type_check["passed"]:
            return self._early_stop(checks, type_check["message"])

        quality_check = self._check_document_quality(submission)
        checks.append(quality_check)
        if not quality_check["passed"]:
            return self._early_stop(checks, quality_check["message"])

        name_check = self._check_patient_names(submission)
        checks.append(name_check)
        if not name_check["passed"]:
            return self._early_stop(checks, name_check["message"])

        checks.append(
            {
                "rule": "DOCUMENT_VALIDATION",
                "passed": True,
                "message": "All document checks passed.",
            }
        )
        return DocumentValidationResult(passed=True, checks=checks)

    def _check_document_types(self, submission: ClaimSubmission) -> dict[str, Any]:
        requirement = self._policy.get_document_requirement(submission.claim_category.value)
        if requirement is None:
            return {
                "rule": "DOCUMENT_TYPES",
                "passed": True,
                "message": "No document requirements configured for this category.",
            }

        type_counts = Counter(doc.actual_type.value for doc in submission.documents)
        missing = [doc_type for doc_type in requirement.required if doc_type not in type_counts]

        if not missing:
            return {
                "rule": "DOCUMENT_TYPES",
                "passed": True,
                "message": "All required document types are present.",
            }

        uploaded_desc = ", ".join(f"{doc_type} (×{count})" for doc_type, count in type_counts.items())
        required_desc = " + ".join(requirement.required)
        message = (
            f"You uploaded {uploaded_desc}; "
            f"{submission.claim_category.value} requires {required_desc}"
        )
        return {
            "rule": "DOCUMENT_TYPES",
            "passed": False,
            "uploaded": dict(type_counts),
            "required": requirement.required,
            "missing": missing,
            "message": message,
        }

    def _check_document_quality(self, submission: ClaimSubmission) -> dict[str, Any]:
        unreadable: list[ClaimDocument] = []
        for doc in submission.documents:
            if doc.quality == DocumentQuality.UNREADABLE:
                unreadable.append(doc)
                continue
            confidence = doc.content.get("extraction_confidence") if doc.content else None
            if confidence is not None and float(confidence) < self._confidence_threshold:
                unreadable.append(doc)

        if not unreadable:
            return {
                "rule": "DOCUMENT_QUALITY",
                "passed": True,
                "message": "All documents are readable.",
            }

        file_names = [doc.file_name or doc.file_id for doc in unreadable]
        if len(file_names) == 1:
            message = (
                f"The document '{file_names[0]}' is unreadable. "
                f"Please re-upload a clear copy of this document."
            )
        else:
            listed = ", ".join(f"'{name}'" for name in file_names)
            message = (
                f"The following documents are unreadable: {listed}. "
                f"Please re-upload clear copies of these documents."
            )

        return {
            "rule": "DOCUMENT_QUALITY",
            "passed": False,
            "unreadable_files": file_names,
            "message": message,
        }

    def _check_patient_names(self, submission: ClaimSubmission) -> dict[str, Any]:
        named_docs: list[tuple[str, str]] = []
        for doc in submission.documents:
            name = _patient_name_from_doc(doc)
            if not name:
                continue
            label = DOCUMENT_TYPE_LABELS.get(doc.actual_type, doc.actual_type.value)
            named_docs.append((label, name))

        if len(named_docs) < 2:
            return {
                "rule": "PATIENT_NAME_CONSISTENCY",
                "passed": True,
                "message": "Insufficient patient names to compare across documents.",
            }

        normalized_names = {_normalize_name(name) for _, name in named_docs}
        if len(normalized_names) == 1:
            return {
                "rule": "PATIENT_NAME_CONSISTENCY",
                "passed": True,
                "message": "Patient names are consistent across documents.",
            }

        message = "; ".join(f"{label}: {name}" for label, name in named_docs)
        return {
            "rule": "PATIENT_NAME_CONSISTENCY",
            "passed": False,
            "names_found": [{"document": label, "patient_name": name} for label, name in named_docs],
            "message": (
                f"The documents appear to belong to different patients: {message}. "
                f"Please verify and re-upload documents for the same patient."
            ),
        }

    def _early_stop(self, checks: list[dict[str, Any]], message: str) -> DocumentValidationResult:
        return DocumentValidationResult(
            passed=False,
            action_required=ActionRequired.REUPLOAD,
            messages=[message],
            checks=checks,
        )
