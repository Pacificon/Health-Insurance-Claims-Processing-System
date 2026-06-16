import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def _tc004_payload() -> dict:
    root = Path(__file__).resolve().parents[2]
    cases = json.loads((root / "test_cases.json").read_text(encoding="utf-8"))["test_cases"]
    for case in cases:
        if case["case_id"] == "TC004":
            return case["input"]
    raise KeyError("TC004")


def _tc011_payload() -> dict:
    root = Path(__file__).resolve().parents[2]
    cases = json.loads((root / "test_cases.json").read_text(encoding="utf-8"))["test_cases"]
    for case in cases:
        if case["case_id"] == "TC011":
            return case["input"]
    raise KeyError("TC011")


def test_post_claims_tc004_approved(client: TestClient):
    response = client.post("/claims", json=_tc004_payload())

    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "APPROVED"
    assert data["approved_amount"] == 1350
    assert data["claim_id"]
    assert len(data["stages"]) >= 4
    assert data["confidence_score"] > 0.85


def test_get_claim_returns_persisted_trace(client: TestClient):
    post = client.post("/claims", json=_tc004_payload())
    claim_id = post.json()["claim_id"]

    get_response = client.get(f"/claims/{claim_id}")

    assert get_response.status_code == 200
    assert get_response.json()["claim_id"] == claim_id
    assert get_response.json()["decision"] == "APPROVED"


def test_get_claim_not_found(client: TestClient):
    response = client.get("/claims/CLM_DOESNOTEXIST")
    assert response.status_code == 404


def test_post_claims_tc011_no_server_error(client: TestClient):
    response = client.post("/claims", json=_tc011_payload())

    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "APPROVED"
    assert "FraudAgent" in data["components_failed"]
    assert data["manual_review_recommended"] is True


def test_post_claims_invalid_member_returns_400(client: TestClient):
    payload = _tc004_payload()
    payload["member_id"] = "EMP_INVALID"

    response = client.post("/claims", json=payload)

    assert response.status_code == 400
