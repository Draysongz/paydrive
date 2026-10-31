import base64
import json

import anthropic

from app.config import settings
from app.providers.base import BaseProvider

SYSTEM_PROMPT = """You are an invoice data extraction engine. Given an image or document of an invoice, extract all structured data and return ONLY valid JSON matching this exact schema:

{
  "invoice_id": "string - the invoice number/ID shown on the document",
  "vendor_name": "string - the company/person who issued the invoice",
  "issue_date": "string (YYYY-MM-DD) or null",
  "due_date": "string (YYYY-MM-DD) or null",
  "line_items": [
    {
      "description": "string",
      "quantity": number,
      "unit_price": number,
      "total": number
    }
  ],
  "subtotal": number,
  "tax_amount": number (0 if no tax),
  "total_amount": number,
  "currency": "string (ISO 4217, e.g. USD)",
  "payment_route": {
    "rail": "paypal" or "web3",
    "recipient": "string - email address for PayPal, wallet address (0x...) for web3"
  }
}

Rules:
- If the document contains a PayPal email or references PayPal, set rail to "paypal" and recipient to the email.
- If the document contains a wallet address (0x...), set rail to "web3" and recipient to the address.
- If neither is clear, default to rail "paypal" and use any email found on the invoice.
- Return ONLY the JSON object, no markdown fences, no explanation."""


class ClaudeProvider(BaseProvider):
    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def extract_invoice(self, content: bytes, mime_type: str) -> dict:
        b64 = base64.standard_b64encode(content).decode("utf-8")

        if mime_type == "application/pdf":
            source = {"type": "base64", "media_type": "application/pdf", "data": b64}
            content_block = {"type": "document", "source": source}
        else:
            source = {"type": "base64", "media_type": mime_type, "data": b64}
            content_block = {"type": "image", "source": source}

        response = await self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": [
                        content_block,
                        {"type": "text", "text": "Extract all invoice data from this document."},
                    ],
                }
            ],
        )

        raw_text = response.content[0].text
        # Strip markdown fences if present
        if raw_text.startswith("```"):
            raw_text = raw_text.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(raw_text)
