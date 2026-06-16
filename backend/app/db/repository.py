import json

from sqlalchemy.orm import Session

from app.db.database import ClaimRecord
from app.models.claims import ClaimSubmission
from app.models.trace import DecisionTrace


class ClaimRepository:
    def save(self, db: Session, submission: ClaimSubmission, trace: DecisionTrace) -> ClaimRecord:
        record = ClaimRecord(
            claim_id=trace.claim_id,
            member_id=submission.member_id,
            policy_id=submission.policy_id,
            claim_category=submission.claim_category.value,
            treatment_date=submission.treatment_date.isoformat(),
            claimed_amount=submission.claimed_amount,
            decision=trace.decision.value if trace.decision else None,
            approved_amount=trace.approved_amount,
            trace_json=trace.model_dump_json(),
            submission_json=submission.model_dump_json(),
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    def get_trace(self, db: Session, claim_id: str) -> DecisionTrace | None:
        record = db.get(ClaimRecord, claim_id)
        if record is None:
            return None
        return DecisionTrace.model_validate(json.loads(record.trace_json))

    def list_recent(self, db: Session, *, limit: int = 20) -> list[ClaimRecord]:
        return db.query(ClaimRecord).order_by(ClaimRecord.created_at.desc()).limit(limit).all()
