from datetime import date
from typing import List, Optional
from src.domain.ap.models import ExtractedInvoice, GoodsReceipt, MatchResult, PurchaseOrder
from src.domain.ar.models import CustomerInvoice, ExtractedRemittance, ReconciliationResult
from src.finance.aging import calculate_days_overdue, get_aging_bucket


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


def reconcile_ar_payment(
    remittance: ExtractedRemittance,
    invoices: List[CustomerInvoice],
    current_date: Optional[date] = None,
) -> ReconciliationResult:
    """
    Pure deterministic Python logic to apply remittance payments to unpaid customer invoices,
    calculate outstanding balances, and determine aging buckets.
    """
    payment_pool = round(remittance.total_payment, 2)
    total_applied = 0.0
    matched_invoice_numbers = []
    max_days_overdue = 0

    # Filter target invoices if referenced in remittance, else reconcile against all customer invoices
    target_invoices = [
        inv for inv in invoices
        if not remittance.referenced_invoices or inv.invoice_number in remittance.referenced_invoices
    ]
    if not target_invoices:
        target_invoices = invoices

    for inv in target_invoices:
        unpaid_amount = round(inv.total_amount - inv.amount_paid, 2)
        if unpaid_amount <= 0:
            continue

        applied = min(payment_pool, unpaid_amount)
        payment_pool = round(payment_pool - applied, 2)
        total_applied = round(total_applied + applied, 2)
        matched_invoice_numbers.append(inv.invoice_number)

        # Check aging on remaining balance
        rem_inv_balance = unpaid_amount - applied
        if rem_inv_balance > 0:
            days = calculate_days_overdue(inv.due_date, current_date)
            if days > max_days_overdue:
                max_days_overdue = days

        if payment_pool <= 0:
            break

    total_owed = sum(round(inv.total_amount - inv.amount_paid, 2) for inv in target_invoices)
    remaining_balance = max(0.0, round(total_owed - total_applied, 2))
    is_fully_paid = remaining_balance == 0.0 and total_owed > 0

    aging_bucket = get_aging_bucket(max_days_overdue if remaining_balance > 0 else 0)

    return ReconciliationResult(
        applied_amount=total_applied,
        remaining_balance=remaining_balance,
        is_fully_paid=is_fully_paid,
        days_overdue=max_days_overdue if remaining_balance > 0 else 0,
        aging_bucket=aging_bucket,
        matched_invoices=matched_invoice_numbers,
    )
