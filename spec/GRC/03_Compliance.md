# Compliance Strategy

## 1. Overview & Responsibilities
The Compliance layer ensures the LangGraph AP/AR Orchestrator adheres to relevant legal, regulatory, and industry standards. 
It focuses on financial accuracy, auditability, data privacy, data retention, explainability, evidence collection, and compliance-control verification. It provides technical controls that support compliance requirements, maintaining a clear separation from Risk Management (which scores risks) and Governance (which handles authorization).

## 2. Financial Accuracy & Reconciliation
**Implementation Files**: [`src/finance/reconciliation.py`](file:///home/moeen/projects/apar_orchestrator/src/finance/reconciliation.py)

The system performs deterministic financial reconciliation. LLM-generated values must never override deterministic calculations. Decimal-safe financial calculations verify:
- Invoice subtotal vs Line-item totals
- Quantity × Unit Price calculations
- Tax and Discounts
- Invoice Total vs Payment Amount vs PO Amount

## 3. Audit Trail & Immutability
The system records critical workflow events (e.g., workflow started, LLM extraction performed, Maker/Checker decisions, transaction approved/rejected, reconciliation results).
- Each event contains metadata: event ID, timestamp, thread ID, actor, event type, and relevant decision references.
- Unnecessary sensitive financial or PII data is NOT stored in audit logs.
- **Tamper Evidence**: Mechanisms include append-only records, event hashes, hash chaining, and controlled write permissions to detect if an audit record has been modified.

## 4. Compliance State Models
**Implementation Files**: [`src/domain/compliance_state.py`](file:///home/moeen/projects/apar_orchestrator/src/domain/compliance_state.py)

Structured Pydantic models define compliance state, rejecting unstructured strings:
- `ComplianceRationale`: Enforces non-empty explanations for decisions.
- `RedactionResult` & `RedactedEntity`: Track redacted PII counts and hashes.
- `ReconciliationResult` & `ReconciliationItem`: Track matching status and exact discrepancies.

## 5. PII Detection & Redaction
**Implementation Files**: [`src/core/security/redaction.py`](file:///home/moeen/projects/apar_orchestrator/src/core/security/redaction.py)

PII is detected and masked before data reaches external LLMs. 
- Patterns target SSNs, bank accounts, routing numbers, credit cards, emails, personal addresses, and phone numbers. 
- The system generates structured redaction results detailing the categories and counts of sensitive data masked, ensuring that the original value remains available only to the authorized internal workflow when required.

## 6. LLM Middleware
**Implementation Files**: [`src/llm/middleware.py`](file:///home/moeen/projects/apar_orchestrator/src/llm/middleware.py)

Creates a clear middleware boundary ensuring sensitive information is redacted BEFORE the external LLM request is created:
1. Internal AP/AR Data
2. PII Detection / Redaction
3. Prompt Construction
4. External LLM Request
5. LLM Response Validation
Unredacted prompts and responses are not logged to external providers.

## 7. Data Retention
**Implementation Files**: [`src/database/retention_jobs.py`](file:///home/moeen/projects/apar_orchestrator/src/database/retention_jobs.py)

Configurable retention policies clean up expired data categories:
- Temporary graph states
- Memory and Database Checkpointers
- LLM request/response metadata
- Audit records
The cleanup job identifies expired records and deletes them according to configuration, avoiding deletion for records under legal/audit holds.

## 8. Explainability & Traceability
Every AI-assisted decision includes traceable evidence. `ComplianceRationale` requires referencing deterministic evidence (like PO IDs, calculated totals, or reconciliation results). Vague explanations like "The AI determined a match" are rejected. The system retains the underlying evidence used to support the decision.

## 9. AI Output Validation
**Implementation Files**: [`src/llm/validation.py`](file:///home/moeen/projects/apar_orchestrator/src/llm/validation.py)

Compliance operates alongside LLM validation to record deterministic passes/fails for outputs (e.g., extracted totals vs line-item calculations). LLM confidence alone is never treated as compliance evidence.

## 10. Compliance Checks
Reusable deterministic checks generate structured results (`PASS`/`FAIL` with evidence):
- `COM-001` → Required invoice fields
- `COM-002` → Financial reconciliation
- `COM-003` → PII handling
- `COM-004` → Audit event recorded
- `COM-005` → Maker-Checker requirement
- `COM-006` → LLM output validation
- `COM-007` → Data retention policy

## 11. Regulatory Mapping
The system provides technical controls that support compliance requirements, rather than claiming outright certification:
- **SOX, SOC 1/2**: Segregation of Duties (supported by Governance RBAC and Maker-Checker), Financial Accuracy (supported by deterministic reconciliation).
- **GDPR, CCPA**: Data Minimization (supported by PII Redaction) and Data Retention (supported by TTL cleanup scripts).

## 12. Separation From Risk & Governance
Strict boundaries are maintained:
- **Risk Management**: Detects and scores risks (duplicates, unusual transactions, prompt injection).
- **Compliance**: Verifies if required controls/evidence exist (PII redacted, reconciliation passed, retention applied, audit event exists).
- **Governance**: Enforces authorization (RBAC, Maker-Checker rules, approval limits).

## 13. Testing
**Implementation Files**: [`tests/unit/test_compliance.py`](file:///home/moeen/projects/apar_orchestrator/tests/unit/test_compliance.py)

Comprehensive unit tests cover:
- **Reconciliation**: Correct line-item math, tax matching, decimal precision.
- **PII**: Bank account/SSN detection, redaction before LLM requests, preservation of financial metrics.
- **Audit**: Tamper-evidence validation, timestamp existence.
- **Retention**: Expired data identified, active data retained.
- **Explainability**: Decisions reference evidence, missing evidence creates findings.

## 14. Recommended Architecture
```text
                 AP / AR Input
                      │
                      ▼
             Security / Sanitization
                      │
                      ▼
                Risk Assessment
                      │
                      ▼
             Compliance Checks
          ┌───────────┼───────────┐
          ▼           ▼           ▼
     Reconciliation  PII       Audit
          │        Redaction    Trail
          │           │           │
          └───────────┼───────────┘
                      ▼
              Governance / Policy
                      │
                      ▼
                Maker-Checker
                      │
                      ▼
               Financial Action
                      │
                      ▼
                 Audit Event
```
