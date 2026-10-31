import logging

from app.providers import get_provider
from app.ingestion.parser import parse_file

logger = logging.getLogger(__name__)


async def extract_invoice_data(file_path: str) -> dict:
    """
    Parse a file and extract structured invoice data using the configured AI provider.
    Returns the structured invoice dict.
    """
    content, mime_type = parse_file(file_path)
    provider = get_provider()
    logger.info(f"Extracting invoice data from {file_path} using {provider.__class__.__name__}")
    data = await provider.extract_invoice(content, mime_type)
    logger.info(f"Extraction complete: invoice_id={data.get('invoice_id')}, vendor={data.get('vendor_name')}")
    return data
