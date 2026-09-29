import pytest
from src.domain.ap.models import ExtractedInvoice, GoodsReceipt, LineItem, PurchaseOrder
from src.finance.matching import perform_3_way_match


def test_perfect_3_way_match():
    invoice = ExtractedInvoice(
        invoice_number="INV-1001",
        vendor_id="VEND-001",
        po_number="PO-1001",
        invoice_total=1000.0,
        line_items=[LineItem(item_id="ITEM-A", quantity=10.0, unit_price=100.0, total_price=1000.0)],
    )
    po = PurchaseOrder(
        po_number="PO-1001",
        vendor_id="VEND-001",
        expected_total=1000.0,
        line_items=[LineItem(item_id="ITEM-A", quantity=10.0, unit_price=100.0, total_price=1000.0)],
    )
    gr = GoodsReceipt(
        receipt_id="GR-9001",
        po_number="PO-1001",
        received_quantity=10.0,
        line_items=[LineItem(item_id="ITEM-A", quantity=10.0, unit_price=100.0, total_price=1000.0)],
    )

    result = perform_3_way_match(invoice, po, gr)
    assert result.is_match is True
    assert result.variance_amount == 0.0
    assert result.tolerance_exceeded is False
    assert result.missing_documents == []


def test_missing_purchase_order():
    invoice = ExtractedInvoice(
        invoice_number="INV-1001",
        vendor_id="VEND-001",
        po_number="PO-MISSING",
        invoice_total=1000.0,
    )
    gr = GoodsReceipt(receipt_id="GR-9001", po_number="PO-MISSING", received_quantity=10.0)

    result = perform_3_way_match(invoice, po=None, goods_receipt=gr)
    assert result.is_match is False
    assert "PURCHASE_ORDER" in result.missing_documents
    assert result.tolerance_exceeded is True


def test_price_variance_within_tolerance():
    invoice = ExtractedInvoice(
        invoice_number="INV-1001",
        vendor_id="VEND-001",
        po_number="PO-1001",
        invoice_total=1005.0,  # 5 dollars variance on 1000 PO total (within default $10 tolerance)
    )
    po = PurchaseOrder(po_number="PO-1001", vendor_id="VEND-001", expected_total=1000.0)
    gr = GoodsReceipt(receipt_id="GR-9001", po_number="PO-1001", received_quantity=0.0)

    result = perform_3_way_match(invoice, po, gr)
    assert result.variance_amount == 5.0
    assert result.tolerance_exceeded is False
    assert result.is_match is False  # Small variance is not exact match, but tolerance is not exceeded


def test_tolerance_exceeded():
    invoice = ExtractedInvoice(
        invoice_number="INV-1001",
        vendor_id="VEND-001",
        po_number="PO-1001",
        invoice_total=1500.0,  # 500 dollars variance
    )
    po = PurchaseOrder(po_number="PO-1001", vendor_id="VEND-001", expected_total=1000.0)
    gr = GoodsReceipt(receipt_id="GR-9001", po_number="PO-1001", received_quantity=10.0)

    result = perform_3_way_match(invoice, po, gr)
    assert result.variance_amount == 500.0
    assert result.tolerance_exceeded is True
    assert result.is_match is False
