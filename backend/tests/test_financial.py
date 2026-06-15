import json
from pathlib import Path

import pytest

from app.engine.financial import FinancialCalculator
from app.models.claims import ClaimSubmission
from app.models.policy import PolicyTerms
from app.services.policy_loader import PolicyLoader


@pytest.fixture
def policy() -> PolicyTerms:
    root = Path(__file__).resolve().parents[2]
    return PolicyLoader(root / "policy_terms.json").load()


@pytest.fixture
def calculator(policy: PolicyTerms) -> FinancialCalculator:
    return FinancialCalculator(policy)


def _load_tc_input(case_id: str) -> dict:
    root = Path(__file__).resolve().parents[2]
    cases = json.loads((root / "test_cases.json").read_text(encoding="utf-8"))["test_cases"]
    for case in cases:
        if case["case_id"] == case_id:
            return case["input"]
    raise KeyError(case_id)


def _submission_from_tc(case_id: str) -> ClaimSubmission:
    return ClaimSubmission.model_validate(_load_tc_input(case_id))


def test_tc004_consultation_copay(calculator: FinancialCalculator):
    submission = _submission_from_tc("TC004")

    result = calculator.calculate(submission)

    assert result.approved_amount == 1350
    assert result.copay_percent == 10
    assert result.copay_amount == 150
    assert result.network_discount_applied is False
    assert result.network_discount_amount == 0
    assert "₹1,350" in result.user_message or "1350" in result.user_message


def test_tc010_network_discount_before_copay(calculator: FinancialCalculator):
    submission = _submission_from_tc("TC010")

    result = calculator.calculate(submission, hospital_name=submission.hospital_name)

    assert result.approved_amount == 3240
    assert result.network_discount_applied is True
    assert result.network_discount_percent == 20
    assert result.network_discount_amount == 900
    assert result.amount_after_network_discount == 3600
    assert result.copay_amount == 360
    assert result.copay_percent == 10

    network_check = next(c for c in result.checks if c["step"] == "NETWORK_DISCOUNT")
    copay_check = next(c for c in result.checks if c["step"] == "COPAY")
    assert network_check["amount_before"] == 4500
    assert network_check["amount_after"] == 3600
    assert copay_check["amount_before"] == 3600
    assert copay_check["deduction"] == 360


def test_tc010_copay_basis_is_post_discount_not_claimed_amount(calculator: FinancialCalculator):
    """Co-pay must be calculated on post-discount amount (₹3,600), not claimed (₹4,500)."""
    submission = _submission_from_tc("TC010")

    result = calculator.calculate(submission, hospital_name="Apollo Hospitals")

    assert result.copay_amount == 360
    assert result.copay_amount != 450


def test_partial_eligible_amount_uses_policy_base(calculator: FinancialCalculator):
    """Dental partial (TC006) passes policy-eligible amount, not full claimed amount."""
    submission = _submission_from_tc("TC006")

    result = calculator.calculate(submission, eligible_amount=8000)

    assert result.eligible_base == 8000
    assert result.approved_amount == 8000
    assert result.copay_amount == 0
