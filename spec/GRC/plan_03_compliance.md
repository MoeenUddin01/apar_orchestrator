# Implementation Plan: Phase 2 - Data Privacy & Compliance Middleware

## Overview
This phase implements the components described in [`03_Compliance.md`](file:///home/moeen/projects/apar_orchestrator/spec/GRC/03_Compliance.md). It focuses on ensuring data privacy (GDPR, CCPA), enforcing financial accuracy through deterministic reconciliation, and providing explainability/traceability for all LLM decisions.

## Step 1: Compliance Domain Models
**File**: [`src/domain/compliance_state.py`](file:///home/moeen/projects/apar_orchestrator/src/domain/compliance_state.py)
- Create `ComplianceRationale` Pydantic model to enforce explainability (e.g., require a `rationale` field when an LLM makes a classification).
- Create `RedactionResult` model to track what PII was removed from a payload.

## Step 2: Data Privacy & PII Redaction
**File**: [`src/core/security/redaction.py`](file:///home/moeen/projects/apar_orchestrator/src/core/security/redaction.py)
- Implement regex patterns to identify sensitive data (SSNs, Bank Accounts, credit cards, standard PII).
- Implement a `Redactor` class with methods to mask this data (e.g., replacing with `[REDACTED_SSN]`) before it leaves the system.

## Step 3: LLM Privacy Middleware
**File**: [`src/llm/middleware.py`](file:///home/moeen/projects/apar_orchestrator/src/llm/middleware.py)
- Create an interceptor/middleware that wraps the LangChain/Groq API calls.
- Apply the `Redactor` to the prompt text before sending it to the LLM.
- Track redaction metrics and emit a `RedactionResult`.

## Step 4: Financial Accuracy & Reconciliation
**File**: [`src/finance/reconciliation.py`](file:///home/moeen/projects/apar_orchestrator/src/finance/reconciliation.py)
- Build deterministic reconciliation nodes that ensure AI-generated payment summaries match line-item totals perfectly before finalizing state.
- Will complement the existing matching/validation logic by explicitly verifying ledger balances against requested payment amounts.

## Step 5: Data Retention & Cleanup
**File**: [`src/database/retention_jobs.py`](file:///home/moeen/projects/apar_orchestrator/src/database/retention_jobs.py)
- Create background job scripts (or callable functions) to delete LangGraph checkpointer state older than a configured TTL (Time-To-Live).
- Ensures compliance with GDPR/CCPA data minimization and retention limits.

## Step 6: Testing
**File**: [`tests/unit/test_compliance.py`](file:///home/moeen/projects/apar_orchestrator/tests/unit/test_compliance.py)
- Unit tests for the `Redactor` to ensure PII is masked correctly without corrupting financial figures.
- Unit tests for the TTL retention jobs to ensure old records are deleted while active records are kept.
