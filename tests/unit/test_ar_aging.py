from datetime import date
import pytest
from src.domain.ar.models import CustomerInvoice, ExtractedRemittance
from src.finance.aging import calculate_days_overdue, get_aging_bucket
from src.finance.matching import reconcile_ar_payment


def test_aging_calculation():
    current = date(2026, 9, 29)
    assert calculate_days_overdue("2026-09-30", current) == 0
    assert calculate_days_overdue("2026-09-29", current) == 0
    assert calculate_days_overdue("2026-08-30", current) == 30
    assert calculate_days_overdue("2026-06-30", current) == 91


def test_aging_bucket_categorization():
    assert get_aging_bucket(0) == "CURRENT"
    assert get_aging_bucket(15) == "30_DAYS"
    assert get_aging_bucket(45) == "60_DAYS"
    assert get_aging_bucket(90) == "90_DAYS_PLUS"


def test_full_payment_reconciliation():
    remittance = ExtractedRemittance(
        customer_identifier="CUST-001",
        referenced_invoices=["INV-2001"],
        total_payment=5000.0,
    )
    invoices = [
        CustomerInvoice(
            invoice_number="INV-2001",
            customer_id="CUST-001",
            total_amount=5000.0,
            amount_paid=0.0,
            due_date="2026-08-01",
        )
    ]

    result = reconcile_ar_payment(remittance, invoices, current_date=date(2026, 9, 29))
    assert result.applied_amount == 5000.0
    assert result.remaining_balance == 0.0
    assert result.is_fully_paid is True
    assert result.aging_bucket == "CURRENT"


def test_partial_overdue_reconciliation():
    remittance = ExtractedRemittance(
        customer_identifier="CUST-001",
        referenced_invoices=["INV-2001"],
        total_payment=2000.0,
    )
    invoices = [
        CustomerInvoice(
            invoice_number="INV-2001",
            customer_id="CUST-001",
            total_amount=5000.0,
            amount_paid=0.0,
            due_date="2026-08-01",  # Overdue by ~59 days
        )
    ]

    result = reconcile_ar_payment(remittance, invoices, current_date=date(2026, 9, 29))
    assert result.applied_amount == 2000.0
    assert result.remaining_balance == 3000.0
    assert result.is_fully_paid is False
    assert result.days_overdue == 59
    assert result.aging_bucket == "60_DAYS"
