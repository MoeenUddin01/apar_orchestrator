from typing import Optional
from src.domain.ap.models import ExtractedInvoice, GoodsReceipt, MatchResult, PurchaseOrder


def perform_3_way_match(
    invoice: ExtractedInvoice,
    po: Optional[PurchaseOrder | dict],
    goods_receipt: Optional[GoodsReceipt | dict],
    tolerance_percentage: float = 0.05,
    tolerance_fixed: float = 10.0,
) -> MatchResult:
    """
    Pure deterministic Python 3-way matching logic.
    Compares Invoice, Purchase Order, and Goods Receipt.
    Calculates exact variances and tolerance thresholds.
    """
    if isinstance(po, dict):
        po = PurchaseOrder(**po)
    if isinstance(goods_receipt, dict):
        goods_receipt = GoodsReceipt(**goods_receipt)
    missing_docs = []
    if po is None:
        missing_docs.append("PURCHASE_ORDER")
    if goods_receipt is None:
        missing_docs.append("GOODS_RECEIPT")

    if missing_docs:
        return MatchResult(
            is_match=False,
            variance_amount=invoice.invoice_total,
            tolerance_exceeded=True,
            missing_documents=missing_docs,
            details={"error": "Missing required financial documents for 3-way match."},
        )

    # Calculate price variance against PO
    variance_amount = round(abs(invoice.invoice_total - po.expected_total), 2)
    
    # Allowed tolerance threshold
    allowed_tolerance = max(po.expected_total * tolerance_percentage, tolerance_fixed)
    tolerance_exceeded = variance_amount > allowed_tolerance

    # Quantity checking against Goods Receipt
    quantity_mismatch = False
    gr_quantity_total = sum(item.quantity for item in goods_receipt.line_items) if goods_receipt.line_items else goods_receipt.received_quantity
    invoice_quantity_total = sum(item.quantity for item in invoice.line_items) if invoice.line_items else 0.0
    
    if invoice.line_items and gr_quantity_total > 0:
        if abs(invoice_quantity_total - gr_quantity_total) > 0.01:
            quantity_mismatch = True

    is_match = (variance_amount == 0.0) and not quantity_mismatch and not tolerance_exceeded

    return MatchResult(
        is_match=is_match,
        variance_amount=variance_amount,
        tolerance_exceeded=tolerance_exceeded,
        missing_documents=[],
        details={
            "po_expected_total": po.expected_total,
            "invoice_total": invoice.invoice_total,
            "gr_quantity_total": gr_quantity_total,
            "invoice_quantity_total": invoice_quantity_total,
            "quantity_mismatch": quantity_mismatch,
            "allowed_tolerance": allowed_tolerance,
        },
    )
