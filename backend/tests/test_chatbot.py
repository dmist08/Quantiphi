import pytest

from app.services import chatbot

from .factories import make_repo, make_user_data


@pytest.fixture
def data():
    return make_user_data()  # api (Python, 50★), web (TypeScript, 20★), forked (Rust fork)


@pytest.mark.parametrize("message,intent", [
    ("What are my top languages?", "top_languages"),
    ("Which are my best repos?", "best_repos"),
    ("Which repos use Python?", "repos_by_language"),
    ("What is my current streak?", "streaks"),
    ("How many stars do I have?", "stars"),
    ("How many followers do I have?", "followers"),
    ("Give me a profile summary.", "profile_summary"),
    ("What is my match score?", "match_score"),
    ("What are my gaps for this job?", "gaps"),
    ("What's the weather like?", "unknown"),
])
def test_intent_detection(data, message, intent):
    assert chatbot.respond(message, data, None)["intent"] == intent


def test_answers_use_cached_facts_and_exclude_forks(data):
    langs = chatbot.respond("top languages", data, None)
    assert "Python" in langs["answer"] and "Rust" not in langs["answer"]
    assert {e["label"] for e in langs["evidence"]} >= {"Python", "TypeScript"}

    best = chatbot.respond("best repos", data, None)
    assert best["evidence"][0]["label"] == "api"
    assert best["evidence"][0]["url"] == "https://github.com/octo/api"
    assert "forked" not in best["answer"]

    stars = chatbot.respond("how many stars", data, None)
    assert "70 stars" in stars["answer"]

    followers = chatbot.respond("followers?", data, None)
    assert followers["answer"] == "You have 10 followers on GitHub."


def test_repos_by_language_case_and_missing(data):
    assert "web" in chatbot.respond("which repos are written in TYPESCRIPT or python", data, None)["answer"]
    assert "api" in chatbot.respond("show projects that use python", data, None)["answer"]
    assert chatbot.respond("repos using rust", data, None)["answer"].startswith("None of your")


def test_streak_answer(data):
    result = chatbot.respond("streak?", data, None)
    assert "current streak is 3 days" in result["answer"]
    assert "longest is 3 days" in result["answer"]


def test_match_and_gaps_need_saved_jd(data):
    assert "No job description is saved" in chatbot.respond("match score", data, None)["answer"]
    match = chatbot.respond("match score", data, "Python and Rust, plus AWS")
    assert "50%" in match["answer"]
    gaps = chatbot.respond("what am I missing", data, "Python and Rust, plus AWS")
    assert gaps["intent"] == "gaps"
    assert "Rust" in gaps["answer"] and "AWS" in gaps["answer"]


def test_unknown_explains_capabilities(data):
    result = chatbot.respond("tell me a joke", data, None)
    assert result["intent"] == "unknown"
    assert "top languages" in result["answer"]
    assert result["evidence"] == []
    assert result["suggestions"]


def test_empty_profile():
    empty = make_user_data(repos=[], counts=(0, 0))
    assert "no language data" in chatbot.respond("languages", empty, None)["answer"]
    assert "don't have any public" in chatbot.respond("best repos", empty, None)["answer"]
    assert "current streak is 0 days" in chatbot.respond("streak", empty, None)["answer"]


def test_chat_api_uses_cache_only(client, fake_github):
    res = client.post("/api/users/octo/chat", json={"message": "top languages"})
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "not_cached"
    assert fake_github.calls == []

    fake_github.queue(make_user_data())
    client.get("/api/users/octo/dashboard")
    body = client.post("/api/users/OCTO/chat", json={"message": "best repos", "history": [
        {"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"},
    ]}).json()
    assert set(body) == {"intent", "answer", "evidence", "suggestions"}
    assert body["intent"] == "best_repos"
    assert len(fake_github.calls) == 1


def test_chat_api_validation(client, fake_github):
    fake_github.queue(make_user_data(repos=[make_repo("x")]))
    client.get("/api/users/octo/dashboard")
    assert client.post("/api/users/octo/chat", json={"message": "  "}).status_code == 422
    assert client.post("/api/users/octo/chat", json={"message": "x" * 2001}).status_code == 413
    bad_history = {"message": "hi", "history": [{"role": "system", "content": "x"}]}
    assert client.post("/api/users/octo/chat", json=bad_history).status_code == 422
    too_long = {"message": "hi", "history": [{"role": "user", "content": "x"}] * 21}
    assert client.post("/api/users/octo/chat", json=too_long).status_code == 422
