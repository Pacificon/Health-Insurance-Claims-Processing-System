from datetime import date

import pytest

from app.models.claims import ClaimCategory, ClaimDocument, ClaimSubmission, DocumentType
from app.services.policy_loader import MemberNotFoundError, PolicyLoader, PolicyNotFoundError


def test_load_policy_terms(policy_loader: PolicyLoader):
    policy = policy_loader.load()
    assert policy.policy_id == "PLUM_GHI_2024"
    assert policy.coverage.per_claim_limit == 5000
    assert "consultation" in policy.opd_categories


def test_get_member(policy_loader: PolicyLoader):
    member = policy_loader.get_member("PLUM_GHI_2024", "EMP001")
    assert member.name == "Rajesh Kumar"
    assert member.join_date == date(2024, 4, 1)


def test_get_member_not_found(policy_loader: PolicyLoader):
    with pytest.raises(MemberNotFoundError):
        policy_loader.get_member("PLUM_GHI_2024", "EMP999")


def test_get_policy_wrong_id(policy_loader: PolicyLoader):
    with pytest.raises(PolicyNotFoundError):
        policy_loader.get_policy("WRONG_POLICY")


def test_document_requirements(policy_loader: PolicyLoader):
    policy = policy_loader.load()
    req = policy.get_document_requirement("CONSULTATION")
    assert req is not None
    assert "PRESCRIPTION" in req.required
    assert "HOSPITAL_BILL" in req.required


def test_network_hospital_match(policy_loader: PolicyLoader):
    policy = policy_loader.load()
    assert policy.is_network_hospital("Apollo Hospitals, Bengaluru") is True
    assert policy.is_network_hospital("City Clinic") is False


def test_claim_submission_model_validation():
    claim = ClaimSubmission(
        member_id="EMP001",
        policy_id="PLUM_GHI_2024",
        claim_category=ClaimCategory.CONSULTATION,
        treatment_date=date(2024, 11, 1),
        claimed_amount=1500,
        documents=[
            ClaimDocument(file_id="F001", actual_type=DocumentType.PRESCRIPTION),
            ClaimDocument(file_id="F002", actual_type=DocumentType.HOSPITAL_BILL),
        ],
    )
    assert claim.claim_category == ClaimCategory.CONSULTATION
    assert len(claim.documents) == 2
