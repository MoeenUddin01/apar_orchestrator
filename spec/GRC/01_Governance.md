# 🏛️ Governance Architecture Specification

This document defines the Governance framework for the LangGraph AP/AR Orchestrator. The Governance layer ensures that all financial workflows execute according to organizational policies, with clear accountability, access controls, and procedural enforcement.

---

## 🎯 1. Core Objectives
- Enforce strict Role-Based Access Control (RBAC) across both automated agents and human operators.
- Guarantee Segregation of Duties (SoD) through Maker-Checker workflows.
- Apply deterministic policy limits before and after LLM execution.

---

## 🏗️ 2. Core Components & Architecture Mapping

All Governance code components are consolidated within the `src/grc/` module.

### 2.1 Role-Based Access Control (RBAC)
**Objective**: Enforce strict segregation of duties for automated agents and human users.

| Role | Responsibilities |
|---|---|
| **System Administrator** | Manages configuration, policy rules, and orchestration settings. |
| **AP/AR Specialist (Maker)** | Initiates transactions, drafts invoices, and reviews standard exceptions. |
| **Financial Controller (Checker)**| Approves high-value transactions and overrides risk flags. |
| **Auditor** | Maintains read-only access to workflow states, audit trails, and reports. |

- **Implementation**: [`src/grc/rbac.py`](file:///home/moeen/projects/apar_orchestrator/src/grc/rbac.py) (Core user roles, permission maps, enforcement helpers)

### 2.2 Maker-Checker Protocol
**Objective**: Introduce a mandatory secondary verification step for critical financial transitions.

- **Process Flow**:
  1. The LLM agent (or human **Maker**) proposes an action.
  2. The workflow pauses state execution.
  3. A secondary independent entity (human **Checker**) reviews the evidence.
  4. State progression only occurs upon explicit Approval.
- **Implementation**: 
  - [`src/grc/nodes.py`](file:///home/moeen/projects/apar_orchestrator/src/grc/nodes.py) (Shared graph nodes for human Checker evaluation)
  - [`src/api/routes/governance.py`](file:///home/moeen/projects/apar_orchestrator/src/api/routes/governance.py) (REST API endpoints for Checker approvals)

### 2.3 Policy Management & Enforcement
**Objective**: Apply deterministic financial limits and logic gates outside the LLM scope.

- **Pre-execution Rules**: Validate input data completeness, required schemas, and authorization.
- **Post-execution Rules**: Validate LLM output formats and verify proposed actions against hard financial thresholds (e.g., maximum daily payment limits).
- **Implementation**: 
  - [`src/grc/policy_rules.py`](file:///home/moeen/projects/apar_orchestrator/src/grc/policy_rules.py) (Hardcoded thresholds and validation logic)
  - [`src/grc/models.py`](file:///home/moeen/projects/apar_orchestrator/src/grc/models.py) (Pydantic models for `GovernanceStatus`, `PolicyResult`, `UserRole`)
