import logging

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import Invoice

logger = logging.getLogger(__name__)


async def check_budget(
    session: AsyncSession, vendor_name: str, total_amount: float
) -> tuple[bool, bool, str]:
    """
    Evaluate budget policy for an invoice.
    Returns (passed, requires_approval, message).

    Rules:
    - If total > auto_approve_limit → requires human approval
    - If vendor is new (no prior settled invoices) → requires human approval
    - Otherwise → auto-approved
    """
    requires_approval = False
    reasons = []

    # Check amount threshold
    if total_amount > settings.auto_approve_limit:
        requires_approval = True
        reasons.append(f"Amount ${total_amount:.2f} exceeds auto-approve limit ${settings.auto_approve_limit:.2f}")

    # Check if vendor is known (has at least one previously settled invoice)
    result = await session.execute(
        select(func.count()).select_from(Invoice).where(
            Invoice.vendor_name == vendor_name,
            Invoice.status == "settled",
        )
    )
    settled_count = result.scalar()
    if settled_count == 0:
        requires_approval = True
        reasons.append(f"New vendor: '{vendor_name}' has no prior settled invoices")

    if requires_approval:
        msg = "Approval required: " + "; ".join(reasons)
        logger.info(msg)
        return True, True, msg
    else:
        msg = f"Auto-approved: ${total_amount:.2f} from known vendor '{vendor_name}'"
        logger.info(msg)
        return True, False, msg
