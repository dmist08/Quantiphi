def test_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "github_token_configured": True}


def test_settings_defaults_and_roundtrip(client):
    assert client.get("/api/settings").json() == {"default_username": None, "theme": "system"}

    res = client.put("/api/settings", json={"default_username": "Octocat", "theme": "dark"})
    assert res.status_code == 200
    assert res.json() == {"default_username": "Octocat", "theme": "dark"}
    assert client.get("/api/settings").json()["theme"] == "dark"


def test_settings_trim_and_clear_username(client):
    assert client.put("/api/settings", json={"default_username": "  octo  ", "theme": "light"}).json() == {
        "default_username": "octo", "theme": "light",
    }
    assert client.put("/api/settings", json={"default_username": "", "theme": "dark"}).json() == {
        "default_username": None, "theme": "dark",
    }
    # Omitted fields fall back to defaults, as documented in the contract.
    assert client.put("/api/settings", json={}).json() == {"default_username": None, "theme": "system"}


def test_settings_persist_across_app_instances(settings):
    from fastapi.testclient import TestClient

    from app.main import create_app

    TestClient(create_app(settings)).put("/api/settings", json={"default_username": "octo", "theme": "dark"})
    assert TestClient(create_app(settings)).get("/api/settings").json()["theme"] == "dark"


def test_settings_rejects_bad_values(client):
    assert client.put("/api/settings", json={"theme": "neon"}).status_code == 422
    res = client.put("/api/settings", json={"default_username": "-bad-", "theme": "light"})
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "invalid_input"
