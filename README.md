# AP/AR Orchestrator

An AI-assisted finance workflow automation system for **Accounts Payable (AP)** and **Accounts Receivable (AR)**.

This project combines **LangGraph orchestration**, **FastAPI**, **PostgreSQL**, deterministic Python financial rules, and controlled LLM capabilities (via Ollama/Groq) to automate repetitive finance workflows while maintaining strict, auditable financial boundaries.

## 1. Core Architecture & Philosophy

The central design principle is strict separation of concerns:
**LLM = Understand and Generate Language**
**Python = Calculate and Decide Financial Outcomes**

- **Automated Workflows:** Invoice intake, data extraction, validation, PO/goods receipt lookup, 3-way matching, payment reconciliation, aging calculations, and routing.
- **Human-in-the-Loop (HITL):** High-value transactions, mismatches, or exceptions are automatically paused via LangGraph checkpointing for human review before resuming.
- **Strict Boundaries:** LLMs are **not** permitted to perform financial math, 3-way matching, routing decisions, or payment authorization.

## 2. Technology Stack

- **Core & API:** Python, FastAPI, uv (package management)
- **Orchestration:** LangGraph (with `FinanceState`)
- **Database:** PostgreSQL
- **AI/LLM:** Ollama / Groq
- **Testing:** Pytest

## 3. Project Structure

```text
src/
├── api/       # FastAPI endpoints and HTTP validation
├── core/      # Config, environment, and logging
├── domain/    # Shared financial domain schemas
├── finance/   # Deterministic financial rules (matching, aging, taxes)
├── database/  # PostgreSQL models and repositories
├── llm/       # LLM extraction, generation, and parsing
└── graph/     # LangGraph workflows and state
tests/         # Pytest suite
scripts/       # Operational and evaluation scripts
spec/          # Phase-by-phase development specifications
```

## 4. Workflows

### Accounts Payable (AP)
`Invoice Intake → LLM Data Extraction → Python Validation → DB PO/Receipt Lookup → Deterministic 3-Way Match → Routing (Matched / Exception)`

### Accounts Receivable (AR)
`Payment Intake → LLM Extraction/Classification → DB Invoice Lookup → Python Payment Reconciliation → Outstanding & Aging Calculation → Routing`

## 5. Local Development

**Prerequisites:** Python, uv, PostgreSQL, and a configured LLM provider.

1. **Install and Sync:**
   ```bash
   git clone <repository-url> apar-orchestrator
   cd apar-orchestrator
   uv sync
   ```

2. **Configuration:**
   Copy `.env.example` to `.env` and set your secrets (e.g., `DATABASE_URL`, `OLLAMA_BASE_URL`, `GROQ_API_KEY`). **Never commit `.env`.**

3. **Run Application:**
   ```bash
   uv run uvicorn api.main:app --app-dir src --reload
   ```

4. **Run Tests:**
   ```bash
   uv run pytest -v
   ```

## 6. Development Roadmap

The project is driven by phase-by-phase specifications (found in `spec/`):
- [ ] **Phase 1:** Foundation (DB, API, State)
- [ ] **Phase 2:** AP MVP (Intake to Matching)
- [ ] **Phase 3:** AR MVP (Intake to Aging)
- [ ] **Phase 4:** Human-in-the-Loop (HITL) Interruption
- [ ] **Phase 5:** AI Communication Drafts
- [ ] **Phase 6:** Evaluation & Hardening

*Goal: Prove AI can be safely integrated into finance by marrying probabilistic extraction with deterministic, auditable accounting controls.*
