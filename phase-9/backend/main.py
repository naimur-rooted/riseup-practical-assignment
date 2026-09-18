"""FastAPI entrypoint — Phase 4 adds the mirror, retry queue, and background worker."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import queue_store
import settings
import storage
import worker
from auth import verify_api_key
from errors import ItemNotFoundError
from mirror_service import mirror_or_queue
from models import Item, ItemCreate, ItemCreated, QueueJob

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Init schema + start the worker (why: retries must run even with no traffic)."""
    storage.init_db()
    queue_store.init_queue()
    app.state.worker_task = asyncio.create_task(worker.run_loop())
    yield
    app.state.worker_task.cancel()


app = FastAPI(title="phase9-capture-api", lifespan=lifespan)

# CORS allowlist: only our extension may call us from a browser context.
# (why the env placeholder: the extension ID is unknown until "Load unpacked" —
#  copy it into .env EXTENSION_ID after the first load, or preflight will fail.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.extension_origin()],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "X-API-Key"],
)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe; the extension and automation use it for checks."""
    return {"status": "ok"}


@app.post(
    "/items",
    response_model=ItemCreated,
    status_code=201,
    dependencies=[Depends(verify_api_key)],
)
def create_item(item: ItemCreate) -> ItemCreated:
    """Save locally first, then mirror; failure queues a retry (graded guarantee)."""
    stored = storage.create_item(item)
    mirror_status = mirror_or_queue(stored)
    return ItemCreated(**stored.model_dump(), mirror=mirror_status)


@app.get("/items", response_model=list[Item])
def list_items() -> list[Item]:
    """List all stored captures (reads stay open in this assignment)."""
    return storage.list_items()


@app.get("/queue", response_model=list[QueueJob])
def list_queue() -> list[QueueJob]:
    """Show retry-queue rows (why: the recorded failure-test demo needs visibility)."""
    return queue_store.list_jobs()


@app.delete(
    "/items/{item_id}", status_code=204, dependencies=[Depends(verify_api_key)]
)
def delete_item(item_id: int) -> None:
    """Delete one capture; the domain error is converted to 404 by the handler below."""
    storage.delete_item(item_id)


@app.exception_handler(ItemNotFoundError)
def item_not_found_handler(_: Request, error: ItemNotFoundError) -> JSONResponse:
    """Convert the domain error to HTTP 404 (why: storage stays HTTP-free)."""
    logger.warning("mapped to 404: %s", error)
    return JSONResponse(status_code=404, content={"detail": str(error)})
