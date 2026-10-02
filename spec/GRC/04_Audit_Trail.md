# Audit Trail Architecture

## 1. Overview
The Audit Trail provides a comprehensive, immutable, and searchable record of every significant event, state change, and decision within the AP/AR Orchestrator. This is critical for debugging, accountability, and external audits.

## 2. What to Log & Schema Definition
The system captures granular data at multiple levels: Workflow Events, Node Transitions, LLM Interactions, Human Interventions, and System Errors.

**JSON Schema Structure**:
```json
{
  "event_id": "uuid",
  "timestamp": "ISO-8601",
  "workflow_id": "AP-12345",
  "actor": "system | llm_agent | user_id",
  "event_type": "NODE_ENTRY | LLM_CALL | APPROVAL | ERROR",
  "node_name": "Invoice_Extraction",
  "payload_snapshot": { ... },
  "hash": "sha256(previous_hash + current_event_data)"
}
```
**Implementation Files**:
- `src/domain/audit_schema.py`: Pydantic models defining standard audit events.

## 3. Storage and Immutability
Logs are emitted asynchronously to a centralized, append-only datastore. To guarantee immutability, each log entry contains a cryptographic hash of its contents combined with the hash of the previous event.
**Implementation Files**:
- `src/database/audit_repository.py`: DB interactions for saving append-only logs.
- `src/core/hashing.py`: Utilities for calculating cryptographic hashes.

## 4. LangGraph Implementation
Utilize LangGraph callbacks or dedicated nodes that hook into the graph execution to emit standard audit events without cluttering the business logic inside the nodes.
**Implementation Files**:
- `src/graph/shared/callbacks/audit_logger.py`: LangGraph listeners that automatically trigger during state transitions.
