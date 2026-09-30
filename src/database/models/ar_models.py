from sqlalchemy import Column, String, Float
from src.database.connection import Base

class CustomerInvoiceDB(Base):
    __tablename__ = "customer_invoices"
    invoice_number = Column(String, primary_key=True, index=True)
    customer_id = Column(String, index=True, nullable=False)
    total_amount = Column(Float, nullable=False)
    amount_paid = Column(Float, default=0.0)
    due_date = Column(String, nullable=False)
    status = Column(String, default="UNPAID")
