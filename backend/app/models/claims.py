from datetime import date
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ClaimCategory(StrEnum):
    CONSULTATION = "CONSULTATION"
    DIAGNOSTIC = "DIAGNOSTIC"
    PHARMACY = "PHARMACY"
    DENTAL = "DENTAL"
    VISION = "VISION"
    ALTERNATIVE_MEDICINE = "ALTERNATIVE_MEDICINE"


class DocumentType(StrEnum):
    PRESCRIPTION = "PRESCRIPTION"
    HOSPITAL_BILL = "HOSPITAL_BILL"
    PHARMACY_BILL = "PHARMACY_BILL"
    LAB_REPORT = "LAB_REPORT"
    DIAGNOSTIC_REPORT = "DIAGNOSTIC_REPORT"
    DENTAL_REPORT = "DENTAL_REPORT"
    DISCHARGE_SUMMARY = "DISCHARGE_SUMMARY"


class DocumentQuality(StrEnum):
    GOOD = "GOOD"
    UNREADABLE = "UNREADABLE"


class Decision(StrEnum):
    APPROVED = "APPROVED"
    PARTIAL = "PARTIAL"
    REJECTED = "REJECTED"
    MANUAL_REVIEW = "MANUAL_REVIEW"


class ClaimDocument(BaseModel):
    file_id: str
    file_name: str | None = None
    actual_type: DocumentType
    quality: DocumentQuality | None = None
    patient_name_on_doc: str | None = None
    content: dict[str, Any] | None = None


class ClaimHistoryEntry(BaseModel):
    claim_id: str
    date: date
    amount: float
    provider: str | None = None


class ClaimSubmission(BaseModel):
    member_id: str
    policy_id: str
    claim_category: ClaimCategory
    treatment_date: date
    claimed_amount: float = Field(gt=0)
    documents: list[ClaimDocument] = Field(min_length=1)
    ytd_claims_amount: float | None = None
    claims_history: list[ClaimHistoryEntry] | None = None
    hospital_name: str | None = None
    simulate_component_failure: bool = False
