import json
from pathlib import Path

import pytest

from app.config import Settings
from app.models.claims import ClaimSubmission, Decision
from app.models.policy import PolicyTerms
from app.models.trace import StageStatus
from app.orchestrator.graph import ClaimsOrchestrator
from app.services.policy_loader import PolicyLoader


@pytest.fixture
def policy() -> PolicyTerms:
    root = Path(__file__).resolve().parents[2]
    return PolicyLoader(root / "policy_terms.json").load()


@pytest.fixture
def settings() -> Settings:
    return Settings()


@pytest.fixture
def orchestrator(policy: PolicyTerms, settings: Settings) -> ClaimsOrchestrator:
    return ClaimsOrchestrator(policy, settings)


def _load_tc_input(case_id: str) -> dict:
    root = Path(__file__).resolve().parents[2]
    cases = json.loads((root / "test_cases.json").read_text(encoding="utf-8"))["test_cases"]
    for case in cases:
        if case["case_id"] == case_id:
            return case["input"]
    raise KeyError(case_id)


def _submission_from_tc(case_id: str) -> ClaimSubmission:
    return ClaimSubmission.model_validate(_load_tc_input(case_id))


def test_tc009_fraud_manual_review(orchestrator: ClaimsOrchestrator):
    submission = _submission_from_tc("TC009")

    trace = orchestrator.process_claim(submission)

    assert trace.decision == Decision.MANUAL_REVIEW
    assert trace.fraud_signals is not None
    assert len(trace.fraud_signals) >= 1
    signal = trace.fraud_signals[0]
    assert signal["same_day_count"] == 4
    assert "CLM_0081" in signal["claim_ids"]
    assert "CLM_0082" in signal["claim_ids"]
    assert "CLM_0083" in signal["claim_ids"]
    assert trace.user_message is not None
    assert "manual review" in trace.user_message.lower() or "flagged" in trace.user_message.lower()

    fraud_stage = next(s for s in trace.stages if s.stage == "FRAUD")
    assert fraud_stage.status == StageStatus.WARNING


def test_tc011_component_failure_graceful_degradation(orchestrator: ClaimsOrchestrator):
    submission = _submission_from_tc("TC011")

    trace = orchestrator.process_claim(submission)

    assert trace.decision == Decision.APPROVED
    assert "FraudAgent" in trace.components_failed
    assert trace.manual_review_recommended is True
    assert trace.confidence_score is not None
    assert trace.confidence_score < 0.85
    assert trace.user_message is not None
    assert "failed" in trace.user_message.lower() or "skipped" in trace.user_message.lower()


def test_tc001_early_stop_no_decision(orchestrator: ClaimsOrchestrator):
    submission = _submission_from_tc("TC001")

    trace = orchestrator.process_claim(submission)

    assert trace.decision is None
    doc_stage = next(s for s in trace.stages if s.stage == "DOCUMENT_VALIDATION")
    assert doc_stage.status == StageStatus.FAILED
    extract_stage = next(s for s in trace.stages if s.stage == "EXTRACTION")
    assert extract_stage.status == StageStatus.SKIPPED


def test_tc004_full_pipeline_approval(orchestrator: ClaimsOrchestrator):
    submission = _submission_from_tc("TC004")

    trace = orchestrator.process_claim(submission)

    assert trace.decision == Decision.APPROVED
    assert trace.approved_amount == 1350
    assert trace.confidence_score is not None
    assert trace.confidence_score > 0.85
