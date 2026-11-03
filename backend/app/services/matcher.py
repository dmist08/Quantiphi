"""Tech Stack Compatibility matcher.

A transparent taxonomy maps job-description keywords (and aliases) to the
GitHub languages that count as evidence. A technology is *matched* when at
least one owned, non-fork repo contains code in one of its accepted languages.

    score = round(100 * matched assessable technologies / total assessable technologies)

Technologies we recognize but cannot verify from repo languages (AWS, Kafka, ...)
are reported as `unassessable` and excluded from the score. If a JD contains no
assessable technology the score is None (not 0).
"""
import re
from dataclasses import dataclass

from .stats import owned_repos

# A keyword must not be glued to letters/digits on either side. '+' and '#' on the
# right keep "C" from matching inside "C++"/"C#"; '.' on the left keeps "js"
# from matching inside "node.js".
_LEFT = r"(?<![A-Za-z0-9_.])"
_RIGHT = r"(?![A-Za-z0-9_+#])"


def word(alias: str, case_sensitive: bool = False) -> str:
    body = r"\s+".join(re.escape(part) for part in alias.split())
    pattern = _LEFT + body + _RIGHT
    return pattern if case_sensitive else f"(?i:{pattern})"


# Single capital letters. "R&D", "C-level", "C-suite", "Objective-C" and "C.V." must not match.
_SINGLE_LETTER = r"(?<![A-Za-z0-9_&'.-]){}(?![A-Za-z0-9_+#&']|-[A-Za-z]|\.[A-Za-z])"


@dataclass(frozen=True)
class Tech:
    name: str
    languages: tuple[str, ...]  # empty tuple = recognized but unassessable
    patterns: tuple[str, ...]

    @property
    def assessable(self) -> bool:
        return bool(self.languages)


JS_TS = ("JavaScript", "TypeScript")
PY = ("Python",)
CSS_LANGS = ("CSS", "SCSS", "Sass", "Less")

TAXONOMY: tuple[Tech, ...] = (
    Tech("Python", ("Python", "Jupyter Notebook"), (word("python"), word("py"))),
    Tech("Django", PY, (word("django"),)),
    Tech("Flask", PY, (word("flask"),)),
    Tech("FastAPI", PY, (word("fastapi"),)),
    Tech("PyTorch", PY, (word("pytorch"),)),
    Tech("TensorFlow", PY, (word("tensorflow"),)),
    Tech("Pandas", ("Python", "Jupyter Notebook"), (word("pandas"),)),
    Tech("NumPy", ("Python", "Jupyter Notebook"), (word("numpy"),)),
    Tech("JavaScript", JS_TS, (word("javascript"), word("js"), word("ecmascript"), word("es6"))),
    Tech("Node.js", JS_TS, (word("node.js"), word("nodejs"))),
    Tech("React", JS_TS, (word("React", case_sensitive=True), word("react.js"), word("reactjs"))),
    Tech("Next.js", JS_TS, (word("next.js"), word("nextjs"))),
    Tech("Vue", JS_TS, (word("vue"), word("vue.js"), word("vuejs"))),
    Tech("TypeScript", ("TypeScript",), (word("typescript"), word("TS", case_sensitive=True) + r"(?!/SCI)")),
    Tech("Angular", ("TypeScript",), (word("angular"), word("angularjs"))),
    Tech("Java", ("Java",), (word("java"),)),
    Tech("Spring", ("Java",), (
        word("spring boot"), word("spring framework"), word("spring mvc"),
        word("Spring", case_sensitive=True) + r"(?=\s*[,/;)])",
    )),
    Tech("C++", ("C++",), (_LEFT + r"(?i:c\+\+)" + _RIGHT, word("cpp"))),
    Tech("C#", ("C#",), (_LEFT + r"(?i:c#)" + _RIGHT, word(".net"), word("dotnet"), word("csharp"))),
    Tech("C", ("C",), (_SINGLE_LETTER.format("C"),)),
    Tech("Go", ("Go",), (word("golang"),)),  # capitalized "Go" handled by _find_go
    Tech("Rust", ("Rust",), (word("rust"),)),
    Tech("Ruby", ("Ruby",), (word("ruby"), word("ruby on rails"), word("Rails", case_sensitive=True))),
    Tech("PHP", ("PHP",), (word("php"), word("laravel"), word("symfony"))),
    Tech("Swift", ("Swift",), (word("Swift", case_sensitive=True), word("swiftui"))),
    Tech("Kotlin", ("Kotlin",), (word("kotlin"),)),
    Tech("Scala", ("Scala",), (word("scala"),)),
    Tech("Dart", ("Dart",), (word("dart"), word("flutter"))),
    Tech("R", ("R",), (_SINGLE_LETTER.format("R"),)),
    Tech("HTML", ("HTML",), (word("html"), word("html5"))),
    Tech("CSS", CSS_LANGS, (word("css"), word("css3"), word("scss"), word("sass"), word("tailwind"))),
    Tech("Shell", ("Shell",), (word("shell"), word("bash"), word("shell scripting"))),
    Tech("Terraform", ("HCL",), (word("terraform"),)),
    Tech("Docker", ("Dockerfile",), (word("docker"), word("dockerfile"))),
    Tech("SQL", ("SQL", "PLpgSQL"), (word("sql"),)),
    # Recognized, but repository languages can't show them.
    Tech("AWS", (), (word("aws"), word("amazon web services"))),
    Tech("Azure", (), (word("azure"),)),
    Tech("GCP", (), (word("gcp"), word("google cloud"))),
    Tech("Kubernetes", (), (word("kubernetes"), word("k8s"))),
    Tech("Kafka", (), (word("kafka"),)),
    Tech("Redis", (), (word("redis"),)),
    Tech("Linux", (), (word("linux"),)),
    Tech("Git", (), (word("git"),)),
    Tech("CI/CD", (), (_LEFT + r"(?i:ci\s*/\s*cd)" + _RIGHT,)),
    Tech("Jenkins", (), (word("jenkins"),)),
    Tech("GraphQL", (), (word("graphql"),)),
    Tech("REST APIs", (), (word("REST", case_sensitive=True), word("restful"))),
    Tech("PostgreSQL", (), (word("postgresql"), word("postgres"))),
    Tech("MySQL", (), (word("mysql"),)),
    Tech("MongoDB", (), (word("mongodb"), word("mongo"))),
    Tech("Spark", (), (word("apache spark"), word("pyspark"), word("Spark", case_sensitive=True))),
    Tech("Airflow", (), (word("airflow"),)),
    Tech("Elasticsearch", (), (word("elasticsearch"),)),
    Tech("Ansible", (), (word("ansible"),)),
)

_COMPILED = {tech.name: [re.compile(p) for p in tech.patterns] for tech in TAXONOMY}

# Capitalized "Go" only counts in a programming context, so "Go above and beyond" does not match.
_GO = re.compile(r"(?<![A-Za-z0-9_.&'-])Go(?![A-Za-z0-9_+#'-])")
_GO_AFTER = re.compile(
    r"\s*(?:[,/;:)\]|]|\.(?:\s|$)|$)"                    # list separator, slash, paren, sentence end
    r"|\s+(?:and|or|&)\s+[A-Z]"                           # "Go and Rust"
    r"|\s+(?i:developers?|engineers?|programming|language|backend|microservices|code)\b"
)
_GO_BEFORE = re.compile(r"[,/(|]\s*$")


def _find_go(text: str) -> int | None:
    for m in _GO.finditer(text):
        if _GO_AFTER.match(text, m.end()) or _GO_BEFORE.search(text, 0, m.start()):
            return m.start()
    return None


def _first_position(tech: Tech, text: str) -> int | None:
    positions = [m.start() for regex in _COMPILED[tech.name] if (m := regex.search(text))]
    if tech.name == "Go" and (go := _find_go(text)) is not None:
        positions.append(go)
    return min(positions) if positions else None


def extract_technologies(text: str) -> list[Tech]:
    """Technologies mentioned in the text, each once, ordered by first mention."""
    found = [(pos, tech) for tech in TAXONOMY if (pos := _first_position(tech, text)) is not None]
    return [tech for _, tech in sorted(found, key=lambda item: item[0])]


def supporting_repos(repos: list[dict], accepted: tuple[str, ...]) -> list[dict]:
    """Owned non-fork repos containing an accepted language, largest matching byte count first."""
    results = []
    for repo in owned_repos(repos):
        sizes = {lang["name"]: lang["size"] or 0 for lang in repo["languages"] if lang["name"] in accepted}
        if sizes:
            best = max(sizes, key=lambda name: (sizes[name], name))
            results.append({"repo": repo, "language": best, "bytes": sum(sizes.values())})
    results.sort(key=lambda r: (-r["bytes"], -r["repo"]["stars"], r["repo"]["name"].lower()))
    return results


def join_names(names: list[str]) -> str:
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + " and " + names[-1]


def analyze(job_description: str, repos: list[dict]) -> dict:
    techs = extract_technologies(job_description)
    assessable = [t for t in techs if t.assessable]
    unassessable = [t.name for t in techs if not t.assessable]

    matched, missing = [], []
    for tech in assessable:
        support = supporting_repos(repos, tech.languages)
        if support:
            matched.append({
                "name": tech.name,
                "accepted_languages": list(tech.languages),
                "evidence": [
                    {"repo": s["repo"]["name"], "url": s["repo"]["url"], "language": s["language"]}
                    for s in support[:3]
                ],
            })
        else:
            missing.append({"name": tech.name, "accepted_languages": list(tech.languages)})

    unassessable_note = (
        f" {len(unassessable)} recognized technolog{'y' if len(unassessable) == 1 else 'ies'} "
        f"({join_names(unassessable)}) can't be verified from repository languages and "
        f"{'is' if len(unassessable) == 1 else 'are'} not part of the score."
        if unassessable else ""
    )

    if not assessable:
        return {
            "status": "no_assessable_keywords",
            "score": None,
            "matched_count": 0,
            "assessable_count": 0,
            "matched": [],
            "missing": [],
            "unassessable": unassessable,
            "explanation": (
                "No technologies that can be checked against repository languages were found in the "
                "job description, so no score is given (this is not the same as 0%)." + unassessable_note
            ),
        }

    score = round(100 * len(matched) / len(assessable))
    return {
        "status": "ok",
        "score": score,
        "matched_count": len(matched),
        "assessable_count": len(assessable),
        "matched": matched,
        "missing": missing,
        "unassessable": unassessable,
        "explanation": (
            f"Matched {len(matched)} of {len(assessable)} assessable technologies: "
            f"score = round(100 × {len(matched)} / {len(assessable)}) = {score}%. "
            "A technology counts as matched when at least one of your public, non-fork repositories "
            "contains code in an accepted language. Repeated keywords count once." + unassessable_note
        ),
    }
