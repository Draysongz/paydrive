"""Generate a sample PDF invoice for testing PayDrive AI."""
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import os

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "sample_invoices")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def create_invoice(filename, invoice_id, vendor, email, items, tax_rate=0.10):
    path = os.path.join(OUTPUT_DIR, filename)
    doc = SimpleDocTemplate(path, pagesize=letter, topMargin=0.5*inch)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("InvTitle", parent=styles["Title"], fontSize=24, textColor=colors.HexColor("#1a1a2e"))
    elements = []

    # Header
    elements.append(Paragraph(f"INVOICE", title_style))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"<b>Invoice #:</b> {invoice_id}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Vendor:</b> {vendor}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Date:</b> 2026-10-30", styles["Normal"]))
    elements.append(Paragraph(f"<b>Due Date:</b> 2026-11-15", styles["Normal"]))
    elements.append(Spacer(1, 8))
    elements.append(Paragraph(f"<b>Pay via PayPal to:</b> {email}", styles["Normal"]))
    elements.append(Spacer(1, 20))

    # Line items table
    subtotal = sum(qty * price for _, qty, price in items)
    tax = round(subtotal * tax_rate, 2)
    total = round(subtotal + tax, 2)

    table_data = [["Description", "Qty", "Unit Price", "Total"]]
    for desc, qty, price in items:
        table_data.append([desc, str(qty), f"${price:.2f}", f"${qty * price:.2f}"])

    table_data.append(["", "", "Subtotal:", f"${subtotal:.2f}"])
    table_data.append(["", "", f"Tax ({int(tax_rate*100)}%):", f"${tax:.2f}"])
    table_data.append(["", "", "TOTAL:", f"${total:.2f}"])

    table = Table(table_data, colWidths=[3*inch, 0.8*inch, 1.2*inch, 1.2*inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -4), 0.5, colors.grey),
        ("LINEABOVE", (2, -3), (-1, -3), 1, colors.black),
        ("FONTNAME", (2, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (2, -1), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(table)

    doc.build(elements)
    print(f"Created: {path}")
    return path


# Invoice 1: Small amount (should auto-approve, under $250)
create_invoice(
    "inv-001-small.pdf",
    "INV-2026-1001",
    "CloudSync Labs",
    "billing@cloudsync.io",
    [
        ("API Gateway Monthly", 1, 89.00),
        ("SSL Certificate Renewal", 1, 29.00),
    ],
    tax_rate=0.08,
)

# Invoice 2: Large amount (should require approval, over $250)
create_invoice(
    "inv-002-large.pdf",
    "INV-2026-8802",
    "Nexus Cloud Infrastructure",
    "payments@nexuscloud.io",
    [
        ("Dedicated Compute Node A1", 1, 320.00),
        ("Bandwidth Overage (TB)", 2, 40.00),
    ],
    tax_rate=0.10,
)

# Invoice 3: Another small one
create_invoice(
    "inv-003-supplies.pdf",
    "INV-2026-5543",
    "OfficeMax Pro",
    "accounts@officemax.io",
    [
        ("Printer Paper (ream)", 5, 12.00),
        ("Toner Cartridge", 1, 85.00),
        ("USB-C Hub", 2, 24.50),
    ],
    tax_rate=0.07,
)

print("\nSample invoices ready in sample_invoices/")
