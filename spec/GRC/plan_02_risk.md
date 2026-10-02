# Implementation Plan: Risk Management Layer (02_Risk.md)

## 1. Objective & Scope
Implement the Risk Management architecture for the LangGraph AP/AR Orchestrator as specified in `spec/GRC/02_Risk.md`. This layer safeguards financial workflows against operational/financial risks (fraud, duplicate payments, bank account tampering) and AI/technical risks (prompt injections, LLM hallucinations, non-deterministic outputs).

Key Objectives:
- Define structured **Risk State & Pydantic Schemas** for graph state tracking.
- Build an **Input Sanitization Engine** to strip prompt injection attempts and malicious inputs.
- Create a **Financial & Operational Risk Scoring Engine** (duplicate checks, threshold alerts, vendor bank account modification flags).
- Develop **AI Validation & Hallucination Defense** utilities to cross-verify LLM outputs against deterministic data.
- Implement an external **Vendor Risk Profiling API Client** mock interface.
- Integrate the shared **`Risk_Assessment` LangGraph node** for AP and AR graphs.
- Provide a REST API interface for risk monitoring and evaluation.

---

## 2. Target Files & Architecture

| Component | Target File Path | Purpose |
| :--- | :--- | :--- |
| **Risk State Schemas** | `src/domain/risk_state.py` | Pydantic schemas (`RiskLevel`, `RiskFlag`, `RiskScore`, `RiskAssessmentResult`). |
| **Input Sanitization** | `src/core/security/sanitization.py` | Defense against prompt injections and adversarial inputs. |
| **Operational Risk Engine** | `src/finance/risk_scoring.py` | Rule-based fraud detection, duplicate invoice checks, and anomaly scoring. |
| **External Risk API** | `src/api/integrations/risk_apis.py` | External vendor dynamic risk profile lookup service client. |
| **LLM Risk & Validation** | `src/llm/validation.py` | Secondary validation checks to prevent hallucinations and cross-reference data. |
| **Graph Node** | `src/graph/shared/nodes/risk_assessment.py` | LangGraph `Risk_Assessment` node executing risk evaluation and updating state. |
| **REST API Routes** | `src/api/routes/risk.py` | REST API endpoints for inspecting risk flags and scores (`GET /risk/assessments`). |
| **Test Suite** | `tests/unit/test_risk_management.py` | Unit tests covering sanitization, scoring, hallucination defense, and node execution. |

---

## 3. Step-by-Step Execution Plan

### Step 1: Define Risk Data Schemas
- **File**: `src/domain/risk_state.py`
- **Tasks**:
  - Define `RiskLevel` Enum (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
  - Define `RiskFlag` Pydantic model (`code`, `category`, `message`, `severity`).
  - Define `RiskScore` Pydantic model (`score: float`, `level: RiskLevel`, `flags: List[RiskFlag]`, `breakdown: dict`).
  - Define `RiskAssessmentResult` Pydantic model for graph state updates.

### Step 2: Implement Input Sanitization & Security Middleware
- **File**: `src/core/security/sanitization.py`
- **Tasks**:
  - Implement `sanitize_input(text: str) -> str` to strip control characters and prompt injection signatures.
  - Implement pattern detection (`detect_prompt_injection(text: str) -> bool`) for adversarial prompt overrides.

### Step 3: Implement Financial & Operational Risk Scoring Engine
- **File**: `src/finance/risk_scoring.py`
- **Tasks**:
  - Implement `check_duplicate_invoice(invoice_number: str, vendor_id: str, history: List[dict]) -> Optional[RiskFlag]`.
  - Implement `check_vendor_bank_change(vendor_id: str, new_bank_account: str, baseline_bank_account: str) -> Optional[RiskFlag]`.
  - Implement `calculate_transaction_anomaly_score(amount: float, historical_amounts: List[float]) -> float`.
  - Implement unified `evaluate_operational_risk(transaction_data: dict) -> RiskScore`.

### Step 4: Implement AI Hallucination & Validation Layer
- **File**: `src/llm/validation.py`
- **Tasks**:
  - Implement `validate_llm_extraction(extracted_data: dict, deterministic_context: dict) -> Tuple[bool, List[str]]`.
  - Add cross-referencing utilities (e.g. verify extracted total equals line items sum within tolerance).

### Step 5: Implement Vendor Risk Profile API Integration
- **File**: `src/api/integrations/risk_apis.py`
- **Tasks**:
  - Create `VendorRiskClient` to simulate dynamic risk score retrieval from external risk providers.

### Step 6: Build LangGraph `Risk_Assessment` Shared Node
- **File**: `src/graph/shared/nodes/risk_assessment.py`
- **Tasks**:
  - Implement `risk_assessment_node(state: dict) -> dict` integrating operational checks, sanitization, and state updates.
  - Set `RiskScore` and `RiskFlags` in graph state. Trigger human approval recommendation if `RiskLevel` is `HIGH` or `CRITICAL`.

### Step 7: Expose REST API Endpoints
- **File**: `src/api/routes/risk.py`
- **Tasks**:
  - Endpoint `POST /api/v1/risk/evaluate`: Run instant risk evaluation on invoice/payment data.
  - Endpoint `GET /api/v1/risk/assessments/{thread_id}`: Retrieve risk assessment state for a graph run.

### Step 8: Comprehensive Verification & Testing
- **File**: `tests/unit/test_risk_management.py`
- **Tasks**:
  - Test prompt injection sanitization.
  - Test duplicate invoice and bank change detection logic.
  - Test LLM validation check for line item sums vs total.
  - Test `risk_assessment_node` execution and graph state updates.
