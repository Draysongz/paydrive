import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.events import event_bus
from app.approval.manager import approval_manager
from app.approval.notifier import send_webhook_notification
from app.db.engine import async_session
from app.db.models import AuditLog, Invoice, LineItem, Settlement, new_id
from app.ingestion.extractor import extract_invoice_data
from app.settlement.router import settlement_router
from app.verification.math_check import verify_math
from app.verification.duplicate_check import check_duplicate
from app.verification.budget_check import check_budget

logger = logging.getLogger(__name__)


async def log_audit(session: AsyncSession, invoice_id: str | None, event_type: str, message: str, details: dict | None = None):
    entry = AuditLog(id=new_id(), invoice_id=invoice_id, event_type=event_type, message=message, details=details)
    session.add(entry)
    await session.commit()
    await event_bus.emit(event_type, message, invoice_id=invoice_id, details=details)


async def process_invoice(file_path: str):
    """Full pipeline: parse → extract → verify → approve → settle."""
    filename = Path(file_path).name
    logger.info(f"Processing: {filename}")

    async with async_session() as session:
        # --- STAGE 1: DETECT ---
        await log_audit(session, None, "file_detected", f"New file: {filename}", {"path": file_path})

        # --- STAGE 2 & 3: PARSE + EXTRACT ---
        try:
            await event_bus.emit("parse_start", f"Parsing {filename}...")
            data = await extract_invoice_data(file_path)
            await log_audit(session, None, "parse_complete", f"Extracted invoice data from {filename}", data)
        except Exception as e:
            await log_audit(session, None, "error", f"Failed to parse {filename}: {e}")
            return

        # --- STAGE 4: VERIFY ---
        # Math check (runs on raw data, before DB insert)
        passed, msg = verify_math(data)
        await log_audit(session, None, "verification_passed" if passed else "verification_failed", msg)
        if not passed:
            return

        # Duplicate check (runs before DB insert to avoid self-match)
        is_dup, msg = await check_duplicate(session, data["vendor_name"], data["invoice_id"])
        if is_dup:
            await log_audit(session, None, "verification_failed", msg)
            return
        await log_audit(session, None, "verification_passed", msg)

        # --- Store in DB ---
        try:
            invoice = Invoice(
                id=new_id(),
                invoice_id=data["invoice_id"],
                vendor_name=data["vendor_name"],
                issue_date=data.get("issue_date"),
                due_date=data.get("due_date"),
                subtotal=data.get("subtotal", 0),
                tax_amount=data.get("tax_amount", 0),
                total_amount=data["total_amount"],
                currency=data.get("currency", "USD"),
                payment_rail=data["payment_route"]["rail"],
                recipient=data["payment_route"]["recipient"],
                source_file=filename,
                status="verified",
                raw_extraction=data,
            )
            session.add(invoice)

            for item in data.get("line_items", []):
                li = LineItem(
                    id=new_id(),
                    invoice_id=invoice.id,
                    description=item["description"],
                    quantity=item["quantity"],
                    unit_price=item["unit_price"],
                    total=item["total"],
                )
                session.add(li)

            await session.commit()
        except Exception as e:
            await session.rollback()
            await log_audit(session, None, "error", f"Failed to store invoice: {e}")
            return

        inv_id = invoice.id

        # Budget check
        passed, needs_approval, msg = await check_budget(session, data["vendor_name"], data["total_amount"])
        await log_audit(session, inv_id, "verification_passed", msg)

        invoice.status = "verified"
        await session.commit()

        # --- STAGE 5: APPROVE ---
        if needs_approval:
            invoice.status = "pending_approval"
            await session.commit()
            await log_audit(session, inv_id, "approval_requested", f"Awaiting human approval for {invoice.vendor_name} ${invoice.total_amount:.2f}")

            # Send webhook notification
            await send_webhook_notification(inv_id, invoice.vendor_name, invoice.total_amount, invoice.currency)

            # Block until approved/rejected
            approved = await approval_manager.request_approval(inv_id)

            if approved:
                invoice.status = "approved"
                await session.commit()
                await log_audit(session, inv_id, "approved", "Invoice approved by user")
            else:
                invoice.status = "rejected"
                await session.commit()
                await log_audit(session, inv_id, "rejected", "Invoice rejected or timed out")
                return
        else:
            invoice.status = "approved"
            await session.commit()
            await log_audit(session, inv_id, "approved", "Auto-approved by policy")

        # --- STAGE 6: SETTLE ---
        invoice.status = "settling"
        await session.commit()
        await log_audit(session, inv_id, "settlement_initiated", f"Settling via {invoice.payment_rail}")

        try:
            result = await settlement_router.settle(invoice)

            settlement = Settlement(
                id=new_id(),
                invoice_id=inv_id,
                rail=invoice.payment_rail,
                status=result["status"],
                provider_ref=result.get("provider_ref"),
                block_number=result.get("block_number"),
                amount=invoice.total_amount,
                currency=invoice.currency,
                extra_data=result.get("metadata"),
                completed_at=datetime.now(timezone.utc) if result["status"] == "completed" else None,
            )
            session.add(settlement)

            if result["status"] == "completed":
                invoice.status = "settled"
                await log_audit(session, inv_id, "settlement_completed",
                    f"Settled via {invoice.payment_rail}: {result.get('provider_ref', 'N/A')}",
                    result.get("metadata"))
            else:
                invoice.status = "settlement_failed"
                await log_audit(session, inv_id, "error", f"Settlement failed: {result}")

            await session.commit()

        except Exception as e:
            invoice.status = "settlement_failed"
            await session.commit()
            await log_audit(session, inv_id, "error", f"Settlement error: {e}")
            logger.exception(f"Settlement failed for {inv_id}")


async def agent_worker(queue: asyncio.Queue):
    """Worker that pulls files from the queue and processes them."""
    logger.info("Agent worker started")
    while True:
        file_path = await queue.get()
        try:
            await process_invoice(file_path)
        except Exception as e:
            logger.exception(f"Unhandled error processing {file_path}: {e}")
        finally:
            queue.task_done()
