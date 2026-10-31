import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class EventBus:
    """In-memory pub/sub for SSE streaming to frontend."""

    def __init__(self):
        self._subscribers: list[asyncio.Queue] = []

    def subscribe(self) -> asyncio.Queue:
        queue = asyncio.Queue()
        self._subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        self._subscribers.remove(queue)

    async def emit(
        self,
        event_type: str,
        message: str,
        invoice_id: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        event = {
            "event_type": event_type,
            "message": message,
            "invoice_id": invoice_id,
            "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        data = json.dumps(event)
        logger.info(f"[EVENT] {event_type}: {message}")
        for queue in self._subscribers:
            await queue.put(data)


# Global singleton
event_bus = EventBus()
