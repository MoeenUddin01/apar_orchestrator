# 🛡️ Risk Management Architecture Specification

This document defines the Risk layer designed to identify, assess, and mitigate risks across the automated AP/AR workflows.

---

## 🎯 1. Core Objectives
- Protect against operational and financial risks (e.g., duplicates, transaction anomalies).
- Protect against AI/technical risks (e.g., prompt injections, math hallucinations).
- Provide a decision-support and scoring mechanism without directly authorizing financial transactions (delegated to Governance).

---

## 🗂️ 2. Risk Categorization Schema (`RiskCategory`)

| Category | Description |
|---|---|
| **SECURITY** | Adversarial inputs, prompt injections, unauthorized role elevation attempts. |
| **FRAUD** | Suspicious transaction patterns and fraudulent invoice submissions. |
| **DUPLICATE** | Exact combinations of `vendor_id` and `invoice_number` collisions. |
| **FINANCIAL** | Transactions exceeding statistical anomalies or hard thresholds. |
| **VENDOR** | Compliance watchlist matches, credit score drops, bank account changes. |
| **OPERATIONAL** | Missing required fields or process execution failures. |
| **AI_VALIDATION** | Mathematical hallucinations, calculation errors, currency mismatches. |
| **EXTERNAL** | External API timeouts, provider downtime, or integration failures. |

---

## 🏗️ 3. Component Architecture & Implementation Mapping

### 3.1 Input Sanitization & Prompt Injection Defense
- **Mitigation**: Sanitizes raw text (removes null bytes/HTML tags). Scans for adversarial prompt patterns via regex while preserving legitimate business instructions.
- **Structured Output**: `SanitizationResult` (`is_suspicious`, `risk_level`, `detected_patterns`, `sanitized_text`, `warnings`).
- **Implementation**: [`src/core/security/sanitization.py`](file:///home/moeen/projects/apar_orchestrator/src/core/security/sanitization.py)

### 3.2 Operational & Financial Risk Scoring
- **Mitigation**: 
  - **Duplicates**: Checks `vendor_id` + `invoice_number` against historical records.
  - **Tampering**: Alerts on vendor bank account modifications (`VERIFY_BANK_ACCOUNT_BEFORE_PAYMENT`).
  - **Statistical Anomalies**: Evaluates transaction amounts against historical baselines deterministically.
- **Implementation**: [`src/finance/risk_scoring.py`](file:///home/moeen/projects/apar_orchestrator/src/finance/risk_scoring.py)

### 3.3 AI Extraction & Hallucination Defense
- **Mitigation**: Deterministically verifies LLM mathematical claims ($\text{quantity} \times \text{unit\_price} = \text{total}$). LLM outputs never override math.
- **Implementation**: [`src/llm/validation.py`](file:///home/moeen/projects/apar_orchestrator/src/llm/validation.py)

### 3.4 External Vendor Risk Screening
- **Mitigation**: Integrates with vendor registries. Gracefully handles API timeouts by elevating risk to `EXTERNAL_RISK_API_UNAVAILABLE` (MEDIUM severity).
- **Implementation**: [`src/api/integrations/risk_apis.py`](file:///home/moeen/projects/apar_orchestrator/src/api/integrations/risk_apis.py)

### 3.5 Shared Risk Assessment Graph Node
- **Mitigation**: Aggregates security findings, risk scores, validation errors, and external flags into a unified `RiskAssessmentResult`.
- **Recommendation Mapping**:
  - `LOW` ➡️ `CONTINUE` (Proceed with standard workflow)
  - `MEDIUM` ➡️ `MONITOR` (Continue with additional monitoring checks)
  - `HIGH` ➡️ `HUMAN_REVIEW_RECOMMENDED` (Recommend human review)
  - `CRITICAL` ➡️ `BLOCK_UNTIL_AUTHORIZED` (Block progression until authorized review)
- **Implementation**: 
  - [`src/graph/shared/nodes/risk_assessment.py`](file:///home/moeen/projects/apar_orchestrator/src/graph/shared/nodes/risk_assessment.py)
  - [`src/domain/risk_state.py`](file:///home/moeen/projects/apar_orchestrator/src/domain/risk_state.py)

### 3.6 REST API Endpoints
- **Endpoints**:
  - `POST /api/v1/risk/evaluate`: Runs instant risk scoring on transaction payloads.
  - `GET /api/v1/risk/assessments/{workflow_id}`: Retrieves structured risk state.
- **Implementation**: [`src/api/routes/risk.py`](file:///home/moeen/projects/apar_orchestrator/src/api/routes/risk.py)
