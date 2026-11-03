from datetime import date

from app.routers.dashboard import get_today
from app.services import chatbot, portfolio_health

from .factories import make_repo, make_user_data

TODAY = date(2026, 11, 3)


def user(repos, counts=(1,) * 50, bio="Builder of things"):
    data = make_user_data(repos=repos, counts=counts)
    data["profile"]["bio"] = bio
    return data


def scores(result):
    return {c["key"]: c["score"] for c in result["checks"]}


def test_normal_scoring():
    repos = [
        make_repo("a", description="Tool", pushed_at="2026-10-01T00:00:00Z"),
        make_repo("b", description="Lib", pushed_at="2026-09-01T00:00:00Z"),
        make_repo("c", description="", pushed_at="2025-01-01T00:00:00Z"),
        make_repo("d", description="App", pushed_at="2024-01-01T00:00:00Z"),
    ]
    result = portfolio_health.evaluate(user(repos), TODAY)
    assert result["status"] == "ok"
    # descriptions 3/4, recent 2/4, consistency 50/100, profile bio + >=3 repos
    assert scores(result) == {"descriptions": 18.8, "recent_projects": 12.5, "consistency": 12.5, "profile": 25.0}
    assert result["score"] == 69  # round(18.75 + 12.5 + 12.5 + 25)
    assert [c["key"] for c in result["checks"]] == ["descriptions", "recent_projects", "consistency", "profile"]
    assert all(c["max_score"] == 25 for c in result["checks"])
    profile_check = result["checks"][3]
    assert profile_check["suggestion"] is None
    # Largest deficits first: recent (12.5) and consistency (12.5) tie, keep check order; then descriptions.
    assert len(result["top_actions"]) == 3
    assert result["top_actions"][0].startswith("Push an update")
    assert result["top_actions"][2] == "Add a one-line description to c."
    assert "not code quality or skill" in result["limitation"]


def test_null_and_blank_descriptions_count_as_missing():
    repos = [make_repo("a", description=None), make_repo("b", description="   "), make_repo("c", description="ok")]
    result = portfolio_health.evaluate(user(repos), TODAY)
    assert result["checks"][0]["detail"] == "1 of 3 active original repos have a description."
    assert scores(result)["descriptions"] == 8.3
    assert result["checks"][0]["suggestion"] == "Add a one-line description to a and b."


def test_description_suggestion_lists_three_then_counts_rest():
    repos = [make_repo(n, description=None) for n in "abcde"]
    suggestion = portfolio_health.evaluate(user(repos), TODAY)["checks"][0]["suggestion"]
    assert suggestion == "Add a one-line description to a, b, c and 2 more."


def test_inactive_repos_and_missing_push_date():
    repos = [make_repo("old", pushed_at="2023-01-01T00:00:00Z"), make_repo("never", pushed_at=None)]
    assert scores(portfolio_health.evaluate(user(repos), TODAY))["recent_projects"] == 0


def test_180_day_boundary_is_inclusive():
    on_boundary = make_repo("edge", pushed_at="2026-05-07T23:59:59Z")   # exactly 180 days before TODAY
    just_outside = make_repo("late", pushed_at="2026-05-06T00:00:00Z")  # 181 days
    assert (TODAY - date(2026, 5, 7)).days == 180
    assert scores(portfolio_health.evaluate(user([on_boundary]), TODAY))["recent_projects"] == 25
    assert scores(portfolio_health.evaluate(user([just_outside]), TODAY))["recent_projects"] == 0


def test_zero_contributions_and_missing_bio():
    result = portfolio_health.evaluate(user([make_repo("a")], counts=(0,) * 30, bio=None), TODAY)
    assert scores(result)["consistency"] == 0
    assert scores(result)["profile"] == 0  # no bio, fewer than 3 repos
    assert result["checks"][3]["suggestion"] == (
        "Add a short bio to your GitHub profile and publish at least 3 original repositories."
    )


def test_consistency_caps_at_full_points():
    result = portfolio_health.evaluate(user([make_repo("a")], counts=(1,) * 150), TODAY)
    assert scores(result)["consistency"] == 25


def test_all_archived_scores_repo_checks_zero_without_dividing_by_zero():
    repos = [make_repo(n, is_archived=True, description="d") for n in ("a", "b", "c")]
    result = portfolio_health.evaluate(user(repos), TODAY)
    assert result["status"] == "ok"
    assert scores(result)["descriptions"] == 0 and scores(result)["recent_projects"] == 0
    assert "archived" in result["checks"][0]["detail"]
    assert scores(result)["profile"] == 25  # archived originals still count toward the 3-repo rule


def test_no_original_repos_returns_null_score():
    forks_only = [make_repo("f", is_fork=True)]
    for repos in ([], forks_only):
        result = portfolio_health.evaluate(user(repos), TODAY)
        assert result["status"] == "no_repos"
        assert result["score"] is None
        assert result["checks"] == []
        assert len(result["top_actions"]) == 1


def test_portfolio_health_api_uses_cache_and_injected_today(app, client, fake_github):
    app.dependency_overrides[get_today] = lambda: TODAY
    assert client.get("/api/users/octo/portfolio-health").json()["error"]["code"] == "not_cached"

    fake_github.queue(make_user_data())
    client.get("/api/users/octo/dashboard")
    body = client.get("/api/users/Octo/portfolio-health").json()
    assert set(body) == {"status", "score", "max_score", "checks", "top_actions", "limitation", "as_of", "meta"}
    assert body["as_of"] == "2026-11-03"
    assert set(body["checks"][0]) == {"key", "label", "score", "max_score", "detail", "suggestion"}
    assert len(fake_github.calls) == 1
    assert client.get("/api/users/-x-/portfolio-health").status_code == 422


def test_chat_portfolio_health_intent():
    data = user([make_repo("a")])
    for q in ("How healthy is my portfolio?", "What's my portfolio health score?", "How can I improve my profile?"):
        result = chatbot.respond(q, data, None, TODAY)
        assert result["intent"] == "portfolio_health", q
        assert "/100" in result["answer"] and "not code quality" in result["answer"]
        assert len(result["evidence"]) == 4
    assert chatbot.respond("What should I improve for this job?", data, "Rust", TODAY)["intent"] == "gaps"
    assert "no original" in chatbot.respond("portfolio health", user([]), None, TODAY)["answer"]
