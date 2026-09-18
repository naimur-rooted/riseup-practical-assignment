"""Static configuration (why: cline.md rule 8 — no magic strings anywhere else)."""

DATABASE_PATH = "items.db"
ITEMS_TABLE = "items"
RETRY_TABLE = "retry_queue"

STATUS_PENDING = "pending"
STATUS_SUCCESS = "success"
STATUS_FAILED = "failed"

MAX_BACKOFF_SECONDS = 300
POLL_INTERVAL_SECONDS = 5
AIRTABLE_TIMEOUT_SECONDS = 5
