import asyncio
import logging
from pathlib import Path

from watchdog.events import FileSystemEventHandler, FileCreatedEvent
from watchdog.observers import Observer

from app.config import settings

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".csv"}


class InboxHandler(FileSystemEventHandler):
    """Watches inbox directory and pushes new files to the processing queue."""

    def __init__(self, queue: asyncio.Queue, loop: asyncio.AbstractEventLoop):
        self.queue = queue
        self.loop = loop

    def on_created(self, event: FileCreatedEvent):
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix.lower() in SUPPORTED_EXTENSIONS:
            logger.info(f"New file detected: {path.name}")
            self.loop.call_soon_threadsafe(self.queue.put_nowait, str(path))


def start_watcher(queue: asyncio.Queue, loop: asyncio.AbstractEventLoop) -> Observer:
    """Starts the filesystem watcher on the inbox directory."""
    inbox = Path(settings.inbox_path)
    inbox.mkdir(parents=True, exist_ok=True)

    handler = InboxHandler(queue, loop)
    observer = Observer()
    observer.schedule(handler, str(inbox), recursive=False)
    observer.daemon = True
    observer.start()
    logger.info(f"File watcher started on: {inbox}")
    return observer
