import dataclasses

import httpx
import pytest

from app.errors import GitHubAuthError, GitHubUnavailableError, RateLimitedError, UserNotFoundError
from app.services.github_client import GitHubClient


def gql_repo(name, stars=1):
    return {
        "name": name, "url": f"https://github.com/octo/{name}", "description": None,
        "stargazerCount": stars, "forkCount": 0, "isFork": False, "isArchived": False,
        "pushedAt": "2026-10-01T00:00:00Z", "primaryLanguage": None,
        "languages": {"edges": [{"size": 10, "node": {"name": "Python", "color": "#3572A5"}}]},
    }


def repo_conn(nodes, has_next=False):
    return {"totalCount": len(nodes), "pageInfo": {"hasNextPage": has_next, "endCursor": "c"}, "nodes": nodes}


def profile_body(has_next=False, typename="User"):
    owner = {
        "__typename": typename,
        "login": "Octo",
        "name": None,
        "avatarUrl": "https://a/x.png",
        "bio": None,
        "url": "https://github.com/Octo",
        "followers": {"totalCount": 3},
        "contributionsCollection": {"contributionCalendar": {
            "totalContributions": 2,
            "weeks": [{"contributionDays": [
                {"date": "2026-11-01", "contributionCount": 0, "contributionLevel": "NONE"},
                {"date": "2026-11-02", "contributionCount": 2, "contributionLevel": "FOURTH_QUARTILE"},
            ]}],
        }},
        "repositories": repo_conn([gql_repo("one", 5)], has_next),
    }
    return {"data": {"rateLimit": {"remaining": 4000, "resetAt": "2026-11-03T12:00:00Z"}, "repositoryOwner": owner}}


def make_client(settings, handler):
    return GitHubClient(settings, transport=httpx.MockTransport(handler))


async def test_normalizes_profile_calendar_and_repos(settings):
    client = make_client(settings, lambda req: httpx.Response(200, json=profile_body()))
    data = await client.fetch_user("octo")
    assert data["profile"]["login"] == "Octo"
    assert data["profile"]["followers"] == 3
    assert [d["level"] for d in data["days"]] == [0, 4]
    assert data["repositories"][0]["description"] is None
    assert data["repositories"][0]["languages"][0]["name"] == "Python"
    assert data["truncated"] is False
    assert data["rate_limit"] == {"remaining": 4000, "reset_at": "2026-11-03T12:00:00Z"}


async def test_graphql_errors_with_http_200_are_detected(settings):
    body = {"data": None, "errors": [{"type": "RATE_LIMITED", "message": "API rate limit exceeded"}]}
    client = make_client(settings, lambda req: httpx.Response(200, json=body))
    with pytest.raises(RateLimitedError):
        await client.fetch_user("octo")

    body = {"data": {"repositoryOwner": None}, "errors": [{"type": "SOMETHING", "message": "boom"}]}
    client = make_client(settings, lambda req: httpx.Response(200, json=body))
    with pytest.raises(GitHubUnavailableError, match="boom"):
        await client.fetch_user("octo")


async def test_missing_user_and_organization_are_404(settings):
    client = make_client(settings, lambda req: httpx.Response(200, json={"data": {"repositoryOwner": None}}))
    with pytest.raises(UserNotFoundError):
        await client.fetch_user("ghost")

    client = make_client(settings, lambda req: httpx.Response(200, json=profile_body(typename="Organization")))
    with pytest.raises(UserNotFoundError, match="organization"):
        await client.fetch_user("github")


async def test_missing_token_raises_auth_error_without_request(settings):
    calls = []
    client = make_client(dataclasses.replace(settings, github_token=None), lambda req: calls.append(req))
    with pytest.raises(GitHubAuthError, match="GITHUB_TOKEN"):
        await client.fetch_user("octo")
    assert calls == []


@pytest.mark.parametrize("status,headers,error", [
    (401, {}, GitHubAuthError),
    (403, {"x-ratelimit-remaining": "0", "x-ratelimit-reset": "1800000000"}, RateLimitedError),
    (429, {}, RateLimitedError),
])
async def test_auth_and_rate_limit_statuses_are_not_retried(settings, status, headers, error):
    calls = []

    def handler(req):
        calls.append(req)
        return httpx.Response(status, headers=headers, json={"message": "nope"})

    with pytest.raises(error) as exc:
        await make_client(settings, handler).fetch_user("octo")
    assert len(calls) == 1
    if status == 403:
        assert exc.value.extra["reset_at"].startswith("2027-01-15")


async def test_5xx_is_retried_once_then_succeeds(settings):
    responses = [httpx.Response(502), httpx.Response(200, json=profile_body())]
    client = make_client(settings, lambda req: responses.pop(0))
    assert (await client.fetch_user("octo"))["profile"]["login"] == "Octo"


async def test_network_error_retried_once_then_503(settings):
    calls = []

    def handler(req):
        calls.append(req)
        raise httpx.ConnectTimeout("timeout", request=req)

    with pytest.raises(GitHubUnavailableError):
        await make_client(settings, handler).fetch_user("octo")
    assert len(calls) == 2


async def test_pagination_is_capped_at_five_pages(settings):
    calls = []

    def handler(req):
        calls.append(req)
        if len(calls) == 1:
            return httpx.Response(200, json=profile_body(has_next=True))
        page = {"rateLimit": {"remaining": 1, "resetAt": None},
                "user": {"repositories": repo_conn([gql_repo(f"r{len(calls)}")], has_next=True)}}
        return httpx.Response(200, json={"data": page})

    data = await make_client(settings, handler).fetch_user("octo")
    assert len(calls) == 5
    assert len(data["repositories"]) == 5
    assert data["truncated"] is True
