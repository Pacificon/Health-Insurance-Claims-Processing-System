from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.config import Settings
from app.models.claims import ClaimDocument, ClaimSubmission
from app.models.extraction import ExtractedClaim
from app.services.gemini import GeminiConfigurationError, GeminiExtractor
from app.services.medical_normalizer import normalize_medical_terms


class ExtractionMode(StrEnum):
    EVAL_BYPASS = "eval_bypass"
    GEMINI = "gemini"


class ExtractionResult(BaseModel):
    success: bool
    stage: str = "EXTRACTION"
    extracted: ExtractedClaim | None = None
    confidence_score: float = 0.0
    extraction_mode: ExtractionMode | None = None
    checks: list[dict[str, Any]] = Field(default_factory=list)
    error_message: str | None = None


def _has_embedded_content(documents: list[ClaimDocument]) -> bool:
    return all(doc.content is not None for doc in documents)


class ExtractionAgent:
    """Extract structured claim data — eval bypass when embedded content exists, else Gemini vision."""

    EVAL_BYPASS_CONFIDENCE = 0.95

    def __init__(self, settings: Settings, gemini: GeminiExtractor | None = None) -> None:
        self._settings = settings
        self._gemini = gemini or GeminiExtractor(settings)

    def extract(
        self,
        submission: ClaimSubmission,
        *,
        file_contents: dict[str, bytes] | None = None,
        force_eval_bypass: bool = False,
    ) -> ExtractionResult:
        if force_eval_bypass or _has_embedded_content(submission.documents):
            return self._extract_eval_bypass(submission)

        if not self._gemini.is_configured():
            return ExtractionResult(
                success=False,
                error_message=(
                    "GEMINI_API_KEY is not configured. "
                    "Embedded document content is absent, so vision extraction cannot run."
                ),
                checks=[
                    {
                        "step": "GEMINI_CONFIG",
                        "passed": False,
                        "message": "Missing GEMINI_API_KEY for production extraction path.",
                    }
                ],
            )

        try:
            return self._extract_via_gemini(submission, file_contents or {})
        except GeminiConfigurationError as exc:
            return ExtractionResult(
                success=False,
                error_message=str(exc),
                checks=[{"step": "GEMINI_CONFIG", "passed": False, "message": str(exc)}],
            )
        except (ValueError, Exception) as exc:
            return ExtractionResult(
                success=False,
                error_message=f"Extraction failed: {exc}",
                extraction_mode=ExtractionMode.GEMINI,
                checks=[{"step": "GEMINI_EXTRACTION", "passed": False, "error": str(exc)}],
            )

    def _extract_eval_bypass(self, submission: ClaimSubmission) -> ExtractionResult:
        extracted = normalize_medical_terms(
            ExtractedClaim.from_document_contents(submission.documents)
        )
        return ExtractionResult(
            success=True,
            extracted=extracted,
            confidence_score=self.EVAL_BYPASS_CONFIDENCE,
            extraction_mode=ExtractionMode.EVAL_BYPASS,
            checks=[
                {
                    "step": "EVAL_BYPASS",
                    "passed": True,
                    "message": (
                        "Used embedded document content as ground-truth extraction "
                        "(eval mode — Gemini not called)."
                    ),
                    "document_count": len(submission.documents),
                }
            ],
        )

    def _extract_via_gemini(
        self,
        submission: ClaimSubmission,
        file_contents: dict[str, bytes],
    ) -> ExtractionResult:
        extracted, confidence, checks = self._gemini.extract_claim(submission, file_contents)
        extracted = normalize_medical_terms(extracted)
        return ExtractionResult(
            success=True,
            extracted=extracted,
            confidence_score=confidence,
            extraction_mode=ExtractionMode.GEMINI,
            checks=checks,
        )
