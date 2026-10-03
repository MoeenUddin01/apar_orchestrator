# GRC & Audit Trail Implementation Roadmap

This document outlines the phased implementation strategy for the Governance, Risk, Compliance (GRC), and Audit Trail architecture within the LangGraph AP/AR Orchestrator. 

---

## 🎯 Phase 1: Foundation & Audit Logging
**Objective**: Establish the base infrastructure for capturing immutable, cryptographically verifiable logs of all LangGraph executions.  
**Status**: ✅ Completed

| Status | Task / Component | Target File |
|:---:|---|---|
| ✅ | Define unified audit log JSON schema | `src/domain/audit_schema.py` |
| ✅ | Set up append-only log storage operations | `src/database/audit_repository.py` |
| ✅ | Implement cryptographic hashing for integrity | `src/core/hashing.py` |
| ✅ | Implement LangGraph execution callbacks | `src/graph/shared/callbacks/audit_logger.py` |

---

## 🔒 Phase 2: Data Privacy & Compliance Middleware
**Objective**: Secure sensitive financial data flowing in and out of the graph and external LLM providers.  
**Status**: ✅ Completed

| Status | Task / Component | Target File |
|:---:|---|---|
| ✅ | Implement PII detection and redaction utilities | `src/core/security/redaction.py` |
| ✅ | Integrate redaction middleware for LLM calls | `src/llm/middleware.py` |
| ✅ | Add compliance rationale to graph state | `src/domain/compliance_state.py` |
| ✅ | Set up data retention and cleanup scripts | `src/database/retention_jobs.py` |

---

## ⚖️ Phase 3: Governance & Role-Based Routing
**Objective**: Implement strict authorization policies and Maker-Checker (human-in-the-loop) workflows.  
**Status**: ✅ Completed

| Status | Task / Component | Target File |
|:---:|---|---|
| ✅ | Define RBAC schemas and user role mockups | `src/core/security/rbac.py` |
| ✅ | Build Maker-Checker nodes for AP and AR graphs | `src/graph/*/nodes/maker_checker.py` |
| ✅ | Implement deterministic policy rules & thresholds | `src/finance/policy_rules.py` |
| ✅ | Add API endpoints for Checker approvals | `src/api/routes/governance.py` |

---

## 🛡️ Phase 4: Risk Mitigation & Anomaly Detection
**Objective**: Protect the system against operational, financial, and technical risks (including Prompt Injections).  
**Status**: ✅ Completed

| Status | Task / Component | Target File |
|:---:|---|---|
| ✅ | Create risk state schemas | `src/domain/risk_state.py` |
| ✅ | Implement the core risk scoring engine | `src/finance/risk_scoring.py` |
| ✅ | Build the Risk Assessment graph node | `src/graph/shared/nodes/risk_assessment.py` |
| ✅ | Add input sanitization middleware | `src/core/security/sanitization.py` |

---

## 📊 Phase 5: Monitoring, Reporting & Refinement
**Objective**: Surface actionable GRC data for stakeholders, auditors, and management.  
**Status**: ⏳ In Progress

| Status | Task / Component | Target File |
|:---:|---|---|
| ✅ | Create audit trail API endpoints for reports | `src/api/routes/audit.py` |
| ✅ | Develop database queries for compliance reports | `src/database/audit_repository.py` |
| ⬜ | Conduct final end-to-end security & compliance review | *Cross-cutting* |

---
> *Note: This roadmap aligns directly with the detailed domain specifications located in the `spec/GRC/` directory.*
