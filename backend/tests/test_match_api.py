from .factories import make_repo, make_user_data


def test_match_saves_latest_jd_and_dashboard_recomputes_badge(client, fake_github, clock):
    fake_github.queue(make_user_data())
    res = client.post("/api/users/octo/match", json={"job_description": "  Python and Rust  "})
    assert res.status_code == 200
    body = res.json()
    assert body["job_description"] == "Python and Rust"
    assert body["match"]["score"] == 50

    client.post("/api/users/octo/match", json={"job_description": "TypeScript"})
    dash = client.get("/api/users/OCTO/dashboard").json()
    assert dash["job_description"] == "TypeScript"
    assert dash["match"]["score"] == 100

    # New repo data changes the badge without re-submitting the JD.
    clock.advance(3601)
    fake_github.queue(make_user_data(repos=[make_repo("py", languages=[("Python", 1)])]))
    assert client.get("/api/users/octo/dashboard").json()["match"]["score"] == 0


def test_match_validation(client, fake_github):
    res = client.post("/api/users/octo/match", json={"job_description": "   "})
    assert res.status_code == 422
    assert res.json()["error"]["field"] == "job_description"

    res = client.post("/api/users/octo/match", json={"job_description": "x" * 20_001})
    assert res.status_code == 413
    assert res.json()["error"]["code"] == "payload_too_large"

    fake_github.queue(make_user_data())
    exactly_limit = " " + "x" * 20_000 + " "  # trimmed before measuring
    assert client.post("/api/users/octo/match", json={"job_description": exactly_limit}).status_code == 200
    assert client.post("/api/users/octo/match", json={}).status_code == 422
    assert client.post("/api/users/-bad/match", json={"job_description": "Python"}).status_code == 422


def test_match_null_score_for_unassessable_jd(client, fake_github):
    fake_github.queue(make_user_data())
    match = client.post("/api/users/octo/match", json={"job_description": "AWS and Kubernetes"}).json()["match"]
    assert match["score"] is None
    assert match["status"] == "no_assessable_keywords"


def test_gap_coach_endpoint_does_not_save_jd(client, fake_github):
    fake_github.queue(make_user_data())
    body = client.post("/api/users/octo/gap-coach", json={"job_description": "Python, Go, AWS"}).json()
    assert body["missing"] == ["Go"]
    assert body["unassessable"] == ["AWS"]
    assert len(body["pitch"]) == 3
    assert client.get("/api/users/octo/dashboard").json()["job_description"] is None
