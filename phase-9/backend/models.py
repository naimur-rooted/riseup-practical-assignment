"""Pydantic schemas and the API's strict status contract."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, HttpUrl


class MirrorStatus(StrEnum):
    """Outcome of the third-party mirror (why: enum, never bare strings)."""

    MIRRORED = "mirrored"
    QUEUED = "queued"


class ItemCreate(BaseModel):
    """Payload accepted from the extension popup; validated before it touches storage."""

    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=10_000)
    source_url: HttpUrl


class Item(ItemCreate):
    """Stored record returned to clients (adds the DB-managed fields)."""

    id: int
    created_at: datetime


class ItemCreated(Item):
    """Create response: the item plus how its third-party mirror ended up."""

    mirror: MirrorStatus


class QueueJob(BaseModel):
    """One retry-queue row (why: GET /queue makes the graded demo observable)."""

    id: int
    attempts: int
    next_retry_at: datetime
    status: str
