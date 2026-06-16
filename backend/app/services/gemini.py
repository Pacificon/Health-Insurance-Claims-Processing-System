import json
import mimetypes
from typing import Any

import google.generativeai as genai
from pydantic import BaseModel, Field, ValidationError

from app.config import Settings
from app.models.claims import ClaimDocument, ClaimSubmission, DocumentType
from app.models.extraction import ExtractedClaim, LineItem


class GeminiConfigurationError(RuntimeError):
    pass


class SingleDocExtraction(BaseModel):
    patient_name: str | None = None
    doctor_name: str | None = None
    doctor_registration: str | None = None
    diagnosis: str | None = None
    treatment: str | None = None
    hospital_name: str | None = None
    tests_ordered: list[str] = Field(default_factory=list)
    line_items: list[LineItem] = Field(default_factory=list)
    medicines: list[str] = Field(default_factory=list)
    pre_authorization_obtained: bool = False
    extraction_confidence: float = Field(default=0.0, ge=0.0, le=1.0)


DOCUMENT_PROMPTS: dict[DocumentType, str] = {
    DocumentType.PRESCRIPTION: (
        "Extract from this medical prescription: doctor name, registration number, "
        "patient name, diagnosis, medicines, tests ordered, clinic/hospital name. "
        "Expand medical abbreviations where possible (e.g. T2DM → Type 2 Diabetes)."
    ),
    DocumentType.HOSPITAL_BILL: (
        "Extract from this hospital/clinic bill: patient name, hospital name, date, "
        "line items (description and amount), and total if visible."
    ),
    DocumentType.PHARMACY_BILL: (
        "Extract from this pharmacy bill: patient name, medicines, line items with amounts, "
        "and pharmacy name if visible."
    ),
    DocumentType.LAB_REPORT: (
        "Extract from this lab report: patient name, test names performed, diagnosis if stated."
    ),
    DocumentType.DIAGNOSTIC_REPORT: (
        "Extract from this diagnostic report: patient name, test/procedure name, diagnosis."
    ),
    DocumentType.DENTAL_REPORT: (
        "Extract from this dental report: patient name, procedures, diagnosis, line items."
    ),
    DocumentType.DISCHARGE_SUMMARY: (
        "Extract from this discharge summary: patient name, hospital name, diagnosis, treatment."
    ),
}


def _merge_doc_extractions(docs: list[SingleDocExtraction]) -> ExtractedClaim:
    diagnosis: str | None = None
    treatment: str | None = None
    tests_ordered: list[str] = []
    line_items: list[LineItem] = []
    hospital_name: str | None = None
    pre_auth = False

    for doc in docs:
        diagnosis = diagnosis or doc.diagnosis
        treatment = treatment or doc.treatment
        hospital_name = hospital_name or doc.hospital_name
        pre_auth = pre_auth or doc.pre_authorization_obtained
        tests_ordered.extend(doc.tests_ordered)
        line_items.extend(doc.line_items)

    return ExtractedClaim(
        diagnosis=diagnosis,
        treatment=treatment,
        tests_ordered=tests_ordered,
        line_items=line_items,
        hospital_name=hospital_name,
        pre_authorization_obtained=pre_auth,
    )


def _guess_mime_type(file_name: str | None, file_bytes: bytes) -> str:
    if file_name:
        guessed, _ = mimetypes.guess_type(file_name)
        if guessed:
            return guessed
    if file_bytes[:4] == b"%PDF":
        return "application/pdf"
    return "image/jpeg"


class GeminiExtractor:
    MODEL_NAME = "gemini-1.5-flash"

    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.gemini_api_key.strip()

    def is_configured(self) -> bool:
        return bool(self._api_key)

    def _require_configured(self) -> None:
        if not self.is_configured():
            raise GeminiConfigurationError(
                "GEMINI_API_KEY is not set. Required for vision extraction on uploaded files."
            )

    def _build_model(self) -> genai.GenerativeModel:
        genai.configure(api_key=self._api_key)
        return genai.GenerativeModel(
            self.MODEL_NAME,
            generation_config={
                "response_mime_type": "application/json",
                "response_schema": SingleDocExtraction.model_json_schema(),
            },
        )

    def extract_document(
        self,
        document: ClaimDocument,
        file_bytes: bytes,
    ) -> SingleDocExtraction:
        self._require_configured()
        prompt = DOCUMENT_PROMPTS.get(
            document.actual_type,
            "Extract all medically relevant structured fields from this health insurance document.",
        )
        mime_type = _guess_mime_type(document.file_name, file_bytes)
        model = self._build_model()
        response = model.generate_content(
            [
                prompt,
                "Return JSON only matching the required schema.",
                {"mime_type": mime_type, "data": file_bytes},
            ]
        )
        raw = json.loads(response.text or "{}")
        return SingleDocExtraction.model_validate(raw)

    def extract_claim(
        self,
        submission: ClaimSubmission,
        file_contents: dict[str, bytes],
    ) -> tuple[ExtractedClaim, float, list[dict[str, Any]]]:
        self._require_configured()
        per_doc: list[SingleDocExtraction] = []
        checks: list[dict[str, Any]] = []
        confidences: list[float] = []

        for document in submission.documents:
            file_bytes = file_contents.get(document.file_id)
            if not file_bytes:
                raise ValueError(
                    f"No file bytes provided for document '{document.file_id}' "
                    f"({document.file_name or document.actual_type.value})."
                )
            try:
                extracted = self.extract_document(document, file_bytes)
            except (ValidationError, json.JSONDecodeError, ValueError) as exc:
                checks.append(
                    {
                        "file_id": document.file_id,
                        "document_type": document.actual_type.value,
                        "passed": False,
                        "error": str(exc),
                    }
                )
                raise
            per_doc.append(extracted)
            confidences.append(extracted.extraction_confidence)
            checks.append(
                {
                    "file_id": document.file_id,
                    "document_type": document.actual_type.value,
                    "passed": True,
                    "confidence": extracted.extraction_confidence,
                    "fields_extracted": list(extracted.model_dump(exclude_none=True).keys()),
                }
            )

        merged = _merge_doc_extractions(per_doc)
        overall_confidence = min(confidences) if confidences else 0.0
        return merged, overall_confidence, checks
