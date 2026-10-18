from datetime import UTC, datetime, timedelta
import secrets
from urllib.parse import urlencode

import httpx
from jose import JWTError, jwt

from app.core.config import (
    LINKEDIN_CLIENT_ID,
    LINKEDIN_CLIENT_SECRET,
    LINKEDIN_REDIRECT_URI,
    LINKEDIN_SCOPES,
    SECRET_KEY,
)


AUTHORIZE_URL = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
USERINFO_URL = "https://api.linkedin.com/v2/userinfo"


class LinkedInNotConfigured(RuntimeError):
    pass


class LinkedInOAuthError(RuntimeError):
    pass


def _require_configuration() -> None:
    if not all((LINKEDIN_CLIENT_ID, LINKEDIN_CLIENT_SECRET, LINKEDIN_REDIRECT_URI)):
        raise LinkedInNotConfigured(
            "LinkedIn OAuth requires LINKEDIN_CLIENT_ID, "
            "LINKEDIN_CLIENT_SECRET, and LINKEDIN_REDIRECT_URI."
        )


def create_authorization_url(user_id: int) -> str:
    _require_configuration()
    now = datetime.now(UTC)
    state = jwt.encode(
        {
            "purpose": "linkedin-connect",
            "user_id": user_id,
            "nonce": secrets.token_urlsafe(32),
            "iat": now,
            "exp": now + timedelta(minutes=10),
        },
        SECRET_KEY,
        algorithm="HS256",
    )
    parameters = {
        'response_type': 'code',
        'client_id': LINKEDIN_CLIENT_ID,
        'redirect_uri': LINKEDIN_REDIRECT_URI,
        'scope': LINKEDIN_SCOPES,
        'state': state,
    }
    return f"{AUTHORIZE_URL}?{urlencode(parameters)}"


def read_authorization_state(state: str) -> int:
    try:
        claims = jwt.decode(state, SECRET_KEY, algorithms=["HS256"])
    except JWTError as error:
        raise LinkedInOAuthError("LinkedIn authorization state is invalid or expired.") from error
    user_id = claims.get("user_id")
    if claims.get("purpose") != "linkedin-connect" or not isinstance(user_id, int):
        raise LinkedInOAuthError("LinkedIn authorization state is invalid.")
    return user_id


async def exchange_code_for_profile(code: str) -> dict[str, str | None]:
    _require_configuration()
    if not code or len(code) > 4096:
        raise LinkedInOAuthError("LinkedIn returned an invalid authorization code.")
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            token_response = await client.post(
                TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": LINKEDIN_REDIRECT_URI,
                    "client_id": LINKEDIN_CLIENT_ID,
                    "client_secret": LINKEDIN_CLIENT_SECRET,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            token_response.raise_for_status()
            token_data = token_response.json()
            if not isinstance(token_data, dict):
                raise LinkedInOAuthError("LinkedIn returned invalid token data.")
            access_token = token_data.get("access_token")
            if not isinstance(access_token, str) or not access_token:
                raise LinkedInOAuthError("LinkedIn did not return an access token.")

            profile_response = await client.get(
                USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            profile_response.raise_for_status()
            profile = profile_response.json()
    except LinkedInOAuthError:
        raise
    except httpx.HTTPStatusError as error:
        raise LinkedInOAuthError(
            f"LinkedIn returned HTTP {error.response.status_code}."
        ) from error
    except httpx.RequestError as error:
        raise LinkedInOAuthError("LinkedIn could not be reached.") from error
    except ValueError as error:
        raise LinkedInOAuthError("LinkedIn returned invalid profile data.") from error

    if (
        not isinstance(profile, dict)
        or not isinstance(profile.get("sub"), str)
        or not profile["sub"]
    ):
        raise LinkedInOAuthError("LinkedIn returned invalid profile data.")
    name = profile.get("name")
    picture = profile.get("picture")
    return {
        "sub": profile["sub"][:255],
        "name": name[:255] if isinstance(name, str) else None,
        "given_name": (
            profile["given_name"][:255]
            if isinstance(profile.get("given_name"), str)
            else None
        ),
        "family_name": (
            profile["family_name"][:255]
            if isinstance(profile.get("family_name"), str)
            else None
        ),
        "picture": (
            picture[:2048]
            if isinstance(picture, str) and picture.startswith("https://")
            else None
        ),
    }
