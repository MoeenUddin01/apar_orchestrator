from typing import Dict, Optional
from src.domain.ap.models import GoodsReceipt, LineItem, PurchaseOrder

# Mock repository dataset for initial database lookups
MOCK_PO_DATABASE: Dict[str, PurchaseOrder] = {
    "PO-1001": PurchaseOrder(
        po_number="PO-1001",
        vendor_id="VEND-001",
        expected_total=1000.0,
        line_items=[
            LineItem(item_id="ITEM-A", description="Widget A", quantity=10.0, unit_price=100.0, total_price=1000.0)
        ],
    ),
    "PO-1002": PurchaseOrder(
        po_number="PO-1002",
        vendor_id="VEND-002",
        expected_total=5000.0,
        line_items=[
            LineItem(item_id="ITEM-B", description="Gadget B", quantity=5.0, unit_price=1000.0, total_price=5000.0)
        ],
    ),
}

MOCK_GR_DATABASE: Dict[str, GoodsReceipt] = {
    "PO-1001": GoodsReceipt(
        receipt_id="GR-9001",
        po_number="PO-1001",
        received_quantity=10.0,
        line_items=[
            LineItem(item_id="ITEM-A", description="Widget A", quantity=10.0, unit_price=100.0, total_price=1000.0)
        ],
    ),
    "PO-1002": GoodsReceipt(
        receipt_id="GR-9002",
        po_number="PO-1002",
        received_quantity=5.0,
        line_items=[
            LineItem(item_id="ITEM-B", description="Gadget B", quantity=5.0, unit_price=1000.0, total_price=5000.0)
        ],
    ),
}


class APRepository:
    """Repository for AP Purchase Orders and Goods Receipts database lookups."""

    async def get_purchase_order(self, po_number: str) -> Optional[PurchaseOrder]:
        """Fetch a Purchase Order by purchase order number."""
        return MOCK_PO_DATABASE.get(po_number)

    async def get_goods_receipt(self, po_number: str) -> Optional[GoodsReceipt]:
        """Fetch a Goods Receipt associated with a purchase order number."""
        return MOCK_GR_DATABASE.get(po_number)


ap_repository = APRepository()
