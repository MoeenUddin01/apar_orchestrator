from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class LineItem(BaseModel):
    """Represents an individual line item on an invoice, purchase order, or goods receipt."""
    item_id: str
    description: Optional[str] = None
    quantity: float
    unit_price: float
    total_price: float


class ExtractedInvoice(BaseModel):
    """Structured invoice payload extracted from raw document text by the LLM extraction boundary."""
    invoice_number: str
    vendor_id: str
    po_number: str
    invoice_total: float
    line_items: List[LineItem] = Field(default_factory=list)


class PurchaseOrder(BaseModel):
    """Purchase Order record retrieved from the database representing expected order financial facts."""
    po_number: str
    vendor_id: str
    expected_total: float
    line_items: List[LineItem] = Field(default_factory=list)


class GoodsReceipt(BaseModel):
    """Goods Receipt record retrieved from the database confirming physical delivery quantities."""
    receipt_id: str
    po_number: str
    received_quantity: float
    line_items: List[LineItem] = Field(default_factory=list)


class MatchResult(BaseModel):
    """Deterministic output of the 3-way matching financial calculations."""
    is_match: bool
    variance_amount: float
    tolerance_exceeded: bool
    missing_documents: List[str] = Field(default_factory=list)
    details: Dict[str, Any] = Field(default_factory=dict)
