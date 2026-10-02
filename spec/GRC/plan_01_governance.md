# Implementation Plan: Governance Layer (01_Governance.md)

## 1. Objective & Scope
Implement the Governance layer for the LangGraph AP/AR Orchestrator inside a dedicated [`src/grc/`](file:///home/moeen/projects/apar_orchestrator/src/grc/) module. This includes:
- **Role-Based Access Control (RBAC)** to enforce segregation of duties (Admin, Maker, Checker, Auditor).
- **Maker-Checker Protocol** integrated into AP and AR LangGraph execution.
- **Deterministic Policy Rules** (pre/post-execution validations and transaction threshold checks).
- **Governance State Tracking** embedded in the shared graph state.

---

## 2. Target Files & Architecture ([`src/grc/`](file:///home/moeen/projects/apar_orchestrator/src/grc/))

| Component | Target File Path | Purpose |
| :--- | :--- | :--- |
| **Package Init** | [`src/grc/__init__.py`](file:///home/moeen/projects/apar_orchestrator/src/grc/__init__.py) | Package exports for models, RBAC, rules, and nodes. |
| **State Models** | [`src/grc/models.py`](file:///home/moeen/projects/apar_orchestrator/src/grc/models.py) | Pydantic models for `GovernanceStatus`, `UserRole`, `MakerCheckerAction`, and `PolicyResult`. |
| **RBAC Security** | [`src/grc/rbac.py`](file:///home/moeen/projects/apar_orchestrator/src/grc/rbac.py) | Role enum, permission maps, and authorization verification helpers. |
| **Policy Engine** | [`src/grc/policy_rules.py`](file:///home/moeen/projects/apar_orchestrator/src/grc/policy_rules.py) | Pre- and post-execution financial limit and validation functions. |
| **Graph Nodes** | [`src/grc/nodes.py`](file:///home/moeen/projects/apar_orchestrator/src/grc/nodes.py) | LangGraph nodes for policy checks and Maker-Checker approval handling. |
| **Governance Endpoints** | [`src/api/routes/governance.py`](file:///home/moeen/projects/apar_orchestrator/src/api/routes/governance.py) | REST API routes for pending approvals and decisions (`POST /governance/decide`). |

---

## 3. Step-by-Step Execution Plan

### Step 1: Define Governance State & Data Schemas
- **File**: [`src/grc/models.py`](file:///home/moeen/projects/apar_orchestrator/src/grc/models.py)
- **Tasks**:
  - Define `UserRole` Enum (`ADMIN`, `MAKER`, `CHECKER`, `AUDITOR`).
  - Define `ApprovalStatus` Enum (`PENDING`, `APPROVED`, `REJECTED`, `BYPASSED`).
  - Define `GovernanceStatus` Pydantic model.

### Step 2: Implement RBAC Logic
- **File**: [`src/grc/rbac.py`](file:///home/moeen/projects/apar_orchestrator/src/grc/rbac.py)
- **Tasks**:
  - Create role-to-permission mapping (`ROLE_PERMISSIONS` dictionary).
  - Implement `verify_role_permission(user_role: UserRole, permission: str) -> bool`.
  - Implement `enforce_permission` helper raising `PermissionDeniedError`.

### Step 3: Implement Financial Policy Rules Engine
- **File**: [`src/grc/policy_rules.py`](file:///home/moeen/projects/apar_orchestrator/src/grc/policy_rules.py)
- **Tasks**:
  - Implement `validate_pre_execution_policy(state: dict) -> PolicyResult`.
  - Implement `validate_post_execution_policy(state: dict) -> PolicyResult` (default threshold `$10,000`).

### Step 4: Build LangGraph Maker-Checker Nodes
- **File**: [`src/grc/nodes.py`](file:///home/moeen/projects/apar_orchestrator/src/grc/nodes.py)
- **Tasks**:
  - `governance_policy_check_node(state)`
  - `maker_checker_review_node(state)`

### Step 5: Implement Governance REST API Routes
- **File**: [`src/api/routes/governance.py`](file:///home/moeen/projects/apar_orchestrator/src/api/routes/governance.py)
- **Tasks**:
  - `POST /api/v1/governance/decide`: Submit Checker decision (Approve/Reject) with RBAC permission checks.

### Step 6: Verification & Testing
- **File**: `tests/unit/test_governance.py`
- **Tasks**:
  - Write unit tests for RBAC permission checks and policy rule thresholds.
