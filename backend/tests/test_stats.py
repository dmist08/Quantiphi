from app.services import stats

from .factories import make_days, make_repo


def test_current_streak_starts_from_previous_day_when_today_is_zero():
    days = make_days([1, 0, 2, 3, 4, 0])
    result = stats.streaks(days)
    assert result["current_streak"] == 3
    assert result["longest_streak"] == 3


def test_current_streak_includes_today_when_active():
    assert stats.streaks(make_days([0, 1, 1]))["current_streak"] == 2


def test_current_streak_zero_when_last_two_days_empty():
    assert stats.streaks(make_days([5, 5, 0, 0]))["current_streak"] == 0


def test_longest_streak_and_summary_values():
    result = stats.streaks(make_days([1, 1, 1, 1, 0, 9, 1]))
    assert result["longest_streak"] == 4
    assert result["active_days"] == 6
    assert result["best_day"] == {"date": "2026-10-09", "count": 9}


def test_zero_activity_user():
    result = stats.streaks(make_days([0] * 30))
    assert result == {"current_streak": 0, "longest_streak": 0, "active_days": 0, "best_day": None}
    assert stats.streaks([])["best_day"] is None


def test_language_percentages_sum_to_100_with_other_bucket():
    repo = make_repo("r", languages=[("A", 333), ("B", 333), ("C", 333), ("D", 1), ("E", 1), ("F", 1), ("G", 1)])
    langs = stats.language_breakdown([repo])
    assert [l["name"] for l in langs] == ["A", "B", "C", "D", "E", "Other"]
    assert sum(l["percent"] for l in langs) == 100
    assert langs[-1]["bytes"] == 2


def test_language_breakdown_excludes_forks_and_handles_no_languages():
    repos = [
        make_repo("own", languages=[("Python", 100)]),
        make_repo("fork", languages=[("Rust", 10_000)], is_fork=True),
        make_repo("empty", languages=[]),
    ]
    langs = stats.language_breakdown(repos)
    assert langs == [{"name": "Python", "color": "#123456", "bytes": 100, "percent": 100}]
    assert stats.language_breakdown([]) == []


def test_round_percentages_largest_remainder():
    assert stats.round_percentages([1, 1, 1]) == [34, 33, 33]
    assert sum(stats.round_percentages([7, 13, 29, 51, 3])) == 100
    assert stats.round_percentages([0, 0]) == [0, 0]


def test_summary_stats_excludes_forks_from_stars():
    data = {
        "repositories": [
            make_repo("a", stars=5, is_archived=True),
            make_repo("b", stars=7),
            make_repo("f", stars=100, is_fork=True),
        ],
        "days": [],
        "total_contributions": 0,
    }
    s = stats.summary_stats(data)
    assert (s["total_stars"], s["public_repos"], s["forked_repos"], s["archived_repos"]) == (12, 2, 1, 1)


def test_contribution_grid_is_seven_rows_sunday_first():
    days = make_days([1] * 10, start="2026-10-06")  # a Tuesday
    grid = stats.contribution_grid(days)
    assert all(len(week) == 7 for week in grid["weeks"])
    assert grid["weeks"][0][:2] == [None, None]
    assert grid["weeks"][0][2]["date"] == "2026-10-06"
    assert grid["weeks"][-1][-1] is None
    assert grid["months"][0] == {"label": "Oct", "week_index": 0}
    assert stats.contribution_grid([])["weeks"] == []


def test_list_repositories_sort_filter_forks_and_pagination():
    repos = [
        make_repo("beta", stars=5, forks=9, languages=[("Python", 1)], pushed_at="2026-01-01T00:00:00Z"),
        make_repo("Alpha", stars=5, forks=1, languages=[("Go", 1)], pushed_at=None),
        make_repo("gamma", stars=50, languages=[("Python", 1)], description=None, pushed_at="2026-06-01T00:00:00Z"),
        make_repo("forky", stars=500, languages=[("Rust", 1)], is_fork=True),
    ]
    by_stars = stats.list_repositories(repos)
    assert [r["name"] for r in by_stars["items"]] == ["gamma", "Alpha", "beta"]
    assert by_stars["available_languages"] == ["Go", "Python"]

    assert [r["name"] for r in stats.list_repositories(repos, sort="forks")["items"]][0] == "beta"
    assert [r["name"] for r in stats.list_repositories(repos, sort="name")["items"]] == ["Alpha", "beta", "gamma"]
    assert [r["name"] for r in stats.list_repositories(repos, sort="updated")["items"]] == ["gamma", "beta", "Alpha"]

    python = stats.list_repositories(repos, language="python")
    assert python["total"] == 2 and python["language"] == "python"

    with_forks = stats.list_repositories(repos, include_forks=True)
    assert with_forks["items"][0]["name"] == "forky"
    assert "Rust" in with_forks["available_languages"]

    page2 = stats.list_repositories(repos, page=2, page_size=2)
    assert (page2["total"], page2["total_pages"], len(page2["items"])) == (3, 2, 1)
    assert stats.list_repositories(repos, page=9)["items"] == []
    assert stats.list_repositories([], page=1)["total_pages"] == 0
