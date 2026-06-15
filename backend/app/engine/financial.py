from typing import Any

from pydantic import BaseModel, Field

from app.models.claims import ClaimSubmission
from app.models.policy import PolicyTerms


class FinancialResult(BaseModel):
    approved_amount: float
    eligible_base: float
    network_discount_applied: bool = False
    network_discount_percent: float = 0.0
    network_discount_amount: float = 0.0
    amount_after_network_discount: float | None = None
    copay_percent: float = 0.0
    copay_amount: float = 0.0
    checks: list[dict[str, Any]] = Field(default_factory=list)
    user_message: str = ""


class FinancialCalculator:
    def __init__(self, policy: PolicyTerms) -> None:
        self._policy = policy

    def calculate(
        self,
        submission: ClaimSubmission,
        *,
        eligible_amount: float | None = None,
        hospital_name: str | None = None,
    ) -> FinancialResult:
        base = eligible_amount if eligible_amount is not None else submission.claimed_amount
        category_config = self._policy.get_category_config(submission.claim_category.value)
        copay_percent = float(category_config.get("copay_percent", 0))
        network_discount_percent = float(category_config.get("network_discount_percent", 0))

        resolved_hospital = hospital_name or submission.hospital_name
        is_network = bool(
            resolved_hospital and self._policy.is_network_hospital(resolved_hospital)
        )

        checks: list[dict[str, Any]] = []
        amount_after_discount = base
        network_discount_amount = 0.0

        if is_network and network_discount_percent > 0:
            network_discount_amount = base * (network_discount_percent / 100)
            amount_after_discount = base - network_discount_amount
            checks.append(
                {
                    "step": "NETWORK_DISCOUNT",
                    "passed": True,
                    "hospital": resolved_hospital,
                    "rate_percent": network_discount_percent,
                    "amount_before": base,
                    "deduction": network_discount_amount,
                    "amount_after": amount_after_discount,
                    "message": (
                        f"Network discount ({network_discount_percent:g}%) on "
                        f"₹{base:,.0f} = ₹{amount_after_discount:,.0f}"
                    ),
                }
            )
        else:
            checks.append(
                {
                    "step": "NETWORK_DISCOUNT",
                    "passed": True,
                    "skipped": True,
                    "message": "No network hospital discount applied.",
                }
            )

        copay_amount = amount_after_discount * (copay_percent / 100)
        approved_amount = amount_after_discount - copay_amount

        if copay_percent > 0:
            checks.append(
                {
                    "step": "COPAY",
                    "passed": True,
                    "rate_percent": copay_percent,
                    "amount_before": amount_after_discount,
                    "deduction": copay_amount,
                    "amount_after": approved_amount,
                    "message": (
                        f"Co-pay ({copay_percent:g}%) on ₹{amount_after_discount:,.0f} = "
                        f"₹{copay_amount:,.0f} deducted"
                    ),
                }
            )

        user_message = self._build_user_message(
            base=base,
            is_network=is_network,
            network_discount_percent=network_discount_percent,
            amount_after_discount=amount_after_discount,
            network_discount_amount=network_discount_amount,
            copay_percent=copay_percent,
            copay_amount=copay_amount,
            approved_amount=approved_amount,
        )

        return FinancialResult(
            approved_amount=round(approved_amount, 2),
            eligible_base=base,
            network_discount_applied=is_network and network_discount_percent > 0,
            network_discount_percent=network_discount_percent if is_network else 0.0,
            network_discount_amount=round(network_discount_amount, 2),
            amount_after_network_discount=round(amount_after_discount, 2) if is_network else None,
            copay_percent=copay_percent,
            copay_amount=round(copay_amount, 2),
            checks=checks,
            user_message=user_message,
        )

    def _build_user_message(
        self,
        *,
        base: float,
        is_network: bool,
        network_discount_percent: float,
        amount_after_discount: float,
        network_discount_amount: float,
        copay_percent: float,
        copay_amount: float,
        approved_amount: float,
    ) -> str:
        parts: list[str] = []
        if is_network and network_discount_percent > 0:
            parts.append(
                f"Network discount ({network_discount_percent:g}%) applied first on "
                f"₹{base:,.0f} = ₹{amount_after_discount:,.0f}."
            )
        if copay_percent > 0:
            basis = amount_after_discount if parts else base
            parts.append(
                f"Co-pay ({copay_percent:g}%) applied on ₹{basis:,.0f} = "
                f"₹{copay_amount:,.0f} deducted."
            )
        parts.append(f"Final approved amount: ₹{approved_amount:,.0f}.")
        return " ".join(parts)
