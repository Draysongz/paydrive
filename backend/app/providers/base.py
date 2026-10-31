from abc import ABC, abstractmethod


class BaseProvider(ABC):
    """Abstract interface for AI invoice extraction providers."""

    @abstractmethod
    async def extract_invoice(self, content: bytes, mime_type: str) -> dict:
        """
        Takes raw file bytes and MIME type, returns structured invoice dict.

        Expected return schema:
        {
            "invoice_id": str,
            "vendor_name": str,
            "issue_date": str | None,
            "due_date": str | None,
            "line_items": [{"description": str, "quantity": float, "unit_price": float, "total": float}],
            "subtotal": float,
            "tax_amount": float,
            "total_amount": float,
            "currency": str,
            "payment_route": {"rail": "paypal" | "web3", "recipient": str}
        }
        """
        ...
