import logging

from app.db.models import Invoice
from app.settlement.paypal_rail import PayPalRail
from app.settlement.web3_rail import Web3Rail

logger = logging.getLogger(__name__)


class SettlementRouter:
    """Routes settlement to the appropriate payment rail."""

    def __init__(self):
        self._paypal = PayPalRail()
        self._web3 = Web3Rail()

    async def settle(self, invoice: Invoice) -> dict:
        """
        Execute settlement for an invoice based on its payment_rail.
        Returns settlement result dict with provider_ref, status, metadata.
        """
        if invoice.payment_rail == "paypal":
            logger.info(f"Routing invoice {invoice.invoice_id} to PayPal rail")
            return await self._paypal.execute(invoice)
        elif invoice.payment_rail == "web3":
            logger.info(f"Routing invoice {invoice.invoice_id} to Web3 rail")
            return await self._web3.execute(invoice)
        else:
            raise ValueError(f"Unsupported payment rail: {invoice.payment_rail}")


settlement_router = SettlementRouter()
