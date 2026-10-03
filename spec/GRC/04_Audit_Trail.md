# 🗃️ Audit Trail Architecture Specification

This document defines the structured, searchable, and cryptographically verifiable Audit Trail for the AP/AR Orchestrator. 

---

## 🎯 1. Core Objectives
- Provide an immutable record of events, decisions, approvals, and financial actions.
- Support debugging, accountability, compliance evidence, and financial audits.
- Act exclusively as an **evidence and traceability layer**, not an authorization layer.

---

## 🗂️ 2. Event Types & Schema

### 2.1 Audit Event Categories
| Category | Event Types |
|---|---|
| **WORKFLOW** | `WORKFLOW_STARTED`, `WORKFLOW_COMPLETED`, `WORKFLOW_FAILED` |
| **NODE** | `NODE_ENTRY`, `NODE_EXIT` |
| **LLM** | `LLM_CALL`, `LLM_VALIDATION` |
| **SECURITY & RISK** | `SECURITY_FINDING`, `RISK_ASSESSMENT`, `RISK_FLAGGED`, `SECURITY_ERROR` |
| **COMPLIANCE** | `COMPLIANCE_ASSESSMENT`, `COMPLIANCE_FINDING`, `RECONCILIATION_RESULT` |
| **GOVERNANCE** | `GOVERNANCE_DECISION`, `MAKER_CHECKER_REQUESTED`, `MAKER_APPROVED`, `MAKER_REJECTED` |
| **FINANCIAL** | `FINANCIAL_ACTION_REQUESTED`, `FINANCIAL_ACTION_EXECUTED`, `FINANCIAL_ACTION_FAILED` |
| **EXTERNAL** | `EXTERNAL_API_CALL`, `EXTERNAL_API_FAILURE`, `ERROR` |

### 2.2 JSON Schema Target (`AuditEvent`)
- `event_id` (uuid)
- `timestamp` (ISO-8601)
- `workflow_id` & `correlation_id`
- `actor_type` & `actor_id`
- `event_type` & `status`
- `summary` & `metadata`
- `previous_hash` & `event_hash` (Cryptographic chain)
- **Implementation**: [`src/domain/audit_schema.py`](file:///home/moeen/projects/apar_orchestrator/src/domain/audit_schema.py)

---

## 🏗️ 3. Component Architecture & Implementation Mapping

### 3.1 Cryptographic Hash Chaining & Storage
**Objective**: Ensure software-level tamper detection regardless of the underlying storage medium.

- **Mitigation**: Each event computes `event_hash = SHA256(previous_hash + canonical_event_data)`. The chain can be verified from genesis to head.
- **Storage**: Append-only SQL repository that automatically applies PII redaction to summaries/metadata before saving.
- **Implementation**: 
  - [`src/core/hashing.py`](file:///home/moeen/projects/apar_orchestrator/src/core/hashing.py) (Hash calculation and chain verification)
  - [`src/database/audit_repository.py`](file:///home/moeen/projects/apar_orchestrator/src/database/audit_repository.py) (Append-only storage and queries)

### 3.2 LangGraph Execution Integration
**Objective**: Automatically capture state transitions without cluttering business logic nodes.

- **Mitigation**: Shared callback listeners hook into the LangGraph event stream (`on_node_entry`, `on_node_exit`, `on_llm_call`, etc.).
- **Implementation**: [`src/graph/shared/callbacks/audit_logger.py`](file:///home/moeen/projects/apar_orchestrator/src/graph/shared/callbacks/audit_logger.py)

### 3.3 Query & Verification APIs
**Objective**: Provide interfaces for auditors, reporting dashboards, and internal system checks.

- **Endpoints**:
  - `GET /api/v1/audit/events/{event_id}`
  - `GET /api/v1/audit/workflows/{workflow_id}`
  - `GET /api/v1/audit/workflows/{workflow_id}/verify` (Triggers cryptographic chain check)
  - `GET /api/v1/audit/reports`
- **Implementation**: [`src/api/routes/audit.py`](file:///home/moeen/projects/apar_orchestrator/src/api/routes/audit.py)

---

## 🗺️ 4. Integration Context

```text
Security    ➡️ Detects
Risk        ➡️ Assesses
Compliance  ➡️ Verifies
Governance  ➡️ Authorizes
Maker       ➡️ Approves
Financial   ➡️ Executes
Audit Trail ➡️ Records & Provides Cryptographic Evidence
```
