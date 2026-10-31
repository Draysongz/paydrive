import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    ForeignKey,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


def utcnow():
    return datetime.now(timezone.utc)


def new_id():
    return str(uuid.uuid4())


class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (UniqueConstraint("vendor_name", "invoice_id", name="uq_vendor_invoice"),)

    id = Column(String, primary_key=True, default=new_id)
    invoice_id = Column(String, nullable=False)
    vendor_name = Column(String, nullable=False)
    issue_date = Column(String, nullable=True)
    due_date = Column(String, nullable=True)
    subtotal = Column(Float, nullable=True)
    tax_amount = Column(Float, default=0.0)
    total_amount = Column(Float, nullable=False)
    currency = Column(String, default="USD")
    payment_rail = Column(String, nullable=False)  # paypal | web3
    recipient = Column(String, nullable=False)
    source_file = Column(String, nullable=False)
    status = Column(String, default="parsed")
    raw_extraction = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    line_items = relationship("LineItem", back_populates="invoice", cascade="all, delete-orphan")
    settlements = relationship("Settlement", back_populates="invoice", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="invoice", cascade="all, delete-orphan")


class LineItem(Base):
    __tablename__ = "line_items"

    id = Column(String, primary_key=True, default=new_id)
    invoice_id = Column(String, ForeignKey("invoices.id"), nullable=False)
    description = Column(Text, nullable=False)
    quantity = Column(Float, nullable=False)
    unit_price = Column(Float, nullable=False)
    total = Column(Float, nullable=False)

    invoice = relationship("Invoice", back_populates="line_items")


class Settlement(Base):
    __tablename__ = "settlements"

    id = Column(String, primary_key=True, default=new_id)
    invoice_id = Column(String, ForeignKey("invoices.id"), nullable=False)
    rail = Column(String, nullable=False)
    status = Column(String, default="initiated")
    provider_ref = Column(String, nullable=True)
    block_number = Column(Integer, nullable=True)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="USD")
    metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    completed_at = Column(DateTime, nullable=True)

    invoice = relationship("Invoice", back_populates="settlements")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=new_id)
    invoice_id = Column(String, ForeignKey("invoices.id"), nullable=True)
    event_type = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utcnow)
