"""Builders for normalized GitHub data and a fake client used instead of the network."""
import copy


def make_repo(name, stars=0, forks=0, languages=None, is_fork=False, is_archived=False,
              description="A repo", pushed_at="2026-10-01T00:00:00Z"):
    languages = languages or []  # list of (name, size)
    return {
        "name": name,
        "url": f"https://github.com/octo/{name}",
        "description": description,
        "stars": stars,
        "forks": forks,
        "is_fork": is_fork,
        "is_archived": is_archived,
        "pushed_at": pushed_at,
        "primary_language": languages[0][0] if languages else None,
        "primary_language_color": "#123456" if languages else None,
        "languages": [{"name": n, "color": "#123456", "size": s} for n, s in languages],
    }


def make_days(counts, start="2026-10-04"):
    """Consecutive days from `start` (a Sunday) with the given counts."""
    from datetime import date, timedelta

    first = date.fromisoformat(start)
    return [
        {"date": (first + timedelta(days=i)).isoformat(), "count": c, "level": min(4, c)}
        for i, c in enumerate(counts)
    ]


def make_user_data(login="Octo", repos=None, counts=(0, 1, 2, 0, 3, 4, 5), followers=10):
    days = make_days(list(counts))
    return {
        "profile": {
            "login": login,
            "name": "Octo Cat",
            "avatar_url": "https://avatars.example/octo.png",
            "bio": None,
            "url": f"https://github.com/{login}",
            "followers": followers,
        },
        "total_contributions": sum(counts),
        "days": days,
        "repositories": repos if repos is not None else [
            make_repo("api", stars=50, forks=5, languages=[("Python", 5000), ("Dockerfile", 100)]),
            make_repo("web", stars=20, forks=2, languages=[("TypeScript", 3000), ("CSS", 500)]),
            make_repo("forked", stars=999, languages=[("Rust", 99999)], is_fork=True),
        ],
        "truncated": False,
        "rate_limit": {"remaining": 4999, "reset_at": "2026-11-03T12:00:00Z"},
    }


class FakeGitHubClient:
    """Returns queued results (dicts) or raises queued exceptions, recording calls."""

    def __init__(self, *results):
        self.results = list(results)
        self.calls = []

    def queue(self, *results):
        self.results.extend(results)

    async def fetch_user(self, login):
        self.calls.append(login)
        if not self.results:
            raise AssertionError("FakeGitHubClient: no queued result")
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return copy.deepcopy(result)
