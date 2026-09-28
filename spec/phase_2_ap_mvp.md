# Phase 2: Accounts Payable (AP) MVP

## 1. Phase Objective
Implement the core Accounts Payable (AP) workflow using LangGraph. The workflow will intake invoices, use an LLM exclusively to extract structured data, and then rely entirely on deterministic Python logic for validation, database lookups, 3-way matching, and routing.

## 2. Architecture & Design
- **`src/apar_orchestrator/api/routes/ap.py`**: Webhook or endpoint for receiving invoices.
- **`src/apar_orchestrator/llm/extractors/`**: Prompt and LLM invocation strictly scoped to mapping unstructured text/PDFs into a Pydantic `Invoice` model.
- **`src/apar_orchestrator/database/repositories/`**: Python functions to fetch Purchase Orders and Goods Receipts from Postgres.
- **`src/apar_orchestrator/finance/matching.py`**: Pure Python logic executing the deterministic 3-way match (comparing PO, Receipt, and Invoice quantities/totals).
- **`src/apar_orchestrator/graph/ap/`**: LangGraph definitions (`graph.py`, `nodes.py`) linking these stages.

## 3. Technical Task List
- [ ] Define the AP Invoice HTTP endpoint.
- [ ] Implement the `extract_invoice` node: calls LLM to output structured JSON matching the `Invoice` schema.
- [ ] Implement the `validate_invoice` node: Python logic to ensure extracted data contains required financial fields.
- [ ] Implement the `lookup_db` node: queries Postgres for associated POs and Goods Receipts.
- [ ] Implement the `match_3_way` node: Python function in `finance/matching.py` to compare line items, calculate variances, and check against tolerances.
- [ ] Implement the `route_ap` edge logic: conditionally route to 'Approve' or 'Exception' based entirely on the deterministic boolean output of the 3-way match.
- [ ] Assemble the AP LangGraph in `graph/ap/graph.py`.

## 4. Input/Output Requirements
**Extraction Output Schema (LLM boundary)**:
```python
class ExtractedInvoice(BaseModel):
    vendor_id: str
    po_number: str
    invoice_total: float
    line_items: List[Dict[str, Any]]
```

**Financial Matching Output (Python boundary)**:
```python
class MatchResult(BaseModel):
    is_match: bool
    variance_amount: float
    tolerance_exceeded: bool
    missing_documents: List[str]
```
*`FinanceState.financial_facts` will be updated with `MatchResult`.*

## 5. Acceptance Criteria
- LangGraph AP workflow successfully runs from end-to-end.
- LLM is strictly used ONLY for extracting `ExtractedInvoice`.
- Calculations (e.g., variance calculation, sum verifications) are proven to run in Python, not by the LLM.
- If a match fails tolerances, the workflow routes to an exception state deterministically.
- Pytest covers perfect matches, PO misses, and tolerance-exceeded scenarios using mocked LLM outputs.
