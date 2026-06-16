from typing import Any

from pydantic import BaseModel, Field

from app.models.claims import ClaimSubmission
from app.models.policy import PolicyTerms


class FraudSignal(BaseModel):
    signal_type: str
    description: str
    claim_ids: list[str] = Field(default_factory=list)
    amounts: list[float] = Field(default_factory=list)
    providers: list[str] = Field(default_factory=list)
    same_day_count: int | None = None


class FraudResult(BaseModel):
    manual_review_required: bool = False
    signals: list[FraudSignal] = Field(default_factory=list)
    checks: list[dict[str, Any]] = Field(default_factory=list)


class FraudSignalAgent:
    COMPONENT_NAME = "FraudAgent"

    def __init__(self, policy: PolicyTerms) -> None:
        self._policy = policy

    def evaluate(self, submission: ClaimSubmission) -> FraudResult:
        limit = self._policy.fraud_thresholds.same_day_claims_limit
        history = submission.claims_history or []
        same_day = [entry for entry in history if entry.date == submission.treatment_date]
        same_day_count = len(same_day) + 1  # include current claim

        # Limit of 2 allows 3 auto-processed claims; the 4th routes to manual review (TC009).
        if len(same_day) <= limit:
            return FraudResult(
                checks=[
                    {
                        "rule": "SAME_DAY_CLAIMS",
                        "passed": True,
                        "same_day_count": same_day_count,
                        "limit": limit,
                        "message": f"Same-day claim count ({same_day_count}) within threshold.",
                    }
                ]
            )

        signal = FraudSignal(
            signal_type="SAME_DAY_CLAIMS_EXCEEDED",
            description=(
                f"Unusual pattern: {same_day_count} claims submitted for "
                f"{submission.treatment_date.isoformat()} (limit: {limit} prior same-day claims)."
            ),
            claim_ids=[entry.claim_id for entry in same_day],
            amounts=[entry.amount for entry in same_day],
            providers=[entry.provider or "Unknown" for entry in same_day],
            same_day_count=same_day_count,
        )
        return FraudResult(
            manual_review_required=True,
            signals=[signal],
            checks=[
                {
                    "rule": "SAME_DAY_CLAIMS",
                    "passed": False,
                    "same_day_count": same_day_count,
                    "limit": limit,
                    "prior_same_day_claims": len(same_day),
                    "message": signal.description,
                }
            ],
        )
