# AP/AR Orchestrator — AI Coding Agent Instructions

## 1. Project Overview
AP/AR Orchestrator automates Accounts Payable (AP) and Accounts Receivable (AR) workflows using **LangGraph** (orchestration), **FastAPI** (API), **PostgreSQL** (persistence), **Python** (deterministic rules), **Ollama/Groq** (LLMs), and **uv** (dependency management). 

**Critical Boundary:**
- **Deterministic Operations (Python/SQL):** Calculations, matching, routing, aging, thresholds, and state changes.
- **Probabilistic Operations (LLM):** Document extraction, classification, and language generation. LLMs must *never* be the source of truth for financial calculations or authorization decisions.

## 2. Core Engineering Principles & LLM Policy
- **Deterministic Logic First:** All financial math, matching (3-way, PO, goods receipt), and routing decisions MUST be implemented in Python. 
- **LLM Scope:** Only use LLMs for extracting structured data from unstructured docs, summarizing exceptions, and drafting communications. LLM output must be validated before entering business logic.
- **Source of Truth:** PostgreSQL (financial facts) and LangGraph `FinanceState` (workflow execution state). LLM output is untrusted until validated.

## 3. Architecture & Code Organization
```text
src/apar_orchestrator/
├── api/       # FastAPI routes, HTTP validation (NO business logic)
├── core/      # Config, environment, logging, exceptions
├── domain/    # Schemas and models (ap, ar, common)
├── finance/   # Pure deterministic rules (matching, aging, taxes, routing)
├── database/  # PostgreSQL models, repositories, connections
├── llm/       # LLM clients, extractors, generators, parsers
└── graph/     # LangGraph workflows and FinanceState definitions
```
**Architecture Rule:**
API → LangGraph → LLM Extraction → Validation → Deterministic Finance → Database/Routing/HITL.

## 4. Spec-Driven Development Workflow
1. Read the active spec in `spec/` (Phase 1-6). Implement *only* the current phase.
2. Review existing implementation and affected modules.
3. Ensure state changes are tracked explicitly in `FinanceState` (workflow info, extractions, validations). Avoid unnecessarily large state objects. 
4. Verify tests pass and report validation results.

## 5. Database, Errors, & Logging
- **Database:** Use parameterized queries or project abstractions. No raw SQL construction or direct LLM execution. Keep DB logic out of graph nodes.
- **Errors:** Handle errors at the appropriate layer (e.g., `DatabaseError`) rather than bare `except Exception`. Failures needing decisions must reflect in `FinanceState`.
- **Logging/Secrets:** Log workflow actions for auditability but NEVER log PII, credentials, or full financial documents. Use environment variables (via `.env`) for secrets.

## 6. Testing & Dependency Management
- **uv:** Use `uv sync`, `uv add`, `uv run` (do not use pip or poetry).
- **Testing Philosophy:** Test pure deterministic functions independently before testing FastAPI/LangGraph integrations.
- **Coverage:** Ensure tests cover perfect matches, mismatches, tolerance boundaries, errors, and LLM structured output parsing.

## 7. Coding Standards & Git Rules
- Modern Python with strict type hints, small pure functions, and clear docstrings.
- **Avoid:** Giant nodes, global mutable state, hidden side effects, or duplicate logic.
- **Git:** Keep commits atomic, focused, and prefixed (e.g., `feat:`, `fix:`, `docs:`). Do not commit `.env` or sensitive data.

## 8. Definition of Done
A feature is complete only when:
- It meets the active specification exactly.
- LLM bounds and deterministic logic are properly separated.
- Code has type hints, error handling, and passing unit tests.
- No secrets are introduced and unrelated functionality remains unmodified.
