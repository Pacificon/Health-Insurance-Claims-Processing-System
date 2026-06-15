def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["policy_id"] == "PLUM_GHI_2024"
    assert data["member_count"] >= 10


def test_policy_summary_endpoint(client):
    response = client.get("/policy/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["policy_id"] == "PLUM_GHI_2024"
    assert "CONSULTATION" in data["claim_categories"]
    assert data["per_claim_limit"] == 5000
