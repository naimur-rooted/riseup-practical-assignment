"""Airtable REST client (Phase 3). Every failure becomes AirtableError — the local
save never waits on this succeeding."""

import json
import logging
import urllib.error
import urllib.request

import settings
from config import AIRTABLE_TIMEOUT_SECONDS
from errors import AirtableError
from models import Item

logger = logging.getLogger(__name__)


def is_configured() -> bool:
    """True when token, base id, and table name all exist (why: fail fast, loudly)."""
    is_token_set = bool(settings.AIRTABLE_TOKEN)
    is_base_set = bool(settings.AIRTABLE_BASE_ID)
    is_table_set = bool(settings.AIRTABLE_TABLE_NAME)
    return is_token_set and is_base_set and is_table_set


def record_fields(item: Item) -> dict[str, str]:
    """Map our item onto Airtable fields (why: the two schemas are not identical)."""
    return {
        "title": item.title,
        "content": item.content,
        "source_url": str(item.source_url),
    }


def send_item(item: Item) -> None:
    """Mirror one stored item right now; failures raise AirtableError."""
    send_fields(record_fields(item))
    logger.info("mirrored item %s to airtable", item.id)


def send_fields(fields: dict[str, str]) -> None:
    """POST one record; unconfigured Airtable is itself a failure (fail closed)."""
    is_unconfigured = not is_configured()
    if is_unconfigured:
        logger.warning("airtable not configured; mirror cannot run")
        raise AirtableError("airtable credentials missing")
    _call(_build_request(fields))


def _build_request(fields: dict[str, str]) -> urllib.request.Request:
    """Build the POST (why: stdlib urllib keeps the dependency list at zero)."""
    body = json.dumps({"fields": fields}).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {settings.AIRTABLE_TOKEN}",
        "Content-Type": "application/json",
    }
    return urllib.request.Request(
        settings.airtable_endpoint(), data=body, method="POST", headers=headers
    )


def _call(request: urllib.request.Request) -> None:
    """Execute the HTTP call; every failure is logged and becomes AirtableError."""
    try:
        urllib.request.urlopen(request, timeout=AIRTABLE_TIMEOUT_SECONDS)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as error:
        logger.warning("airtable call failed: %s", error)
        raise AirtableError(f"airtable call failed: {error}") from error
