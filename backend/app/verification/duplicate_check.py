import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Invoice

logger = logging.getLogger(__name__)


async def check_duplicate(session: AsyncSession, vendor_name: str, invoice_id: str) -> tuple[bool, str]:
    """
    Check if an invoice with the same vendor_name and invoice_id already exists.
    Returns (is_duplicate, message).
    """
    result = await session.execute(
        select(Invoice).where(
            Invoice.vendor_name == vendor_name,
            Invoice.invoice_id == invoice_id,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        msg = f"Duplicate invoice detected: {vendor_name} / {invoice_id} (existing record: {existing.id})"
        logger.warning(msg)
        return True, msg

    logger.info(f"No duplicate found for {vendor_name} / {invoice_id}")
    return False, f"No duplicate: {vendor_name} / {invoice_id}"
