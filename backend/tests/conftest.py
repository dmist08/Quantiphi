import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

from .factories import FakeGitHubClient


class Clock:
    def __init__(self, now=1_800_000_000.0):
        self.now = now

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


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
def fake_github() -> FakeGitHubClient:
    return FakeGitHubClient()


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def app(settings, fake_github, clock):
    app = create_app(settings, github_client=fake_github)
    app.state.cache._clock = clock
    return app


@pytest.fixture
def client(app) -> TestClient:
    return TestClient(app)
