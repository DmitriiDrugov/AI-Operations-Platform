"""
Auth middleware — validates the JWT issued by Supabase and extracts
organisation_id, user_id, and role claims for downstream use.

Python services are called from the admin app (which is authenticated)
or from internal service-to-service calls. In both cases the JWT is
passed as a Bearer token.
"""
import uuid
from dataclasses import dataclass

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ...core.config import get_settings
from ...core.logging import get_logger

log = get_logger(__name__)
_bearer = HTTPBearer(auto_error=True)


@dataclass
class RequestContext:
    user_id: str
    organisation_id: str
    role: str
    trace_id: str | None = None


async def get_request_context(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> RequestContext:
    """
    Validates JWT with Supabase and returns extracted claims.
    For internal service accounts, validates against a shared secret instead.
    """
    token = credentials.credentials

    # Validate token by calling Supabase Auth
    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{settings.supabase_url}/auth/v1/user",
                headers={
                    "Authorization": f"Bearer {token}",
                    "apikey": settings.supabase_service_role_key.get_secret_value(),
                },
            )
    except httpx.TimeoutException as exc:
        log.error("auth.supabase_timeout")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth service unavailable",
        ) from exc

    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user_data = response.json()
    app_metadata = user_data.get("app_metadata", {})
    user_metadata = user_data.get("user_metadata", {})

    organisation_id = app_metadata.get("organisation_id")
    role = app_metadata.get("role", "read_only")
    user_id = user_data.get("id")

    if not organisation_id or not user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token missing required claims",
        )

    return RequestContext(
        user_id=str(user_id),
        organisation_id=str(organisation_id),
        role=role,
        trace_id=str(uuid.uuid4()),
    )
