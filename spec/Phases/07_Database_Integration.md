# Phase 7: Live Database & Synthetic Data Integration

## Objective
Migrate the orchestrator from using hardcoded, in-memory mock repositories to a live PostgreSQL database hosted on Supabase using SQLAlchemy, and generate robust synthetic datasets for end-to-end testing.

## Key Components

### 1. SQLAlchemy Modeling
- **Location:** `src/database/models/ap_models.py`, `src/database/models/ar_models.py`
- **Description:** Defined robust declarative mapping for our core financial documents:
  - `PurchaseOrderDB` & `GoodsReceiptDB`: AP models utilizing `JSONB` for nested line item structures.
  - `CustomerInvoiceDB`: AR models tracking amounts, due dates, and statuses.

### 2. Live Repository Migration
- **Location:** `src/database/repositories/ap_repository.py`, `src/database/repositories/ar_repository.py`
- **Description:** Replaced hardcoded dictionary lookups with asynchronous SQLAlchemy `select` queries against the live Postgres tables. Integrated with `AsyncSessionLocal` for connection pooling.

### 3. Synthetic CSV Generation
- **Location:** `scripts/generate_seed_data.py`
- **Description:** Created a Python generator script to procedurally output large-scale testing scenarios into CSV format under the `data/` directory.
- **Scenarios Generated (~300 records):**
  - **AP:** Perfect 3-Way Matches, Quantity Mismatches (Short shipment), High-Value ($>50k) limits, and Missing Goods Receipts.
  - **AR:** Complex aging brackets (CURRENT, 30_DAYS, 60_DAYS, 90_DAYS_PLUS) with varying statuses (`PAID`, `PROCESSING`, `UNPAID`).

### 4. Supabase Network Resolution & Seeding
- **Location:** `scripts/setup_postgres.py`, `.env`
- **Description:** Implemented a robust data seeder that:
  - Safely drops and recreates all tables.
  - Forcibly injects the 7 core integration test fixtures (`PO-1001`, `INV-2001`, etc.) to preserve CI/CD evaluation environments.
  - Bulk imports the generated CSV files directly into Supabase.
- **Networking:** Resolved Supabase free-tier IPv6 routing restrictions by implementing the IPv4 **Transaction Pooler** (`port 6543`) combined with `?prepared_statement_cache_size=0` for `asyncpg` compatibility.

## Success Criteria
- [x] AP and AR repositories successfully query a live database.
- [x] Test baseline is preserved while allowing high-volume scale testing.
- [x] IPv4 pooler networking successfully writes across local dev restrictions.
