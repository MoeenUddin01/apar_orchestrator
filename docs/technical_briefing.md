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
