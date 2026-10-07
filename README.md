# 💼 AP/AR Orchestrator

An AI-assisted finance workflow automation system for **Accounts Payable (AP)** and **Accounts Receivable (AR)**.

The project combines **LangGraph orchestration**, **FastAPI**, **PostgreSQL**, deterministic Python financial rules, and controlled LLM capabilities to automate repetitive finance workflows while keeping financial decisions deterministic, auditable, and secure.

---

## 🎯 1. Overview & Core Design Philosophy

Finance operations often involve repetitive workflows (extracting invoice data, matching purchase orders, reconciling payments, and routing exceptions). AP/AR Orchestrator automates these workflows while maintaining a strict separation between **AI-assisted language tasks** and **deterministic financial decisions**.

> **Core Principle:** 
> `LLM = Understand and Generate Language`
> `Python = Calculate and Decide Financial Outcomes`

The system does **not** allow an LLM to calculate financial values, perform financial matching, authorize payments, or override business rules. LLMs are intentionally restricted to tasks like document extraction and drafting communication, while deterministic Python logic handles 3-way matching and routing.

---

## 🏛️ 2. Architecture & Tech Stack

The system is implemented as an asynchronous, graph-driven orchestration service.

*   **Orchestration Engine:** **LangGraph** (`langgraph>=1.2.12`) — manages DAG state transitions, conditional routing, and Human-In-The-Loop (HITL) pause/resume logic via `MemorySaver()` checkpoints.
*   **API Layer:** **FastAPI** (`fastapi>=0.141.1`) paired with `uvicorn` — provides the HTTP REST interface for document ingestion and workflow resumption.
*   **Database Integration:** **PostgreSQL** via Supabase. Uses **SQLAlchemy Asyncio** with `asyncpg` (`asyncpg>=0.31.0`) and `NullPool` in tests to prevent async event loop conflicts. 
*   **Validation & Schema:** **Pydantic** — enforces strict schema conformity across the AI boundary and API payloads.
*   **LLM Provider:** **Groq** (`qwen3.8-27b`) via `langchain-groq` — leveraged primarily for unstructured document extraction and communication generation.
*   **Package Management:** **uv** — handles fast dependency resolution and virtual environments.

### High-Level Architecture Flow

```text
                         Client
                           │
                           ▼
                    ┌──────────────┐
                    │   FastAPI    │
                    │ API Layer    │
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  LangGraph   │
                    │ Orchestrator │
                    └──────┬───────┘
                           │
                 ┌─────────┴─────────┐
                 ▼                   ▼
             AP Workflow        AR Workflow
                 │                   │
                 ▼                   ▼
          LLM Extraction       LLM Extraction
                 │                   │
                 ▼                   ▼
             Validation          Validation
                 │                   │
                 └─────────┬─────────┘
                           ▼
                 ┌───────────────────┐
                 │ Deterministic     │
                 │ Finance Logic     │
                 └─────────┬─────────┘
                           │
                 ┌─────────┴─────────┐
                 ▼                   ▼
            PostgreSQL          Routing/HITL
```

---

## 📂 3. Project Structure

The architecture strictly enforces separation of concerns:

*   [`src/api/`](src/api/) - FastAPI routing and endpoints (AP, AR, Governance, Risk, and Document storage ingestion).
*   [`src/core/`](src/core/) - Application config, centralized logging, and security sanitization for prompt injection defense.
*   [`src/database/`](src/database/) - SQLAlchemy models, async connections, and repository patterns.
*   [`src/domain/`](src/domain/) - Pure Pydantic schemas representing core financial entities, risk state, and Document Storage interfaces.
*   [`src/finance/`](src/finance/) - **Deterministic boundary**: contains pure Python math for 3-way matching, aging, HITL routing policies, and risk scoring.
*   [`src/graph/`](src/graph/) - LangGraph state machine definitions, nodes, and shared risk assessment logic.
*   [`src/grc/`](src/grc/) - **Governance, Risk & Compliance layer**: Role-Based Access Control (RBAC), deterministic policy rules engine, and Maker-Checker graph nodes.
*   [`src/llm/`](src/llm/) - **Probabilistic boundary**: LLM prompt templates, structured output wrappers, and validation scripts for deterministic extraction cross-checking.
*   [`spec/`](spec/) - Architecture specifications and implementation plans for GRC, Invoice Intelligence, and Phased Development.
*   [`tests/`](tests/) - Unit and integration tests (Pytest).
*   [`scripts/`](scripts/) - Operational scripts for database seeding, automated Playwright UI QA testing, and hash-chain verification.

---

## 🔄 4. Key Workflows & State Machine

The workflows are modeled as DAGs utilizing a single `FinanceState` TypedDict to hold shared workflow state (document references, extracted data, financial facts, routing decisions, etc.).

### Accounts Payable (AP)
*   **Flow:** Document Ingestion → `LLMPrivacyMiddleware` (PII Redaction) → `extract_invoice` → `validate_invoice` → `lookup_db` (Purchase Orders & Goods Receipts) → `match_3_way` (Math) → `reconciliation_node` → `risk_assessment_node` → `governance_policy_node` → **Decision Router**.
*   **Matching Rules:** Compares Invoice, Purchase Order, and Goods Receipt for quantity, unit price, and total amount tolerances.
*   **Exceptions:** Price mismatches, missing goods receipts, or high-value amounts route to exception handlers (drafting discrepancy notices) and pause for Human-In-The-Loop review.

### Accounts Receivable (AR)
*   **Flow:** `LLMPrivacyMiddleware` → `extract_remittance` → `lookup_invoices` → `reconcile_payment` → `calculate_aging` → `risk_assessment_node` → `governance_policy_node` → **Decision Router**.
*   **Reconciliation:** Calculates outstanding balances and applies payments deterministically.
*   **Exceptions:** Partial payments on severely overdue invoices trigger LLM overdue reminder drafts and halt for review.

---

## 🛡️ 5. Governance, Risk & Compliance (GRC)

A unified enterprise GRC layer applies symmetrically across both AP and AR workflows:

1. **Governance & RBAC:** Enforces segregation of duties across `ADMIN`, `MAKER`, `CHECKER`, and `AUDITOR` roles. Manages Maker-Checker approval nodes and REST decision endpoints.
2. **Security & Input Sanitization:** Strips control characters, script/style tags, and detects prompt injection signatures before LLM processing.
3. **Operational Risk Engine:** Rule-based risk detection for duplicate invoices, transaction anomalies, and bank account modifications.
4. **Hardened Audit Trail:** PostgreSQL append-only `audit_events` table enriched with `workflow_type`, `actor_role`, `risk_score`, and SHA-256 tamper-evident cryptographic hash chains (`previous_hash` + `payload` $\rightarrow$ `event_hash`).

---

## 🧠 6. Invoice Intelligence Architecture

The Invoice Intelligence module handles unstructured document ingestion preceding deterministic validation:

1. **Document Storage Abstraction:** Prevents state bloat by storing raw binary PDFs/images out-of-state via `LocalStorageProvider`, passing lightweight `document_id` UUID references inside `FinanceState`.
2. **REST Upload API:** `POST /api/v1/documents/upload` safely ingests files with strict MIME type and size validation.
3. **Pre-Validation Multilingual Normalization:** Converts Arabic-Indic digits (`١٢٣` $\rightarrow$ `123`), localized decimal marks, and localized dates into ASCII primitives **before** downstream financial validation.
4. **Canonical Data Contract:** Enforces strict Pydantic compatibility (`ExtractedInvoice`) ensuring non-breaking integration with legacy deterministic nodes.

---

## 🧪 7. Testing & Quality Assurance

The system maintains a comprehensive test suite guaranteeing the determinism and safety of financial operations. Testing infrastructure is isolated using `poolclass=NullPool` to prevent async event loop conflicts.

*   **Backend Unit & Integration Tests:** 91+ automated Pytest cases covering AP/AR workflows, GRC role validation, risk management, and audit trail integrity.
*   **Playwright UI E2E QA Suite (`scripts/run_comprehensive_qa.py`):** Simulates direct human interactions with the Streamlit dashboard, verifying 10 AP and 10 AR scenarios (including High-value approvals, duplicate invoice detection, and security injection blocks).
*   **Cryptographic Hash-Chain Verification (`scripts/verify_db_and_hash_chains.py`):** Direct SQL inspection tool that validates 100% cryptographic hash-chain validity across all PostgreSQL audit records.

### Testing Cheat Sheet
To trigger specific workflows in the UI, use the following payload examples mapping to seeded DB records:

<details>
<summary><b>Click to expand AP/AR Test Payloads</b></summary>

**AP - Perfect 3-Way Match (Auto-Approve)**
```text
Invoice Number: INV-9905
Vendor ID: VEND-124
PO Reference: PO-1020
Date: 2026-09-30
Description: 27-Inch 4K UHD Monitor
Quantity: 37
Unit Price: $250.00
Total Billed: $9,250.00
```

**AP - High-Value Executive Approval (>$10,000)**
```text
Invoice Number: INV-9903
Vendor ID: VEND-118
PO Reference: PO-1088
Date: 2026-09-30
Description: Enterprise Rack Server R740
Quantity: 4
Unit Price: $15,000.00
Total Billed: $60,000.00
```

**AR - Full Payment on Current Invoice (Auto-Close)**
```text
Customer ID: CUST-218
Date: 2026-09-30
Amount Paid: $7,113.94
Payment applied to the following reference invoices:
INV-2015
```
</details>

---

## 💻 8. Local Development

### Prerequisites
*   Python 3.10+
*   [uv](https://github.com/astral-sh/uv) (Package Manager)
*   PostgreSQL
*   Git

### Installation
```bash
git clone <repository-url>
cd apar_orchestrator
uv sync
```

### Environment Configuration
Create a `.env` file in the root directory (never commit this file):
```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/ap_ar_db
LLM_PROVIDER=groq
GROQ_API_KEY=your_api_key_here
```

### Running the Application
Start the FastAPI backend:
```bash
uv run uvicorn src.api.main:app --reload --port 8000
```
Start the Streamlit UI (in a separate terminal):
```bash
uv run streamlit run src/ui/app.py
```

### Running Tests
```bash
uv run pytest -v
```

---

## ✅ 9. Current Project Status

The project is currently **fully implemented** up to Phase 6 (Evaluation & Hardening) and has successfully integrated the Enterprise GRC Layer and Invoice Intelligence Foundation.

- [x] Finalize architecture & database schema
- [x] Implement AP MVP & AR MVP
- [x] Implement Human-in-the-Loop (HITL) Checkpointing
- [x] Implement AI Communication & Evaluation Framework
- [x] Implement Governance & RBAC (Maker-Checker)
- [x] Implement Financial Compliance & Risk Engines
- [x] Implement GDPR/CCPA PII Privacy Middleware
- [x] Implement Immutable Tamper-Evident Audit Trails
- [x] Hardened AP GRC Workflow & Checkpoint Resume
- [x] Wire GRC Architecture into Accounts Receivable (AR) Workflow
- [x] Implement Invoice Intelligence Phase 1–3 (Document Storage Abstraction & Document Upload API)

*Future extensions (e.g., Azure Document Intelligence OCR integration, ERP bindings, and actual payment execution) are intentionally outside the initial scope.*
