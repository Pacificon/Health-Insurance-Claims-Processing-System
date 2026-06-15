from fastapi import FastAPI

from app.config import get_settings
from app.services.policy_loader import get_policy_loader

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Multi-agent health insurance claims adjudication API",
)


@app.on_event("startup")
def warm_policy_cache() -> None:
    get_policy_loader().load()


@app.get("/health")
def health() -> dict:
    loader = get_policy_loader()
    policy = loader.load()
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "policy_id": policy.policy_id,
        "member_count": len(policy.members),
    }


@app.get("/policy/summary")
def policy_summary() -> dict:
    policy = get_policy_loader().load()
    return {
        "policy_id": policy.policy_id,
        "policy_name": policy.policy_name,
        "insurer": policy.insurer,
        "per_claim_limit": policy.coverage.per_claim_limit,
        "claim_categories": list(policy.document_requirements.keys()),
        "network_hospital_count": len(policy.network_hospitals),
        "member_count": len(policy.members),
    }
