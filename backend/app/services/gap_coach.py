"""JD gap coach: deterministic, evidence-based advice built on the matcher result.

It never claims a technology without repo evidence and always states that
language coverage does not prove proficiency.
"""
from . import stats
from .matcher import TAXONOMY, join_names, supporting_repos

DISCLAIMER = (
    "Language coverage shows that code in a language exists in public repositories; "
    "it does not prove proficiency."
)
MAX_HIGHLIGHTS = 3


def _highlight_repos(repos: list[dict], matched_languages: set[str]) -> list[dict]:
    candidates = []
    for repo in stats.owned_repos(repos):
        langs = sorted({lang["name"] for lang in repo["languages"]} & matched_languages)
        if langs:
            candidates.append((repo, langs))
    # Stable sorts, least significant key first: name, newest push, stars, matched-language count.
    candidates.sort(key=lambda c: c[0]["name"].lower())
    candidates.sort(key=lambda c: c[0]["pushed_at"] or "", reverse=True)
    candidates.sort(key=lambda c: (-len(c[1]), -c[0]["stars"]))

    highlights = []
    for repo, langs in candidates[:MAX_HIGHLIGHTS]:
        stars = repo["stars"]
        reason = f"Uses {join_names(langs)}; {stars} star{'s' if stars != 1 else ''}"
        reason += " (archived)." if repo["is_archived"] else "."
        highlights.append({
            "name": repo["name"], "url": repo["url"], "stars": stars,
            "matched_languages": langs, "reason": reason,
        })
    return highlights


def _pitch(match: dict, highlights: list[dict], top_languages: list[str]) -> list[str]:
    matched = [m["name"] for m in match["matched"]]
    missing = [m["name"] for m in match["missing"]]
    unassessable = match["unassessable"]

    if match["status"] == "no_assessable_keywords":
        return [
            "This role doesn't list languages or frameworks that can be checked against my public code.",
            f"It emphasizes {join_names(unassessable)}, which repository languages can't demonstrate."
            if unassessable else "There is nothing in it to compare my repositories against.",
            "I'd speak to my relevant experience directly rather than rely on my GitHub profile for this role.",
        ]

    if not matched:
        shown = join_names(top_languages) if top_languages else "no measurable languages yet"
        return [
            f"My public repositories don't yet show the technologies this role lists ({join_names(missing)}).",
            "I won't claim them based on my GitHub; any experience with them would have to come from elsewhere.",
            f"What my GitHub does show is work in {shown}.",
        ]

    total = match["assessable_count"]
    lines = [
        f"My public GitHub shows work in {join_names(matched)}: {len(matched)} of the {total} "
        f"technolog{'y' if total == 1 else 'ies'} in this role that can be checked against code.",
        f"The clearest examples are {join_names([h['name'] for h in highlights])}.",
    ]
    if missing:
        lines.append(f"I don't have public work in {join_names(missing)} yet and would be upfront about that.")
    else:
        lines.append("Every checkable technology in the role appears in my repos, though that alone doesn't prove depth.")
    return lines


def coach(match: dict, repos: list[dict]) -> dict:
    accepted_by_name = {tech.name: tech.languages for tech in TAXONOMY}
    strengths = []
    matched_languages: set[str] = set()
    for item in match["matched"]:
        accepted = accepted_by_name[item["name"]]
        support = supporting_repos(repos, accepted)
        matched_languages.update(accepted)
        count = len(support)
        strengths.append({
            "name": item["name"],
            "summary": (
                f"{item['name']} is backed by {count} of your public repo{'s' if count != 1 else ''} "
                f"(largest: {support[0]['repo']['name']})."
            ),
            "evidence": item["evidence"],
        })

    highlights = _highlight_repos(repos, matched_languages)
    top_languages = [lang["name"] for lang in stats.language_breakdown(repos) if lang["name"] != "Other"][:3]
    return {
        "status": match["status"],
        "score": match["score"],
        "strengths": strengths,
        "missing": [m["name"] for m in match["missing"]],
        "highlight_repos": highlights,
        "unassessable": match["unassessable"],
        "pitch": _pitch(match, highlights, top_languages),
        "disclaimer": DISCLAIMER,
    }
