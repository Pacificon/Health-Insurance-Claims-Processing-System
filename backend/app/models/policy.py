from datetime import date
from typing import Any

from pydantic import BaseModel, Field


class FamilyFloater(BaseModel):
    enabled: bool
    combined_limit: int
    covered_relationships: list[str]


class Coverage(BaseModel):
    sum_insured_per_employee: int
    annual_opd_limit: int
    per_claim_limit: int
    family_floater: FamilyFloater


class PolicyHolder(BaseModel):
    company_name: str
    employee_count: int
    policy_start_date: date
    policy_end_date: date
    renewal_status: str


class WaitingPeriods(BaseModel):
    initial_waiting_period_days: int
    pre_existing_conditions_days: int
    specific_conditions: dict[str, int]


class Exclusions(BaseModel):
    conditions: list[str]
    dental_exclusions: list[str]
    vision_exclusions: list[str]


class PreAuthorization(BaseModel):
    required_for: list[str]
    validity_days: int


class SubmissionRules(BaseModel):
    deadline_days_from_treatment: int
    minimum_claim_amount: int
    currency: str


class DocumentRequirement(BaseModel):
    required: list[str]
    optional: list[str]


class FraudThresholds(BaseModel):
    same_day_claims_limit: int
    monthly_claims_limit: int
    high_value_claim_threshold: int
    auto_manual_review_above: int
    fraud_score_manual_review_threshold: float


class Member(BaseModel):
    member_id: str
    name: str
    date_of_birth: date
    gender: str
    relationship: str
    join_date: date | None = None
    dependents: list[str] | None = None
    primary_member_id: str | None = None


class PolicyTerms(BaseModel):
    policy_id: str
    policy_name: str
    insurer: str
    policy_holder: PolicyHolder
    coverage: Coverage
    opd_categories: dict[str, dict[str, Any]]
    waiting_periods: WaitingPeriods
    exclusions: Exclusions
    pre_authorization: PreAuthorization
    network_hospitals: list[str]
    submission_rules: SubmissionRules
    document_requirements: dict[str, DocumentRequirement]
    fraud_thresholds: FraudThresholds
    members: list[Member]

    def get_member(self, member_id: str) -> Member | None:
        for member in self.members:
            if member.member_id == member_id:
                return member
        return None

    def get_document_requirement(self, claim_category: str) -> DocumentRequirement | None:
        req = self.document_requirements.get(claim_category)
        if req is None:
            return None
        if isinstance(req, DocumentRequirement):
            return req
        return DocumentRequirement.model_validate(req)

    def is_network_hospital(self, hospital_name: str) -> bool:
        normalized = hospital_name.strip().lower()
        return any(h.lower() in normalized or normalized in h.lower() for h in self.network_hospitals)

    def get_category_config(self, claim_category: str) -> dict[str, Any]:
        key = claim_category.lower()
        return self.opd_categories.get(key, {})
