import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


async def send_webhook_notification(invoice_id: str, vendor: str, amount: float, currency: str):
    """Send a webhook notification for invoices requiring approval."""
    if not settings.webhook_url:
        return

    payload = {
        "type": "approval_required",
        "invoice_id": invoice_id,
        "vendor": vendor,
        "amount": amount,
        "currency": currency,
        "message": f"Invoice {invoice_id} from {vendor} for {currency} {amount:.2f} requires approval",
        "approve_url": f"http://{settings.host}:{settings.port}/api/invoices/{invoice_id}/approve",
        "reject_url": f"http://{settings.host}:{settings.port}/api/invoices/{invoice_id}/reject",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(settings.webhook_url, json=payload)
            logger.info(f"Webhook sent for {invoice_id}: status {resp.status_code}")
    except Exception as e:
        logger.error(f"Webhook notification failed for {invoice_id}: {e}")
