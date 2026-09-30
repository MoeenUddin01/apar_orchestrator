import json
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.database.repositories.ap_repository import MOCK_PO_DATABASE, MOCK_GR_DATABASE
from src.database.repositories.ar_repository import MOCK_INVOICE_DATABASE

def seed_database():
    """
    Since the application currently relies on mock databases for the MVP, 
    this seeding script outputs the deterministic state of the database into the 
    tests/fixtures directory to simulate a 'pre-loaded' PostgreSQL state.
    
    When SQLAlchemy models are implemented, this script will be updated to 
    insert these records directly into the Postgres tables.
    """
    print("--- Seeding Database (Mock Layer) ---")
    
    fixtures_dir = Path(__file__).parent.parent / "tests" / "fixtures"
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    
    po_file = fixtures_dir / "seeded_pos.json"
    gr_file = fixtures_dir / "seeded_grs.json"
    inv_file = fixtures_dir / "seeded_customer_invoices.json"
    
    with open(po_file, "w") as f:
        json.dump({k: v.model_dump() for k, v in MOCK_PO_DATABASE.items()}, f, indent=2)
    print(f"Seeded {len(MOCK_PO_DATABASE)} Purchase Orders to {po_file}")
    
    with open(gr_file, "w") as f:
        json.dump({k: v.model_dump() for k, v in MOCK_GR_DATABASE.items()}, f, indent=2)
    print(f"Seeded {len(MOCK_GR_DATABASE)} Goods Receipts to {gr_file}")
    
    with open(inv_file, "w") as f:
        json.dump({k: [inv.model_dump() for inv in v] for k, v in MOCK_INVOICE_DATABASE.items()}, f, indent=2)
    print(f"Seeded {len(MOCK_INVOICE_DATABASE)} Customers with Invoices to {inv_file}")
    
    print("Database seeding simulation complete.")

if __name__ == "__main__":
    seed_database()
