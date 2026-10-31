import logging

logger = logging.getLogger(__name__)

TOLERANCE = 0.01  # Allow 1 cent rounding tolerance


def verify_math(invoice_data: dict) -> tuple[bool, str]:
    """
    Verify that line item totals sum correctly and match the invoice total.
    Returns (passed, message).
    """
    line_items = invoice_data.get("line_items", [])

    # Check each line item: quantity * unit_price == total
    for i, item in enumerate(line_items):
        expected = round(item["quantity"] * item["unit_price"], 2)
        actual = round(item["total"], 2)
        if abs(expected - actual) > TOLERANCE:
            msg = (
                f"Line item {i+1} math error: "
                f"{item['quantity']} × ${item['unit_price']:.2f} = ${expected:.2f}, "
                f"but invoice shows ${actual:.2f}"
            )
            logger.warning(msg)
            return False, msg

    # Check subtotal
    computed_subtotal = round(sum(item["total"] for item in line_items), 2)
    stated_subtotal = round(invoice_data.get("subtotal", 0), 2)
    if abs(computed_subtotal - stated_subtotal) > TOLERANCE:
        msg = f"Subtotal mismatch: computed ${computed_subtotal:.2f} vs stated ${stated_subtotal:.2f}"
        logger.warning(msg)
        return False, msg

    # Check total = subtotal + tax
    computed_total = round(stated_subtotal + invoice_data.get("tax_amount", 0), 2)
    stated_total = round(invoice_data.get("total_amount", 0), 2)
    if abs(computed_total - stated_total) > TOLERANCE:
        msg = f"Total mismatch: ${stated_subtotal:.2f} + ${invoice_data.get('tax_amount', 0):.2f} tax = ${computed_total:.2f}, but invoice shows ${stated_total:.2f}"
        logger.warning(msg)
        return False, msg

    logger.info(f"Math verification passed: ${stated_total:.2f}")
    return True, f"Math verified: ${stated_total:.2f}"
