from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from src.database.connection import AsyncSessionLocal
from src.database.models.ap_models import PurchaseOrderDB, GoodsReceiptDB, InvoiceDB
from src.domain.ap.models import GoodsReceipt, LineItem, PurchaseOrder


class APRepository:
    """Repository for AP Purchase Orders, Goods Receipts, and Invoices database operations."""

    def __init__(self):
        self._in_memory_invoices: List[Dict[str, Any]] = []

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

    async def save_invoice(self, invoice_data: Dict[str, Any]) -> bool:
        """
        Persists a successfully processed AP invoice.
        Prevents duplicate persistence of the same workflow transaction.
        """
        workflow_id = invoice_data.get("workflow_id", "")
        invoice_number = invoice_data.get("invoice_number", "")
        vendor_id = invoice_data.get("vendor_id", "")
        invoice_total = float(invoice_data.get("invoice_total") or invoice_data.get("amount") or 0.0)
        status = invoice_data.get("status", "COMPLETED")
        created_at = invoice_data.get("created_at") or datetime.now(timezone.utc).isoformat()

        if not invoice_number or not vendor_id:
            return False

        # Check in-memory for duplicate workflow_id
        for existing in self._in_memory_invoices:
            if existing.get("workflow_id") == workflow_id and workflow_id:
                return False

        record_id = workflow_id if workflow_id else f"{vendor_id}-{invoice_number}-{datetime.now(timezone.utc).timestamp()}"

        record_dict = {
            "id": record_id,
            "invoice_number": invoice_number,
            "vendor_id": vendor_id,
            "invoice_total": invoice_total,
            "amount": invoice_total,
            "workflow_id": workflow_id,
            "status": status,
            "created_at": created_at,
        }

        self._in_memory_invoices.append(record_dict)

        try:
            async with AsyncSessionLocal() as session:
                # Check DB for duplicate workflow_id
                if workflow_id:
                    stmt = select(InvoiceDB).where(InvoiceDB.workflow_id == workflow_id)
                    existing_db = (await session.execute(stmt)).scalar_one_or_none()
                    if existing_db:
                        return False

                db_record = InvoiceDB(
                    id=record_id,
                    invoice_number=invoice_number,
                    vendor_id=vendor_id,
                    invoice_total=invoice_total,
                    workflow_id=workflow_id,
                    status=status,
                    created_at=created_at,
                )
                session.add(db_record)
                await session.commit()
        except Exception:
            # Fallback to in-memory store if DB is unavailable or uninitialized
            pass

        return True

    async def get_historical_invoices_by_vendor(self, vendor_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves historical processed invoices for a vendor from PostgreSQL and in-memory store.
        """
        if not vendor_id:
            return []

        norm_vendor = str(vendor_id).strip().upper()
        results_map: Dict[str, Dict[str, Any]] = {}

        # 1. Query PostgreSQL DB
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(InvoiceDB).where(InvoiceDB.vendor_id == vendor_id)
                db_invoices = (await session.execute(stmt)).scalars().all()
                for inv in db_invoices:
                    key = inv.id or f"{inv.vendor_id}-{inv.invoice_number}"
                    results_map[key] = {
                        "id": inv.id,
                        "invoice_number": inv.invoice_number,
                        "vendor_id": inv.vendor_id,
                        "invoice_total": inv.invoice_total,
                        "amount": inv.invoice_total,
                        "workflow_id": inv.workflow_id,
                        "status": inv.status,
                        "created_at": inv.created_at,
                    }
        except Exception:
            pass

        # 2. Add in-memory invoices
        for inv in self._in_memory_invoices:
            if str(inv.get("vendor_id", "")).strip().upper() == norm_vendor:
                key = inv.get("id") or f"{inv.get('vendor_id')}-{inv.get('invoice_number')}"
                if key not in results_map:
                    results_map[key] = dict(inv)

        return list(results_map.values())

    def clear(self):
        """Clears in-memory invoices (useful for test isolation)."""
        self._in_memory_invoices.clear()


ap_repository = APRepository()

