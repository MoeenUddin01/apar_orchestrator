# AP/AR Orchestrator — AI Coding Agent Instructions

## 1. Project Overview

AP/AR Orchestrator is a finance workflow automation system for **Accounts Payable (AP)** and **Accounts Receivable (AR)**.

The system uses:

* **LangGraph** for workflow orchestration and state management
* **FastAPI** for the application/API layer
* **PostgreSQL** for financial data and workflow persistence
* **Python** for deterministic financial calculations and business rules
* **Ollama and/or Groq** for controlled LLM capabilities
* **uv** for Python environment and dependency management
* **Pytest** for automated testing

The system is intentionally designed with a strict boundary between:

1. **Probabilistic AI operations** — document extraction, classification where explicitly allowed, and natural-language generation.
2. **Deterministic financial operations** — calculations, matching, aging, thresholds, routing, and financial state changes.

The LLM must never become the source of truth for financial calculations or authorization decisions.

---

# 2. Core Engineering Principles

## 2.1 Deterministic Financial Logic

All financial calculations and business-critical financial decisions MUST be implemented using deterministic Python code.

This includes, but is not limited to:

* Amount calculations
* Tax calculations
* Currency calculations
* Quantity calculations
* Variance calculations
* Invoice totals
* Outstanding balances
* Payment reconciliation
* Invoice matching
* Purchase-order matching
* Goods-receipt matching
* 3-way matching
* Aging calculations
* Aging buckets
* Tolerance checks
* Approval thresholds
* Exception routing
* Payment authorization rules

Do NOT ask an LLM to perform these operations.

### Incorrect

```text
LLM → "The invoice appears to match the purchase order."
```

### Correct

```text
LLM
  ↓
Extract structured invoice data
  ↓
Python validation
  ↓
Python deterministic matching
  ↓
Python routing decision
```

The LLM may provide extracted data, but deterministic Python must make the financial decision.

---

# 3. LLM Usage Policy

LLMs are restricted to tasks where probabilistic language understanding provides value.

Allowed uses include:

* Extracting structured information from unstructured documents
* Parsing invoice information
* Parsing payment/remittance information
* Controlled classification when explicitly defined by the active specification
* Generating natural-language summaries
* Drafting customer/vendor communications
* Summarizing financial exceptions using already-computed facts

LLMs MUST NOT:

* Perform financial arithmetic
* Calculate balances
* Calculate taxes
* Calculate aging
* Perform 3-way matching
* Determine whether a payment is authorized
* Decide whether an invoice should be paid
* Override deterministic business rules
* Change approval thresholds
* Directly modify financial records
* Bypass human approval
* Make autonomous payment decisions

LLM output must be validated before it enters deterministic business logic.

---

# 4. Source of Truth

The system must have clear sources of truth.

### Financial facts

PostgreSQL and deterministic application logic are the source of truth.

### Extracted information

LLM output is considered **untrusted input** until validated.

### Workflow state

LangGraph `FinanceState` is the source of truth for the state of an active workflow execution.

### Business rules

Business rules belong in deterministic Python modules, not prompts.

---

# 5. Spec-Driven Development

This project follows **Spec-Driven Development (SDD)**.

Before implementing a feature:

1. Read `CLAUDE.md`.
2. Identify the active project phase.
3. Read the corresponding file inside `spec/`.
4. Inspect the existing implementation.
5. Determine which modules are affected.
6. Implement only the functionality defined by the active specification.
7. Add or update tests.
8. Run the relevant test suite.
9. Report what was changed and how it was validated.

Do NOT implement future-phase functionality unless explicitly requested.

---

# 6. Project Phases

The planned development phases are:

### Phase 1 — Foundation

Project infrastructure:

* uv configuration
* Application package
* Configuration management
* Logging
* FastAPI foundation
* PostgreSQL connection
* Initial database structure
* LangGraph setup
* `FinanceState`
* Basic tests

### Phase 2 — AP MVP

Accounts Payable workflow:

```text
Invoice
  ↓
Receive
  ↓
Extract
  ↓
Validate
  ↓
Lookup PO
  ↓
Lookup Goods Receipt
  ↓
3-Way Match
  ↓
Route
```

### Phase 3 — AR MVP

Accounts Receivable workflow:

```text
Payment / Remittance
  ↓
Extract / Classify
  ↓
Identify Customer
  ↓
Lookup Invoices
  ↓
Reconcile Payment
  ↓
Calculate Outstanding Balance
  ↓
Calculate Aging
  ↓
Route
```

### Phase 4 — HITL

Human-in-the-loop workflow:

* Exception review
* High-value approval
* Human decisions
* LangGraph interrupts/checkpointing
* Workflow resume

### Phase 5 — AI Communication

LLM-generated communication:

* Vendor communication
* Customer payment reminders
* Exception summaries
* Internal workflow summaries

Generated communication must be based on deterministic facts produced by the system.

### Phase 6 — Evaluation

Evaluation of:

* AP workflows
* AR workflows
* Perfect matches
* Mismatches
* Exceptions
* Aging calculations
* Routing
* LLM extraction
* LLM-generated communication

---

# 7. Architecture

The project should maintain the following high-level separation:

```text
                     FastAPI
                        │
                        ▼
                  LangGraph
                 Orchestration
                        │
             ┌──────────┴──────────┐
             │                     │
             ▼                     ▼
            AP                     AR
             │                     │
             ▼                     ▼
       LLM Extraction        LLM Extraction
             │                     │
             ▼                     ▼
       Validation              Validation
             │                     │
             └──────────┬──────────┘
                        ▼
              Deterministic Finance
                        │
             ┌──────────┴──────────┐
             │                     │
             ▼                     ▼
         PostgreSQL          Routing / HITL
```

Each layer must have a clear responsibility.

---

# 8. Source Code Organization

The recommended application structure is:

```text
src/
└── apar_orchestrator/
    ├── api/
    ├── core/
    ├── domain/
    ├── finance/
    ├── database/
    ├── llm/
    └── graph/
```

## `api/`

Contains FastAPI application setup and HTTP routes.

The API layer should:

* Validate HTTP input
* Call application/workflow functionality
* Return appropriate responses
* Handle API-level errors

The API layer should NOT contain financial calculations.

---

## `core/`

Contains application-wide infrastructure:

* Configuration
* Environment handling
* Logging
* Shared exceptions
* Constants where appropriate

Do not place business logic here.

---

## `domain/`

Contains domain-level concepts and schemas for AP, AR, and shared finance concepts.

Examples:

```text
domain/
├── ap/
├── ar/
└── common/
```

Keep domain definitions independent from FastAPI and LLM implementation details where possible.

---

## `finance/`

Contains deterministic financial business logic.

Examples:

```text
finance/
├── matching.py
├── aging.py
├── taxes.py
└── routing.py
```

Functions in this package should preferably be:

* Pure
* Deterministic
* Independently testable
* Explicitly typed

Do not call an LLM from this package.

---

## `database/`

Contains PostgreSQL integration.

Responsibilities include:

* Database connection
* Models
* Queries
* Repositories
* Persistence

Database access should not be scattered throughout LangGraph nodes.

Prefer repository functions/classes that provide clear interfaces to the workflow layer.

---

## `llm/`

Contains all LLM-related functionality.

Recommended separation:

```text
llm/
├── clients/
├── extractors/
├── generators/
└── parsers/
```

Keep provider-specific code isolated.

For example, switching from Ollama to Groq should not require rewriting AP or AR workflows.

---

## `graph/`

Contains LangGraph workflow orchestration.

Recommended structure:

```text
graph/
├── state.py
├── common/
├── ap/
│   ├── nodes.py
│   └── graph.py
└── ar/
    ├── nodes.py
    └── graph.py
```

LangGraph nodes should orchestrate operations rather than contain large amounts of business logic.

A node should generally:

1. Read required state.
2. Call the appropriate service/function.
3. Update the state.
4. Return the state update.

---

# 9. FinanceState Rules

All LangGraph workflows must use the shared `FinanceState`.

Do not hide important workflow information inside local variables that other nodes cannot access.

State should contain only information needed for workflow execution.

Examples of state categories:

```text
workflow information
input information
extracted information
validation results
database records
matching results
financial calculations
routing decisions
approval status
communication drafts
errors
```

Avoid creating an unnecessarily large state object.

When adding a new state field:

1. Determine why it is required.
2. Add an appropriate type.
3. Document its purpose.
4. Update affected nodes.
5. Add/update tests.

---

# 10. Database Rules

Database operations must be explicit and predictable.

Rules:

* Use parameterized queries or the project's database abstraction.
* Never construct unsafe SQL using string interpolation.
* Handle database exceptions.
* Do not expose raw database exceptions to API users.
* Keep database access separate from financial calculations.
* Do not allow LLM output to directly execute SQL.
* Validate data before persistence.
* Use transactions where multiple related updates must succeed together.

---

# 11. Error Handling

Errors must be handled at the appropriate layer.

Expected failures should produce useful, actionable information.

Examples:

```text
Invoice extraction failed.
Purchase order was not found.
Goods receipt was not found.
Invoice amount exceeds configured tolerance.
Payment could not be matched.
Database operation failed.
Human approval is required.
```

Do not silently swallow exceptions.

Avoid:

```python
try:
    ...
except Exception:
    pass
```

Prefer:

```python
try:
    ...
except DatabaseError as exc:
    logger.exception("Failed to retrieve purchase order")
    ...
```

Errors that affect workflow decisions should be represented in `FinanceState` when appropriate.

---

# 12. Logging

Use structured, meaningful logs.

Logs should help answer:

* Which workflow was executed?
* Which stage failed?
* Which entity was being processed?
* What decision was made?
* Why did routing occur?
* Was human approval required?

Never log:

* API keys
* Passwords
* Database credentials
* Full sensitive documents
* Secrets
* Unnecessary personal/financial information

Use identifiers rather than dumping entire financial documents into logs.

---

# 13. Configuration and Secrets

Secrets must come from environment variables or approved configuration mechanisms.

Never hard-code:

```text
API keys
passwords
database credentials
tokens
private endpoints
```

`.env` is for local development.

`.env` MUST NOT be committed to Git.

Maintain:

```text
.env.example
```

containing variable names and safe placeholder values.

---

# 14. Dependency Management

Use `uv` for Python dependency and environment management.

Preferred commands:

```bash
uv sync
uv add <package>
uv remove <package>
uv run <command>
```

Do not use:

```bash
pip install ...
poetry add ...
```

unless explicitly required for a compatibility/debugging reason.

---

# 15. Testing Requirements

Tests are required for deterministic business logic.

At minimum, test:

### AP

* Perfect 3-way match
* Quantity mismatch
* Price mismatch
* Missing purchase order
* Missing goods receipt
* Tolerance boundary
* Above-tolerance exception

### AR

* Full payment
* Partial payment
* Unmatched payment
* Outstanding balance
* Aging calculation
* Aging bucket boundaries
* Overdue routing

### Workflow

Test:

* Correct node execution
* Conditional routing
* Error paths
* HITL interruption/resume
* State updates

### LLM

LLM tests should focus on:

* Structured output validity
* Parser behavior
* Invalid output handling
* Required-field validation

Do not rely exclusively on live LLM calls in unit tests.

---

# 16. Testing Philosophy

Prefer:

```text
Pure function
      ↓
Unit test
```

before:

```text
FastAPI
  ↓
LangGraph
  ↓
Database
  ↓
LLM
  ↓
Unit test
```

Keep deterministic financial rules easy to test independently.

Integration tests should verify that components work together.

---

# 17. Coding Standards

Use modern Python with strict type hints.

Every public function should have:

* Type hints
* Clear parameters
* Clear return type
* Useful docstring when behavior is non-obvious

Prefer small functions with one responsibility.

Avoid:

* Giant functions
* Giant LangGraph nodes
* Global mutable state
* Hidden side effects
* Duplicate business logic
* Magic numbers
* Hard-coded credentials
* Unnecessary abstractions

---

# 18. Adding a New Feature

Before implementing a new feature:

### Step 1

Identify the phase.

### Step 2

Read its specification.

### Step 3

Identify affected layers.

For example:

```text
API
Graph
Finance
Database
LLM
Tests
```

### Step 4

Implement the smallest coherent change.

### Step 5

Add tests.

### Step 6

Run validation.

### Step 7

Review the implementation against the specification.

### Step 8

Report:

```text
Implemented:
- ...

Files changed:
- ...

Tests:
- ...

Validation:
- ...

Known limitations:
- ...
```

---

# 19. Git Rules

Keep commits focused.

Prefer:

```text
feat: implement AP three-way matching
feat: add AR aging calculation
test: add AP matching edge cases
fix: handle missing purchase order
docs: update AP workflow specification
```

Avoid large commits containing unrelated changes.

Do not commit:

```text
.env
credentials
secrets
database dumps
generated sensitive financial data
large temporary files
```

---

# 20. Definition of Done

A feature is not complete merely because the code runs.

A feature is considered complete when:

* The active specification is satisfied.
* Code follows the project architecture.
* Deterministic rules are separated from LLM functionality.
* Appropriate type hints are present.
* Error handling exists.
* Tests are implemented.
* Relevant tests pass.
* No secrets are introduced.
* Documentation is updated when necessary.
* No unrelated functionality was modified.

---

# 21. Agent Behavior

When working on this project:

### DO

* Inspect before modifying.
* Follow the active specification.
* Keep changes modular.
* Explain architectural decisions when necessary.
* Add tests.
* Prefer deterministic logic for financial operations.
* Keep LLM boundaries explicit.
* Reuse existing abstractions.
* Report validation results.

### DO NOT

* Invent unspecified features.
* Rewrite unrelated files.
* Move business logic into prompts.
* Allow LLMs to perform financial calculations.
* Bypass approval workflows.
* Hard-code secrets.
* Add dependencies without justification.
* Delete tests to make them pass.
* Ignore failing tests.
* Create duplicate implementations of existing logic.

---

# 22. Final Architectural Rule

When uncertain about where functionality belongs, use this decision process:

```text
Is it an HTTP concern?
        ↓
      api/

Is it configuration/infrastructure?
        ↓
      core/

Is it financial/business logic?
        ↓
      finance/

Is it database persistence?
        ↓
      database/

Is it LLM interaction?
        ↓
      llm/

Is it workflow orchestration?
        ↓
      graph/

Is it a domain concept/schema?
        ↓
      domain/
```

The goal is to keep the system understandable, testable, auditable, and safe for financial workflows.
