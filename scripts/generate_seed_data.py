import csv
import json
import random
from datetime import date, timedelta
from pathlib import Path

# Base execution date: September 30, 2026
BASE_DATE = date(2026, 9, 30)

ITEMS_CATALOG = [
    ("ITEM-101", "Standard Laptop Dock", 150.0),
    ("ITEM-102", "Ergonomic Office Chair", 200.0),
    ("ITEM-103", "Wireless Keyboard & Mouse Combo", 50.0),
    ("ITEM-104", "Enterprise Rack Server R740", 15000.0),
    ("ITEM-105", "27-Inch 4K UHD Monitor", 250.0),
    ("ITEM-106", "Cat6 Ethernet Spool 1000ft", 120.0),
    ("ITEM-107", "Gigabit Managed Switch 24-Port", 450.0),
    ("ITEM-108", "Noise Cancelling Headset", 85.0),
    ("ITEM-109", "Solid State Drive 2TB NVMe", 180.0),
    ("ITEM-110", "Standing Desk Frame Motorized", 400.0),
]


def generate_datasets(output_dir: Path = Path(".")):
    output_dir.mkdir(parents=True, exist_ok=True)

    po_rows = []
    gr_rows = []
    ar_rows = []

    # ---------------------------------------------------------
    # 1. GENERATE 100 PURCHASE ORDERS & GOODS RECEIPTS
    # ---------------------------------------------------------
    for i in range(1, 101):
        po_number = f"PO-{1000 + i}"
        vendor_id = f"VEND-{random.randint(101, 140)}"

        # Scenario distribution:
        # Rows 1-60: Standard Perfect Matches
        # Rows 61-75: Quantity Mismatches (receipt < PO)
        # Rows 76-85: Price Tolerance Mismatches
        # Rows 86-92: High-Value Approvals (> $50,000)
        # Rows 93-100: Missing Goods Receipts (no GR entry)

        if 86 <= i <= 92:
            # High-Value Approval Scenario
            item_id, desc, unit_price = ("ITEM-104", "Enterprise Rack Server R740", 15000.0)
            qty = float(random.randint(4, 8))  # $60,000 to $120,000
        else:
            item_id, desc, unit_price = random.choice(
                [it for it in ITEMS_CATALOG if it[0] != "ITEM-104"]
            )
            qty = float(random.randint(5, 40))

        total_price = round(qty * unit_price, 2)
        line_items = [
            {
                "item_id": item_id,
                "description": desc,
                "quantity": qty,
                "unit_price": unit_price,
                "total_price": total_price,
            }
        ]

        po_rows.append(
            {
                "po_number": po_number,
                "vendor_id": vendor_id,
                "expected_total": f"{total_price:.2f}",
                "line_items": json.dumps(line_items),
            }
        )

        # Goods Receipts Generation
        if i >= 93:
            # Scenario: Missing Goods Receipt
            continue

        receipt_id = f"GR-{9000 + i}"
        if 61 <= i <= 75:
            # Scenario: Quantity Mismatch (Short shipment)
            received_qty = float(max(1, int(qty - random.randint(2, 5))))
        else:
            # Perfect receipt
            received_qty = qty

        gr_line_items = [
            {
                "item_id": item_id,
                "description": desc,
                "quantity": received_qty,
                "unit_price": unit_price,
                "total_price": round(received_qty * unit_price, 2),
            }
        ]

        gr_rows.append(
            {
                "receipt_id": receipt_id,
                "po_number": po_number,
                "received_quantity": received_qty,
                "line_items": json.dumps(gr_line_items),
            }
        )

    # ---------------------------------------------------------
    # 2. GENERATE 100 CUSTOMER INVOICES (AR)
    # ---------------------------------------------------------
    for i in range(1, 101):
        invoice_number = f"INV-{2000 + i}"
        customer_id = f"CUST-{random.randint(201, 250)}"
        total_amount = round(random.uniform(500.0, 15000.0), 2)

        # Scenario distribution:
        # Rows 1-30: CURRENT (due_date in the future)
        # Rows 31-60: 30_DAYS overdue (1 to 30 days past)
        # Rows 61-80: 60_DAYS overdue (31 to 60 days past)
        # Rows 81-92: 90_DAYS_PLUS overdue (> 60 days past)
        # Rows 93-100: PAID (fully settled)

        if 1 <= i <= 30:
            due_date = BASE_DATE + timedelta(days=random.randint(5, 30))
            status = random.choice(["UNPAID", "PROCESSING"])
            amount_paid = 0.0 if status == "UNPAID" else round(total_amount * 0.4, 2)
        elif 31 <= i <= 60:
            due_date = BASE_DATE - timedelta(days=random.randint(1, 30))
            status = random.choice(["UNPAID", "PROCESSING"])
            amount_paid = 0.0 if status == "UNPAID" else round(total_amount * 0.5, 2)
        elif 61 <= i <= 80:
            due_date = BASE_DATE - timedelta(days=random.randint(31, 60))
            status = "UNPAID"
            amount_paid = 0.0
        elif 81 <= i <= 92:
            due_date = BASE_DATE - timedelta(days=random.randint(61, 120))
            status = "UNPAID"
            amount_paid = 0.0
        else:
            due_date = BASE_DATE - timedelta(days=random.randint(10, 45))
            status = "PAID"
            amount_paid = total_amount

        ar_rows.append(
            {
                "invoice_number": invoice_number,
                "customer_id": customer_id,
                "total_amount": f"{total_amount:.2f}",
                "amount_paid": f"{amount_paid:.2f}",
                "due_date": due_date.strftime("%Y-%m-%d"),
                "status": status,
            }
        )

    # ---------------------------------------------------------
    # 3. WRITE CSV FILES
    # ---------------------------------------------------------
    po_file = output_dir / "purchase_orders.csv"
    with open(po_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["po_number", "vendor_id", "expected_total", "line_items"]
        )
        writer.writeheader()
        writer.writerows(po_rows)

    gr_file = output_dir / "goods_receipts.csv"
    with open(gr_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["receipt_id", "po_number", "received_quantity", "line_items"]
        )
        writer.writeheader()
        writer.writerows(gr_rows)

    ar_file = output_dir / "customer_invoices.csv"
    with open(ar_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "invoice_number",
                "customer_id",
                "total_amount",
                "amount_paid",
                "due_date",
                "status",
            ],
        )
        writer.writeheader()
        writer.writerows(ar_rows)

    print(f"Generated {len(po_rows)} rows in {po_file}")
    print(f"Generated {len(gr_rows)} rows in {gr_file}")
    print(f"Generated {len(ar_rows)} rows in {ar_file}")


if __name__ == "__main__":
    generate_datasets(Path("data"))