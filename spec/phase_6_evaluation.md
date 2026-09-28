# Phase 6: Evaluation & Hardening

## 1. Phase Objective
Establish a rigorous testing and evaluation framework to prove the reliability of the system. This phase involves creating synthetic test data loading scripts and defining Pytest execution paths that validate both perfect-match ("happy path") scenarios and complex exception scenarios.

## 2. Architecture & Design
- **`scripts/seed_database.py`**: Script to pre-load PostgreSQL with known states (specific POs, Vendors, Invoices).
- **`scripts/run_evaluation.py`**: Script to execute bulk workflow runs and measure accuracy.
- **`tests/fixtures/`**: Mocked PDFs, text files, and expected JSON extractions.
- **`tests/integration/`**: End-to-end tests exercising LangGraph state transitions from API entry to database persistence.

## 3. Technical Task List
- [ ] Write `seed_database.py` to generate deterministic synthetic records (e.g., POs with exact quantities, customers with known outstanding balances).
- [ ] Create a library of synthetic invoice/remittance input text (both perfect formats and messy formats).
- [ ] Write end-to-end Pytest cases for AP: perfect 3-way match, quantity mismatch, missing PO, tolerance exceeded.
- [ ] Write end-to-end Pytest cases for AR: full payment, partial payment, aging bucket boundary tests.
- [ ] Implement `run_evaluation.py` to test the LLM extraction accuracy against a ground-truth dataset (measuring hallucination rates or extraction failures).
- [ ] Ensure all LLM nodes in unit tests can be mocked to guarantee CI/CD reliability without relying on external API calls.

## 4. Input/Output Requirements
**Evaluation Metrics**:
- **Extraction Accuracy**: % of LLM extractions that perfectly match ground truth JSON.
- **Routing Determinism**: 100% of workflows route correctly based on predefined Python logic.
- **Financial Math Accuracy**: 100% precision on float arithmetic and date math.

## 5. Acceptance Criteria
- Synthetic database seeding works out-of-the-box for local testing.
- The Pytest suite achieves >90% coverage on all `finance/` deterministic logic.
- Both perfect-match and exception scenarios are proven to transition to the correct terminal LangGraph state.
- `run_evaluation.py` executes successfully and provides a summary report of extraction and routing accuracy.
