# Technical Briefing: AP/AR Orchestrator Implementation

## 1. Final Architecture & Tech Stack
The AP/AR Orchestrator has been successfully implemented as an asynchronous, graph-driven orchestration service that isolates non-deterministic LLM operations from deterministic financial logic.

**Final Tech Stack:**
*   **Orchestration Engine:** **LangGraph** (`langgraph>=1.2.12`) — manages state transitions, conditional routing, and Human-In-The-Loop (HITL) pause/resume logic via checkpoints.
*   **API Layer:** **FastAPI** (`fastapi>=0.141.1`) paired with `uvicorn` — provides the HTTP interface for document ingestion and workflow resumption.
*   **Database Integration:** **PostgreSQL** via Supabase. We utilize **SQLAlchemy Asyncio** with `asyncpg` (`asyncpg>=0.31.0`) and `NullPool` in tests to prevent async event loop conflicts. 
*   **Validation & Schema:** **Pydantic** — enforces strict schema conformity across the AI boundary and API payloads.
*   **LLM Provider:** **Groq** via `langchain-groq` — leveraged primarily for unstructured document extraction and communication generation (using `qwen3.8-27b`).
*   **Package Management:** **uv** — handles fast dependency resolution and virtual environments.

**Final Directory Structure Summary:**
The architecture strictly enforces separation of concerns:
*   [`src/api/`](file:///home/moeen/projects/apar_orchestrator/src/api/) - FastAPI routing and endpoints (AP, AR, Governance, and `risk.py` endpoints, with `risk_apis.py` for external vendor screening).
*   [`src/core/`](file:///home/moeen/projects/apar_orchestrator/src/core/) - Application config, centralized logging, and [`src/core/security/sanitization.py`](file:///home/moeen/projects/apar_orchestrator/src/core/security/sanitization.py) for prompt injection defense & input sanitization.
*   [`src/database/`](file:///home/moeen/projects/apar_orchestrator/src/database/) - SQLAlchemy models, async connections, and repository patterns.
*   [`src/domain/`](file:///home/moeen/projects/apar_orchestrator/src/domain/) - Pure Pydantic schemas representing core financial entities and `risk_state.py` for risk tracking.
*   [`src/finance/`](file:///home/moeen/projects/apar_orchestrator/src/finance/) - **Deterministic boundary**: contains pure Python math for 3-way matching, aging, HITL routing policies, and `risk_scoring.py` for fraud detection, duplicate invoice checking, and transaction anomaly scoring.
*   [`src/graph/`](file:///home/moeen/projects/apar_orchestrator/src/graph/) - LangGraph state machine definitions, nodes, and [`src/graph/shared/nodes/risk_assessment.py`](file:///home/moeen/projects/apar_orchestrator/src/graph/shared/nodes/risk_assessment.py) for shared risk evaluation.
*   [`src/grc/`](file:///home/moeen/projects/apar_orchestrator/src/grc/) - **Governance, Risk & Compliance layer**: Role-Based Access Control (RBAC), deterministic policy rules engine, and Maker-Checker graph nodes.
*   [`src/llm/`](file:///home/moeen/projects/apar_orchestrator/src/llm/) - **Probabilistic boundary**: contains LLM prompt templates, structured output wrappers, and `validation.py` for deterministic extraction cross-checking.
*   [`spec/GRC/`](file:///home/moeen/projects/apar_orchestrator/spec/GRC/) - Architecture specifications and implementation plans (`01_Governance.md`, `02_Risk.md`, `plan_02_risk.md`, `03_Compliance.md`, `04_Audit_Trail.md`, `05_Implementation_Phases.md`).
*   [`spec/Invoice_Intelligence/`](file:///home/moeen/projects/apar_orchestrator/spec/Invoice_Intelligence/) - Ingestion, OCR, and Invoice Intelligence specifications (`01_Architecture.md` to `10_Implementation_Plan.md`).
*   `tests/` - Unit and integration tests (Pytest).



---

## 2. LangGraph State Machine (The Core Engine)
The workflows are modeled as DAGs (Directed Acyclic Graphs) where state mutations are strictly managed. 

**FinanceState Schema:**
A single `TypedDict` holds the shared workflow state:
*   `workflow_id`, `workflow_type`, `status`
*   `raw_document` (input) -> `extracted_data` (structured output from LLM)
*   `financial_facts` (DB lookups & deterministic math results)
*   `routing_decision` & `hitl_decision` (where the workflow goes next)
*   `drafted_communications` (LLM-drafted emails)

**Graph Execution Flow:**
*   **AP Workflow**: `LLMPrivacyMiddleware` (PII Redaction) → `extract_invoice` → `validate_invoice` → `lookup_db` (Purchase Orders & Goods Receipts) → `match_3_way` (Math) → `reconciliation_node` → `risk_assessment_node` → `governance_policy_node` → **Decision Router**.
    *   *If Maker-Checker Required (High-Value >$10k or High/Critical Risk):* Routes to `maker_checker_node` → pauses at `human_review` for dual authorization.
    *   *If 3-Way Variance Mismatch / Missing PO / Missing GR:* Routes to `generate_discrepancy` → pauses at `human_review`.
    *   *If Low Risk & Matched:* `COMPLETED`.
*   **AR Workflow**: `LLMPrivacyMiddleware` (PII Redaction) → `extract_remittance` → `lookup_invoices` (DB lookup) → `reconcile_payment` → `calculate_aging` → `risk_assessment_node` → `governance_policy_node` → **Decision Router**.
    *   *If Maker-Checker Required (High-Value Remittance >$10k or High/Critical Risk):* Routes to `maker_checker_node` → pauses at `human_review` for dual authorization.
    *   *If Overdue Payment Exception:* Routes to `generate_overdue` → pauses at `human_review`.
    *   *If Low Risk & Settle/Partial Match:* `COMPLETED`.

**HITL & Governance Resumption Strategy:**
The workflows utilize LangGraph's `MemorySaver()` checkpointer. During graph compilation, `interrupt_before=["human_review"]` is defined for nodes requiring manual review or Maker-Checker authorization. When reaching an interrupt point, execution halts, persisting state using `thread_id` (mapped to `workflow_id`). 
* For **HITL Exception Reviews**: The API layer exposes `/ap/{id}/resume` and `/ar/{id}/resume` to inject decision inputs.
* For **Maker-Checker Governance Approvals**: The API exposes `POST /governance/decide` to validate RBAC roles (`MAKER` vs `CHECKER`), record audit entries, update state via `aupdate_state()`, and trigger `ainvoke(None, config=config)` to resume state safely without re-running earlier nodes.

---

## 3. The AI / Deterministic Boundary (Crucial for Evaluation)
To prevent the LLM from hallucinating financial figures or autonomously authorizing payments, a hard barrier exists between probabilistic reasoning and deterministic execution.

**Probabilistic LLM Boundaries:**
1.  **Document Extraction**: [`src/llm/extractors/invoice_extractor.py`](file:///home/moeen/projects/apar_orchestrator/src/llm/extractors/invoice_extractor.py) and `remittance_extractor.py`. LLMs are restricted to parsing raw text/JSON into Pydantic models. They perform NO calculations. (Regex fallbacks exist for resilience).
2.  **Communication Drafts**: [`src/llm/generators/communications.py`](file:///home/moeen/projects/apar_orchestrator/src/llm/generators/communications.py). LLMs draft the text for discrepancy notices and overdue reminders using *deterministic facts* injected into prompts as context.

**Deterministic Math Boundaries:**
1.  **3-Way Matching**: [`src/finance/matching.py`](file:///home/moeen/projects/apar_orchestrator/src/finance/matching.py). Evaluates quantity, unit price, totals, and tolerances using standard Python floating-point logic. 
2.  **Routing & HITL Rules**: [`src/finance/routing.py`](file:///home/moeen/projects/apar_orchestrator/src/finance/routing.py). Dictates the exact threshold logic (e.g., invoices > $10,000 or mismatch variance > $10.00).
*The LLM never calls these functions and never influences the routing decision output.*

---

## 4. Database & API Integration
**FastAPI Endpoints:**
The service exposes the following domain-driven endpoints:
*   `POST /ap/process-invoice` — Ingests a new vendor invoice and initiates the LangGraph execution.
*   `GET /ap/{workflow_id}/state` — Retrieves the current state of a paused AP execution.
*   `POST /ap/{workflow_id}/resume` — Injects executive approval (APPROVE/REJECT) to a paused AP execution.
*   `POST /governance/decide` — Submits a Maker-Checker approval or rejection decision enforced via RBAC.
*   `POST /risk/evaluate` — Evaluates instant risk metrics, prompt injection checks, and fraud scoring on transaction payloads.
*   `GET /risk/assessments/{workflow_id}` — Retrieves structured risk state, flags, and recommended actions for a workflow thread.
*(The equivalent routes exist for AR at `/ar/process-payment`, `/ar/{workflow_id}/state`, etc.)*


**Database Seeding & Querying:**
The application connects to a Supabase PostgreSQL instance. We established the schema using `Base.metadata.create_all` and seeded it using [`scripts/setup_postgres.py`](file:///home/moeen/projects/apar_orchestrator/scripts/setup_postgres.py) with both edge-case test rows and batch CSV data.
Repository classes (`ap_repository.py` and `ar_repository.py`) execute non-blocking queries utilizing SQLAlchemy's `AsyncSessionLocal` to fetch required truth records (Purchase Orders, Goods Receipts, and Open Invoices) during graph traversal.

---

## 5. Testing & Validation
The system maintains a comprehensive, green test suite of **84 automated backend unit/integration tests** (`pytest`) alongside an **automated Playwright-based End-to-End UI QA suite** (`scripts/run_comprehensive_qa.py`) and a **PostgreSQL Cryptographic Hash-Chain Verification tool** (`scripts/verify_db_and_hash_chains.py`).

Crucially, testing infrastructure has been isolated using `poolclass=NullPool` on the async DB engines, preventing `InterfaceError` connection pooling anomalies across async test loops.

### 5.1 End-to-End Playwright UI QA Suite (`scripts/run_comprehensive_qa.py`)
Simulates direct human interactions with the Streamlit web dashboard via Playwright browser automation, testing both Accounts Payable (AP) and Accounts Receivable (AR) end-to-end:

* **AP Scenarios (10/10 Passed):** Normal auto-approval (`AP-1`), High-value approval flow (`AP-2`), High-value rejection flow (`AP-3`), 3-way match variance exception (`AP-4`), Historical duplicate invoice detection (`AP-5`), Malformed input extraction (`AP-6`), Unauthorized MAKER approval block (`AP-7`), Security prompt injection defense (`AP-8`), $10,000 boundary rule enforcement (`AP-9`), and Sequential workflow isolation (`AP-10`).
* **AR Scenarios (10/10 Passed):** Normal remittance matching (`AR-1`), Partial payment handling (`AR-2`), Full payment settlement (`AR-3`), Overdue invoice detection (`AR-4`), Payment mismatch exception (`AR-5`), High-value AR governance (`AR-6`), Malformed remittance handling (`AR-7`), Duplicate payment detection (`AR-8`), Unauthorized MAKER approval block (`AR-9`), and Sequential AR transaction isolation (`AR-10`).

### 5.2 Duplicate Invoice Detection & Database Persistence
* **InvoiceDB Model (`invoices` table):** Stores processed invoices (`invoice_number`, `vendor_id`, `invoice_total`, `workflow_id`, `status`, `created_at`).
* **State Hydration:** Prior to `risk_assessment_node`, historical vendor invoices are queried from PostgreSQL and injected into `state["historical_invoices"]`.
* **Deterministic Detection:** `check_duplicate_invoice()` compares incoming invoice numbers against historical vendor records, assigning elevated risk scores (60.0) and flagging duplicates (`DUPLICATE_INVOICE_NUMBER`) to force HITL review.

### 5.3 PostgreSQL Audit & Cryptographic Hash-Chain Verification (`scripts/verify_db_and_hash_chains.py`)
Direct SQL inspection verifies runtime GRC guarantees:
* **116 PostgreSQL Audit Records:** Enriched with actor metadata, GRC domain, decisions, and risk levels across 40 unique workflow instances.
* **100% Cryptographic Hash-Chain Validity:** Computes `SHA-256(event_id + workflow_id + timestamp + event_type + previous_hash + payload)` for every event to guarantee immutable tamper-evidence.
* **100% Cross-Workflow Isolation:** Validates strict domain separation between AP (`AP_EXTRACTION`, `3_WAY_MATCH`, `AP_RISK`, `AP_GOVERNANCE`) and AR (`AR_REMITTANCE_MATCH`, `AR_RISK`, `AR_GOVERNANCE`).

### 5.4 Backend Unit & Integration Tests (84 Passing Tests)
*   **AP Workflows & GRC (`test_ap_workflow.py`, `test_grc_workflow.py`):**
    *   **AP - Perfect Match:** Full 3-way match passes automatically, routing status to `COMPLETED`.
    *   **AP - Price Tolerance Exceeded:** Identifies variance, automatically triggers exception protocols, generates a discrepancy communication via LLM, and halts execution (`REQUIRES_APPROVAL`).
    *   **AP - High-Value Invoice Maker-Checker Approval:** High-value invoices (>$10,000) pause at `maker_checker_node` requiring dual authorization. Responding via `/governance/decide` with `CHECKER` role successfully updates state to `COMPLETED`.
    *   **AP - Audit Trail Logging:** Verifies immutable log entries for all node executions and Maker-Checker actions.
*   **AR Workflows & GRC (`test_ar_workflow.py`):**
    *   **AR - Full Payment:** Validates exact payment application against outstanding DB invoices, updating balance to zero (`COMPLETED`).
    *   **AR - Partial Payment:** Confirms partial balance retention routes strictly to `COMPLETED` without marking the underlying invoice fully paid.
    *   **AR - High-Value Remittance Maker-Checker Approval:** High-value remittances (>$10,000) trigger `rule_high_value_remittance` governance policy and halt for `MAKER_CHECKER_REQUIRED`. Submitting a `CHECKER` approval resumes the graph to `COMPLETED`.
    *   **AR - High-Risk Remittance Routing:** Remittances triggering high/critical risk flags (e.g. customer anomaly or prompt injection) pause for Maker-Checker approval or human review.
    *   **AR - Overdue Payment Escalation:** Triggers overdue LLM correspondence drafting and halts for HITL review (`REQUIRES_APPROVAL`).
*   **GRC - Governance & RBAC (`test_governance.py`):** Enforces segregation of duties across `ADMIN`, `MAKER`, `CHECKER`, and `AUDITOR` roles and validates Maker-Checker decision submission.
*   **GRC - Risk & Security Management (`test_risk_management.py`):** Validates prompt injection sanitization, duplicate invoice detection, bank modification alerts, transaction anomaly scoring, LLM line item math checks, external risk API fallbacks, and node execution.
*   **Audit Trail & Backcheck Integrity (`test_audit_trail.py`):** Validates SHA-256 cryptographic hash-chaining (`previous_hash` + canonical payload $\rightarrow$ `event_hash`), PII redaction, schema completeness, Maker-Checker actor verification (`actor_type`, `actor_id`, `actor_role`), risk level/score/flags persistence, and AP/AR backcheck queries.

---

## 5. Governance, Risk & Compliance (GRC) Architecture
The system incorporates a unified enterprise GRC layer applied symmetrically across **both Accounts Payable (AP) and Accounts Receivable (AR)** workflows:

1. **Governance & RBAC ([`src/grc/`](file:///home/moeen/projects/apar_orchestrator/src/grc/))**: Enforces segregation of duties across `ADMIN`, `MAKER`, `CHECKER`, and `AUDITOR` roles. Manages `maker_checker_node` approval nodes and REST decision endpoints (`POST /governance/decide`).
2. **Security & Input Sanitization ([`src/core/security/sanitization.py`](file:///home/moeen/projects/apar_orchestrator/src/core/security/sanitization.py))**: Strips control characters, script/style tags, and null bytes. Detects prompt injection signatures.
3. **Operational Risk Engine ([`src/finance/risk_scoring.py`](file:///home/moeen/projects/apar_orchestrator/src/finance/risk_scoring.py))**: Rule-based risk detection for duplicate invoices, customer/vendor transaction anomalies, and bank account modifications.
4. **AI Extraction Validation ([`src/llm/validation.py`](file:///home/moeen/projects/apar_orchestrator/src/llm/validation.py))**: Deterministically cross-checks line item calculations and currency consistency. Prevents LLM outputs from overriding deterministic math.
5. **External Risk Client ([`src/api/integrations/risk_apis.py`](file:///home/moeen/projects/apar_orchestrator/src/api/integrations/risk_apis.py))**: External sanctions and compliance watchlist screening interface.
6. **Shared Risk Assessment Node ([`src/graph/shared/nodes/risk_assessment.py`](file:///home/moeen/projects/apar_orchestrator/src/graph/shared/nodes/risk_assessment.py))**: LangGraph node transparently evaluating AP vendor and AR customer identifiers to aggregate risk flags and assign severity levels (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
7. **Compliance & Data Privacy Layer**: Ensures regulatory data minimization via dynamic PII redaction middleware ([`src/llm/middleware.py`](file:///home/moeen/projects/apar_orchestrator/src/llm/middleware.py)), financial deterministic reconciliation ([`src/finance/reconciliation.py`](file:///home/moeen/projects/apar_orchestrator/src/finance/reconciliation.py)), and automated TTL state cleanup jobs ([`src/database/retention_jobs.py`](file:///home/moeen/projects/apar_orchestrator/src/database/retention_jobs.py)). Mandates structured rationales for all decisions ([`src/domain/compliance_state.py`](file:///home/moeen/projects/apar_orchestrator/src/domain/compliance_state.py)).
8. **Hardened GRC Audit Trail Table (`audit_events`)**: PostgreSQL append-only audit trail enriched with explicit backcheck columns:
   - `workflow_type`, `transaction_id`, `actor_type`, `actor_id`, `actor_role`
   - `grc_domain`, `event_type`, `action`, `decision`, `reason`
   - `risk_level`, `risk_score`, `risk_flags`, `approval_required`, `approval_status`
   - `previous_hash`, `event_hash` (SHA-256 tamper-evident chain)

---

### Standard SQL Backcheck Queries for Financial Controllers & Auditors

```sql
-- 1. All audit events for a single transaction (e.g. INV-9903)
SELECT *
FROM audit_events
WHERE transaction_id = 'INV-9903'
ORDER BY timestamp;

-- 2. Who approved a transaction and why
SELECT
    transaction_id,
    actor_id,
    actor_role,
    action,
    decision,
    reason,
    approval_required,
    approval_status,
    timestamp
FROM audit_events
WHERE transaction_id = 'INV-9903'
  AND decision = 'APPROVED'
ORDER BY timestamp;

-- 3. All Checker / Financial Controller approvals
SELECT
    timestamp,
    workflow_type,
    transaction_id,
    actor_id,
    actor_role,
    action,
    decision,
    risk_level,
    risk_score,
    reason
FROM audit_events
WHERE actor_role IN ('CHECKER', 'FINANCIAL_CONTROLLER')
  AND decision = 'APPROVED'
ORDER BY timestamp DESC;
```

---

## 5.1 Invoice Intelligence Architecture (`spec/Invoice_Intelligence/`)
The **Invoice Intelligence** specification framework defines the intelligent ingestion, document storage abstraction, OCR, multilingual normalization, confidence evaluation, and HITL data correction layer preceding deterministic validation:

1. **Document Storage Abstraction ([`02_Document_Input.md`](file:///home/moeen/projects/apar_orchestrator/spec/Invoice_Intelligence/02_Document_Input.md))**: Prevents state bloat by storing raw binary PDFs/images out-of-state via `DocumentStorageInterface`, passing lightweight `document_id` references inside `FinanceState`.
2. **Pre-Validation Multilingual Normalization ([`03_OCR_Multilingual_Extraction.md`](file:///home/moeen/projects/apar_orchestrator/spec/Invoice_Intelligence/03_OCR_Multilingual_Extraction.md))**: Converts Arabic-Indic digits (`١٢٣` $\rightarrow$ `123`), localized decimal marks (`12.345,67`), and localized dates into ASCII primitives **BEFORE** downstream deterministic validation.
3. **Canonical Data Contract ([`04_Canonical_Invoice_Schema.md`](file:///home/moeen/projects/apar_orchestrator/spec/Invoice_Intelligence/04_Canonical_Invoice_Schema.md))**: Enforces strict compatibility with `ExtractedInvoice` (`invoice_number`, `vendor_id`, `po_number`, `invoice_total`, `total_price`), ensuring non-breaking integration with `validate_invoice`, `lookup_db`, and `match_3_way`.
4. **Cyclic HITL Correction Flow ([`05_Confidence_and_HITL.md`](file:///home/moeen/projects/apar_orchestrator/spec/Invoice_Intelligence/05_Confidence_and_HITL.md))**: Enables operators to submit `CORRECT_DATA` for low-confidence extractions, merging edits into state, emitting `HUMAN_CORRECTION_APPLIED` audit events, and cyclically re-entering `validate_invoice`.
5. **Target LangGraph Pipeline Integration ([`06_AP_Integration.md`](file:///home/moeen/projects/apar_orchestrator/spec/Invoice_Intelligence/06_AP_Integration.md))**: Integrates `ingest_document`, `extract_invoice`, `evaluate_confidence`, cyclic `human_review`, and post-matching GRC authorization nodes.
6. **Immutable Audit Trail Integration**: Emits standardized audit events (`DOCUMENT_RECEIVED`, `EXTRACTION_COMPLETED`, `LOW_CONFIDENCE_ROUTING`, `HUMAN_CORRECTION_APPLIED`, `REVALIDATION`).



---

## 6. Testing Cheat Sheet

Copy and paste the following test documents directly into the Streamlit UI to trigger different paths in the workflows. These documents map exactly to the seeded database records.

### 🧾 Accounts Payable (AP) Workflows

**1. Perfect 3-Way Match (Auto-Approve)**
Matches the Purchase Order and Goods Receipt perfectly. The workflow will run straight through and finish with `COMPLETED`.
```text
INVOICE
-----------------
Invoice Number: INV-9905
Vendor ID: VEND-124
PO Reference: PO-1020
Date: 2026-09-30

Description: 27-Inch 4K UHD Monitor
Quantity: 37
Unit Price: $250.00
Total Billed: $9,250.00
```

**2. Price Tolerance Exception**
Using the same PO (`PO-1020`), but the vendor bills $500 per unit instead of the agreed $250. The math engine will catch the variance, halt the graph, and draft an exception email.
```text
INVOICE
-----------------
Invoice Number: INV-9906
Vendor ID: VEND-124
PO Reference: PO-1020
Date: 2026-09-30

Description: 27-Inch 4K UHD Monitor
Quantity: 37
Unit Price: $500.00
Total Billed: $18,500.00
```

**3. Quantity Exception (Short Shipment)**
The vendor billed for 10 units, but the warehouse logged receipt of 8 units in the database. Fails the match, routes to Human-In-The-Loop.
```text
INVOICE
-----------------
Invoice Number: INV-9902
Vendor ID: VEND-129
PO Reference: PO-1062
Date: 2026-09-30

Description: Ergonomic Office Chair
Quantity: 10
Unit Price: $200.00
Total Billed: $2,000.00
```

**4. High-Value Executive Approval**
Perfect match, but the total amount ($60,000) exceeds the threshold (>$10,000). The routing logic halts the workflow for human approval.
```text
INVOICE
-----------------
Invoice Number: INV-9903
Vendor ID: VEND-118
PO Reference: PO-1088
Date: 2026-09-30

Description: Enterprise Rack Server R740
Quantity: 4
Unit Price: $15,000.00
Total Billed: $60,000.00
```

**5. Missing Goods Receipt Exception**
The invoice matches the PO, but the goods have not been received at the warehouse (No GR record exists).
```text
INVOICE
-----------------
Invoice Number: INV-9904
Vendor ID: VEND-122
PO Reference: PO-1095
Date: 2026-09-30

Description: Gigabit Managed Switch 24-Port
Quantity: 30
Unit Price: $450.00
Total Billed: $13,500.00
```

### 💸 Accounts Receivable (AR) Workflows

**6. Full Payment on Current Invoice (Auto-Close)**
This invoice (`INV-2015`) isn't due until October 18th. The customer already paid part of it, leaving a balance of $7,113.94. This remittance pays the exact remaining balance. The system completes it.
```text
REMITTANCE ADVICE
-----------------
Customer ID: CUST-218
Date: 2026-09-30
Amount Paid: $7,113.94

Payment applied to the following reference invoices:
INV-2015
```

**7. Partial Payment on Current Invoice**
Paying only $1,000 towards an invoice that isn't due yet. The system accepts the payment, lowers the balance, and safely completes without overdue alerts.
```text
REMITTANCE ADVICE
-----------------
Customer ID: CUST-218
Date: 2026-09-30
Amount Paid: $1,000.00

Payment applied to the following reference invoices:
INV-2015
```

**8. Full Payment on an OVERDUE Invoice**
`INV-2045` was due on September 28th. This payment finally settles it in full. The system completes processing without complaining since the balance is zeroed out.
```text
REMITTANCE ADVICE
-----------------
Customer ID: CUST-226
Date: 2026-09-30
Amount Paid: $2,290.94

Payment applied to the following reference invoices:
INV-2045
```

**9. Partial Payment on a Severely OVERDUE Invoice**
`INV-2070` was due on August 19th. The customer owes $7,608.81 but is only sending $1,000. This triggers the AI to draft an overdue reminder and halts the workflow for review.
```text
REMITTANCE ADVICE
-----------------
Customer ID: CUST-212
Date: 2026-09-30
Amount Paid: $1,000.00

Payment applied to the following reference invoices:
INV-2070
```

**10. High-Value Remittance Executive Approval (AR GRC)**
Remittance payment ($15,000.00) exceeds the governance policy threshold (>$10,000). The AR GRC engine evaluates `rule_high_value_remittance`, triggering `MAKER_CHECKER_REQUIRED` and pausing execution for `CHECKER` dual authorization.
```text
REMITTANCE ADVICE
-----------------
Customer ID: CUST-218
Date: 2026-09-30
Amount Paid: $15,000.00

Payment applied to the following reference invoices:
INV-2015
```

---


# AP/AR Orchestrator

An AI-assisted finance workflow automation system for **Accounts Payable (AP)** and **Accounts Receivable (AR)**.

The project combines **LangGraph orchestration**, **FastAPI**, **PostgreSQL**, deterministic Python financial rules, and controlled LLM capabilities to automate repetitive finance workflows while keeping financial decisions deterministic and auditable.

---

## 1. Overview

Finance operations often involve repetitive workflows such as:

- Extracting information from invoices
- Validating financial documents
- Matching invoices against purchase orders and goods receipts
- Reconciling customer payments
- Calculating outstanding balances
- Calculating invoice aging
- Routing exceptions
- Requesting human approval
- Drafting vendor/customer communications

AP/AR Orchestrator is designed to automate these workflows while maintaining a strict separation between **AI-assisted language tasks** and **deterministic financial decisions**.

The system does not allow an LLM to calculate financial values, perform financial matching, authorize payments, or override business rules.

---

# 2. Core Design Principle

The central architectural principle is:

```text
LLM = Understand and Generate Language

Python = Calculate and Decide Financial Outcomes
```

For example:

```text
Invoice PDF
     │
     ▼
LLM Extraction
     │
     ▼
Structured Invoice Data
     │
     ▼
Python Validation
     │
     ▼
Database Lookup
     │
     ├── Purchase Order
     └── Goods Receipt
     │
     ▼
Python 3-Way Matching
     │
     ▼
Deterministic Routing
```

The LLM provides information.

The deterministic application logic makes the financial decision.

---

# 3. Key Features

## Accounts Payable

The AP workflow supports the planned automation of:

- Invoice intake
- Invoice data extraction
- Invoice validation
- Purchase order lookup
- Goods receipt lookup
- 3-way matching
- Tolerance checking
- Exception routing
- Approval workflows

### AP 3-Way Matching

The system compares:

```text
Invoice
   ↕
Purchase Order
   ↕
Goods Receipt
```

Relevant fields may include:

- Vendor
- PO number
- Invoice number
- Product/item
- Quantity
- Unit price
- Total amount
- Received quantity

The actual matching rules are implemented in deterministic Python.

---

## Accounts Receivable

The AR workflow focuses on:

- Payment/remittance processing
- Customer identification
- Invoice lookup
- Payment reconciliation
- Outstanding balance calculation
- Invoice aging
- Overdue detection
- Exception routing

Example:

```text
Invoice Amount = $5,000
Payment        = $3,000

Outstanding Balance = $2,000
```

The calculation is performed by Python, not an LLM.

---

## Human-in-the-Loop

Certain situations require human review.

Examples include:

- High-value transactions
- Failed matching
- Large discrepancies
- Unmatched payments
- Financial exceptions
- Approval-required transactions

The planned workflow is:

```text
Automated Processing
        │
        ▼
Deterministic Rules
        │
        ▼
Exception / Approval Required
        │
        ▼
Human Review
        │
   ┌────┴────┐
   ▼         ▼
Approve    Reject
   │         │
   ▼         ▼
Resume     End / Escalate
```

LangGraph checkpointing and interrupts will be used for workflow suspension and resumption.

---

# 4. AI Responsibilities

LLMs are intentionally restricted to specific tasks.

### Allowed

```text
Document extraction
Structured information extraction
Controlled classification
Natural-language generation
Exception summaries
Vendor/customer communication drafts
```

### Not Allowed

```text
Financial calculations
Tax calculations
Aging calculations
3-way matching
Payment authorization
Approval threshold decisions
Financial database modification
Business-rule overrides
```

This design makes financial behavior deterministic and easier to test and audit.

---

# 5. Technology Stack

| Component | Technology |
| --- | --- |
| Language | Python |
| Workflow orchestration | LangGraph |
| API | FastAPI |
| Database | PostgreSQL |
| LLM provider | Ollama / Groq |
| Package management | uv |
| Testing | Pytest |
| Configuration | Environment variables |
| Workflow state | LangGraph `FinanceState` |

The final dependency list will be defined in [`pyproject.toml`](file:///home/moeen/projects/apar_orchestrator/pyproject.toml).

---

# 6. Architecture

High-level architecture:

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
                 │                   │
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
                 │                   │
                 ▼                   ▼
            PostgreSQL          Routing/HITL
```

---

# 7. Project Structure

The planned project structure is:

```text
apar-orchestrator/
│
├── .env
├── .env.example
├── .gitignore
├── pyproject.toml
├── CLAUDE.md
├── README.md
│
├── spec/
│   ├── GRC/
│   │   ├── 01_Governance.md
│   │   ├── 02_Risk.md
│   │   ├── 03_Compliance.md
│   │   ├── 04_Audit_Trail.md
│   │   └── 05_Implementation_Phases.md
│   ├── Invoice_Intelligence/
│   │   ├── 01_Architecture.md
│   │   ├── 02_Document_Input.md
│   │   ├── 03_OCR_Multilingual_Extraction.md
│   │   ├── 04_Canonical_Invoice_Schema.md
│   │   ├── 05_Confidence_and_HITL.md
│   │   ├── 06_AP_Integration.md
│   │   ├── 07_Error_Handling.md
│   │   ├── 08_Security_Integration.md
│   │   ├── 09_Testing.md
│   │   └── 10_Implementation_Plan.md
│   └── Phases/
│       ├── 01_Foundation.md
│       ├── 02_AP_MVP.md
│       ├── 03_AR_MVP.md
│       ├── 04_HITL.md
│       ├── 05_Communication.md
│       ├── 06_Evaluation.md
│       └── 07_Database_Integration.md

│
├── src/
│   └── apar_orchestrator/
│       ├── __init__.py
│       │
│       ├── api/
│       │   ├── main.py
│       │   └── routes/
│       │       ├── health.py
│       │       ├── ap.py
│       │       └── ar.py
│       │
│       ├── core/
│       │   ├── config.py
│       │   ├── logging.py
│       │   └── exceptions.py
│       │
│       ├── domain/
│       │   ├── ap/
│       │   ├── ar/
│       │   └── common/
│       │
│       ├── finance/
│       │   ├── matching.py
│       │   ├── aging.py
│       │   ├── taxes.py
│       │   └── routing.py
│       │
│       ├── database/
│       │   ├── connection.py
│       │   ├── models/
│       │   └── repositories/
│       │
│       ├── llm/
│       │   ├── clients/
│       │   ├── extractors/
│       │   ├── generators/
│       │   └── parsers/
│       │
│       └── graph/
│           ├── state.py
│           ├── common/
│           ├── ap/
│           │   ├── nodes.py
│           │   └── graph.py
│           └── ar/
│               ├── nodes.py
│               └── graph.py
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│
├── scripts/
│   ├── seed_database.py
│   └── run_evaluation.py
│
└── docs/
    └── architecture.md
```

---

# 8. Directory Responsibilities

### `api/`

FastAPI application and HTTP endpoints.

### `core/`

Configuration, logging, exceptions, and shared infrastructure.

### `domain/`

AP, AR, and shared financial domain models and concepts.

### `finance/`

Deterministic financial calculations and business rules.

### `database/`

PostgreSQL connections, models, queries, and repositories.

### `llm/`

LLM providers, extraction, generation, and structured-output parsing.

### `graph/`

LangGraph state, nodes, workflows, and routing.

### `tests/`

Unit and integration tests.

### `scripts/`

Operational/development scripts such as database seeding and evaluation.

### `spec/`

Specifications for each development phase.

### `docs/`

Additional architecture and project documentation.

---

# 9. AP Workflow

The planned AP MVP is:

```text
Receive Invoice
       │
       ▼
Extract Invoice Data
       │
       ▼
Validate Invoice
       │
       ▼
Find Purchase Order
       │
       ▼
Find Goods Receipt
       │
       ▼
Perform 3-Way Match
       │
       ▼
Evaluate Tolerances
       │
       ▼
Route Result
       │
       ├───────────────┐
       ▼               ▼
    Matched         Exception
       │               │
       ▼               ▼
   Continue          HITL
```

The exact matching and tolerance rules will be defined in the AP specification.

---

# 10. AR Workflow

The planned AR MVP is:

```text
Receive Payment / Remittance
             │
             ▼
       Extract / Classify
             │
             ▼
      Identify Customer
             │
             ▼
       Find Invoices
             │
             ▼
      Reconcile Payment
             │
             ▼
   Calculate Outstanding
             │
             ▼
       Calculate Aging
             │
             ▼
        Route Result
             │
       ┌─────┴─────┐
       ▼           ▼
    Normal       Overdue
                     │
                     ▼
               Escalation
```

The exact reconciliation and aging rules will be defined in the AR specification.

---

# 11. Spec-Driven Development

Development is divided into six phases.

```text
Phase 1
Foundation
   ↓
Phase 2
AP MVP
   ↓
Phase 3
AR MVP
   ↓
Phase 4
HITL
   ↓
Phase 5
AI Communication
   ↓
Phase 6
Evaluation
```

Each phase has a dedicated specification in `spec/`.

The coding agent should not implement functionality from future phases unless explicitly instructed.

---

# 12. Phase 1 — Foundation

Phase 1 establishes the technical foundation:

- Python package structure
- uv configuration
- Environment configuration
- Logging
- FastAPI application
- PostgreSQL connection
- Initial database structure
- LangGraph setup
- `FinanceState`
- Health endpoint
- Basic test infrastructure

The project should not attempt to implement the complete AP/AR workflows during this phase.

---

# 13. Phase 2 — AP MVP

Phase 2 implements the first complete AP workflow.

Expected capabilities:

- Receive invoice
- Extract invoice fields
- Validate extracted data
- Retrieve PO information
- Retrieve goods receipt information
- Perform deterministic 3-way matching
- Evaluate tolerances
- Route matched/exception results

---

# 14. Phase 3 — AR MVP

Phase 3 implements the first complete AR workflow.

Expected capabilities:

- Receive payment/remittance information
- Extract relevant information
- Identify customer
- Retrieve invoice information
- Reconcile payments
- Calculate outstanding balances
- Calculate aging
- Determine overdue status
- Route results

---

# 15. Phase 4 — Human-in-the-Loop

Phase 4 introduces human intervention.

Expected capabilities:

- Workflow interruption
- Persistent workflow state
- Exception review
- High-value approval
- Human decision
- Workflow resume

The human decision must not be replaced by an LLM.

---

# 16. Phase 5 — AI Communication

Phase 5 introduces controlled natural-language generation.

Potential capabilities:

- Overdue payment reminder drafts
- Vendor discrepancy emails
- Exception summaries
- Internal finance summaries

Generated messages must be based on deterministic financial facts.

Example:

```text
Python calculates:

Invoice: INV-1024
Outstanding: $2,000
Days overdue: 18
Customer: ABC Ltd

            ↓

LLM

            ↓

Draft customer reminder
```

The LLM does not calculate the `$2,000` or `18 days`.

---

# 17. Phase 6 — Evaluation

The evaluation phase will test both deterministic and AI-assisted components.

### AP scenarios

```text
Perfect match
Quantity mismatch
Price mismatch
Missing PO
Missing goods receipt
Tolerance boundary
Tolerance exceeded
```

### AR scenarios

```text
Full payment
Partial payment
Unmatched payment
Overdue invoice
Current invoice
Different aging buckets
Multiple invoice reconciliation
```

### AI scenarios

```text
Valid extraction
Missing fields
Malformed structured output
Invalid values
Communication generation
```

The evaluation system should use reproducible test data.

---

# 18. Local Development

## Prerequisites

Install:

- Python
- uv
- PostgreSQL
- Git

An LLM provider should also be configured depending on the selected development mode.

---

## Install the project

Clone the repository and enter the project directory:

```bash
git clone <repository-url>
cd apar-orchestrator
```

Create/sync the environment:

```bash
uv sync
```

---

# 19. Environment Variables

Create a local `.env` file.

Example:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/ap_ar_db

LLM_PROVIDER=ollama

OLLAMA_BASE_URL=http://localhost:11434

GROQ_API_KEY=

LANGGRAPH_CHECKPOINT_DATABASE_URL=
```

The exact variables will be finalized during Phase 1.

Never commit `.env`.

Use `.env.example` to document required configuration without exposing secrets.

---

# 20. Running the Application

Once Phase 1 is implemented, the FastAPI application will be started through uv.

Example:

```bash
uv run uvicorn api.main:app --app-dir src --reload
```

The exact command may change according to the final application entry point.

---

# 21. Running Tests

Run the complete test suite:

```bash
uv run pytest
```

Run a specific test directory:

```bash
uv run pytest tests/unit
```

Run with verbose output:

```bash
uv run pytest -v
```

The project should maintain fast deterministic unit tests and separate integration tests where external systems are required.

---

# 22. Security

This project handles financial workflow data, so security is an important design requirement.

Never commit:

```text
.env
API keys
database passwords
access tokens
private credentials
real customer financial data
real vendor financial data
```

Do not include sensitive financial information in logs unnecessarily.

Use synthetic data for development and automated testing unless a controlled environment explicitly requires otherwise.

---

# 23. Development Philosophy

The project prioritizes:

### Determinism

Financial calculations must be reproducible.

### Modularity

Each component should have one clear responsibility.

### Testability

Important business logic must be independently testable.

### Explainability

Financial routing decisions should be understandable from deterministic rules and recorded workflow state.

### Controlled AI

LLMs should be used where language understanding/generation is useful, not where deterministic business logic is required.

### Incremental Development

Implement one specification phase at a time instead of building the entire system simultaneously.

---

# 24. Current Project Status

The project is currently **fully implemented** up to Phase 6 (Evaluation & Hardening) and has successfully integrated the **Enterprise GRC Layer**.

Planned implementation order:

```text
[x] Finalize architecture
[x] Define FinanceState
[x] Define database schema
[x] Create Phase 1 specification
[x] Implement Phase 1
[x] Create Phase 2 specification
[x] Implement AP MVP
[x] Create Phase 3 specification
[x] Implement AR MVP
[x] Create Phase 4 specification
[x] Implement HITL
[x] Implement AI communication
[x] Implement evaluation framework
[x] Implement Governance & RBAC (Maker-Checker)
[x] Implement Financial Compliance & Risk Engines
[x] Implement GDPR/CCPA PII Privacy Middleware
[x] Implement Immutable Audit Trails
[x] Hardened AP GRC Workflow & Checkpoint Resume
[x] Wire GRC Architecture into Accounts Receivable (AR) Workflow
```

The project should not be considered production-ready until security, reliability, observability, database migration strategy, testing, and deployment requirements have been properly addressed.

---

# 25. Future Extensions

Possible future extensions include:

- Additional finance workflows
- More document formats
- OCR integration (Azure Document Intelligence)
- ERP integrations
- Accounting-system integrations
- Advanced reconciliation
- Workflow dashboards
- Approval dashboards
- Monitoring and observability
- Production deployment
- Executing final Financial Action (Payments)

These are intentionally outside the initial MVP scope unless added to a future specification.

---

# 26. Project Goal

The goal of AP/AR Orchestrator is not simply to demonstrate an LLM or LangGraph.

The goal is to demonstrate how **AI can be safely integrated into financial workflows** by combining:

```text
                 AI
                 │
       ┌─────────┴─────────┐
       │                   │
 Language Understanding   Generation
       │                   │
       └─────────┬─────────┘
                 │
                 ▼
          LangGraph
         Orchestration
                 │
                 ▼
      Deterministic Finance
                 │
                 ▼
            PostgreSQL
                 │
                 ▼
          Human Approval
```

This architecture keeps AI useful while ensuring that financial calculations, matching, routing, and approval controls remain deterministic, testable, and auditable.
