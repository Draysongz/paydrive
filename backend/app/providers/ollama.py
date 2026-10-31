import base64
import json

import httpx

from app.config import settings
from app.providers.base import BaseProvider

SYSTEM_PROMPT = """You are an invoice data extraction engine. Given an image of an invoice, extract all structured data and return ONLY valid JSON matching this exact schema:

{
  "invoice_id": "string",
  "vendor_name": "string",
  "issue_date": "string (YYYY-MM-DD) or null",
  "due_date": "string (YYYY-MM-DD) or null",
  "line_items": [{"description": "string", "quantity": number, "unit_price": number, "total": number}],
  "subtotal": number,
  "tax_amount": number,
  "total_amount": number,
  "currency": "string",
  "payment_route": {"rail": "paypal" or "web3", "recipient": "string"}
}

Return ONLY the JSON object, no explanation."""


class OllamaProvider(BaseProvider):
    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.model = settings.ollama_model

    async def extract_invoice(self, content: bytes, mime_type: str) -> dict:
        b64 = base64.standard_b64encode(content).decode("utf-8")

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": f"{SYSTEM_PROMPT}\n\nExtract all invoice data from this document image.",
                    "images": [b64],
                    "stream": False,
                },
            )
            response.raise_for_status()
            result = response.json()

        raw_text = result["response"]
        if raw_text.startswith("```"):
            raw_text = raw_text.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(raw_text)
