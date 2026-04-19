from __future__ import annotations

from functools import lru_cache

import httpx
from fastapi import Depends, Header, HTTPException
from jose import JWTError, jwt

from app.settings import settings


@lru_cache(maxsize=1)
def _get_openid_config() -> dict:
    tenant = settings.teams_tenant_id or "common"
    url = f"https://login.microsoftonline.com/{tenant}/v2.0/.well-known/openid-configuration"
    response = httpx.get(url, timeout=10.0)
    response.raise_for_status()
    return response.json()


@lru_cache(maxsize=1)
def _get_jwks() -> dict:
    config = _get_openid_config()
    jwks_uri = config.get("jwks_uri")
    if not jwks_uri:
        raise RuntimeError("Missing jwks_uri in OpenID configuration")
    response = httpx.get(jwks_uri, timeout=10.0)
    response.raise_for_status()
    return response.json()


def _parse_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="missing Authorization header")
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="invalid bearer token format")
    return parts[1]


def decode_teams_token(token: str) -> dict:
    if settings.teams_disable_jwt_validation:
        # Local dev shortcut for demos where Azure AD is unavailable.
        return {"sub": "dev-user", "name": "Dev User", "preferred_username": "dev@local"}

    if not settings.teams_client_id:
        raise HTTPException(status_code=500, detail="TEAMS_CLIENT_ID is not configured")

    openid_config = _get_openid_config()
    issuer = openid_config.get("issuer")

    try:
        claims = jwt.decode(
            token,
            _get_jwks(),
            algorithms=["RS256"],
            audience=settings.teams_client_id,
            issuer=issuer,
            options={"verify_at_hash": False},
        )
    except JWTError as exc:
        raise HTTPException(status_code=401, detail=f"invalid AAD token: {exc}") from exc

    return claims


def get_teams_claims(authorization: str | None = Header(default=None)) -> dict:
    token = _parse_bearer_token(authorization)
    return decode_teams_token(token)


def get_teams_user_identity(claims: dict = Depends(get_teams_claims)) -> dict:
    return {
        "aad_object_id": claims.get("oid") or claims.get("sub"),
        "display_name": claims.get("name"),
        "email": claims.get("preferred_username") or claims.get("upn") or claims.get("email"),
        "tenant_id": claims.get("tid"),
    }
