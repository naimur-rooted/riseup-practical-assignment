"""Shared SQLite plumbing (why: one connection policy for every store — DRY)."""

import sqlite3

from config import DATABASE_PATH

DbParam = str | int | float | bytes | None


def connect() -> sqlite3.Connection:
    """Open a connection with column-name rows (why: column access beats index bugs)."""
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def execute(
    sql: str, params: tuple[DbParam, ...]
) -> sqlite3.Cursor:
    """Run one write statement on a fresh connection (why: stores stay plumbing-free)."""
    with connect() as connection:
        return connection.execute(sql, params)
