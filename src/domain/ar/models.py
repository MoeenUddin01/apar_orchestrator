from datetime import date
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class ExtractedRemittance(BaseModel):
    """Structured remittance advice extracted from payment text/emails by LLM extraction boundary."""
    remittance_id: Optional[str] = "REM-UNKNOWN"
    customer_identifier: str
    referenced_invoices: List[str] = Field(default_factory=list)
    total_payment: float


class CustomerInvoice(BaseModel):
    """Customer invoice record retrieved from database representing outstanding receivable amounts."""
    invoice_number: str
    customer_id: str
    total_amount: float
    amount_paid: float = 0.0
    due_date: str  # YYYY-MM-DD format
    status: str = "UNPAID"


class ReconciliationResult(BaseModel):
    """Deterministic output of Accounts Receivable payment application and aging calculation."""
    applied_amount: float
    remaining_balance: float
    is_fully_paid: bool
    days_overdue: int
    aging_bucket: Literal["CURRENT", "30_DAYS", "60_DAYS", "90_DAYS_PLUS"]
    matched_invoices: List[str] = Field(default_factory=list)
