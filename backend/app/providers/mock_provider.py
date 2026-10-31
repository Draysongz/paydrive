import logging

from app.providers.base import BaseProvider

logger = logging.getLogger(__name__)


class MockProvider(BaseProvider):
    """Mock provider that returns hardcoded invoice data for testing without API access."""

    MOCK_INVOICES = {
        "inv-001-small.pdf": {
            "invoice_id": "INV-2026-1001",
            "vendor_name": "CloudSync Labs",
            "issue_date": "2026-10-30",
            "due_date": "2026-11-15",
            "line_items": [
                {"description": "API Gateway Monthly", "quantity": 1, "unit_price": 89.00, "total": 89.00},
                {"description": "SSL Certificate Renewal", "quantity": 1, "unit_price": 29.00, "total": 29.00},
            ],
            "subtotal": 118.00,
            "tax_amount": 9.44,
            "total_amount": 127.44,
            "currency": "USD",
            "payment_route": {"rail": "paypal", "recipient": "billing@cloudsync.io"},
        },
        "inv-002-large.pdf": {
            "invoice_id": "INV-2026-8802",
            "vendor_name": "Nexus Cloud Infrastructure",
            "issue_date": "2026-10-30",
            "due_date": "2026-11-15",
            "line_items": [
                {"description": "Dedicated Compute Node A1", "quantity": 1, "unit_price": 320.00, "total": 320.00},
                {"description": "Bandwidth Overage (TB)", "quantity": 2, "unit_price": 40.00, "total": 80.00},
            ],
            "subtotal": 400.00,
            "tax_amount": 40.00,
            "total_amount": 440.00,
            "currency": "USD",
            "payment_route": {"rail": "paypal", "recipient": "payments@nexuscloud.io"},
        },
        "inv-003-supplies.pdf": {
            "invoice_id": "INV-2026-5543",
            "vendor_name": "OfficeMax Pro",
            "issue_date": "2026-10-30",
            "due_date": "2026-11-15",
            "line_items": [
                {"description": "Printer Paper (ream)", "quantity": 5, "unit_price": 12.00, "total": 60.00},
                {"description": "Toner Cartridge", "quantity": 1, "unit_price": 85.00, "total": 85.00},
                {"description": "USB-C Hub", "quantity": 2, "unit_price": 24.50, "total": 49.00},
            ],
            "subtotal": 194.00,
            "tax_amount": 13.58,
            "total_amount": 207.58,
            "currency": "USD",
            "payment_route": {"rail": "paypal", "recipient": "accounts@officemax.io"},
        },
    }

    _call_count: int = 0  # Class variable — persists across instances

    async def extract_invoice(self, content: bytes, mime_type: str) -> dict:
        keys = list(self.MOCK_INVOICES.keys())
        key = keys[MockProvider._call_count % len(keys)]
        MockProvider._call_count += 1
        logger.info(f"MockProvider: returning {key} (call #{MockProvider._call_count})")
        return self.MOCK_INVOICES[key]
