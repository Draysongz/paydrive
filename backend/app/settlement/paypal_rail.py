import logging
import uuid
from datetime import datetime, timezone

import httpx

from app.config import settings
from app.db.models import Invoice

logger = logging.getLogger(__name__)


class PayPalRail:
    """PayPal settlement rail using OAuth2 + Payouts API."""

    def __init__(self):
        self._token: str | None = None
        self._token_expires: datetime | None = None

    async def _get_token(self) -> str:
        """Get or refresh OAuth2 access token."""
        now = datetime.now(timezone.utc)
        if self._token and self._token_expires and now < self._token_expires:
            return self._token

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{settings.paypal_base_url}/v1/oauth2/token",
                data={"grant_type": "client_credentials"},
                auth=(settings.paypal_client_id, settings.paypal_client_secret),
                headers={"Accept": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()

        self._token = data["access_token"]
        # Expire 60 seconds early to be safe
        from datetime import timedelta
        self._token_expires = now + timedelta(seconds=data["expires_in"] - 60)
        logger.info("PayPal OAuth2 token refreshed")
        return self._token

    async def execute(self, invoice: Invoice) -> dict:
        """Execute a PayPal payout for the invoice."""
        token = await self._get_token()
        sender_batch_id = f"PD-{uuid.uuid4().hex[:12]}"

        payout_payload = {
            "sender_batch_header": {
                "sender_batch_id": sender_batch_id,
                "email_subject": f"Payment for Invoice {invoice.invoice_id}",
                "email_message": f"You have received a payment for invoice {invoice.invoice_id} from PayDrive AI.",
            },
            "items": [
                {
                    "recipient_type": "EMAIL",
                    "amount": {
                        "value": f"{invoice.total_amount:.2f}",
                        "currency": invoice.currency,
                    },
                    "receiver": invoice.recipient,
                    "note": f"Invoice {invoice.invoice_id} - {invoice.vendor_name}",
                    "sender_item_id": str(invoice.id),
                }
            ],
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{settings.paypal_base_url}/v1/payments/payouts",
                json=payout_payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            result = resp.json()

        batch_id = result["batch_header"]["payout_batch_id"]
        batch_status = result["batch_header"]["batch_status"]

        logger.info(f"PayPal payout created: batch_id={batch_id}, status={batch_status}")

        return {
            "provider_ref": batch_id,
            "status": "completed" if batch_status in ("SUCCESS", "PENDING") else "failed",
            "metadata": result,
        }
