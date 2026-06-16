from typing import Any

from pydantic import BaseModel, Field

from app.agents.document_validator import DocumentValidationResult
from app.agents.extraction_agent import ExtractionResult
from app.agents.fraud_agent import FraudResult
from app.engine.financial import FinancialResult
from app.engine.policy_engine import PolicyEvaluationResult
from app.models.claims import Decision


class SynthesizedDecision(BaseModel):
    decision: Decision | None = None
    approved_amount: float = 0.0
    confidence_score: float = 0.0
    rejection_reasons: list[str] = Field(default_factory=list)
    user_message: str = ""
    manual_review_recommended: bool = False


class DecisionSynthesizer:
    COMPONENT_FAILURE_CONFIDENCE_FACTOR = 0.75

    def synthesize(
        self,
        *,
        doc_validation: DocumentValidationResult | None = None,
        extraction: ExtractionResult | None = None,
        policy_result: PolicyEvaluationResult | None = None,
        financial_result: FinancialResult | None = None,
        fraud_result: FraudResult | None = None,
        components_failed: list[str] | None = None,
        early_stop: bool = False,
    ) -> SynthesizedDecision:
        failed = components_failed or []

        if early_stop and doc_validation and not doc_validation.passed:
            message = doc_validation.messages[0] if doc_validation.messages else "Document validation failed."
            return SynthesizedDecision(
                decision=None,
                user_message=message,
                confidence_score=0.0,
            )

        if extraction is None or not extraction.success or extraction.extracted is None:
            return SynthesizedDecision(
                decision=Decision.REJECTED,
                rejection_reasons=["EXTRACTION_FAILED"],
                user_message=extraction.error_message if extraction else "Extraction failed.",
                confidence_score=0.5,
            )

        if policy_result is None:
            return SynthesizedDecision(
                decision=Decision.REJECTED,
                rejection_reasons=["POLICY_EVALUATION_FAILED"],
                user_message="Policy evaluation did not complete.",
                confidence_score=0.5,
            )

        confidence = min(extraction.confidence_score, policy_result.confidence_score)
        manual_review = False
        rejection_reasons = list(policy_result.rejection_reasons)

        if policy_result.decision == Decision.REJECTED:
            return SynthesizedDecision(
                decision=Decision.REJECTED,
                approved_amount=0.0,
                confidence_score=confidence,
                rejection_reasons=rejection_reasons,
                user_message=policy_result.user_message,
                manual_review_recommended=bool(failed),
            )

        approved_amount = financial_result.approved_amount if financial_result else 0.0
        messages: list[str] = []

        if policy_result.decision == Decision.PARTIAL:
            decision = Decision.PARTIAL
            messages.append(policy_result.user_message)
        else:
            decision = Decision.APPROVED
            messages.append(policy_result.user_message)

        if financial_result:
            messages.append(financial_result.user_message)

        if fraud_result and fraud_result.manual_review_required:
            decision = Decision.MANUAL_REVIEW
            signal_text = "; ".join(signal.description for signal in fraud_result.signals)
            messages.append(f"Flagged for manual review: {signal_text}")

        if failed:
            confidence *= self.COMPONENT_FAILURE_CONFIDENCE_FACTOR
            manual_review = True
            names = ", ".join(failed)
            messages.append(
                f"Component(s) failed during processing ({names}) and were skipped. "
                f"Manual review is recommended due to incomplete processing."
            )

        return SynthesizedDecision(
            decision=decision,
            approved_amount=approved_amount,
            confidence_score=round(confidence, 2),
            rejection_reasons=rejection_reasons,
            user_message=" ".join(m for m in messages if m),
            manual_review_recommended=manual_review,
        )

    def financial_breakdown_dict(self, financial_result: FinancialResult | None) -> dict[str, Any] | None:
        if financial_result is None:
            return None
        return {
            "eligible_base": financial_result.eligible_base,
            "network_discount_applied": financial_result.network_discount_applied,
            "network_discount_percent": financial_result.network_discount_percent,
            "network_discount_amount": financial_result.network_discount_amount,
            "amount_after_network_discount": financial_result.amount_after_network_discount,
            "copay_percent": financial_result.copay_percent,
            "copay_amount": financial_result.copay_amount,
            "approved_amount": financial_result.approved_amount,
        }
