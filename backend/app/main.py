from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.claims import router as claims_router
from app.config import get_settings
from app.db.database import init_db
from app.services.policy_loader import get_policy_loader

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Multi-agent health insurance claims adjudication API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.cors_origin_regex or None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    init_db()
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


app.include_router(claims_router)
