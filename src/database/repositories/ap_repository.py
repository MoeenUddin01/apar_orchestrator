from typing import Optional
from sqlalchemy import select
from src.database.connection import AsyncSessionLocal
from src.database.models.ap_models import PurchaseOrderDB, GoodsReceiptDB
from src.domain.ap.models import GoodsReceipt, LineItem, PurchaseOrder


class APRepository:
    """Repository for AP Purchase Orders and Goods Receipts database lookups."""

    async def get_purchase_order(self, po_number: str) -> Optional[PurchaseOrder]:
        """Fetch a Purchase Order by purchase order number from PostgreSQL."""
        async with AsyncSessionLocal() as session:
            stmt = select(PurchaseOrderDB).where(PurchaseOrderDB.po_number == po_number)
            result = await session.execute(stmt)
            db_po = result.scalar_one_or_none()
            
            if db_po:
                line_items = [LineItem(**item) for item in db_po.line_items]
                return PurchaseOrder(
                    po_number=db_po.po_number,
                    vendor_id=db_po.vendor_id,
                    expected_total=db_po.expected_total,
                    line_items=line_items
                )
            return None

    async def get_goods_receipt(self, po_number: str) -> Optional[GoodsReceipt]:
        """Fetch a Goods Receipt associated with a purchase order number from PostgreSQL."""
        async with AsyncSessionLocal() as session:
            stmt = select(GoodsReceiptDB).where(GoodsReceiptDB.po_number == po_number)
            result = await session.execute(stmt)
            db_gr = result.scalar_one_or_none()
            
            if db_gr:
                line_items = [LineItem(**item) for item in db_gr.line_items]
                return GoodsReceipt(
                    receipt_id=db_gr.receipt_id,
                    po_number=db_gr.po_number,
                    received_quantity=db_gr.received_quantity,
                    line_items=line_items
                )
            return None


ap_repository = APRepository()
