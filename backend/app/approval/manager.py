import asyncio
import logging
from datetime import timedelta

from app.config import settings

logger = logging.getLogger(__name__)


class ApprovalManager:
    """Manages human-in-the-loop approval state for invoices."""

    def __init__(self):
        self._pending: dict[str, asyncio.Event] = {}
        self._decisions: dict[str, bool] = {}

    async def request_approval(self, invoice_id: str) -> bool:
        """
        Block until the invoice is approved or rejected, or times out.
        Returns True if approved, False if rejected or timed out.
        """
        event = asyncio.Event()
        self._pending[invoice_id] = event

        timeout = timedelta(hours=settings.approval_timeout_hours).total_seconds()
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning(f"Approval timed out for invoice {invoice_id}")
            self._pending.pop(invoice_id, None)
            self._decisions[invoice_id] = False
            return False

        self._pending.pop(invoice_id, None)
        approved = self._decisions.pop(invoice_id, False)
        return approved

    def approve(self, invoice_id: str):
        """Approve a pending invoice."""
        self._decisions[invoice_id] = True
        event = self._pending.get(invoice_id)
        if event:
            event.set()
            logger.info(f"Invoice {invoice_id} approved")

    def reject(self, invoice_id: str):
        """Reject a pending invoice."""
        self._decisions[invoice_id] = False
        event = self._pending.get(invoice_id)
        if event:
            event.set()
            logger.info(f"Invoice {invoice_id} rejected")

    def get_pending(self) -> list[str]:
        """Return list of invoice IDs awaiting approval."""
        return list(self._pending.keys())


# Global singleton
approval_manager = ApprovalManager()
