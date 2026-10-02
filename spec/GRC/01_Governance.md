# Governance Framework

## 1. Overview
The Governance layer for the LangGraph AP/AR Orchestrator ensures that all financial workflows are executed according to predefined organizational policies, with clear accountability, access controls, and procedural enforcement.

## 2. Core Components & Architecture Mapping ([`src/grc/`](file:///home/moeen/projects/apar_orchestrator/src/grc/))

All GRC code components are consolidated cleanly within the [`src/grc/`](file:///home/moeen/projects/apar_orchestrator/src/grc/) module.

### 2.1 Role-Based Access Control (RBAC)
To ensure segregation of duties, the system enforces strict RBAC for both automated agents and human users:
- **System Administrator**: Manages configuration, policy rules, and LLM orchestration settings.
- **AP/AR Specialist (Maker)**: Initiates transactions, drafts invoices, and reviews exceptions.
- **Financial Controller (Checker)**: Approves high-value transactions, overrides risk flags.
- **Auditor**: Read-only access to workflow states, audit trails, and compliance reports.
**Implementation Files**: 
- [`src/grc/rbac.py`](file:///home/moeen/projects/apar_orchestrator/src/grc/rbac.py): Core user roles, permission maps, and enforcement helpers.

### 2.2 Maker-Checker Protocol
For critical financial transitions (e.g., invoice approval, payment authorization), a Maker-Checker node is introduced into the LangGraph orchestration.
- The LLM agent (or human Maker) proposes an action.
- A secondary, independent node (or human Checker) must validate the action before state progression.
**Implementation Files**:
- [`src/grc/nodes.py`](file:///home/moeen/projects/apar_orchestrator/src/grc/nodes.py): Shared graph nodes for evaluating policies and applying human Checker decisions.
- [`src/api/routes/governance.py`](file:///home/moeen/projects/apar_orchestrator/src/api/routes/governance.py): REST API endpoints for human Checkers to submit approval decisions.

### 2.3 Policy Management & Enforcement
Policies are defined as deterministic rules enforced before and after LLM agent executions:
- **Pre-execution Rules**: Validate input data completeness and authorization.
- **Post-execution Rules**: Validate LLM output formats and verify proposed actions against financial limits (e.g., maximum daily payment limits).
**Implementation Files**:
- [`src/grc/policy_rules.py`](file:///home/moeen/projects/apar_orchestrator/src/grc/policy_rules.py): Hardcoded thresholds and policy validation logic.
- [`src/grc/models.py`](file:///home/moeen/projects/apar_orchestrator/src/grc/models.py): Pydantic models for `GovernanceStatus`, `PolicyResult`, `UserRole`, tracking approval levels in the graph state.
