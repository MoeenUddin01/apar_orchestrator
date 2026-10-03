# 🗺️ Implementation Plan: Compliance Middleware

## 🎯 1. Objective & Scope
Implement the Compliance layer to ensure data privacy (GDPR, CCPA), enforce financial accuracy through deterministic reconciliation, and provide explainability for all LLM decisions.

---

## 🗂️ 2. Target Files & Architecture

| Component | Target File Path | Purpose |
|---|---|---|
| **Domain Models** | [`src/domain/compliance_state.py`](file:///home/moeen/projects/apar_orchestrator/src/domain/compliance_state.py) | `ComplianceRationale`, `RedactionResult`. |
| **PII Redaction** | [`src/core/security/redaction.py`](file:///home/moeen/projects/apar_orchestrator/src/core/security/redaction.py) | Regex-based masking of sensitive data. |
| **Privacy Middleware** | [`src/llm/middleware.py`](file:///home/moeen/projects/apar_orchestrator/src/llm/middleware.py) | Wraps LLM calls to apply redaction before API requests. |
| **Reconciliation** | [`src/finance/reconciliation.py`](file:///home/moeen/projects/apar_orchestrator/src/finance/reconciliation.py) | Deterministic financial math verification. |
| **Data Retention** | [`src/database/retention_jobs.py`](file:///home/moeen/projects/apar_orchestrator/src/database/retention_jobs.py) | TTL cleanup scripts for checkpointer state. |

---

## 🚀 3. Step-by-Step Execution Plan

### Step 1: Compliance Domain Models
**File**: [`src/domain/compliance_state.py`](file:///home/moeen/projects/apar_orchestrator/src/domain/compliance_state.py)
- Create `ComplianceRationale` Pydantic model to enforce explainability.
- Create `RedactionResult` model to track masked PII.

### Step 2: Data Privacy & PII Redaction
**File**: [`src/core/security/redaction.py`](file:///home/moeen/projects/apar_orchestrator/src/core/security/redaction.py)
- Implement regex patterns for SSNs, Bank Accounts, credit cards.
- Implement `Redactor` class methods to mask data (e.g., `[REDACTED_SSN]`).

### Step 3: LLM Privacy Middleware
**File**: [`src/llm/middleware.py`](file:///home/moeen/projects/apar_orchestrator/src/llm/middleware.py)
- Create interceptor wrapping LangChain/Groq API calls.
- Apply `Redactor` to the prompt text before sending to LLM.
- Track metrics and emit `RedactionResult`.

### Step 4: Financial Accuracy & Reconciliation
**File**: [`src/finance/reconciliation.py`](file:///home/moeen/projects/apar_orchestrator/src/finance/reconciliation.py)
- Build deterministic reconciliation nodes.
- Verify ledger balances against requested payment amounts.

### Step 5: Data Retention & Cleanup
**File**: [`src/database/retention_jobs.py`](file:///home/moeen/projects/apar_orchestrator/src/database/retention_jobs.py)
- Create TTL background job scripts to delete old LangGraph checkpointer state.

### Step 6: Testing
**File**: `tests/unit/test_compliance.py`
- Unit tests for `Redactor`.
- Unit tests for TTL retention jobs.
