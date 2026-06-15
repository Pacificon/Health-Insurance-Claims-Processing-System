import json
from pathlib import Path

import pytest

from app.agents.document_validator import ActionRequired, DocumentValidator
from app.models.claims import ClaimSubmission
from app.models.policy import PolicyTerms
from app.services.policy_loader import PolicyLoader


@pytest.fixture
def policy() -> PolicyTerms:
    root = Path(__file__).resolve().parents[2]
    return PolicyLoader(root / "policy_terms.json").load()


@pytest.fixture
def validator(policy: PolicyTerms) -> DocumentValidator:
    return DocumentValidator(policy)


def _load_tc_input(case_id: str) -> dict:
    root = Path(__file__).resolve().parents[2]
    cases = json.loads((root / "test_cases.json").read_text(encoding="utf-8"))["test_cases"]
    for case in cases:
        if case["case_id"] == case_id:
            return case["input"]
    raise KeyError(case_id)


def _submission_from_tc(case_id: str) -> ClaimSubmission:
    return ClaimSubmission.model_validate(_load_tc_input(case_id))


def test_tc001_wrong_document_types(validator: DocumentValidator):
    submission = _submission_from_tc("TC001")

    result = validator.validate(submission)

    assert result.passed is False
    assert result.decision is None
    assert result.stage == "DOCUMENT_VALIDATION"
    assert result.action_required == ActionRequired.REUPLOAD
    assert len(result.messages) == 1
    message = result.messages[0]
    assert "PRESCRIPTION (×2)" in message
    assert "CONSULTATION requires PRESCRIPTION + HOSPITAL_BILL" in message


def test_tc002_unreadable_document(validator: DocumentValidator):
    submission = _submission_from_tc("TC002")

    result = validator.validate(submission)

    assert result.passed is False
    assert result.decision is None
    assert result.action_required == ActionRequired.REUPLOAD
    message = result.messages[0]
    assert "blurry_bill.jpg" in message
    assert "re-upload" in message.lower()
    assert "reject" not in message.lower()


def test_tc003_patient_name_mismatch(validator: DocumentValidator):
    submission = _submission_from_tc("TC003")

    result = validator.validate(submission)

    assert result.passed is False
    assert result.decision is None
    assert result.action_required == ActionRequired.REUPLOAD
    message = result.messages[0]
    assert "Rajesh Kumar" in message
    assert "Arjun Mehta" in message
    assert "Prescription" in message
    assert "Bill" in message


def test_tc004_valid_documents_pass(validator: DocumentValidator):
    submission = _submission_from_tc("TC004")

    result = validator.validate(submission)

    assert result.passed is True
    assert result.action_required is None
    assert result.messages == []
