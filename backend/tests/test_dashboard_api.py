import asyncio

from app.errors import GitHubAuthError, GitHubUnavailableError, RateLimitedError, UserNotFoundError

from .factories import make_repo, make_user_data


def test_dashboard_happy_path(client, fake_github):
    fake_github.queue(make_user_data())
    res = client.get("/api/users/octo/dashboard")
    assert res.status_code == 200
    body = res.json()
    assert body["profile"]["login"] == "Octo"
    assert body["stats"]["total_stars"] == 70  # fork with 999 stars excluded
    assert body["stats"]["current_streak"] == 3
    assert sum(l["percent"] for l in body["languages"]) == 100
    assert "Rust" not in [l["name"] for l in body["languages"]]
    assert all(len(w) == 7 for w in body["contributions"]["weeks"])
    assert body["meta"]["stale"] is False and body["meta"]["warning"] is None
    assert body["match"] is None


def test_cache_hit_within_ttl_and_case_insensitive_key(client, fake_github, clock):
    fake_github.queue(make_user_data(login="Octo"))
    client.get("/api/users/octo/dashboard")
    clock.advance(600)
    res = client.get("/api/users/OCTO/dashboard")
    assert res.json()["profile"]["login"] == "Octo"
    assert len(fake_github.calls) == 1


def test_ttl_expiry_refetches_and_deleted_repos_disappear(client, fake_github, clock):
    fake_github.queue(make_user_data())
    client.get("/api/users/octo/dashboard")
    clock.advance(3601)
    fake_github.queue(make_user_data(repos=[make_repo("only", stars=1)]))
    res = client.get("/api/users/octo/repositories")
    assert [r["name"] for r in res.json()["items"]] == ["only"]
    assert len(fake_github.calls) == 2


def test_stale_cache_fallback_on_refresh_failure(client, fake_github, clock):
    fake_github.queue(make_user_data())
    client.get("/api/users/octo/dashboard")
    clock.advance(3601)
    fake_github.queue(GitHubUnavailableError("GitHub is unavailable (HTTP 502)."))
    body = client.get("/api/users/octo/dashboard").json()
    assert body["meta"]["stale"] is True
    assert body["meta"]["error_code"] == "github_unavailable"
    assert "cached data" in body["meta"]["warning"]
    assert body["stats"]["total_stars"] == 70  # old data left intact


def test_rate_limit_with_cache_is_stale_without_cache_is_429(client, fake_github, clock):
    fake_github.queue(RateLimitedError("GitHub API rate limit exceeded.", reset_at="2026-11-03T12:00:00Z"))
    res = client.get("/api/users/octo/dashboard")
    assert res.status_code == 429
    assert res.json()["error"] == {
        "code": "rate_limited", "message": "GitHub API rate limit exceeded.", "reset_at": "2026-11-03T12:00:00Z",
    }

    fake_github.queue(make_user_data())
    client.get("/api/users/octo/dashboard")
    clock.advance(120)
    fake_github.queue(RateLimitedError("GitHub API rate limit exceeded."))
    meta = client.get("/api/users/octo/dashboard?refresh=true").json()["meta"]
    assert meta["stale"] is True and meta["error_code"] == "rate_limited"


def test_error_mapping_without_cache(client, fake_github):
    fake_github.queue(GitHubAuthError("GITHUB_TOKEN is missing or invalid."))
    assert client.get("/api/users/octo/dashboard").status_code == 401
    fake_github.queue(GitHubUnavailableError("down"))
    assert client.get("/api/users/octo/dashboard").json()["error"]["code"] == "github_unavailable"
    fake_github.queue(UserNotFoundError("nope"))
    assert client.get("/api/users/ghost/dashboard").status_code == 404


def test_invalid_username_is_422_without_fetch(client, fake_github):
    for bad in ["-octo", "octo-", "a" * 40, "oc_to"]:
        res = client.get(f"/api/users/{bad}/dashboard")
        assert res.status_code == 422, bad
        assert res.json()["error"]["field"] == "username"
    assert fake_github.calls == []


def test_refresh_throttled_within_60_seconds(client, fake_github, clock):
    fake_github.queue(make_user_data())
    client.get("/api/users/octo/dashboard")
    clock.advance(30)
    body = client.get("/api/users/octo/dashboard?refresh=true").json()
    assert "try again in 30s" in body["meta"]["notice"]
    assert len(fake_github.calls) == 1

    clock.advance(31)
    fake_github.queue(make_user_data(followers=99))
    body = client.get("/api/users/octo/dashboard?refresh=true").json()
    assert body["profile"]["followers"] == 99
    assert body["meta"]["notice"] is None


def test_zero_activity_user_with_no_repos(client, fake_github):
    fake_github.queue(make_user_data(repos=[], counts=(0, 0, 0)))
    body = client.get("/api/users/octo/dashboard").json()
    assert body["stats"]["current_streak"] == 0
    assert body["stats"]["best_day"] is None
    assert body["languages"] == []
    assert client.get("/api/users/octo/repositories").json()["items"] == []


def test_repositories_query_validation(client, fake_github):
    fake_github.queue(make_user_data())
    assert client.get("/api/users/octo/repositories?sort=bogus").status_code == 422
    assert client.get("/api/users/octo/repositories?page=0").status_code == 422
    assert client.get("/api/users/octo/repositories?page_size=51").status_code == 422
    body = client.get("/api/users/octo/repositories?include_forks=true&sort=name").json()
    assert [r["name"] for r in body["items"]] == ["api", "forked", "web"]


async def test_per_username_lock_prevents_duplicate_fetches(app, fake_github):
    gate = asyncio.Event()
    original = fake_github.fetch_user

    async def slow_fetch(login):
        await gate.wait()
        return await original(login)

    fake_github.fetch_user = slow_fetch
    fake_github.queue(make_user_data())
    cache = app.state.cache
    tasks = [asyncio.create_task(cache.get_user_data(name)) for name in ("octo", "Octo", "OCTO")]
    await asyncio.sleep(0)
    gate.set()
    results = await asyncio.gather(*tasks)
    assert len(fake_github.calls) == 1
    assert {r["profile"]["login"] for r in results} == {"Octo"}
