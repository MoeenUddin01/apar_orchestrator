# 📋 Compliance Strategy Architecture

This document defines the Compliance layer for the LangGraph AP/AR Orchestrator, ensuring adherence to legal, regulatory, and industry standards.

---

## 🎯 1. Core Objectives
- Ensure strict financial accuracy and determinism.
- Guarantee auditability, explainability, and traceability of all actions.
- Enforce data privacy, PII protection, and correct data retention schedules.
- Maintain a strict boundary: **Compliance verifies**, Risk scores, and Governance authorizes.

---

## 🏗️ 2. Core Components & Architecture Mapping

### 2.1 Financial Accuracy & Reconciliation
**Objective**: Ensure LLM-generated values never override deterministic financial math.

- **Mitigation**: Decimal-safe reconciliation verifies line-item totals, tax/discounts, and PO matching against requested payments.
- **Implementation**: [`src/finance/reconciliation.py`](file:///home/moeen/projects/apar_orchestrator/src/finance/reconciliation.py)

### 2.2 PII Detection & Redaction
**Objective**: Mask sensitive data before it reaches external LLM providers.

- **Mitigation**: Regex-based redaction targeting SSNs, bank accounts, credit cards, emails, addresses, and phone numbers. The system outputs a structured `RedactionResult`.
- **Implementation**: [`src/core/security/redaction.py`](file:///home/moeen/projects/apar_orchestrator/src/core/security/redaction.py)

### 2.3 LLM Privacy Middleware
**Objective**: Create a secure boundary preventing raw PII from escaping the orchestration system.

- **Mitigation**: Intercepts prompts, applies the `Redactor`, and tracks redaction metrics *before* generating the external API request.
- **Implementation**: [`src/llm/middleware.py`](file:///home/moeen/projects/apar_orchestrator/src/llm/middleware.py)

### 2.4 Compliance State Models & Explainability
**Objective**: Standardize compliance tracking and force deterministic evidence for decisions.

- **Mitigation**: Pydantic models (e.g., `ComplianceRationale`, `ReconciliationResult`) that reject unstructured justifications (e.g., "The AI determined a match").
- **Implementation**: [`src/domain/compliance_state.py`](file:///home/moeen/projects/apar_orchestrator/src/domain/compliance_state.py)

### 2.5 Data Retention & Cleanup
**Objective**: Prevent indefinite storage of ephemeral or sensitive state data.

- **Mitigation**: Configurable Time-To-Live (TTL) background jobs that sweep expired graph states, memory checkpointers, and LLM metadata (respecting legal holds).
- **Implementation**: [`src/database/retention_jobs.py`](file:///home/moeen/projects/apar_orchestrator/src/database/retention_jobs.py)

---

## ⚖️ 3. Standardized Compliance Checks

Reusable deterministic checks generate structured results (`PASS`/`FAIL` with evidence):

| Code | Check Name | Description |
|---|---|---|
| **COM-001** | Required Invoice Fields | Validates presence of critical vendor/invoice data. |
| **COM-002** | Financial Reconciliation | Verifies math calculations (subtotals vs line items). |
| **COM-003** | PII Handling | Confirms `RedactionResult` was successfully applied. |
| **COM-004** | Audit Event Recorded | Verifies cryptographic audit log generation. |
| **COM-005** | Maker-Checker Requirement | Confirms SoD human-in-the-loop steps. |
| **COM-006** | LLM Output Validation | Confirms deterministic extraction rules passed. |
| **COM-007** | Data Retention Policy | Verifies TTL logic on checkpointer storage. |

---

## 🗺️ 4. Regulatory Mapping
*The system provides technical controls supporting compliance, rather than claiming direct certification.*

- **SOX, SOC 1/2**: Segregation of Duties (via Governance RBAC) and Financial Accuracy (via Reconciliation).
- **GDPR, CCPA**: Data Minimization (via PII Redaction) and Data Retention (via TTL Cleanup).
