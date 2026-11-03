"""Rule-based portfolio chatbot.

Intents are detected with plain keyword rules, in priority order, and every
answer is built only from cached GitHub data and the saved job description.
No external AI service is used. Each answer carries the evidence it was built from.
"""
import re

from . import matcher, stats

SUGGESTIONS = [
    "What are my top languages?",
    "Which are my best repos?",
    "Which repos use Python?",
    "What is my current streak?",
    "How many stars do I have?",
    "How many followers do I have?",
    "Give me a profile summary.",
    "What is my match score?",
    "What are my gaps for this job?",
]

CAPABILITIES = (
    "I answer questions using your cached GitHub data: top languages, best repos, repos using a "
    "specific language, contribution streaks, stars, followers, a profile summary, and (after you save "
    "a job description) your match score and gaps. Try one of the suggested questions."
)

# Short language names are only matched with exact casing ("Go", "C", "R") to avoid
# matching ordinary words like "go".
_CASE_SENSITIVE_MAX_LEN = 2


def _has(text: str, *patterns: str) -> bool:
    return any(re.search(p, text) for p in patterns)


def _evidence(label: str, value: str, url: str | None = None) -> dict:
    return {"label": label, "value": value, "url": url}


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def _mentioned_language(message: str, repos: list[dict]) -> str | None:
    """The first-mentioned language the user owns, falling back to the matcher taxonomy."""
    found = []
    for lang in stats.user_languages(repos):
        flags = 0 if len(lang) <= _CASE_SENSITIVE_MAX_LEN else re.IGNORECASE
        if m := re.search(r"(?<![A-Za-z0-9_])" + re.escape(lang) + r"(?![A-Za-z0-9_+#])", message, flags):
            found.append((m.start(), lang))
    if found:
        return min(found)[1]
    techs = [t for t in matcher.extract_technologies(message) if t.assessable]
    return techs[0].languages[0] if techs else None


def detect_intent(message: str, repos: list[dict]) -> tuple[str, str | None]:
    text = message.lower()
    if _has(text, r"\bmatch", r"\bscore", r"compatib", r"\bfit\b", r"percent"):
        return "match_score", None
    if _has(text, r"\bgaps?\b", r"\bmissing\b", r"\black", r"\bweak", r"\bimprove"):
        return "gaps", None
    if _has(text, r"streak", r"consecutive", r"contribut", r"active days?", r"\bcommits?\b", r"best day"):
        return "streaks", None
    if _has(text, r"follower"):
        return "followers", None
    if _has(text, r"\brepos?\b", r"repositor", r"project", r"\bwritten\b", r"\bbuilt\b", r"\buse[sd]?\b"):
        language = _mentioned_language(message, repos)
        if language:
            return "repos_by_language", language
        if _has(text, r"\bbest\b", r"\btop\b", r"popular", r"most starred", r"showcase", r"highlight"):
            return "best_repos", None
    if _has(text, r"\bstars?\b", r"starred"):
        return "stars", None
    if _has(text, r"language", r"\bstack\b", r"\btech"):
        return "top_languages", None
    if _has(text, r"summar", r"overview", r"\babout\b", r"\bwho\b", r"profile", r"introduc"):
        return "profile_summary", None
    return "unknown", None


def _top_languages(data: dict) -> tuple[str, list[dict]]:
    langs = stats.language_breakdown(data["repositories"])
    if not langs:
        return "There is no language data in your public non-fork repositories yet.", []
    parts = [f"{l['name']} ({l['percent']}%)" for l in langs]
    answer = f"Your top languages by code size are {matcher.join_names(parts)}. Forks are excluded."
    return answer, [_evidence(l["name"], f"{l['percent']}% · {l['bytes']} bytes") for l in langs]


def _best_repos(data: dict) -> tuple[str, list[dict]]:
    owned = sorted(stats.owned_repos(data["repositories"]),
                   key=lambda r: (-r["stars"], -r["forks"], r["name"].lower()))[:3]
    if not owned:
        return "You don't have any public non-fork repositories yet.", []
    names = [f"{r['name']} ({_plural(r['stars'], 'star')})" for r in owned]
    evidence = [
        _evidence(r["name"], f"★ {r['stars']} · forks {r['forks']} · {r['primary_language'] or 'no language'}", r["url"])
        for r in owned
    ]
    return f"Your best repos by stars are {matcher.join_names(names)}.", evidence


def _repos_by_language(data: dict, language: str) -> tuple[str, list[dict]]:
    support = matcher.supporting_repos(data["repositories"], (language,))
    if not support:
        return f"None of your public non-fork repositories contain {language} code.", []
    shown = support[:5]
    answer = (
        f"{_plural(len(support), 'repo')} contain{'s' if len(support) == 1 else ''} {language} code. "
        f"Largest first: {matcher.join_names([s['repo']['name'] for s in shown])}."
    )
    evidence = [_evidence(s["repo"]["name"], f"{s['bytes']} bytes of {language}", s["repo"]["url"]) for s in shown]
    return answer, evidence


def _streaks(data: dict) -> tuple[str, list[dict]]:
    s = stats.streaks(data["days"])
    answer = (
        f"Your current streak is {_plural(s['current_streak'], 'day')} and your longest is "
        f"{_plural(s['longest_streak'], 'day')}. You were active on {_plural(s['active_days'], 'day')} "
        "in the last year"
    )
    answer += (f", and your best day was {s['best_day']['date']} with "
               f"{_plural(s['best_day']['count'], 'contribution')}." if s["best_day"] else ".")
    evidence = [
        _evidence("Current streak", str(s["current_streak"])),
        _evidence("Longest streak", str(s["longest_streak"])),
        _evidence("Active days", str(s["active_days"])),
    ]
    if s["best_day"]:
        evidence.append(_evidence("Best day", f"{s['best_day']['date']} · {s['best_day']['count']}"))
    return answer, evidence


def _stars(data: dict) -> tuple[str, list[dict]]:
    owned = stats.owned_repos(data["repositories"])
    total = sum(r["stars"] for r in owned)
    answer = f"You have {_plural(total, 'star')} across {_plural(len(owned), 'public non-fork repo')}."
    evidence = [_evidence("Total stars", str(total))]
    if owned and total:
        top = max(owned, key=lambda r: (r["stars"], r["name"]))
        answer += f" The most starred is {top['name']} with {top['stars']}."
        evidence.append(_evidence(top["name"], f"★ {top['stars']}", top["url"]))
    return answer, evidence


def _followers(data: dict) -> tuple[str, list[dict]]:
    n = data["profile"]["followers"]
    return f"You have {_plural(n, 'follower')} on GitHub.", [_evidence("Followers", str(n), data["profile"]["url"])]


def _profile_summary(data: dict) -> tuple[str, list[dict]]:
    profile = data["profile"]
    summary = stats.summary_stats(data)
    langs = [l["name"] for l in stats.language_breakdown(data["repositories"]) if l["name"] != "Other"][:3]
    who = f"{profile['name']} (@{profile['login']})" if profile["name"] else f"@{profile['login']}"
    answer = (
        f"{who} has {_plural(summary['public_repos'], 'public non-fork repo')}, "
        f"{_plural(summary['total_stars'], 'star')}, {_plural(profile['followers'], 'follower')} and "
        f"{_plural(summary['total_contributions'], 'contribution')} in the last year."
    )
    if langs:
        answer += f" Main languages: {matcher.join_names(langs)}."
    evidence = [
        _evidence("Public repos", str(summary["public_repos"])),
        _evidence("Total stars", str(summary["total_stars"])),
        _evidence("Followers", str(profile["followers"])),
        _evidence("Contributions", str(summary["total_contributions"])),
    ]
    return answer, evidence


NO_JD = "No job description is saved yet. Paste one in the job description panel to get a match score and gaps."


def _match_score(data: dict, jd: str | None) -> tuple[str, list[dict]]:
    if not jd:
        return NO_JD, []
    result = matcher.analyze(jd, data["repositories"])
    evidence = [_evidence(m["name"], "matched via " + ", ".join(e["repo"] for e in m["evidence"])) for m in result["matched"]]
    if result["score"] is None:
        return result["explanation"], evidence
    return f"Your match score is {result['score']}%. {result['explanation']}", evidence


def _gaps(data: dict, jd: str | None) -> tuple[str, list[dict]]:
    if not jd:
        return NO_JD, []
    result = matcher.analyze(jd, data["repositories"])
    missing = [m["name"] for m in result["missing"]]
    if result["status"] == "no_assessable_keywords":
        answer = "The saved job description has no technologies that can be checked against your repositories."
    elif missing:
        answer = f"Your public repos don't show {matcher.join_names(missing)}, which the job description asks for."
    else:
        answer = "Every checkable technology in the job description appears in your public repos."
    if result["unassessable"]:
        answer += f" {matcher.join_names(result['unassessable'])} can't be verified from repository languages."
    evidence = [_evidence(name, "no supporting repo") for name in missing]
    evidence += [_evidence(name, "not assessable from languages") for name in result["unassessable"]]
    return answer, evidence


def respond(message: str, data: dict, job_description: str | None) -> dict:
    intent, language = detect_intent(message, data["repositories"])
    if intent == "top_languages":
        answer, evidence = _top_languages(data)
    elif intent == "best_repos":
        answer, evidence = _best_repos(data)
    elif intent == "repos_by_language":
        answer, evidence = _repos_by_language(data, language)
    elif intent == "streaks":
        answer, evidence = _streaks(data)
    elif intent == "stars":
        answer, evidence = _stars(data)
    elif intent == "followers":
        answer, evidence = _followers(data)
    elif intent == "profile_summary":
        answer, evidence = _profile_summary(data)
    elif intent == "match_score":
        answer, evidence = _match_score(data, job_description)
    elif intent == "gaps":
        answer, evidence = _gaps(data, job_description)
    else:
        answer, evidence = CAPABILITIES, []
    return {"intent": intent, "answer": answer, "evidence": evidence, "suggestions": SUGGESTIONS}
