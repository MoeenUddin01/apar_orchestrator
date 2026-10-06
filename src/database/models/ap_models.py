from sqlalchemy import Column, String, Float
from sqlalchemy.dialects.postgresql import JSONB
from src.database.connection import Base

class PurchaseOrderDB(Base):
    __tablename__ = "purchase_orders"
    po_number = Column(String, primary_key=True, index=True)
    vendor_id = Column(String, index=True, nullable=False)
    expected_total = Column(Float, nullable=False)
    line_items = Column(JSONB, default=[])

class GoodsReceiptDB(Base):
    __tablename__ = "goods_receipts"
    receipt_id = Column(String, primary_key=True, index=True)
    po_number = Column(String, index=True, nullable=False)
    received_quantity = Column(Float, nullable=False)
    line_items = Column(JSONB, default=[])

class InvoiceDB(Base):
    __tablename__ = "invoices"
    id = Column(String, primary_key=True, index=True)
    invoice_number = Column(String, index=True, nullable=False)
    vendor_id = Column(String, index=True, nullable=False)
    invoice_total = Column(Float, nullable=False)
    workflow_id = Column(String, index=True, nullable=False)
    status = Column(String, nullable=False, default="COMPLETED")
    created_at = Column(String, nullable=False)

