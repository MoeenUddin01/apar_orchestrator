# Risk Management Architecture

## 1. Overview
The Risk layer is designed to identify, assess, and mitigate risks across the automated AP/AR workflows. This includes operational and financial risks (e.g., duplicate payments, vendor bank tampering, transaction anomalies) and AI/technical risks (e.g., prompt injections, LLM math hallucinations, non-deterministic outputs).

The Risk Management layer functions as a decision-support and safety layer. It scores and flags risk without directly authorizing or rejecting financial transactions, leaving authorization to the Governance & Maker-Checker layer.

---

## 2. Risk Categories & Architecture Mapping

### 2.1 Categorization Schema (`RiskCategory`)
- `SECURITY`: Adversarial inputs, prompt injection signatures, and unauthorized role elevation attempts.
- `FRAUD`: Duplicate invoice submissions and suspicious transaction patterns.
- `DUPLICATE`: Exact matching vendor ID and invoice number collisions.
- `FINANCIAL`: Transactions exceeding threshold limits or statistical anomalies.
- `VENDOR`: Vendor compliance watchlist matches, credit score drops, and bank account modifications.
- `OPERATIONAL`: Missing required financial fields or process execution failures.
- `AI_VALIDATION`: Mathematical extraction hallucinations, subtotal discrepancies, and currency mismatches.
- `EXTERNAL`: External API timeouts, provider unavailability, or integration failures.

---

## 3. Component Architecture & Implementation Mapping

### 3.1 Input Sanitization & Prompt Injection Defense
- **Mitigation**: Sanitizes incoming unstructured text inputs by removing null bytes, HTML/script tags, and inline event handlers. Scans for adversarial prompt injection patterns using word-boundary regexes (instruction overrides, system prompt extraction, control bypasses, role manipulation, secret revelation). Protects against false positives (e.g., legitimate business instructions containing words like "previous instructions" are preserved).
- **Structured Output**: `SanitizationResult` (`is_suspicious`, `risk_level`, `detected_patterns`, `sanitized_text`, `warnings`).
- **Implementation Files**: `src/core/security/sanitization.py`.

### 3.2 Operational & Financial Risk Scoring
- **Mitigation**: 
  - **Duplicate Invoice Detection**: Checks exact combinations of `vendor_id` AND `invoice_number` against historical records. Single weak matches do not trigger duplicate flags.
  - **Vendor Bank Account Tampering**: Compares invoice bank details against baseline records. Generates a `CRITICAL` risk flag recommending manual verification (`VERIFY_BANK_ACCOUNT_BEFORE_PAYMENT`).
  - **Statistical Anomaly Scoring**: Evaluates transaction amounts against historical vendor baselines. Deterministically handles edge cases (empty history, single historical value ratios, zero standard deviation, negative amounts).
  - **High-Value Thresholds**: Flags transactions exceeding configured threshold limits (e.g., $10,000).
- **Implementation Files**: `src/finance/risk_scoring.py`.

### 3.3 AI Extraction & Hallucination Defense
- **Mitigation**: Cross-checks LLM-extracted financial data against deterministic math rules. Verifies that $\text{quantity} \times \text{unit\_price} = \text{item\_total}$, line item sums match declared totals, subtotal + tax equals invoice total, currency is consistent across items, and required fields are present. LLM outputs are never allowed to override deterministic financial calculations.
- **Implementation Files**: `src/llm/validation.py`.

### 3.4 External Vendor Risk Screening
- **Mitigation**: Integrates with external vendor risk and sanctions registries (`VendorRiskClient`). Handles API timeouts and provider unavailability gracefully by generating `EXTERNAL_RISK_API_UNAVAILABLE` flags with `MEDIUM` severity to prevent silent low-risk fallbacks.
- **Implementation Files**: `src/api/integrations/risk_apis.py`.

### 3.5 Shared Risk Assessment Graph Node
- **Mitigation**: Dedicated `risk_assessment_node` executes in AP and AR LangGraph workflows. It aggregates security findings, operational risk scores, LLM validation errors, and external vendor flags into a unified `RiskAssessmentResult`.
- **Workflow Recommendation Mapping**:
  - `LOW` $\rightarrow$ `CONTINUE` (Proceed with standard workflow)
  - `MEDIUM` $\rightarrow$ `MONITOR` (Continue with additional monitoring checks)
  - `HIGH` $\rightarrow$ `HUMAN_REVIEW_RECOMMENDED` (Recommend human review in governance layer)
  - `CRITICAL` $\rightarrow$ `BLOCK_UNTIL_AUTHORIZED` (Block progression until authorized human review)
- **Implementation Files**: `src/graph/shared/nodes/risk_assessment.py`, `src/domain/risk_state.py`.

### 3.6 REST API Endpoints
- **Endpoints**:
  - `POST /api/v1/risk/evaluate`: Runs instant risk scoring on transaction payloads.
  - `GET /api/v1/risk/assessments/{workflow_id}`: Retrieves structured risk state, flags, and recommended actions for a workflow thread without exposing system secrets.
- **Implementation Files**: `src/api/routes/risk.py`.
