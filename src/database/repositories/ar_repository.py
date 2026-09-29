from typing import Dict, List, Optional
from src.domain.ar.models import CustomerInvoice

# Mock repository dataset for AR Customer Invoices
MOCK_INVOICE_DATABASE: Dict[str, List[CustomerInvoice]] = {
    "CUST-001": [
        CustomerInvoice(
            invoice_number="INV-2001",
            customer_id="CUST-001",
            total_amount=5000.0,
            amount_paid=0.0,
            due_date="2026-08-01",  # Overdue
            status="UNPAID",
        ),
        CustomerInvoice(
            invoice_number="INV-2002",
            customer_id="CUST-001",
            total_amount=2000.0,
            amount_paid=0.0,
            due_date="2026-10-15",  # Current
            status="UNPAID",
        ),
    ],
    "CUST-002": [
        CustomerInvoice(
            invoice_number="INV-3001",
            customer_id="CUST-002",
            total_amount=1500.0,
            amount_paid=0.0,
            due_date="2026-09-30",
            status="UNPAID",
        ),
    ],
}


class ARRepository:
    """Repository for Accounts Receivable customer invoice database lookups."""

    async def get_customer_invoices(self, customer_identifier: str) -> List[CustomerInvoice]:
        """Retrieve all unpaid or open customer invoices for a specific customer identifier."""
        return MOCK_INVOICE_DATABASE.get(customer_identifier, [])

    async def get_invoice_by_number(self, invoice_number: str) -> Optional[CustomerInvoice]:
        """Look up a specific customer invoice by invoice number."""
        for inv_list in MOCK_INVOICE_DATABASE.values():
            for inv in inv_list:
                if inv.invoice_number == invoice_number:
                    return inv
        return None


ar_repository = ARRepository()
