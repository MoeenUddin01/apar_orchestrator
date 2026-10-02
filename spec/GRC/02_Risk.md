# Risk Management Architecture

## 1. Overview
The Risk layer is designed to identify, assess, and mitigate risks across the automated AP/AR workflows. This includes operational risks (e.g., duplicate payments, fraud) and technical risks specific to Generative AI (e.g., hallucinations, non-deterministic outputs).

## 2. Risk Categories, Mitigations & Architecture Mapping

### 2.1 Operational & Financial Risks
- **Fraud Detection & Transaction Limits**: 
  - **Mitigation**: Dedicated rule-based nodes verify vendor bank account changes, flag unusual payment amounts compared to historical baselines, and detect duplicate invoice numbers. Transactions exceeding thresholds require manual approval.
  - **Implementation Files**: `src/finance/risk_scoring.py` (rules engine and threshold checks).
- **Vendor/Customer Risk Profiling**:
  - **Mitigation**: Integration with external risk assessment APIs to maintain dynamic risk scores.
  - **Implementation Files**: `src/api/integrations/risk_apis.py`.

### 2.2 AI & Technical Risks
- **LLM Hallucinations**:
  - **Mitigation**: Output formatting enforcement using strictly typed Pydantic models. Secondary validation nodes that cross-reference LLM extraction with deterministic data.
  - **Implementation Files**: `src/llm/validation.py` (secondary checks), `src/domain/llm_schemas.py`.
- **Prompt Injection & Adversarial Inputs**:
  - **Mitigation**: Input sanitization nodes strip potentially malicious instructions from external communications before passing them to reasoning agents.
  - **Implementation Files**: `src/core/security/sanitization.py`.

## 3. Risk Assessment Node
A dedicated `Risk_Assessment` node is added to the AP and AR graphs.
- **Input**: Current graph state.
- **Processing**: Evaluates deterministic rules and secondary LLM risk-scoring prompts.
- **Output**: Updates `RiskScore` and `RiskFlags` in the state.
**Implementation Files**:
- `src/graph/shared/nodes/risk_assessment.py`: The shared graph node for risk evaluation.
- `src/domain/risk_state.py`: Pydantic schemas for risk-related state tracking.
