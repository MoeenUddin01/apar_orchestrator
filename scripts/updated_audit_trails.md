# Audit Trail Architecture

## 1. Overview

The Audit Trail provides a structured and searchable record of important events, decisions, approvals, errors, and financial actions within the AP/AR Orchestrator.

It supports:

- Debugging
- Accountability
- Risk and Compliance evidence
- Decision traceability
- Financial audit support

The Audit Trail records what happened but does not authorize or execute financial actions.

---

## 2. What to Log & Schema Definition

The system should capture:

- Workflow events
- Node transitions
- LLM interactions
- Security findings
- Risk assessments
- Compliance checks
- Governance decisions
- Maker-Checker approvals/rejections
- Financial actions
- External API calls
- System errors

### JSON Schema

```json
{
  "event_id": "uuid",
  "timestamp": "ISO-8601",
  "workflow_id": "AP-12345",
  "correlation_id": "uuid",
  "actor_type": "SYSTEM | USER | LLM_AGENT | SERVICE",
  "actor_id": "risk-service",
  "event_type": "RISK_ASSESSMENT",
  "node_name": "Risk_Assessment",
  "status": "SUCCESS",
  "result": "HIGH_RISK",
  "summary": "Invoice requires human review",
  "evidence_refs": [],
  "metadata": {},
  "previous_hash": "sha256...",
  "event_hash": "sha256..."
}
```

### Main Event Types

```text
WORKFLOW_STARTED
WORKFLOW_COMPLETED
WORKFLOW_FAILED
NODE_ENTRY
NODE_EXIT
LLM_CALL
LLM_VALIDATION
SECURITY_FINDING
RISK_ASSESSMENT
RISK_FLAGGED
COMPLIANCE_ASSESSMENT
COMPLIANCE_FINDING
RECONCILIATION_RESULT
GOVERNANCE_DECISION
MAKER_CHECKER_REQUESTED
MAKER_APPROVED
MAKER_REJECTED
FINANCIAL_ACTION_REQUESTED
FINANCIAL_ACTION_EXECUTED
FINANCIAL_ACTION_FAILED
EXTERNAL_API_CALL
EXTERNAL_API_FAILURE
ERROR
SECURITY_ERROR
```

### Implementation File

- `src/domain/audit_schema.py` — Pydantic models defining standard audit events.

---

## 3. Storage, Hashing & Data Protection

Audit events should be stored in an append-only repository.

Each event contains a hash of the current event and the previous event:

```text
event_hash = SHA256(previous_hash + canonical_event_data)
```

This provides **tamper detection** through hash chaining.

> Hashing alone does not make storage physically immutable. Do not claim immutability unless actual immutable/WORM storage is implemented.

Sensitive information must not be unnecessarily stored in audit logs.

Do not store:

- Passwords
- API keys
- Access tokens
- Unredacted PII
- Unnecessary bank/account information
- Unnecessary raw LLM prompts or responses

Use the existing redaction layer before persistence.

### Implementation Files

- `src/database/audit_repository.py` — stores and retrieves append-only audit events.
- `src/core/hashing.py` — hash generation and chain verification.
- `src/core/security/redaction.py` — sensitive data redaction.

---

## 4. Risk & Compliance Integration

The Audit Trail must record important events from the Risk and Compliance layers.

### Risk Events

Record:

- Risk level
- Risk flags
- Recommended action
- Evidence references

Example:

```text
RISK_ASSESSMENT
Risk: HIGH
Action: HUMAN_REVIEW_RECOMMENDED
```

### Compliance Events

Record:

- Compliance status
- Compliance findings
- Reconciliation results
- Evidence references

Example:

```text
COMPLIANCE_ASSESSMENT
Status: PASS
Check: COM-002
```

The Audit Trail records these results but does not make the Risk or Compliance decisions.

---

## 5. Governance, Maker-Checker & Financial Actions

Record the complete authorization path:

```text
Risk Assessment
      ↓
Compliance
      ↓
Governance Decision
      ↓
Maker-Checker Approval
      ↓
Financial Action
```

Important events:

- `GOVERNANCE_DECISION`
- `MAKER_CHECKER_REQUESTED`
- `MAKER_APPROVED`
- `MAKER_REJECTED`
- `FINANCIAL_ACTION_REQUESTED`
- `FINANCIAL_ACTION_EXECUTED`
- `FINANCIAL_ACTION_FAILED`

This allows the team to reconstruct why and how a financial action occurred.

---

## 6. LangGraph Implementation

Use LangGraph callbacks/listeners or shared audit infrastructure to automatically generate audit events.

The audit implementation should capture:

- Workflow ID
- Node name
- Node entry/exit
- Execution status
- Errors
- Decision/evidence references

Business nodes should not contain duplicated audit logic.

### Implementation File

- `src/graph/shared/callbacks/audit_logger.py` — LangGraph audit callbacks/listeners.

---

## 7. Audit Integrity & Failure Handling

The system should provide:

```text
get_event(event_id)
get_workflow_events(workflow_id)
get_correlation_events(correlation_id)
verify_chain(workflow_id)
```

Critical audit events such as:

- Governance authorization
- Maker approval
- Financial execution
- Security decisions

must not silently disappear if audit persistence fails.

Use retry, durable handling, or controlled failure.

---

## 8. Testing

Create/update:

- `tests/unit/test_audit_trail.py`

Tests should cover:

- Audit schema validation
- Event creation
- Hash generation
- Hash-chain verification
- Tampering detection
- PII redaction
- Append-only behavior
- Risk events
- Compliance events
- Governance events
- Maker-Checker events
- Financial action events
- LangGraph callbacks
- Audit persistence failures

---

## 9. Architecture Principle

```text
Security → Detects
Risk → Assesses
Compliance → Verifies
Governance → Authorizes
Maker-Checker → Approves
Financial Action → Executes
Audit Trail → Records & provides evidence
```

The Audit Trail is an **evidence and traceability layer**, not an authorization layer.

---

## 10. Implementation Requirement

Before implementation:

1. Inspect existing audit-related files.
2. Reuse existing architecture where possible.
3. Do not rewrite unrelated components.
4. Integrate with the existing Risk and Compliance layers.
5. Keep sensitive data protected.
6. Add tests for all critical audit behavior.

After implementation, report:

- Files changed
- Audit events implemented
- Hash-chain implementation
- Privacy/redaction handling
- Risk/Compliance integration
- LangGraph integration
- Tests and results
- Remaining limitations
