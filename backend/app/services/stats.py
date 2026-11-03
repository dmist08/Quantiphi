"""Pure functions that turn cached GitHub data into dashboard statistics.

Nothing here touches the network or the database, which keeps it easy to test.
"""
import math
from datetime import date

TOP_LANGUAGE_COUNT = 5
SORT_OPTIONS = ("stars", "forks", "updated", "name")


def owned_repos(repos: list[dict]) -> list[dict]:
    """Owned, non-fork repos: the set used for stars, languages and matching."""
    return [r for r in repos if not r["is_fork"]]


def round_percentages(values: list[int]) -> list[int]:
    """Integer percentages that sum to exactly 100 (largest-remainder method)."""
    total = sum(values)
    if total <= 0:
        return [0] * len(values)
    raw = [v * 100 / total for v in values]
    floors = [math.floor(x) for x in raw]
    leftover = 100 - sum(floors)
    # Hand out the remaining points to the largest fractional parts (stable by index).
    by_remainder = sorted(range(len(values)), key=lambda i: (-(raw[i] - floors[i]), i))
    for i in by_remainder[:leftover]:
        floors[i] += 1
    return floors


def language_breakdown(repos: list[dict]) -> list[dict]:
    """Top 5 languages by total bytes across owned non-fork repos, plus 'Other'."""
    totals: dict[str, int] = {}
    colors: dict[str, str | None] = {}
    for repo in owned_repos(repos):
        for lang in repo["languages"]:
            totals[lang["name"]] = totals.get(lang["name"], 0) + (lang["size"] or 0)
            colors.setdefault(lang["name"], lang.get("color"))

    ranked = sorted((item for item in totals.items() if item[1] > 0), key=lambda kv: (-kv[1], kv[0]))
    if not ranked:
        return []
    top = [{"name": n, "color": colors[n], "bytes": b} for n, b in ranked[:TOP_LANGUAGE_COUNT]]
    rest = sum(b for _, b in ranked[TOP_LANGUAGE_COUNT:])
    if rest > 0:
        top.append({"name": "Other", "color": None, "bytes": rest})
    for item, pct in zip(top, round_percentages([item["bytes"] for item in top])):
        item["percent"] = pct
    return top


def user_languages(repos: list[dict]) -> set[str]:
    """Every language present in at least one owned non-fork repo."""
    return {lang["name"] for repo in owned_repos(repos) for lang in repo["languages"]}


def streaks(days: list[dict]) -> dict:
    """Current/longest streak, active days and best day from daily counts.

    The current streak ends at the most recent day; if that day has zero
    contributions (the user may not have committed *yet* today), counting
    starts from the previous day instead.
    """
    ordered = sorted(days, key=lambda d: d["date"])
    counts = [d["count"] for d in ordered]

    longest = run = 0
    for c in counts:
        run = run + 1 if c > 0 else 0
        longest = max(longest, run)

    current = 0
    idx = len(counts) - 1
    if idx >= 0 and counts[idx] == 0:
        idx -= 1
    while idx >= 0 and counts[idx] > 0:
        current += 1
        idx -= 1

    best = max(ordered, key=lambda d: (d["count"], d["date"]), default=None)
    return {
        "current_streak": current,
        "longest_streak": longest,
        "active_days": sum(1 for c in counts if c > 0),
        "best_day": {"date": best["date"], "count": best["count"]} if best and best["count"] > 0 else None,
    }


def contribution_grid(days: list[dict]) -> dict:
    """Group days into Sunday-first weeks of exactly 7 slots (None = padding)."""
    ordered = sorted(days, key=lambda d: d["date"])
    if not ordered:
        return {"start_date": None, "end_date": None, "weeks": [], "months": []}

    weeks: list[list[dict | None]] = []
    week: list[dict | None] = []
    months: list[dict] = []
    for day in ordered:
        d = date.fromisoformat(day["date"])
        slot = (d.weekday() + 1) % 7  # Python: Monday=0; grid: Sunday=0
        if not week:
            week = [None] * slot  # leading padding for the first (partial) week
        elif slot == 0:
            weeks.append(week)
            week = []
        if d.day == 1 or not months:
            label = d.strftime("%b")
            week_index = len(weeks)
            if not months or months[-1]["week_index"] != week_index:
                months.append({"label": label, "week_index": week_index})
            else:
                months[-1]["label"] = label
        week.append({"date": day["date"], "count": day["count"], "level": day["level"]})
    week.extend([None] * (7 - len(week)))
    weeks.append(week)
    return {"start_date": ordered[0]["date"], "end_date": ordered[-1]["date"], "weeks": weeks, "months": months}


def summary_stats(data: dict) -> dict:
    repos = data["repositories"]
    owned = owned_repos(repos)
    return {
        "total_stars": sum(r["stars"] for r in owned),
        "public_repos": len(owned),
        "forked_repos": len(repos) - len(owned),
        "archived_repos": sum(1 for r in owned if r["is_archived"]),
        "total_contributions": data["total_contributions"],
        **streaks(data["days"]),
    }


def _sort_key(sort: str):
    if sort == "stars":
        return lambda r: (-r["stars"], r["name"].lower())
    if sort == "forks":
        return lambda r: (-r["forks"], r["name"].lower())
    if sort == "name":
        return lambda r: r["name"].lower()
    raise ValueError(sort)


def list_repositories(repos: list[dict], sort: str = "stars", language: str | None = None,
                      include_forks: bool = False, page: int = 1, page_size: int = 12) -> dict:
    in_scope = repos if include_forks else owned_repos(repos)
    available = sorted({r["primary_language"] for r in in_scope if r["primary_language"]}, key=str.lower)

    language = (language or "").strip() or None
    filtered = [
        r for r in in_scope
        if language is None or (r["primary_language"] or "").lower() == language.lower()
    ]

    if sort == "updated":
        # Most recently pushed first, repos never pushed last, ties by name.
        filtered = sorted(filtered, key=lambda r: r["name"].lower())
        filtered = sorted(filtered, key=lambda r: r["pushed_at"] or "", reverse=True)
    else:
        filtered = sorted(filtered, key=_sort_key(sort))

    total = len(filtered)
    start = (page - 1) * page_size
    items = [
        {
            "name": r["name"],
            "url": r["url"],
            "description": r["description"],
            "stars": r["stars"],
            "forks": r["forks"],
            "language": r["primary_language"],
            "language_color": r["primary_language_color"],
            "is_fork": r["is_fork"],
            "is_archived": r["is_archived"],
            "pushed_at": r["pushed_at"],
        }
        for r in filtered[start:start + page_size]
    ]
    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": math.ceil(total / page_size) if total else 0,
        "sort": sort,
        "language": language,
        "include_forks": include_forks,
        "available_languages": available,
    }
