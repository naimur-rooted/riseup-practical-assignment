"""Retry-queue persistence (Phase 4) — the worker's source of due jobs."""

import json
import logging
import sqlite3
from datetime import datetime, timedelta, timezone

import db
from config import (
    MAX_BACKOFF_SECONDS,
    RETRY_TABLE,
    STATUS_PENDING,
    STATUS_SUCCESS,
)
from models import QueueJob

logger = logging.getLogger(__name__)

_QUEUE_COLUMNS = "id, payload, attempts, next_retry_at, status"


def init_queue() -> None:
    """Create the retry_queue table when missing (why: same idempotent-startup policy)."""
    with db.connect() as connection:
        connection.execute(
            f"CREATE TABLE IF NOT EXISTS {RETRY_TABLE} ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "payload TEXT NOT NULL, "
            "attempts INTEGER NOT NULL DEFAULT 0, "
            "next_retry_at TEXT NOT NULL, "
            "status TEXT NOT NULL)"
        )


def _utc_now() -> datetime:
    """Timezone-aware now (why: naive datetimes silently compare wrong)."""
    return datetime.now(timezone.utc)


def enqueue(fields: dict[str, str]) -> None:
    """Queue one failed mirror as pending, due immediately (attempts starts at 0)."""
    due_now = _utc_now().isoformat()
    sql = (
        f"INSERT INTO {RETRY_TABLE} (payload, attempts, next_retry_at, status) "
        "VALUES (?, 0, ?, ?)"
    )
    db.execute(sql, (json.dumps(fields), due_now, STATUS_PENDING))
    logger.info("mirror queued for retry (pending, due now)")


def fetch_due() -> list[sqlite3.Row]:
    """Return pending jobs whose time has come (why: the worker polls only this)."""
    with db.connect() as connection:
        return connection.execute(
            f"SELECT {_QUEUE_COLUMNS} FROM {RETRY_TABLE} "
            "WHERE status = ? AND next_retry_at <= ? ORDER BY id",
            (STATUS_PENDING, _utc_now().isoformat()),
        ).fetchall()


def list_jobs() -> list[QueueJob]:
    """Return every job (why: GET /queue powers the recorded failure-test demo)."""
    with db.connect() as connection:
        rows = connection.execute(
            f"SELECT {_QUEUE_COLUMNS} FROM {RETRY_TABLE} ORDER BY id"
        ).fetchall()
    return [_row_to_job(row) for row in rows]


def _row_to_job(row: sqlite3.Row) -> QueueJob:
    """Map one queue row onto the API model (why: single DRY mapping)."""
    return QueueJob(
        id=int(row["id"]),
        attempts=int(row["attempts"]),
        next_retry_at=row["next_retry_at"],
        status=row["status"],
    )


def mark_success(job_id: int) -> None:
    """Close a job that finally reached Airtable."""
    sql = f"UPDATE {RETRY_TABLE} SET status = ? WHERE id = ?"
    db.execute(sql, (STATUS_SUCCESS, job_id))
    logger.info("job %s marked %s", job_id, STATUS_SUCCESS)


def mark_failure(job_id: int, previous_attempts: int) -> None:
    """Bump attempts and reschedule (why: exponential backoff capped at 5 minutes)."""
    attempts = previous_attempts + 1
    delay = min(2**attempts, MAX_BACKOFF_SECONDS)
    next_retry_at = (_utc_now() + timedelta(seconds=delay)).isoformat()
    sql = f"UPDATE {RETRY_TABLE} SET attempts = ?, next_retry_at = ? WHERE id = ?"
    db.execute(sql, (attempts, next_retry_at, job_id))
    logger.warning("job %s failed; next retry in %ss", job_id, delay)
