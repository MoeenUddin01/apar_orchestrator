# Phase 3: Accounts Receivable (AR) MVP

## 1. Phase Objective
Implement the core Accounts Receivable (AR) workflow. This phase handles incoming payments/remittances by classifying the payment text via LLM, fetching existing invoices from the database, reconciling the payment using deterministic math, and calculating aging/overdue states.

## 2. Architecture & Design
- **`src/apar_orchestrator/api/routes/ar.py`**: Webhook or endpoint for receiving payments or remittance advices.
- **`src/apar_orchestrator/llm/extractors/`**: LLM prompts restricted to extracting customer names, invoice references, and payment amounts from unstructured remittance emails/notes.
- **`src/apar_orchestrator/finance/aging.py`**: Pure Python functions that calculate days overdue based on invoice due dates and current dates.
- **`src/apar_orchestrator/finance/matching.py`**: Python reconciliation logic to apply payment amounts to outstanding invoice balances.
- **`src/apar_orchestrator/graph/ar/`**: LangGraph definitions linking the AR pipeline.

## 3. Technical Task List
- [ ] Define the AR Payment HTTP endpoint.
- [ ] Implement the `extract_remittance` node: LLM parses unstructured text into a structured `Remittance` schema.
- [ ] Implement the `lookup_invoices` node: retrieve unpaid invoices for the identified customer from PostgreSQL.
- [ ] Implement the `reconcile_payment` node: Python logic applying payment amounts to invoice totals, calculating new outstanding balances.
- [ ] Implement the `calculate_aging` node: Python logic to bucket remaining balances (e.g., 30/60/90 days overdue).
- [ ] Implement the `route_ar` edge: conditionally transition the state to 'Closed', 'Partial', or 'Overdue' based entirely on the deterministic math outputs.
- [ ] Assemble the AR LangGraph in `graph/ar/graph.py`.

## 4. Input/Output Requirements
**Extraction Output Schema (LLM boundary)**:
```python
class ExtractedRemittance(BaseModel):
    customer_identifier: str
    referenced_invoices: List[str]
    total_payment: float
```

**Financial Math Output (Python boundary)**:
```python
class ReconciliationResult(BaseModel):
    applied_amount: float
    remaining_balance: float
    is_fully_paid: bool
    days_overdue: int
    aging_bucket: Literal["CURRENT", "30_DAYS", "60_DAYS", "90_DAYS_PLUS"]
```

## 5. Acceptance Criteria
- LangGraph AR workflow executes end-to-end for a payment payload.
- Outstanding balances and aging buckets are calculated strictly via Python `datetime` and float arithmetic.
- Payments covering partial invoices are accurately reflected in `remaining_balance`.
- State correctly routes to 'Overdue' when deterministic logic outputs `days_overdue > 0` and `remaining_balance > 0`.
- Unit tests validate the AR math independently of the graph.
