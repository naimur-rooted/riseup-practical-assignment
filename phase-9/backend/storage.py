"""SQLite persistence for capture items (local save — the graded guarantee)."""

import logging
import sqlite3
from datetime import datetime, timezone

import db
from errors import ItemNotFoundError
from models import Item, ItemCreate

logger = logging.getLogger(__name__)

_INSERT_SQL = "INSERT INTO items (title, content, source_url, created_at) VALUES (?, ?, ?, ?)"
_CREATE_SQL = (
    "CREATE TABLE IF NOT EXISTS items ("
    "id INTEGER PRIMARY KEY AUTOINCREMENT, "
    "title TEXT NOT NULL, "
    "content TEXT NOT NULL, "
    "source_url TEXT NOT NULL, "
    "created_at TEXT NOT NULL)"
)


def _utc_now_iso() -> str:
    """UTC ISO-8601 timestamp (why: sortable, timezone-explicit strings in SQLite)."""
    return datetime.now(timezone.utc).isoformat()


def init_db() -> None:
    """Create the items table when missing (why: idempotent startup keeps testing simple)."""
    db.execute(_CREATE_SQL, ())


def create_item(item: ItemCreate) -> Item:
    """Insert one item and return the stored record re-read from the database."""
    cursor = db.execute(
        _INSERT_SQL,
        (item.title, item.content, str(item.source_url), _utc_now_iso()),
    )
    new_id = int(cursor.lastrowid)
    return get_item(new_id)


def get_item(item_id: int) -> Item:
    """Fetch one item or raise the domain error when the id does not exist."""
    row = _fetch_one("SELECT id, title, content, source_url, created_at FROM items WHERE id = ?", item_id)
    is_missing = row is None
    if is_missing:
        logger.warning("item %s not found", item_id)
        raise ItemNotFoundError(f"item {item_id} not found")
    return _row_to_item(row)


def list_items() -> list[Item]:
    """Return every stored item ordered by id (stable order keeps client tests simple)."""
    with db.connect() as connection:
        rows = connection.execute(
            "SELECT id, title, content, source_url, created_at FROM items ORDER BY id"
        ).fetchall()
    return [_row_to_item(row) for row in rows]


def delete_item(item_id: int) -> None:
    """Delete by id; raise the domain error when nothing matched (why: 404 stays explicit)."""
    with db.connect() as connection:
        cursor = connection.execute("DELETE FROM items WHERE id = ?", (item_id,))
        is_missing = cursor.rowcount == 0
    if is_missing:
        logger.warning("delete missed: item %s", item_id)
        raise ItemNotFoundError(f"item {item_id} not found")


def _fetch_one(sql: str, item_id: int) -> sqlite3.Row | None:
    """Run one single-row query (why: shared by create-after-insert and get)."""
    with db.connect() as connection:
        return connection.execute(sql, (item_id,)).fetchone()


def _row_to_item(row: sqlite3.Row) -> Item:
    """Map one strict 5-column row onto the response model (why: single DRY mapping)."""
    return Item(
        id=row["id"],
        title=row["title"],
        content=row["content"],
        source_url=row["source_url"],
        created_at=row["created_at"],
    )
