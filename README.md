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
*   `src/api/` - FastAPI routing and endpoints.
*   `src/core/` - Application config and centralized logging.
*   `src/database/` - SQLAlchemy models, async connections, and repository patterns.
*   `src/domain/` - Pure Pydantic schemas representing core financial entities.
*   `src/finance/` - **Deterministic boundary**: contains pure Python math for 3-way matching, aging, and HITL routing policies.
*   `src/graph/` - LangGraph state machine definitions, nodes, and conditional edge logic for AP and AR.
*   `src/llm/` - **Probabilistic boundary**: contains LLM prompt templates and structured output wrappers.
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
*   **AP Workflow**: `extract_invoice` → `validate_invoice` → `lookup_db` (Purchase Orders & Goods Receipts) → `match_3_way` (Math) → **Decision Router** (Approve / Exception / HITL).
    *   *If Exception/HITL:* Routes to `generate_discrepancy` → pauses at `human_review`.
*   **AR Workflow**: `extract_remittance` → `lookup_invoices` (DB lookup) → `reconcile_payment` → `calculate_aging` → **Decision Router** (Closed / Partial / Overdue).
    *   *If Overdue:* Routes to `generate_overdue` → pauses at `human_review`.

**HITL Implementation Strategy:**
The workflows utilize LangGraph's `MemorySaver()` checkpointer. During graph compilation, `interrupt_before=["human_review"]` is defined. When the graph reaches the `human_review` node, execution halts, persisting the state using the provided `thread_id` (mapped to `workflow_id`). The API layer exposes a `/resume` endpoint which injects `hitl_input` into the state and calls `ainvoke` with the same `thread_id` to complete the graph.

---

## 3. The AI / Deterministic Boundary (Crucial for Evaluation)
To prevent the LLM from hallucinating financial figures or autonomously authorizing payments, a hard barrier exists between probabilistic reasoning and deterministic execution.

**Probabilistic LLM Boundaries:**
1.  **Document Extraction**: `src/llm/extractors/invoice_extractor.py` and `remittance_extractor.py`. LLMs are restricted to parsing raw text/JSON into Pydantic models. They perform NO calculations. (Regex fallbacks exist for resilience).
2.  **Communication Drafts**: `src/llm/generators/communications.py`. LLMs draft the text for discrepancy notices and overdue reminders using *deterministic facts* injected into prompts as context.

**Deterministic Math Boundaries:**
1.  **3-Way Matching**: `src/finance/matching.py`. Evaluates quantity, unit price, totals, and tolerances using standard Python floating-point logic. 
2.  **Routing & HITL Rules**: `src/finance/routing.py`. Dictates the exact threshold logic (e.g., invoices > $10,000 or mismatch variance > $10.00).
*The LLM never calls these functions and never influences the routing decision output.*

---

## 4. Database & API Integration
**FastAPI Endpoints:**
The service exposes the following domain-driven endpoints:
*   `POST /ap/process-invoice` — Ingests a new vendor invoice and initiates the LangGraph execution.
*   `GET /ap/{workflow_id}/state` — Retrieves the current state of a paused AP execution.
*   `POST /ap/{workflow_id}/resume` — Injects executive approval (APPROVE/REJECT) to a paused AP execution.
*(The equivalent routes exist for AR at `/ar/process-payment`, `/ar/{workflow_id}/state`, etc.)*

**Database Seeding & Querying:**
The application connects to a Supabase PostgreSQL instance. We established the schema using `Base.metadata.create_all` and seeded it using `scripts/setup_postgres.py` with both edge-case test rows and batch CSV data.
Repository classes (`ap_repository.py` and `ar_repository.py`) execute non-blocking queries utilizing SQLAlchemy's `AsyncSessionLocal` to fetch required truth records (Purchase Orders, Goods Receipts, and Open Invoices) during graph traversal.

---

## 5. Testing & Validation
The system currently maintains robust unit and integration tests executing via `pytest` and `pytest-asyncio`. 
Crucially, testing infrastructure has been isolated using `poolclass=NullPool` on the async DB engines, preventing `InterfaceError` connection pooling anomalies across async test loops.

**Validated Scenarios (Green Test Suite):**
*   **AP - Perfect Match:** `test_ap_workflow_perfect_match`. Full 3-way match passes automatically, routing status to `COMPLETED`.
*   **AP - Tolerance Exceeded:** `test_ap_workflow_tolerance_exceeded`. Identifies variance, automatically triggers exception protocols, generates a discrepancy communication via LLM, and halts execution (`REQUIRES_APPROVAL`).
*   **AP - Exception Routing:** Mismatches correctly bypass approval.
*   **AR - Full Payment:** Validates exact payment application against outstanding DB invoices.
*   **AR - Partial Payment:** Confirms partial balance retention routes strictly to `COMPLETED` without marking the underlying invoice fully paid.
*   **AR - Overdue:** Triggers overdue LLM correspondence and halts for HITL review.


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

The final dependency list will be defined in `pyproject.toml`.

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
│   ├── phase_1_foundation.md
│   ├── phase_2_ap_mvp.md
│   ├── phase_3_ar_mvp.md
│   ├── phase_4_hitl.md
│   ├── phase_5_communication.md
│   └── phase_6_evaluation.md
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

The project is currently **fully implemented** up to Phase 6 (Evaluation & Hardening).

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
```

The project should not be considered production-ready until security, reliability, observability, database migration strategy, testing, and deployment requirements have been properly addressed.

---

# 25. Future Extensions

Possible future extensions include:

- Additional finance workflows
- More document formats
- OCR integration
- ERP integrations
- Accounting-system integrations
- Advanced reconciliation
- Audit trails
- Role-based access control
- Workflow dashboards
- Approval dashboards
- Monitoring and observability
- Production deployment

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
