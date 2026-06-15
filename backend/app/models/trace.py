from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.models.claims import Decision


class StageStatus(StrEnum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    WARNING = "WARNING"


class StageTrace(BaseModel):
    stage: str
    status: StageStatus
    checks: list[dict[str, Any]] = Field(default_factory=list)
    fields: dict[str, Any] | None = None
    rule: str | None = None
    detail: str | None = None
    messages: list[str] = Field(default_factory=list)


class DecisionTrace(BaseModel):
    claim_id: str
    stages: list[StageTrace] = Field(default_factory=list)
    decision: Decision | None = None
    approved_amount: float = 0
    rejection_reasons: list[str] = Field(default_factory=list)
    confidence_score: float | None = None
    components_failed: list[str] = Field(default_factory=list)
    manual_review_recommended: bool = False
    user_message: str | None = None
    financial_breakdown: dict[str, Any] | None = None
    line_item_decisions: list[dict[str, Any]] | None = None
    fraud_signals: list[dict[str, Any]] | None = None
