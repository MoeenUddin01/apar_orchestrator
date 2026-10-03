# 🗺️ Implementation Plan: Risk Management Layer

## 🎯 1. Objective & Scope
Implement the Risk Management architecture to safeguard workflows against operational, financial, and AI risks.
- **Risk Schemas**: For graph state tracking.
- **Sanitization Engine**: Block prompt injection attempts.
- **Scoring Engine**: Duplicate checks, threshold alerts, vendor tampering.
- **Validation layer**: Hallucination defense.
- **External Profiling**: API Client mock for risk lookups.

---

## 🗂️ 2. Target Files & Architecture

| Component | Target File Path | Purpose |
|---|---|---|
| **Risk State** | [`src/domain/risk_state.py`](file:///home/moeen/projects/apar_orchestrator/src/domain/risk_state.py) | `RiskLevel`, `RiskFlag`, `RiskScore`, `RiskAssessmentResult`. |
| **Sanitization** | [`src/core/security/sanitization.py`](file:///home/moeen/projects/apar_orchestrator/src/core/security/sanitization.py) | Defense against adversarial inputs. |
| **Operational Risk** | [`src/finance/risk_scoring.py`](file:///home/moeen/projects/apar_orchestrator/src/finance/risk_scoring.py) | Fraud detection, duplicates, anomaly scoring. |
| **External Risk** | [`src/api/integrations/risk_apis.py`](file:///home/moeen/projects/apar_orchestrator/src/api/integrations/risk_apis.py) | Vendor risk lookup service client. |
| **LLM Validation** | [`src/llm/validation.py`](file:///home/moeen/projects/apar_orchestrator/src/llm/validation.py) | Prevention of hallucinations and data cross-referencing. |
| **Graph Node** | [`src/graph/shared/nodes/risk_assessment.py`](file:///home/moeen/projects/apar_orchestrator/src/graph/shared/nodes/risk_assessment.py) | LangGraph `Risk_Assessment` node executing risk evaluations. |
| **REST APIs** | [`src/api/routes/risk.py`](file:///home/moeen/projects/apar_orchestrator/src/api/routes/risk.py) | Endpoints for inspecting risk flags and scores. |

---

## 🚀 3. Step-by-Step Execution Plan

### Step 1: Define Risk Data Schemas
**File**: [`src/domain/risk_state.py`](file:///home/moeen/projects/apar_orchestrator/src/domain/risk_state.py)
- Define `RiskLevel` Enum (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
- Define `RiskFlag`, `RiskScore`, and `RiskAssessmentResult`.

### Step 2: Implement Input Sanitization & Security Middleware
**File**: [`src/core/security/sanitization.py`](file:///home/moeen/projects/apar_orchestrator/src/core/security/sanitization.py)
- Implement `sanitize_input(text: str) -> str`.
- Implement pattern detection (`detect_prompt_injection(text: str) -> bool`).

### Step 3: Implement Financial & Operational Risk Scoring Engine
**File**: [`src/finance/risk_scoring.py`](file:///home/moeen/projects/apar_orchestrator/src/finance/risk_scoring.py)
- Implement `check_duplicate_invoice`.
- Implement `check_vendor_bank_change`.
- Implement `calculate_transaction_anomaly_score`.
- Implement `evaluate_operational_risk`.

### Step 4: Implement AI Hallucination & Validation Layer
**File**: [`src/llm/validation.py`](file:///home/moeen/projects/apar_orchestrator/src/llm/validation.py)
- Implement `validate_llm_extraction`.
- Add cross-referencing utilities (e.g., verifying sums).

### Step 5: Implement Vendor Risk Profile API Integration
**File**: [`src/api/integrations/risk_apis.py`](file:///home/moeen/projects/apar_orchestrator/src/api/integrations/risk_apis.py)
- Create `VendorRiskClient` to simulate external risk scores.

### Step 6: Build LangGraph `Risk_Assessment` Node
**File**: [`src/graph/shared/nodes/risk_assessment.py`](file:///home/moeen/projects/apar_orchestrator/src/graph/shared/nodes/risk_assessment.py)
- Implement `risk_assessment_node(state: dict) -> dict`.
- Set `RiskScore` and `RiskFlags` in graph state.

### Step 7: Expose REST API Endpoints
**File**: [`src/api/routes/risk.py`](file:///home/moeen/projects/apar_orchestrator/src/api/routes/risk.py)
- Endpoint `POST /api/v1/risk/evaluate`.
- Endpoint `GET /api/v1/risk/assessments/{thread_id}`.

### Step 8: Comprehensive Verification & Testing
**File**: `tests/unit/test_risk_management.py`
- Test prompt injection sanitization.
- Test duplicate invoice/bank change detection.
- Test LLM validation math checks.
- Test node execution and state updates.
