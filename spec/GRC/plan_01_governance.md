# 🗺️ Implementation Plan: Governance Layer

## 🎯 1. Objective & Scope
Implement the Governance layer for the LangGraph AP/AR Orchestrator inside the `src/grc/` module.
- **RBAC**: Enforce segregation of duties.
- **Maker-Checker Protocol**: Integrated into LangGraph workflows.
- **Deterministic Policy Rules**: Pre/post-execution validations and transaction limits.
- **Governance State Tracking**: Embedded in the shared graph state.

---

## 🗂️ 2. Target Files & Architecture

| Component | Target File Path | Purpose |
|---|---|---|
| **Package Init** | [`src/grc/__init__.py`](file:///home/moeen/projects/apar_orchestrator/src/grc/__init__.py) | Package exports for models, RBAC, rules, nodes. |
| **State Models** | [`src/grc/models.py`](file:///home/moeen/projects/apar_orchestrator/src/grc/models.py) | Pydantic models for `GovernanceStatus`, `UserRole`, `PolicyResult`. |
| **RBAC Security** | [`src/grc/rbac.py`](file:///home/moeen/projects/apar_orchestrator/src/grc/rbac.py) | Role enum, permission maps, authorization helpers. |
| **Policy Engine** | [`src/grc/policy_rules.py`](file:///home/moeen/projects/apar_orchestrator/src/grc/policy_rules.py) | Pre- and post-execution financial limit validation. |
| **Graph Nodes** | [`src/grc/nodes.py`](file:///home/moeen/projects/apar_orchestrator/src/grc/nodes.py) | LangGraph nodes for policy checks and Maker-Checker handling. |
| **Governance APIs** | [`src/api/routes/governance.py`](file:///home/moeen/projects/apar_orchestrator/src/api/routes/governance.py) | REST API routes for pending approvals (`POST /governance/decide`). |

---

## 🚀 3. Step-by-Step Execution Plan

### Step 1: Define Governance State & Data Schemas
**File**: [`src/grc/models.py`](file:///home/moeen/projects/apar_orchestrator/src/grc/models.py)
- Define `UserRole` Enum (`ADMIN`, `MAKER`, `CHECKER`, `AUDITOR`).
- Define `ApprovalStatus` Enum (`PENDING`, `APPROVED`, `REJECTED`, `BYPASSED`).
- Define `GovernanceStatus` Pydantic model.

### Step 2: Implement RBAC Logic
**File**: [`src/grc/rbac.py`](file:///home/moeen/projects/apar_orchestrator/src/grc/rbac.py)
- Create role-to-permission mapping.
- Implement `verify_role_permission(user_role: UserRole, permission: str) -> bool`.
- Implement `enforce_permission` helper (raises `PermissionDeniedError`).

### Step 3: Implement Financial Policy Rules Engine
**File**: [`src/grc/policy_rules.py`](file:///home/moeen/projects/apar_orchestrator/src/grc/policy_rules.py)
- Implement `validate_pre_execution_policy(state: dict) -> PolicyResult`.
- Implement `validate_post_execution_policy(state: dict) -> PolicyResult` (e.g., threshold $10,000).

### Step 4: Build LangGraph Maker-Checker Nodes
**File**: [`src/grc/nodes.py`](file:///home/moeen/projects/apar_orchestrator/src/grc/nodes.py)
- Build `governance_policy_check_node(state)`.
- Build `maker_checker_review_node(state)`.

### Step 5: Implement Governance REST API Routes
**File**: [`src/api/routes/governance.py`](file:///home/moeen/projects/apar_orchestrator/src/api/routes/governance.py)
- Endpoint `POST /api/v1/governance/decide`: Submit Checker decision (Approve/Reject) with RBAC checks.

### Step 6: Verification & Testing
**File**: `tests/unit/test_governance.py`
- Write unit tests for RBAC permission checks and policy rule thresholds.
