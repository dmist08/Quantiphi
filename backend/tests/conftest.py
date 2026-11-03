import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        github_token="test-token",
        llm_api_key=None,
        llm_model="test-model",
        database_path=str(tmp_path / "test.db"),
        cache_ttl_seconds=3600,
        refresh_min_interval_seconds=60,
    )


@pytest.fixture
def client(settings) -> TestClient:
    return TestClient(create_app(settings))
