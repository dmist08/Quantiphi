import pytest

from app.services import gap_coach, matcher

from .factories import make_repo


def names(text):
    return [t.name for t in matcher.extract_technologies(text)]


@pytest.mark.parametrize("text,expected,absent", [
    ("Strong JavaScript skills", ["JavaScript"], ["Java"]),
    ("Java and Spring Boot", ["Java", "Spring"], ["JavaScript"]),
    ("Must build scalable systems", [], ["Scala"]),
    ("Scala or Kotlin", ["Scala", "Kotlin"], []),
    ("C, C++ and C# experience", ["C", "C++", "C#"], []),
    ("C/C++ firmware", ["C", "C++"], []),
    ("Python/Java services", ["Python", "Java"], []),
    ("Work with R&D teams", [], ["R"]),
    ("Statistics in R.", ["R"], []),
    ("Present to C-level and C-suite executives", [], ["C"]),
    ("We go above and beyond", [], ["Go"]),
    ("Go above and beyond for customers", [], ["Go"]),
    ("Golang microservices", ["Go"], []),
    ("Python, Go, and Rust", ["Python", "Go", "Rust"], []),
    ("Backend in Go.", ["Go"], []),
    ("Go developer wanted", ["Go"], []),
    ("Languages (Go)", ["Go"], []),
    ("Node.js and React", ["Node.js", "React"], ["JavaScript"]),
    ("ASP.NET and .NET Core", ["C#"], []),
    ("MySQL, PostgreSQL and SQL", ["MySQL", "PostgreSQL", "SQL"], []),
    ("Terraform and Docker on AWS", ["Terraform", "Docker", "AWS"], []),
])
def test_keyword_boundaries(text, expected, absent):
    found = names(text)
    for name in expected:
        assert name in found, (text, found)
    for name in absent:
        assert name not in found, (text, found)


def test_repeated_keywords_count_once():
    techs = names("Python python PYTHON py and Python again, plus Python.")
    assert techs == ["Python"]


def test_order_follows_first_mention():
    assert names("Rust then Python then Rust") == ["Rust", "Python"]


REPOS = [
    make_repo("ml", stars=10, languages=[("Jupyter Notebook", 9000), ("Python", 1000)]),
    make_repo("site", stars=3, languages=[("TypeScript", 500), ("CSS", 50)]),
    make_repo("rusty-fork", stars=100, languages=[("Rust", 10_000)], is_fork=True),
    make_repo("infra", stars=1, languages=[("HCL", 10)], is_archived=True),
]


def test_score_and_partition():
    result = matcher.analyze("Python, React, Rust and Terraform on AWS with Kubernetes", REPOS)
    assert result["status"] == "ok"
    assert [m["name"] for m in result["matched"]] == ["Python", "React", "Terraform"]
    assert [m["name"] for m in result["missing"]] == ["Rust"]  # fork doesn't count
    assert result["unassessable"] == ["AWS", "Kubernetes"]
    assert result["score"] == 75
    assert result["matched"][0]["evidence"][0] == {
        "repo": "ml", "url": "https://github.com/octo/ml", "language": "Jupyter Notebook",
    }
    assert "round(100 × 3 / 4)" in result["explanation"]


def test_only_unassessable_gives_null_score_not_zero():
    result = matcher.analyze("Experience with AWS, Kafka, Redis and Linux", REPOS)
    assert result["status"] == "no_assessable_keywords"
    assert result["score"] is None
    assert result["unassessable"] == ["AWS", "Kafka", "Redis", "Linux"]
    assert "not the same as 0%" in result["explanation"]


def test_no_keywords_at_all_gives_null_score():
    result = matcher.analyze("Great communicator who goes above and beyond.", REPOS)
    assert (result["score"], result["unassessable"]) == (None, [])


def test_zero_matches_is_zero_percent():
    assert matcher.analyze("Rust and Haskell", REPOS)["score"] == 0


def test_user_with_no_repos():
    result = matcher.analyze("Python", [])
    assert result["score"] == 0
    assert result["missing"][0]["name"] == "Python"


def test_gap_coach_is_evidence_based_and_deterministic():
    match = matcher.analyze("Python, TypeScript, Rust, AWS", REPOS)
    first = gap_coach.coach(match, REPOS)
    assert first == gap_coach.coach(match, REPOS)
    assert [s["name"] for s in first["strengths"]] == ["Python", "TypeScript"]
    assert first["missing"] == ["Rust"]
    assert first["unassessable"] == ["AWS"]
    assert [h["name"] for h in first["highlight_repos"]] == ["ml", "site"]
    assert len(first["pitch"]) == 3
    assert "Rust" not in first["pitch"][0]  # never claims an unsupported skill
    assert "Rust" in first["pitch"][2]
    assert "does not prove proficiency" in first["disclaimer"]


def test_gap_coach_with_no_matches_and_no_assessable():
    none_matched = gap_coach.coach(matcher.analyze("Rust", REPOS), REPOS)
    assert none_matched["highlight_repos"] == []
    assert "don't yet show" in none_matched["pitch"][0]

    unassessable = gap_coach.coach(matcher.analyze("AWS and Linux", REPOS), REPOS)
    assert unassessable["score"] is None and len(unassessable["pitch"]) == 3


def test_highlights_capped_at_three():
    repos = [make_repo(f"r{i}", stars=i, languages=[("Python", 10)]) for i in range(6)]
    result = gap_coach.coach(matcher.analyze("Python", repos), repos)
    assert [h["name"] for h in result["highlight_repos"]] == ["r5", "r4", "r3"]
