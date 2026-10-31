import base64
import json

import httpx

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


class GroqProvider(BaseProvider):
    """Groq provider using their OpenAI-compatible vision API."""

    def __init__(self):
        self.api_key = settings.groq_api_key
        self.model = settings.groq_model
        self.base_url = "https://api.groq.com/openai/v1"

    async def extract_invoice(self, content: bytes, mime_type: str) -> dict:
        # Groq vision only accepts images, not PDFs — convert if needed
        if mime_type == "application/pdf":
            import fitz
            doc = fitz.open(stream=content, filetype="pdf")
            page = doc[0]
            pix = page.get_pixmap(dpi=200)
            content = pix.tobytes("png")
            mime_type = "image/png"
            doc.close()

        b64 = base64.standard_b64encode(content).decode("utf-8")
        data_url = f"data:{mime_type};base64,{b64}"

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "max_tokens": 2048,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {
                            "role": "user",
                            "content": [
                                {"type": "image_url", "image_url": {"url": data_url}},
                                {"type": "text", "text": "Extract all invoice data from this document."},
                            ],
                        },
                    ],
                },
            )
            response.raise_for_status()
            result = response.json()

        raw_text = result["choices"][0]["message"]["content"]
        if raw_text.startswith("```"):
            raw_text = raw_text.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(raw_text)
