# GRC & Audit Trail Implementation Phases

## Phase 1: Foundation & Audit Logging
**Goal**: Establish the base infrastructure for capturing immutable logs of the LangGraph execution.
- [ ] Define the unified audit log JSON schema in [`src/domain/audit_schema.py`](file:///home/moeen/projects/apar_orchestrator/src/domain/audit_schema.py).
- [ ] Set up append-only log storage operations in [`src/database/audit_repository.py`](file:///home/moeen/projects/apar_orchestrator/src/database/audit_repository.py).
- [ ] Implement cryptographic hashing for log integrity in [`src/core/hashing.py`](file:///home/moeen/projects/apar_orchestrator/src/core/hashing.py).
- [ ] Implement LangGraph execution listeners (callbacks) in [`src/graph/shared/callbacks/audit_logger.py`](file:///home/moeen/projects/apar_orchestrator/src/graph/shared/callbacks/audit_logger.py).

## Phase 2: Data Privacy & Compliance Middleware
**Goal**: Secure data flowing in and out of the graph and LLMs.
- [ ] Implement PII detection and redaction utilities in [`src/core/security/redaction.py`](file:///home/moeen/projects/apar_orchestrator/src/core/security/redaction.py).
- [ ] Integrate redaction middleware before LLM calls in [`src/llm/middleware.py`](file:///home/moeen/projects/apar_orchestrator/src/llm/middleware.py).
- [ ] Add explainability and compliance rationale fields to graph state in [`src/domain/compliance_state.py`](file:///home/moeen/projects/apar_orchestrator/src/domain/compliance_state.py).
- [ ] Set up data retention and cleanup scripts for checkpointers in [`src/database/retention_jobs.py`](file:///home/moeen/projects/apar_orchestrator/src/database/retention_jobs.py).

## Phase 3: Governance & Role-Based Routing
**Goal**: Implement Maker-Checker and human-in-the-loop workflows.
- [ ] Define RBAC schemas and user role mockups in [`src/core/security/rbac.py`](file:///home/moeen/projects/apar_orchestrator/src/core/security/rbac.py).
- [ ] Build Maker-Checker nodes for AP and AR graphs in [`src/graph/ap/nodes/maker_checker.py`](file:///home/moeen/projects/apar_orchestrator/src/graph/ap/nodes/maker_checker.py) and [`src/graph/ar/nodes/maker_checker.py`](file:///home/moeen/projects/apar_orchestrator/src/graph/ar/nodes/maker_checker.py).
- [ ] Implement deterministic policy rules and thresholds in [`src/finance/policy_rules.py`](file:///home/moeen/projects/apar_orchestrator/src/finance/policy_rules.py).
- [ ] Add endpoints for Checkers to approve/reject actions in [`src/api/routes/governance.py`](file:///home/moeen/projects/apar_orchestrator/src/api/routes/governance.py).

## Phase 4: Risk Mitigation & Anomaly Detection
**Goal**: Protect the system against operational and technical risks.
- [ ] Create the risk state schemas in [`src/domain/risk_state.py`](file:///home/moeen/projects/apar_orchestrator/src/domain/risk_state.py).
- [ ] Implement the core risk scoring engine in [`src/finance/risk_scoring.py`](file:///home/moeen/projects/apar_orchestrator/src/finance/risk_scoring.py).
- [ ] Build the `Risk_Assessment` node in [`src/graph/shared/nodes/risk_assessment.py`](file:///home/moeen/projects/apar_orchestrator/src/graph/shared/nodes/risk_assessment.py) and add it to the AP/AR graphs.
- [ ] Add input sanitization middleware to prevent prompt injection in [`src/core/security/sanitization.py`](file:///home/moeen/projects/apar_orchestrator/src/core/security/sanitization.py).

## Phase 5: Monitoring, Reporting & Refinement
**Goal**: Surface GRC data for stakeholders.
- [ ] Create audit trail query API endpoints for reports in [`src/api/routes/audit.py`](file:///home/moeen/projects/apar_orchestrator/src/api/routes/audit.py).
- [ ] Develop database queries for common compliance reports in [`src/database/audit_repository.py`](file:///home/moeen/projects/apar_orchestrator/src/database/audit_repository.py).
- [ ] Conduct a final end-to-end security and compliance review of the orchestration system.
