import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app
from app.services.policy_loader import PolicyLoader, create_policy_loader


@pytest.fixture
def settings() -> Settings:
    return Settings()


@pytest.fixture
def policy_loader(settings: Settings) -> PolicyLoader:
    return create_policy_loader(settings)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
