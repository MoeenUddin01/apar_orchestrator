# Compliance Strategy

## 1. Overview
The Compliance layer ensures the LangGraph AP/AR Orchestrator adheres to relevant legal, regulatory, and industry standards, including data privacy, financial reporting integrity, and system security.

## 2. Regulatory Alignment & Architecture Mapping

### 2.1 Financial Regulations (SOX, SOC 1/2)
- **Segregation of Duties**: Enforced via the Governance Maker-Checker model.
- **Financial Accuracy**: Deterministic reconciliation nodes ensure that AI-generated summaries match line-item totals perfectly before finalizing state.
  - **Implementation Files**: [`src/finance/reconciliation.py`](file:///home/moeen/projects/apar_orchestrator/src/finance/reconciliation.py).
- **System Integrity**: Immutable audit logs guarantee that the sequence of automated decisions cannot be altered post-execution.

### 2.2 Data Privacy (GDPR, CCPA)
- **Data Minimization & PII Redaction**: The orchestration graph masks Personally Identifiable Information (PII) such as SSNs, personal addresses, and bank details before they are sent to external LLM APIs.
  - **Implementation Files**: 
    - [`src/core/security/redaction.py`](file:///home/moeen/projects/apar_orchestrator/src/core/security/redaction.py): Utilities for identifying and masking PII.
    - [`src/llm/middleware.py`](file:///home/moeen/projects/apar_orchestrator/src/llm/middleware.py): Hook to apply redaction right before the LLM API call.
- **Data Retention**: Configurable TTL (Time-To-Live) for temporary graph states.
  - **Implementation Files**: [`src/database/retention_jobs.py`](file:///home/moeen/projects/apar_orchestrator/src/database/retention_jobs.py) (Database cleanup scripts).

## 3. Explainability and Traceability
Compliance in AI-driven financial systems requires explainability. Every LLM decision (e.g., "Invoice matches PO") must be accompanied by a generated rationale.
- **Implementation Files**:
  - [`src/domain/compliance_state.py`](file:///home/moeen/projects/apar_orchestrator/src/domain/compliance_state.py): Pydantic models enforcing rationale fields in graph state outputs.
