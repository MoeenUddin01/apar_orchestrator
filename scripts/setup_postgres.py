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
            
            # --- Generate 200 additional random records ---
            import random
            from datetime import timedelta, date

            generated_records = []
            
            # Generate 100 AP records (Purchase Orders & Goods Receipts)
            for i in range(10, 110):
                po_num = f"PO-{1000 + i}"
                vendor = f"VEND-{random.randint(10, 50):03d}"
                amount = round(random.uniform(500.0, 15000.0), 2)
                qty = float(random.randint(5, 100))
                unit_price = round(amount / qty, 2)
                
                # Re-adjust amount to perfectly match unit_price * qty
                amount = round(unit_price * qty, 2)

                line_items = [
                    {"item_id": f"ITEM-{random.randint(100, 999)}", "description": "Bulk Supplies", "quantity": qty, "unit_price": unit_price, "total_price": amount}
                ]

                # Create PO
                generated_records.append(PurchaseOrderDB(
                    po_number=po_num,
                    vendor_id=vendor,
                    expected_total=amount,
                    line_items=line_items
                ))

                # Create matching GR 90% of the time, 10% missing GR
                if random.random() > 0.1:
                    generated_records.append(GoodsReceiptDB(
                        receipt_id=f"GR-{9000 + i}",
                        po_number=po_num,
                        received_quantity=qty,
                        line_items=line_items
                    ))

            # Generate 100 AR records (Customer Invoices)
            today = date.today()
            statuses = ["UNPAID", "PAID", "PROCESSING"]
            
            for i in range(10, 110):
                inv_num = f"INV-{2000 + i}"
                cust = f"CUST-{random.randint(10, 50):03d}"
                total = round(random.uniform(200.0, 5000.0), 2)
                status = random.choices(statuses, weights=[0.6, 0.3, 0.1])[0]
                amount_paid = total if status == "PAID" else (round(total / 2, 2) if status == "PROCESSING" else 0.0)
                
                # Random due date between 30 days ago and 30 days from now
                offset = random.randint(-30, 30)
                due_date_str = (today + timedelta(days=offset)).isoformat()

                generated_records.append(CustomerInvoiceDB(
                    invoice_number=inv_num,
                    customer_id=cust,
                    total_amount=total,
                    amount_paid=amount_paid,
                    due_date=due_date_str,
                    status=status
                ))

            session.add_all(generated_records)
            await session.commit()
            print(f"Successfully seeded 7 core test records and {len(generated_records)} generated records into Supabase PostgreSQL!")

    except Exception as e:
        print(f"Error setting up database: {e}")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(setup_database())
