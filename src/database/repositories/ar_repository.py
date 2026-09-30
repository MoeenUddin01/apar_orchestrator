from typing import List, Optional
from sqlalchemy import select
from src.database.connection import AsyncSessionLocal
from src.database.models.ar_models import CustomerInvoiceDB
from src.domain.ar.models import CustomerInvoice


class ARRepository:
    """Repository for Accounts Receivable customer invoice database lookups."""

    async def get_customer_invoices(self, customer_identifier: str) -> List[CustomerInvoice]:
        """Retrieve all unpaid or open customer invoices for a specific customer identifier from PostgreSQL."""
        async with AsyncSessionLocal() as session:
            stmt = select(CustomerInvoiceDB).where(CustomerInvoiceDB.customer_id == customer_identifier)
            result = await session.execute(stmt)
            db_invoices = result.scalars().all()
            
            return [
                CustomerInvoice(
                    invoice_number=inv.invoice_number,
                    customer_id=inv.customer_id,
                    total_amount=inv.total_amount,
                    amount_paid=inv.amount_paid,
                    due_date=inv.due_date,
                    status=inv.status
                )
                for inv in db_invoices
            ]

    async def get_invoice_by_number(self, invoice_number: str) -> Optional[CustomerInvoice]:
        """Look up a specific customer invoice by invoice number from PostgreSQL."""
        async with AsyncSessionLocal() as session:
            stmt = select(CustomerInvoiceDB).where(CustomerInvoiceDB.invoice_number == invoice_number)
            result = await session.execute(stmt)
            inv = result.scalar_one_or_none()
            
            if inv:
                return CustomerInvoice(
                    invoice_number=inv.invoice_number,
                    customer_id=inv.customer_id,
                    total_amount=inv.total_amount,
                    amount_paid=inv.amount_paid,
                    due_date=inv.due_date,
                    status=inv.status
                )
            return None


ar_repository = ARRepository()
