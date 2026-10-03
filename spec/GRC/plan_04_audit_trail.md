# 🗺️ Implementation Plan: Audit Trail

## 🎯 1. Objective & Scope
Implement an immutable, tamper-evident cryptographic Audit Trail system. Captures workflow events, LLM interactions, risk assessments, and financial executions using SHA-256 hash chaining.

---

## 🗂️ 2. Target Files & Architecture

| Component | Target File Path | Purpose |
|---|---|---|
| **Domain Models** | [`src/domain/audit_schema.py`](file:///home/moeen/projects/apar_orchestrator/src/domain/audit_schema.py) | `ActorType`, `EventType`, `AuditEvent` Pydantic models. |
| **Crypto Hashing** | [`src/core/hashing.py`](file:///home/moeen/projects/apar_orchestrator/src/core/hashing.py) | SHA-256 hash chaining and chain verification. |
| **Redaction** | [`src/core/security/redaction.py`](file:///home/moeen/projects/apar_orchestrator/src/core/security/redaction.py) | PII redaction prior to log persistence. |
| **Database Repo** | [`src/database/audit_repository.py`](file:///home/moeen/projects/apar_orchestrator/src/database/audit_repository.py) | Append-only persistent repository operations. |
| **Graph Callbacks** | [`src/graph/shared/callbacks/audit_logger.py`](file:///home/moeen/projects/apar_orchestrator/src/graph/shared/callbacks/audit_logger.py) | LangGraph `AuditLoggerCallbackHandler`. |
| **REST APIs** | [`src/api/routes/audit.py`](file:///home/moeen/projects/apar_orchestrator/src/api/routes/audit.py) | Endpoints for fetching events and verifying hash chains. |

---

## 🚀 3. Step-by-Step Execution Plan

### Step 1: Domain Models
**File**: [`src/domain/audit_schema.py`](file:///home/moeen/projects/apar_orchestrator/src/domain/audit_schema.py)
- Define `ActorType` and `EventType` enumerations.
- Define `AuditEvent` Pydantic model (including `previous_hash` and `event_hash`).

### Step 2: Cryptographic Hashing Engine
**File**: [`src/core/hashing.py`](file:///home/moeen/projects/apar_orchestrator/src/core/hashing.py)
- `compute_event_hash(event_dict, previous_hash) -> str`.
- `verify_event_hash(event) -> bool`.
- `verify_chain(events) -> Tuple[bool, Optional[str]]`.

### Step 3: Sensitive Data Redaction for Audit Logs
**File**: [`src/core/security/redaction.py`](file:///home/moeen/projects/apar_orchestrator/src/core/security/redaction.py)
- Ensure sensitive data (PII) is redacted before persisting to the database.

### Step 4: Append-Only Database Repository
**File**: [`src/database/audit_repository.py`](file:///home/moeen/projects/apar_orchestrator/src/database/audit_repository.py)
- Implement `log_event`.
- Implement `get_event`, `get_workflow_events`.
- Implement `verify_chain(workflow_id)`.

### Step 5: LangGraph Audit Callback Listener
**File**: [`src/graph/shared/callbacks/audit_logger.py`](file:///home/moeen/projects/apar_orchestrator/src/graph/shared/callbacks/audit_logger.py)
- Implement `AuditLoggerCallbackHandler` to capture node entry/exit and LLM interactions automatically.

### Step 6: API Endpoints
**File**: [`src/api/routes/audit.py`](file:///home/moeen/projects/apar_orchestrator/src/api/routes/audit.py)
- `GET /api/v1/audit/events/{event_id}`.
- `GET /api/v1/audit/workflows/{workflow_id}`.
- `GET /api/v1/audit/workflows/{workflow_id}/verify`.

### Step 7: Unit Tests
**File**: `tests/unit/test_audit_trail.py`
- Test hash chaining, tamper detection, append-only operations, and REST endpoints.
