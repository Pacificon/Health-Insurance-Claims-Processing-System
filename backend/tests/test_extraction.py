import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.agents.extraction_agent import ExtractionAgent, ExtractionMode
from app.config import Settings
from app.models.claims import ClaimSubmission
from app.models.extraction import ExtractedClaim
from app.services.gemini import GeminiExtractor, SingleDocExtraction
from app.services.medical_normalizer import normalize_medical_terms


@pytest.fixture
def settings() -> Settings:
    return Settings(gemini_api_key="")


@pytest.fixture
def agent(settings: Settings) -> ExtractionAgent:
    return ExtractionAgent(settings)


def _load_tc_input(case_id: str) -> dict:
    root = Path(__file__).resolve().parents[2]
    cases = json.loads((root / "test_cases.json").read_text(encoding="utf-8"))["test_cases"]
    for case in cases:
        if case["case_id"] == case_id:
            return case["input"]
    raise KeyError(case_id)


def _submission_from_tc(case_id: str) -> ClaimSubmission:
    return ClaimSubmission.model_validate(_load_tc_input(case_id))


def test_eval_bypass_tc004(agent: ExtractionAgent):
    submission = _submission_from_tc("TC004")

    result = agent.extract(submission)

    assert result.success is True
    assert result.extraction_mode == ExtractionMode.EVAL_BYPASS
    assert result.extracted is not None
    assert result.extracted.diagnosis == "Viral Fever"
    assert result.extracted.hospital_name == "City Clinic, Bengaluru"
    assert len(result.extracted.line_items) == 3
    assert result.confidence_score >= 0.85


def test_eval_bypass_tc005_diabetes(agent: ExtractionAgent):
    submission = _submission_from_tc("TC005")

    result = agent.extract(submission)

    assert result.success is True
    assert result.extracted is not None
    assert "Diabetes" in (result.extracted.diagnosis or "")


def test_t2dm_shorthand_normalized():
    extracted = ExtractedClaim(diagnosis="T2DM", treatment="Follow-up for T2DM")
    normalized = normalize_medical_terms(extracted)

    assert normalized.diagnosis == "Type 2 Diabetes Mellitus"
    assert normalized.treatment == "Follow-up for Type 2 Diabetes Mellitus"


def test_eval_bypass_requires_all_documents_have_content(agent: ExtractionAgent):
    submission = ClaimSubmission.model_validate(
        {
            "member_id": "EMP001",
            "policy_id": "PLUM_GHI_2024",
            "claim_category": "CONSULTATION",
            "treatment_date": "2024-11-01",
            "claimed_amount": 1500,
            "documents": [
                {
                    "file_id": "F1",
                    "actual_type": "PRESCRIPTION",
                    "content": {"diagnosis": "Viral Fever"},
                },
                {"file_id": "F2", "actual_type": "HOSPITAL_BILL"},
            ],
        }
    )

    result = agent.extract(submission)

    assert result.success is False
    assert "GEMINI_API_KEY" in (result.error_message or "")


def test_gemini_path_without_api_key(agent: ExtractionAgent):
    submission = ClaimSubmission.model_validate(
        {
            "member_id": "EMP001",
            "policy_id": "PLUM_GHI_2024",
            "claim_category": "CONSULTATION",
            "treatment_date": "2024-11-01",
            "claimed_amount": 1500,
            "documents": [
                {"file_id": "F1", "file_name": "rx.jpg", "actual_type": "PRESCRIPTION"},
                {"file_id": "F2", "file_name": "bill.jpg", "actual_type": "HOSPITAL_BILL"},
            ],
        }
    )

    result = agent.extract(submission, file_contents={"F1": b"fake", "F2": b"fake"})

    assert result.success is False
    assert result.extraction_mode is None
    assert "GEMINI_API_KEY" in (result.error_message or "")


def test_gemini_path_delegates_to_extractor(settings: Settings):
    mock_gemini = MagicMock(spec=GeminiExtractor)
    mock_gemini.is_configured.return_value = True
    mock_gemini.extract_claim.return_value = (
        ExtractedClaim(diagnosis="Acute Bronchitis", hospital_name="Apollo Hospitals"),
        0.88,
        [{"file_id": "F1", "passed": True}],
    )
    agent = ExtractionAgent(settings, gemini=mock_gemini)
    submission = ClaimSubmission.model_validate(
        {
            "member_id": "EMP010",
            "policy_id": "PLUM_GHI_2024",
            "claim_category": "CONSULTATION",
            "treatment_date": "2024-11-03",
            "claimed_amount": 4500,
            "documents": [
                {"file_id": "F1", "file_name": "rx.jpg", "actual_type": "PRESCRIPTION"},
                {"file_id": "F2", "file_name": "bill.jpg", "actual_type": "HOSPITAL_BILL"},
            ],
        }
    )
    file_contents = {"F1": b"img1", "F2": b"img2"}

    result = agent.extract(submission, file_contents=file_contents)

    assert result.success is True
    assert result.extraction_mode == ExtractionMode.GEMINI
    assert result.extracted is not None
    assert result.extracted.diagnosis == "Acute Bronchitis"
    mock_gemini.extract_claim.assert_called_once_with(submission, file_contents)


def test_force_eval_bypass_skips_gemini(settings: Settings):
    mock_gemini = MagicMock(spec=GeminiExtractor)
    agent = ExtractionAgent(settings, gemini=mock_gemini)
    submission = ClaimSubmission.model_validate(_load_tc_input("TC004"))

    result = agent.extract(submission, force_eval_bypass=True)

    assert result.success is True
    assert result.extraction_mode == ExtractionMode.EVAL_BYPASS
    mock_gemini.extract_claim.assert_not_called()


def test_merge_single_doc_extraction_schema():
    doc = SingleDocExtraction(
        diagnosis="MRI Brain",
        tests_ordered=["MRI Brain"],
        extraction_confidence=0.9,
    )
    assert doc.diagnosis == "MRI Brain"
    assert doc.extraction_confidence == 0.9
