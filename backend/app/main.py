import asyncio
import logging

from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sse_starlette.sse import EventSourceResponse

from app.config import settings
from app.db.engine import init_db, get_session
from app.db.models import Invoice, LineItem, Settlement, AuditLog
from app.agent.engine import agent_worker
from app.agent.events import event_bus
from app.approval.manager import approval_manager
from app.ingestion.watcher import start_watcher

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

file_queue: asyncio.Queue = asyncio.Queue()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    logger.info("Database initialized")

    loop = asyncio.get_event_loop()
    observer = start_watcher(file_queue, loop)

    worker_task = asyncio.create_task(agent_worker(file_queue))

    yield

    # Shutdown
    observer.stop()
    observer.join()
    worker_task.cancel()


app = FastAPI(title="PayDrive AI", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- SSE Endpoint ---

@app.get("/api/events")
async def event_stream():
    queue = event_bus.subscribe()

    async def stream():
        try:
            while True:
                data = await queue.get()
                yield {"event": "agent_event", "data": data}
        except asyncio.CancelledError:
            event_bus.unsubscribe(queue)

    return EventSourceResponse(stream())


# --- Invoice Endpoints ---

class InvoiceResponse(BaseModel):
    id: str
    invoice_id: str
    vendor_name: str
    issue_date: str | None
    due_date: str | None
    subtotal: float | None
    tax_amount: float
    total_amount: float
    currency: str
    payment_rail: str
    recipient: str
    source_file: str
    status: str
    created_at: str
    line_items: list[dict] = []
    settlements: list[dict] = []

    model_config = {"from_attributes": True}


@app.get("/api/invoices")
async def list_invoices(session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Invoice)
        .options(selectinload(Invoice.line_items), selectinload(Invoice.settlements))
        .order_by(desc(Invoice.created_at))
    )
    invoices = result.scalars().all()
    return [_invoice_to_dict(inv) for inv in invoices]


@app.get("/api/invoices/{invoice_id}")
async def get_invoice(invoice_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Invoice)
        .options(selectinload(Invoice.line_items), selectinload(Invoice.settlements))
        .where(Invoice.id == invoice_id)
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return _invoice_to_dict(invoice)


@app.post("/api/invoices/{invoice_id}/approve")
async def approve_invoice(invoice_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if invoice.status != "pending_approval":
        raise HTTPException(status_code=400, detail=f"Invoice status is '{invoice.status}', not pending_approval")
    approval_manager.approve(invoice_id)
    return {"status": "approved", "invoice_id": invoice_id}


@app.post("/api/invoices/{invoice_id}/reject")
async def reject_invoice(invoice_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if invoice.status != "pending_approval":
        raise HTTPException(status_code=400, detail=f"Invoice status is '{invoice.status}', not pending_approval")
    approval_manager.reject(invoice_id)
    return {"status": "rejected", "invoice_id": invoice_id}


# --- Audit Log Endpoint ---

@app.get("/api/audit-logs")
async def list_audit_logs(invoice_id: str | None = None, session: AsyncSession = Depends(get_session)):
    query = select(AuditLog).order_by(desc(AuditLog.created_at))
    if invoice_id:
        query = query.where(AuditLog.invoice_id == invoice_id)
    result = await session.execute(query.limit(200))
    logs = result.scalars().all()
    return [
        {
            "id": log.id,
            "invoice_id": log.invoice_id,
            "event_type": log.event_type,
            "message": log.message,
            "details": log.details,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]


# --- Pending Approvals ---

@app.get("/api/approvals/pending")
async def pending_approvals():
    return {"pending": approval_manager.get_pending()}


# --- Health ---

@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


# --- Manual file trigger (for testing) ---

class FileSubmission(BaseModel):
    file_path: str


@app.post("/api/ingest")
async def manual_ingest(submission: FileSubmission):
    file_queue.put_nowait(submission.file_path)
    return {"status": "queued", "file": submission.file_path}


# --- Helpers ---

def _invoice_to_dict(inv: Invoice) -> dict:
    return {
        "id": inv.id,
        "invoice_id": inv.invoice_id,
        "vendor_name": inv.vendor_name,
        "issue_date": inv.issue_date,
        "due_date": inv.due_date,
        "subtotal": inv.subtotal,
        "tax_amount": inv.tax_amount,
        "total_amount": inv.total_amount,
        "currency": inv.currency,
        "payment_rail": inv.payment_rail,
        "recipient": inv.recipient,
        "source_file": inv.source_file,
        "status": inv.status,
        "created_at": inv.created_at.isoformat() if inv.created_at else None,
        "line_items": [
            {
                "id": li.id,
                "description": li.description,
                "quantity": li.quantity,
                "unit_price": li.unit_price,
                "total": li.total,
            }
            for li in inv.line_items
        ],
        "settlements": [
            {
                "id": s.id,
                "rail": s.rail,
                "status": s.status,
                "provider_ref": s.provider_ref,
                "block_number": s.block_number,
                "amount": s.amount,
                "currency": s.currency,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "completed_at": s.completed_at.isoformat() if s.completed_at else None,
            }
            for s in inv.settlements
        ],
    }
