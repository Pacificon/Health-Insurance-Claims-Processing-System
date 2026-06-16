from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.database import get_db
from app.db.repository import ClaimRepository
from app.models.claims import ClaimSubmission
from app.models.trace import DecisionTrace
from app.orchestrator.graph import ClaimsOrchestrator
from app.services.policy_loader import get_policy_loader

router = APIRouter(tags=["claims"])
_repository = ClaimRepository()


def _get_orchestrator() -> ClaimsOrchestrator:
    settings = get_settings()
    policy = get_policy_loader().load()
    return ClaimsOrchestrator(policy, settings)


@router.post("/claims", response_model=DecisionTrace, status_code=200)
def submit_claim(
    submission: ClaimSubmission,
    db: Session = Depends(get_db),
) -> DecisionTrace:
    orchestrator = _get_orchestrator()
    try:
        trace = orchestrator.process_claim(submission)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    _repository.save(db, submission, trace)
    return trace


@router.get("/claims/{claim_id}", response_model=DecisionTrace)
def get_claim(claim_id: str, db: Session = Depends(get_db)) -> DecisionTrace:
    trace = _repository.get_trace(db, claim_id)
    if trace is None:
        raise HTTPException(status_code=404, detail=f"Claim '{claim_id}' not found.")
    return trace
