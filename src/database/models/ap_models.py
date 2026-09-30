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
