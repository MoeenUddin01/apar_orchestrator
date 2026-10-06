import json
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent

def get_fixture_path(filename: str) -> Path:
    return FIXTURES_DIR / filename

def load_json_fixture(filename: str) -> dict:
    with open(get_fixture_path(filename), "r") as f:
        return json.load(f)

# Hardcoded test payloads for various scenarios

# AP: Perfect match
PERFECT_INVOICE_JSON = {
    "invoice_number": "INV-PERFECT",
    "vendor_id": "VEND-135",
    "po_number": "PO-1001",
    "invoice_total": 1200.0,
    "line_items": [
        {
            "item_id": "ITEM-102",
            "quantity": 6.0,
            "unit_price": 200.0,
            "total_price": 1200.0
        }
    ]
}

# AP: Tolerance Exceeded
TOLERANCE_EXCEEDED_INVOICE_JSON = {
    "invoice_number": "INV-TOL",
    "vendor_id": "VEND-135",
    "po_number": "PO-1001",
    "invoice_total": 1500.0,  # Expected 1200.0
    "line_items": [
        {
            "item_id": "ITEM-102",
            "quantity": 6.0,
            "unit_price": 250.0,
            "total_price": 1500.0
        }
    ]
}

# AP: High Value
HIGH_VALUE_INVOICE_JSON = {
    "invoice_number": "INV-HIGH",
    "vendor_id": "VEND-134",
    "po_number": "PO-1012",
    "invoice_total": 50000.0,
    "line_items": [
        {
            "item_id": "ITEM-110",
            "quantity": 100.0,
            "unit_price": 500.0,
            "total_price": 50000.0
        }
    ]
}

# AR: Full Payment
FULL_PAYMENT_REMITTANCE_JSON = {
    "remittance_id": "REM-FULL",
    "customer_identifier": "CUST-001",
    "total_payment": 5000.0,
    "referenced_invoices": ["INV-2001"]
}

# AR: Partial Payment
PARTIAL_PAYMENT_REMITTANCE_JSON = {
    "remittance_id": "REM-PART",
    "customer_identifier": "CUST-001",
    "total_payment": 1000.0,
    "referenced_invoices": ["INV-2002"]
}

def write_fixtures():
    with open(get_fixture_path("perfect_invoice.json"), "w") as f:
        json.dump(PERFECT_INVOICE_JSON, f, indent=2)
    with open(get_fixture_path("tolerance_exceeded_invoice.json"), "w") as f:
        json.dump(TOLERANCE_EXCEEDED_INVOICE_JSON, f, indent=2)
    with open(get_fixture_path("full_payment_remittance.json"), "w") as f:
        json.dump(FULL_PAYMENT_REMITTANCE_JSON, f, indent=2)

if __name__ == "__main__":
    write_fixtures()
