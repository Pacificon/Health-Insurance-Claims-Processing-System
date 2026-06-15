from datetime import date, timedelta
import re
from typing import Any

from pydantic import BaseModel, Field

from app.models.claims import ClaimCategory, ClaimSubmission, Decision
from app.models.extraction import ExtractedClaim, LineItem
from app.models.policy import Member, PolicyTerms


class LineItemDecision(BaseModel):
    description: str
    amount: float
    approved: bool
    reason: str | None = None


class PolicyEvaluationResult(BaseModel):
    passed: bool
    decision: Decision | None = None
    rejection_reasons: list[str] = Field(default_factory=list)
    eligible_amount: float | None = None
    line_item_decisions: list[LineItemDecision] = Field(default_factory=list)
    eligibility_date: date | None = None
    user_message: str = ""
    confidence_score: float = 0.95
    checks: list[dict[str, Any]] = Field(default_factory=list)


# Maps policy waiting_periods.specific_conditions keys to searchable terms.
WAITING_PERIOD_KEYWORDS: dict[str, list[str]] = {
    "diabetes": ["diabetes", "t2dm", "type 2 diabetes", "diabetes mellitus"],
    "hypertension": ["hypertension", "htn", "high blood pressure"],
    "thyroid_disorders": ["thyroid", "hypothyroid", "hyperthyroid"],
    "joint_replacement": ["joint replacement", "knee replacement", "hip replacement"],
    "maternity": ["maternity", "pregnancy", "prenatal"],
    "mental_health": ["depression", "anxiety", "mental health", "psychiatric"],
    "obesity_treatment": ["obesity treatment", "weight loss program", "bariatric surgery"],
    "hernia": ["hernia"],
    "cataract": ["cataract"],
}

EXCLUSION_KEYWORDS: dict[str, list[str]] = {
    "obesity and weight loss programs": [
        "obesity",
        "weight loss",
        "bariatric",
        "diet program",
        "nutrition program",
        "bmi",
        "morbid obesity",
    ],
    "bariatric surgery": ["bariatric"],
    "cosmetic or aesthetic procedures": ["cosmetic", "aesthetic", "teeth whitening", "whitening"],
    "teeth whitening": ["teeth whitening", "whitening", "bleaching"],
}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


def _text_contains_any(text: str, keywords: list[str]) -> bool:
    normalized = _normalize(text)
    return any(kw in normalized for kw in keywords)


def _collect_claim_text(extracted: ExtractedClaim) -> str:
    parts = [
        extracted.diagnosis or "",
        extracted.treatment or "",
        " ".join(extracted.tests_ordered),
        " ".join(item.description for item in extracted.line_items),
    ]
    return " ".join(parts)


def _match_excluded_procedure(description: str, excluded: list[str]) -> str | None:
    normalized = _normalize(description)
    for proc in excluded:
        if _normalize(proc) in normalized or normalized in _normalize(proc):
            return proc
    for proc in excluded:
        proc_norm = _normalize(proc)
        if any(word in normalized for word in proc_norm.split() if len(word) > 4):
            return proc
    return None


def _match_covered_procedure(description: str, covered: list[str]) -> bool:
    normalized = _normalize(description)
    for proc in covered:
        proc_norm = _normalize(proc)
        if proc_norm in normalized or normalized in proc_norm:
            return True
    return False


class PolicyEngine:
    def __init__(self, policy: PolicyTerms) -> None:
        self._policy = policy

    def evaluate(
        self,
        submission: ClaimSubmission,
        member: Member,
        extracted: ExtractedClaim,
    ) -> PolicyEvaluationResult:
        checks: list[dict[str, Any]] = []

        per_claim = self._check_per_claim_limit(submission)
        checks.append(per_claim)
        if not per_claim["passed"]:
            return self._rejected(
                ["PER_CLAIM_EXCEEDED"],
                per_claim["message"],
                checks,
                confidence=0.98,
            )

        exclusion = self._check_exclusions(extracted)
        checks.append(exclusion)
        if not exclusion["passed"]:
            return self._rejected(
                ["EXCLUDED_CONDITION"],
                exclusion["message"],
                checks,
                confidence=0.95,
            )

        waiting = self._check_waiting_period(submission, member, extracted)
        checks.append(waiting)
        if not waiting["passed"]:
            return PolicyEvaluationResult(
                passed=False,
                decision=Decision.REJECTED,
                rejection_reasons=["WAITING_PERIOD"],
                eligibility_date=waiting.get("eligibility_date"),
                user_message=waiting["message"],
                confidence_score=0.94,
                checks=checks,
            )

        pre_auth = self._check_pre_authorization(submission, extracted)
        checks.append(pre_auth)
        if not pre_auth["passed"]:
            return self._rejected(
                ["PRE_AUTH_MISSING"],
                pre_auth["message"],
                checks,
                confidence=0.96,
            )

        if submission.claim_category == ClaimCategory.DENTAL and extracted.line_items:
            dental = self._evaluate_dental_line_items(extracted.line_items)
            checks.append(dental["check"])
            if dental["decision"] == Decision.PARTIAL:
                return PolicyEvaluationResult(
                    passed=True,
                    decision=Decision.PARTIAL,
                    eligible_amount=dental["eligible_amount"],
                    line_item_decisions=dental["line_item_decisions"],
                    user_message=dental["message"],
                    confidence_score=0.93,
                    checks=checks,
                )
            if dental["decision"] == Decision.REJECTED:
                return self._rejected(
                    ["EXCLUDED_CONDITION"],
                    dental["message"],
                    checks,
                    confidence=0.94,
                )

        checks.append({"rule": "POLICY_CLEAR", "passed": True, "message": "All policy checks passed"})
        return PolicyEvaluationResult(
            passed=True,
            decision=None,
            user_message="Claim meets policy requirements.",
            confidence_score=0.92,
            checks=checks,
        )

    def _check_per_claim_limit(self, submission: ClaimSubmission) -> dict[str, Any]:
        limit = self._policy.coverage.per_claim_limit
        passed = submission.claimed_amount <= limit
        return {
            "rule": "PER_CLAIM_LIMIT",
            "passed": passed,
            "limit": limit,
            "claimed_amount": submission.claimed_amount,
            "message": (
                f"Claim amount ₹{submission.claimed_amount:,.0f} exceeds the per-claim limit of "
                f"₹{limit:,.0f}. Please split this into separate claims or reduce the billed amount."
                if not passed
                else f"Claim amount within per-claim limit of ₹{limit:,.0f}."
            ),
        }

    def _check_exclusions(self, extracted: ExtractedClaim) -> dict[str, Any]:
        claim_text = _collect_claim_text(extracted)
        for exclusion in self._policy.exclusions.conditions:
            keywords = EXCLUSION_KEYWORDS.get(_normalize(exclusion), [_normalize(exclusion)])
            if _text_contains_any(claim_text, keywords):
                return {
                    "rule": "EXCLUDED_CONDITION",
                    "passed": False,
                    "matched_exclusion": exclusion,
                    "message": (
                        f"This claim is not covered under your policy. The treatment relates to "
                        f"'{exclusion}', which is excluded from coverage."
                    ),
                }
        return {"rule": "EXCLUDED_CONDITION", "passed": True, "message": "No policy exclusions matched."}

    def _check_waiting_period(
        self,
        submission: ClaimSubmission,
        member: Member,
        extracted: ExtractedClaim,
    ) -> dict[str, Any]:
        if member.join_date is None:
            return {"rule": "WAITING_PERIOD", "passed": True, "message": "No join date; waiting period skipped."}

        claim_text = _collect_claim_text(extracted)
        for condition_key, wait_days in self._policy.waiting_periods.specific_conditions.items():
            keywords = WAITING_PERIOD_KEYWORDS.get(condition_key, [condition_key.replace("_", " ")])
            if not _text_contains_any(claim_text, keywords):
                continue

            eligibility_date = member.join_date + timedelta(days=wait_days)
            if submission.treatment_date < eligibility_date:
                condition_label = condition_key.replace("_", " ")
                return {
                    "rule": "WAITING_PERIOD",
                    "passed": False,
                    "condition": condition_key,
                    "wait_days": wait_days,
                    "eligibility_date": eligibility_date,
                    "message": (
                        f"Claims related to {condition_label} are subject to a {wait_days}-day waiting "
                        f"period from your policy join date ({member.join_date.isoformat()}). "
                        f"You will be eligible for {condition_label}-related claims from "
                        f"{eligibility_date.isoformat()}."
                    ),
                }

        return {"rule": "WAITING_PERIOD", "passed": True, "message": "No waiting period violations."}

    def _check_pre_authorization(self, submission: ClaimSubmission, extracted: ExtractedClaim) -> dict[str, Any]:
        category = submission.claim_category.value.lower()
        category_config = self._policy.get_category_config(submission.claim_category.value)
        threshold = float(category_config.get("pre_auth_threshold", 10000))
        high_value_tests = category_config.get("high_value_tests_requiring_pre_auth", ["MRI", "CT Scan", "PET Scan"])

        if extracted.pre_authorization_obtained:
            return {"rule": "PRE_AUTHORIZATION", "passed": True, "message": "Pre-authorization on file."}

        texts_to_check = extracted.tests_ordered + [item.description for item in extracted.line_items]
        if extracted.diagnosis:
            texts_to_check.append(extracted.diagnosis)

        requires_pre_auth = False
        matched_test = None
        for text in texts_to_check:
            for test_name in high_value_tests:
                if test_name.lower() in text.lower():
                    requires_pre_auth = True
                    matched_test = test_name
                    break
            if requires_pre_auth:
                break

        amount = submission.claimed_amount
        if category == "diagnostic" and requires_pre_auth and amount > threshold:
            return {
                "rule": "PRE_AUTHORIZATION",
                "passed": False,
                "matched_test": matched_test,
                "threshold": threshold,
                "message": (
                    f"Pre-authorization is required for {matched_test} procedures above ₹{threshold:,.0f}. "
                    f"Your claim of ₹{amount:,.0f} was submitted without pre-authorization. "
                    f"Please obtain pre-authorization from Plum and resubmit this claim with the "
                    f"pre-auth reference number."
                ),
            }

        return {"rule": "PRE_AUTHORIZATION", "passed": True, "message": "Pre-authorization not required."}

    def _evaluate_dental_line_items(self, line_items: list[LineItem]) -> dict[str, Any]:
        dental_config = self._policy.get_category_config("DENTAL")
        covered = dental_config.get("covered_procedures", [])
        excluded = dental_config.get("excluded_procedures", [])

        decisions: list[LineItemDecision] = []
        approved_total = 0.0
        rejected_count = 0

        for item in line_items:
            excluded_match = _match_excluded_procedure(item.description, excluded)
            if excluded_match:
                decisions.append(
                    LineItemDecision(
                        description=item.description,
                        amount=item.amount,
                        approved=False,
                        reason=f"Excluded procedure: {excluded_match} is not covered under dental OPD.",
                    )
                )
                rejected_count += 1
                continue

            if _match_covered_procedure(item.description, covered):
                decisions.append(
                    LineItemDecision(
                        description=item.description,
                        amount=item.amount,
                        approved=True,
                        reason="Covered dental procedure.",
                    )
                )
                approved_total += item.amount
            else:
                decisions.append(
                    LineItemDecision(
                        description=item.description,
                        amount=item.amount,
                        approved=False,
                        reason="Procedure not listed as covered under dental OPD.",
                    )
                )
                rejected_count += 1

        approved_count = sum(1 for d in decisions if d.approved)
        if approved_count > 0 and rejected_count > 0:
            return {
                "decision": Decision.PARTIAL,
                "eligible_amount": approved_total,
                "line_item_decisions": decisions,
                "message": "Some line items are covered and others are excluded under your dental policy.",
                "check": {
                    "rule": "DENTAL_LINE_ITEMS",
                    "passed": True,
                    "partial": True,
                    "approved_amount": approved_total,
                },
            }
        if approved_count == 0:
            return {
                "decision": Decision.REJECTED,
                "eligible_amount": 0,
                "line_item_decisions": decisions,
                "message": "None of the billed dental procedures are covered under your policy.",
                "check": {"rule": "DENTAL_LINE_ITEMS", "passed": False},
            }
        return {
            "decision": None,
            "eligible_amount": approved_total,
            "line_item_decisions": decisions,
            "message": "All dental line items are covered.",
            "check": {"rule": "DENTAL_LINE_ITEMS", "passed": True},
        }

    def _rejected(
        self,
        reasons: list[str],
        message: str,
        checks: list[dict[str, Any]],
        confidence: float,
    ) -> PolicyEvaluationResult:
        return PolicyEvaluationResult(
            passed=False,
            decision=Decision.REJECTED,
            rejection_reasons=reasons,
            user_message=message,
            confidence_score=confidence,
            checks=checks,
        )
