import re
from typing import Any

import httpx

from app.utils.redis import get_or_load_json


class GitHubProfileNotFound(LookupError):
    pass


class GitHubRateLimitExceeded(RuntimeError):
    pass


class GitHubServiceError(RuntimeError):
    pass


USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")
PROFILE_FIELDS = (
    "login",
    "name",
    "bio",
    "public_repos",
    "followers",
    "following",
    "html_url",
)


async def get_github_profile(username: str) -> dict[str, Any]:
    username = username.strip()
    if (
        not USERNAME_PATTERN.fullmatch(username)
        or "--" in username
    ):
        raise ValueError("Enter a valid public GitHub username.")

    async def fetch_profile() -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(
                timeout=10,
                headers={"Accept": "application/vnd.github+json"},
            ) as client:
                response = await client.get(
                    f"https://api.github.com/users/{username}"
                )
                if response.status_code == 404:
                    raise GitHubProfileNotFound("GitHub profile was not found.")
                if response.status_code == 403 and response.headers.get(
                    "x-ratelimit-remaining"
                ) == "0":
                    raise GitHubRateLimitExceeded(
                        "GitHub's public API rate limit was reached."
                    )
                response.raise_for_status()
                profile = response.json()
        except (GitHubProfileNotFound, GitHubRateLimitExceeded):
            raise
        except httpx.HTTPStatusError as error:
            raise GitHubServiceError(
                f"GitHub returned HTTP {error.response.status_code}."
            ) from error
        except httpx.RequestError as error:
            raise GitHubServiceError("GitHub could not be reached.") from error
        except ValueError as error:
            raise GitHubServiceError("GitHub returned invalid profile data.") from error

        if not isinstance(profile, dict) or not isinstance(profile.get("login"), str):
            raise GitHubServiceError("GitHub returned invalid profile data.")
        return {
            key: profile.get(key)
            for key in PROFILE_FIELDS
        }

    return await get_or_load_json(
        f"verisphere:github:profile:{username.lower()}",
        ttl_seconds=900,
        loader=fetch_profile,
    )
