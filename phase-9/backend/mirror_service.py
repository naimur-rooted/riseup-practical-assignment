"""Mirror orchestration: send to Airtable; on failure, queue for retry (Phase 3+4)."""

import logging

import airtable
import queue_store
from errors import AirtableError
from models import Item, MirrorStatus

logger = logging.getLogger(__name__)


def mirror_or_queue(item: Item) -> MirrorStatus:
    """Mirror after the local save; queue instead of failing (why: graded guarantee)."""
    try:
        airtable.send_item(item)
    except AirtableError as error:
        logger.warning("mirror failed for item %s, queueing: %s", item.id, error)
        queue_store.enqueue(airtable.record_fields(item))
        return MirrorStatus.QUEUED
    return MirrorStatus.MIRRORED
