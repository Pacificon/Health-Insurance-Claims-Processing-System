import json
from datetime import date
from pathlib import Path

import pytest

from app.engine.policy_engine import PolicyEngine
from app.models.claims import ClaimCategory, ClaimDocument, ClaimSubmission, Decision, DocumentType
from app.models.extraction import ExtractedClaim
from app.models.policy import PolicyTerms
from app.services.policy_loader import PolicyLoader


@pytest.fixture
def policy() -> PolicyTerms:
    root = Path(__file__).resolve().parents[2]
    return PolicyLoader(root / "policy_terms.json").load()


@pytest.fixture
def engine(policy: PolicyTerms) -> PolicyEngine:
    return PolicyEngine(policy)


def _load_tc_input(case_id: str) -> dict:
    root = Path(__file__).resolve().parents[2]
    cases = json.loads((root / "test_cases.json").read_text(encoding="utf-8"))["test_cases"]
    for case in cases:
        if case["case_id"] == case_id:
            return case["input"]
    raise KeyError(case_id)


def _submission_from_tc(case_id: str) -> ClaimSubmission:
    raw = _load_tc_input(case_id)
    return ClaimSubmission.model_validate(raw)


def _extracted_from_tc(case_id: str) -> ExtractedClaim:
    raw = _load_tc_input(case_id)
    docs = [ClaimDocument.model_validate(d) for d in raw["documents"]]
    return ExtractedClaim.from_document_contents(docs)


def _member(policy: PolicyTerms, member_id: str):
    member = policy.get_member(member_id)
    assert member is not None
    return member


def test_tc005_waiting_period_diabetes(engine: PolicyEngine, policy: PolicyTerms):
    submission = _submission_from_tc("TC005")
    extracted = _extracted_from_tc("TC005")
    member = _member(policy, "EMP005")

    result = engine.evaluate(submission, member, extracted)

    assert result.decision == Decision.REJECTED
    assert "WAITING_PERIOD" in result.rejection_reasons
    assert result.eligibility_date == date(2024, 11, 30)
    assert "2024-11-30" in result.user_message


def test_tc007_pre_auth_missing(engine: PolicyEngine, policy: PolicyTerms):
    submission = _submission_from_tc("TC007")
    extracted = _extracted_from_tc("TC007")
    member = _member(policy, "EMP007")

    result = engine.evaluate(submission, member, extracted)

    assert result.decision == Decision.REJECTED
    assert "PRE_AUTH_MISSING" in result.rejection_reasons
    assert "pre-authorization" in result.user_message.lower()
    assert "resubmit" in result.user_message.lower()


def test_tc008_per_claim_limit_exceeded(engine: PolicyEngine, policy: PolicyTerms):
    submission = _submission_from_tc("TC008")
    extracted = _extracted_from_tc("TC008")
    member = _member(policy, "EMP003")

    result = engine.evaluate(submission, member, extracted)

    assert result.decision == Decision.REJECTED
    assert "PER_CLAIM_EXCEEDED" in result.rejection_reasons
    assert "5,000" in result.user_message or "5000" in result.user_message
    assert "7,500" in result.user_message or "7500" in result.user_message


def test_tc012_excluded_obesity(engine: PolicyEngine, policy: PolicyTerms):
    submission = _submission_from_tc("TC012")
    extracted = _extracted_from_tc("TC012")
    member = _member(policy, "EMP009")

    result = engine.evaluate(submission, member, extracted)

    assert result.decision == Decision.REJECTED
    assert "EXCLUDED_CONDITION" in result.rejection_reasons
    assert result.confidence_score > 0.90


def test_tc006_dental_partial(engine: PolicyEngine, policy: PolicyTerms):
    submission = _submission_from_tc("TC006")
    extracted = _extracted_from_tc("TC006")
    member = _member(policy, "EMP002")

    result = engine.evaluate(submission, member, extracted)

    assert result.decision == Decision.PARTIAL
    assert result.eligible_amount == 8000
    assert len(result.line_item_decisions) == 2
    approved = [d for d in result.line_item_decisions if d.approved]
    rejected = [d for d in result.line_item_decisions if not d.approved]
    assert len(approved) == 1
    assert len(rejected) == 1
    assert "Root Canal" in approved[0].description
    assert "Whitening" in rejected[0].description


def test_tc004_policy_passes(engine: PolicyEngine, policy: PolicyTerms):
    submission = _submission_from_tc("TC004")
    extracted = _extracted_from_tc("TC004")
    member = _member(policy, "EMP001")

    result = engine.evaluate(submission, member, extracted)

    assert result.passed is True
    assert result.decision is None
    assert result.rejection_reasons == []
