from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class LineItem(BaseModel):
    item_id: str
    description: Optional[str] = None
    quantity: float
    unit_price: float
    total_price: float


class ExtractedInvoice(BaseModel):
    invoice_number: str
    vendor_id: str
    po_number: str
    invoice_total: float
    line_items: List[LineItem] = Field(default_factory=list)


class PurchaseOrder(BaseModel):
    po_number: str
    vendor_id: str
    expected_total: float
    line_items: List[LineItem] = Field(default_factory=list)


class GoodsReceipt(BaseModel):
    receipt_id: str
    po_number: str
    received_quantity: float
    line_items: List[LineItem] = Field(default_factory=list)


class MatchResult(BaseModel):
    is_match: bool
    variance_amount: float
    tolerance_exceeded: bool
    missing_documents: List[str] = Field(default_factory=list)
    details: Dict[str, Any] = Field(default_factory=dict)
