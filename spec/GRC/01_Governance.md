# Governance Framework

## 1. Overview
The Governance layer for the LangGraph AP/AR Orchestrator ensures that all financial workflows are executed according to predefined organizational policies, with clear accountability, access controls, and procedural enforcement.

## 2. Core Components & Architecture Mapping

### 2.1 Role-Based Access Control (RBAC)
To ensure segregation of duties, the system enforces strict RBAC for both automated agents and human users:
- **System Administrator**: Manages configuration, policy rules, and LLM orchestration settings.
- **AP/AR Specialist (Maker)**: Initiates transactions, drafts invoices, and reviews exceptions.
- **Financial Controller (Checker)**: Approves high-value transactions, overrides risk flags.
- **Auditor**: Read-only access to workflow states, audit trails, and compliance reports.
**Implementation Files**: 
- `src/core/security/rbac.py`: Core user roles and permission checks.

### 2.2 Maker-Checker Protocol
For critical financial transitions (e.g., invoice approval, payment authorization), a Maker-Checker node is introduced into the LangGraph orchestration.
- The LLM agent (or human Maker) proposes an action.
- A secondary, independent node (or human Checker) must validate the action before state progression.
**Implementation Files**:
- `src/graph/ap/nodes/maker_checker.py`: AP specific approval routing node.
- `src/graph/ar/nodes/maker_checker.py`: AR specific approval routing node.
- `src/api/routes/governance.py`: API endpoints for human Checkers to submit decisions.

### 2.3 Policy Management & Enforcement
Policies are defined as deterministic rules enforced before and after LLM agent executions:
- **Pre-execution Rules**: Validate input data completeness and authorization.
- **Post-execution Rules**: Validate LLM output formats and verify proposed actions against financial limits (e.g., maximum daily payment limits).
**Implementation Files**:
- `src/finance/policy_rules.py`: Hardcoded thresholds and policy validation logic.
- `src/domain/governance_state.py`: Pydantic models for `GovernanceStatus`, tracking approval levels in the graph state.
