"""Portfolio health: how well a public GitHub profile is presented, from cached data.

Four checks worth 25 points each:
- descriptions:    share of original, non-archived repos with a non-empty description
- recent_projects: share of those repos pushed within the last 180 days
- consistency:     min(active contribution days / 100, 1)
- profile:         half for a non-empty bio, half for at least 3 original repos

"Original" means owned and not a fork. `today` is a parameter so results are
deterministic and testable.
"""
from datetime import date

from . import stats
from .matcher import join_names

CHECK_MAX = 25
RECENT_DAYS = 180
TARGET_ACTIVE_DAYS = 100
MIN_ORIGINAL_REPOS = 3
LIMITATION = (
    "This measures how your public profile is presented and how active it is, "
    "not code quality or skill."
)


def _check(key: str, label: str, fraction: float, detail: str, suggestion: str | None) -> dict:
    points = CHECK_MAX * max(0.0, min(fraction, 1.0))
    return {
        "key": key,
        "label": label,
        "score": round(points, 1),
        "max_score": CHECK_MAX,
        "detail": detail,
        "suggestion": suggestion if points < CHECK_MAX else None,
        "_points": points,  # unrounded, removed before returning
    }


def _pushed_date(repo: dict) -> date | None:
    return date.fromisoformat(repo["pushed_at"][:10]) if repo.get("pushed_at") else None


def _descriptions(active: list[dict], archived_only: bool) -> dict:
    label = "Repository descriptions"
    if not active:
        detail = "All original repositories are archived, so none count." if archived_only else "No original repositories."
        return _check("descriptions", label, 0, detail, "Unarchive or publish an active project with a clear description.")
    missing = [r["name"] for r in active if not (r["description"] or "").strip()]
    described = len(active) - len(missing)
    names = join_names(missing) if len(missing) <= 3 else f"{', '.join(missing[:3])} and {len(missing) - 3} more"
    return _check(
        "descriptions", label, described / len(active),
        f"{described} of {len(active)} active original repos have a description.",
        f"Add a one-line description to {names}.",
    )


def _recent(active: list[dict], today: date, archived_only: bool) -> dict:
    label = "Recently updated projects"
    if not active:
        detail = "All original repositories are archived, so none count." if archived_only else "No original repositories."
        return _check("recent_projects", label, 0, detail, "Start or revive an active project.")
    recent = [r for r in active if (pushed := _pushed_date(r)) and (today - pushed).days <= RECENT_DAYS]
    return _check(
        "recent_projects", label, len(recent) / len(active),
        f"{len(recent)} of {len(active)} active original repos were pushed in the last {RECENT_DAYS} days.",
        "Push an update to an older project you want to showcase, or archive ones you no longer maintain.",
    )


def _consistency(days: list[dict]) -> dict:
    active_days = sum(1 for d in days if d["count"] > 0)
    return _check(
        "consistency", "Contribution consistency", active_days / TARGET_ACTIVE_DAYS,
        f"{active_days} active contribution days in the last year ({TARGET_ACTIVE_DAYS} earns full points).",
        "Contribute on more days; small, regular commits count.",
    )


def _profile(profile: dict, original_count: int) -> dict:
    has_bio = bool((profile.get("bio") or "").strip())
    enough_repos = original_count >= MIN_ORIGINAL_REPOS
    todo = []
    if not has_bio:
        todo.append("add a short bio to your GitHub profile")
    if not enough_repos:
        todo.append(f"publish at least {MIN_ORIGINAL_REPOS} original repositories")
    suggestion = " and ".join(todo)
    return _check(
        "profile", "Profile completeness", 0.5 * has_bio + 0.5 * enough_repos,
        f"Bio {'present' if has_bio else 'missing'}; {original_count} original repos "
        f"({MIN_ORIGINAL_REPOS} needed).",
        (suggestion[0].upper() + suggestion[1:] + ".") if suggestion else None,
    )


def evaluate(data: dict, today: date) -> dict:
    original = stats.owned_repos(data["repositories"])
    base = {"as_of": today.isoformat(), "limitation": LIMITATION}
    if not original:
        return {
            **base,
            "status": "no_repos",
            "score": None,
            "max_score": 100,
            "checks": [],
            "top_actions": ["Publish an original (non-fork) public repository so there is something to evaluate."],
        }

    active = [r for r in original if not r["is_archived"]]
    archived_only = not active
    checks = [
        _descriptions(active, archived_only),
        _recent(active, today, archived_only),
        _consistency(data["days"]),
        _profile(data["profile"], len(original)),
    ]
    total = round(sum(c["_points"] for c in checks))
    # Biggest point deficit first; stable, so ties keep check order.
    ranked = sorted((c for c in checks if c["suggestion"]), key=lambda c: c["_points"] - CHECK_MAX)
    top_actions = [c["suggestion"] for c in ranked[:3]]
    for c in checks:
        del c["_points"]
    return {**base, "status": "ok", "score": total, "max_score": 100, "checks": checks, "top_actions": top_actions}
