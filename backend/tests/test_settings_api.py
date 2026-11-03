def test_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_settings_defaults_and_roundtrip(client):
    assert client.get("/api/settings").json() == {"default_username": None, "theme": "system"}

    res = client.put("/api/settings", json={"default_username": "Octocat", "theme": "dark"})
    assert res.status_code == 200
    assert res.json() == {"default_username": "Octocat", "theme": "dark"}
    assert client.get("/api/settings").json()["theme"] == "dark"


def test_settings_rejects_bad_values(client):
    assert client.put("/api/settings", json={"theme": "neon"}).status_code == 422
    res = client.put("/api/settings", json={"default_username": "-bad-", "theme": "light"})
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "invalid_input"
