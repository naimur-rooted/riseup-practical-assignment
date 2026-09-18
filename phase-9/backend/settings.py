"""Runtime settings loaded from .env (why: secrets never live in code or git)."""

import os

from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY", "")
EXTENSION_ID = os.getenv("EXTENSION_ID", "REPLACE_WITH_EXTENSION_ID")

AIRTABLE_TOKEN = os.getenv("AIRTABLE_TOKEN", "")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID", "")
AIRTABLE_TABLE_NAME = os.getenv("AIRTABLE_TABLE_NAME", "")
# Test hook (why: the retry queue can be demoed against backend/mock_airtable.py
# without touching the real service; leave unset in production).
AIRTABLE_API_URL = os.getenv("AIRTABLE_API_URL", "https://api.airtable.com")


def extension_origin() -> str:
    """Build the exact browser origin (why: CORS matches full scheme+host strings)."""
    return f"chrome-extension://{EXTENSION_ID}"


def airtable_endpoint() -> str:
    """Full record-creation URL (why: base id and table name must come from env)."""
    return f"{AIRTABLE_API_URL}/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"
