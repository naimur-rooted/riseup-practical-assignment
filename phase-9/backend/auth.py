"""API-key auth for write endpoints.

WHY CORS ALONE IS NOT AUTH (required comment):
CORS is a *browser-enforced* policy that only stops web pages on other origins
from calling us from inside a browser. A request sent with curl, Postman, or any
non-browser client ignores CORS entirely — the server still receives and answers
it. So CORS protects *our users' browsers* from other websites; it does NOT
protect the API from direct callers. That is why the X-API-Key check below
exists independently of the CORS layer: it is enforced server-side on every
write request, no matter who sent it.
"""

import logging
import secrets

from fastapi import Header, HTTPException, status

import settings

logger = logging.getLogger(__name__)


def verify_api_key(x_api_key: str = Header(default="")) -> None:
    """Reject the request unless X-API-Key matches the server key from .env.

    Fail-closed: if the server key is unset, nothing can ever match.
    secrets.compare_digest (why: constant-time comparison defeats timing probes).
    """
    is_server_key_set = bool(settings.API_KEY)
    is_key_valid = is_server_key_set and secrets.compare_digest(
        x_api_key, settings.API_KEY
    )
    if is_key_valid:
        return
    logger.warning("rejected write: missing or invalid API key")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="missing or invalid API key",
    )
