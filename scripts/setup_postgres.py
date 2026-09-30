import sys
import os
import asyncio
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.database.connection import engine, Base, AsyncSessionLocal
from src.database.models import PurchaseOrderDB, GoodsReceiptDB, CustomerInvoiceDB

async def setup_database():
    print("Connecting to Supabase PostgreSQL...")
    try:
        # Create all tables
        async with engine.begin() as conn:
            print("Creating tables (if they don't exist)...")
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
            print("Tables created successfully!")

        print("Seeding database with mock data...")
        async with AsyncSessionLocal() as session:
            # Seed AP Data
            po_1 = PurchaseOrderDB(
                po_number="PO-1001",
                vendor_id="VEND-001",
                expected_total=1000.0,
                line_items=[
                    {"item_id": "ITEM-A", "description": "Widget A", "quantity": 10.0, "unit_price": 100.0, "total_price": 1000.0}
                ]
            )
            po_2 = PurchaseOrderDB(
                po_number="PO-1002",
                vendor_id="VEND-002",
                expected_total=5000.0,
                line_items=[
                    {"item_id": "ITEM-B", "description": "Gadget B", "quantity": 5.0, "unit_price": 1000.0, "total_price": 5000.0}
                ]
            )
            gr_1 = GoodsReceiptDB(
                receipt_id="GR-9001",
                po_number="PO-1001",
                received_quantity=10.0,
                line_items=[
                    {"item_id": "ITEM-A", "description": "Widget A", "quantity": 10.0, "unit_price": 100.0, "total_price": 1000.0}
                ]
            )
            gr_2 = GoodsReceiptDB(
                receipt_id="GR-9002",
                po_number="PO-1002",
                received_quantity=5.0,
                line_items=[
                    {"item_id": "ITEM-B", "description": "Gadget B", "quantity": 5.0, "unit_price": 1000.0, "total_price": 5000.0}
                ]
            )

            # Seed AR Data
            inv_1 = CustomerInvoiceDB(
                invoice_number="INV-2001",
                customer_id="CUST-001",
                total_amount=5000.0,
                amount_paid=0.0,
                due_date="2026-08-01",
                status="UNPAID"
            )
            inv_2 = CustomerInvoiceDB(
                invoice_number="INV-2002",
                customer_id="CUST-001",
                total_amount=2000.0,
                amount_paid=0.0,
                due_date="2026-10-15",
                status="UNPAID"
            )
            inv_3 = CustomerInvoiceDB(
                invoice_number="INV-3001",
                customer_id="CUST-002",
                total_amount=1500.0,
                amount_paid=0.0,
                due_date="2026-09-30",
                status="UNPAID"
            )

            session.add_all([po_1, po_2, gr_1, gr_2, inv_1, inv_2, inv_3])
            
            # --- Load generated CSV data ---
            import csv
            import json
            
            data_dir = Path(__file__).parent.parent / "data"
            
            po_file = data_dir / "purchase_orders.csv"
            gr_file = data_dir / "goods_receipts.csv"
            inv_file = data_dir / "customer_invoices.csv"
            
            csv_records = []
            
            # 1. Load Purchase Orders
            if po_file.exists():
                with open(po_file, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # Skip hardcoded test records to prevent test breakage/PK conflicts
                        if row["po_number"] in ["PO-1001", "PO-1002"]: continue
                        csv_records.append(PurchaseOrderDB(
                            po_number=row["po_number"],
                            vendor_id=row["vendor_id"],
                            expected_total=float(row["expected_total"]),
                            line_items=json.loads(row["line_items"])
                        ))
            
            # 2. Load Goods Receipts
            if gr_file.exists():
                with open(gr_file, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row["po_number"] in ["PO-1001", "PO-1002"]: continue
                        csv_records.append(GoodsReceiptDB(
                            receipt_id=row["receipt_id"],
                            po_number=row["po_number"],
                            received_quantity=float(row["received_quantity"]),
                            line_items=json.loads(row["line_items"])
                        ))
                    
            # 3. Load Customer Invoices
            if inv_file.exists():
                with open(inv_file, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row["invoice_number"] in ["INV-2001", "INV-2002", "INV-3001"]: continue
                        csv_records.append(CustomerInvoiceDB(
                            invoice_number=row["invoice_number"],
                            customer_id=row["customer_id"],
                            total_amount=float(row["total_amount"]),
                            amount_paid=float(row["amount_paid"]),
                            due_date=row["due_date"],
                            status=row["status"]
                        ))

            session.add_all(csv_records)
            await session.commit()
            print(f"Successfully seeded 7 core test records and {len(csv_records)} CSV records into Supabase PostgreSQL!")

    except Exception as e:
        print(f"Error setting up database: {e}")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(setup_database())
