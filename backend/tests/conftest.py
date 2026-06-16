import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.db.database import reset_db
from app.main import app
from app.services.policy_loader import PolicyLoader, create_policy_loader


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    db_path = tmp_path / "claims_test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    get_settings.cache_clear()
    reset_db(get_settings().database_url)
    yield


@pytest.fixture
def settings() -> Settings:
    return Settings()


@pytest.fixture
def policy_loader(settings: Settings) -> PolicyLoader:
    return create_policy_loader(settings)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
