import hmac
from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from football_api.settings import ApiSettings, get_settings

_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(
    provided: Annotated[str | None, Security(_header)],
    settings: Annotated[ApiSettings, Depends(get_settings)],
) -> None:
    # compare_digest avoids leaking key contents through response timing.
    if provided and any(hmac.compare_digest(provided, k) for k in settings.valid_api_keys):
        return
    raise HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        detail="Missing or invalid API key",
        headers={"WWW-Authenticate": "ApiKey"},
    )
