import json
import pytest
from src.database.repositories.ap_repository import ap_repository
from src.graph.ap.graph import ap_graph
from src.graph.state import FinanceState


@pytest.fixture(autouse=True)
def clear_ap_repo():
    """Clear in-memory invoices before each test."""
    ap_repository.clear()
    yield
    ap_repository.clear()


@pytest.mark.asyncio
async def test_duplicate_pipeline_first_submission_no_duplicate():
    """First submission should pass without duplicate flags and persist on completion."""
    raw_doc = """Invoice: INV-DUP-100
PO: PO-1001
Vendor: VEND-135
Line Items:
- item_id: ITEM-102, quantity: 6.0, unit_price: 200.0, total_price: 1200.0
Total: 1200"""

    initial_state: FinanceState = {
        "workflow_id": "wf-dup-test-1",
        "workflow_type": "AP",
        "status": "PENDING",
        "raw_document": raw_doc,
        "validation_errors": [],
        "financial_facts": {},
    }

    config = {"configurable": {"thread_id": "wf-dup-test-1"}}
    final_state = await ap_graph.ainvoke(initial_state, config=config)

    assert final_state["status"] == "COMPLETED"
    assert final_state["routing_decision"] == "APPROVE"
    assert final_state["risk_score"] == 0.0
    assert not any(f.get("code") == "DUPLICATE_INVOICE_DETECTED" for f in final_state.get("risk_flags", []))

    # Verify invoice was persisted to repository
    history = await ap_repository.get_historical_invoices_by_vendor("VEND-135")
    assert len(history) == 1
    assert history[0]["invoice_number"] == "INV-DUP-100"


@pytest.mark.asyncio
async def test_duplicate_pipeline_resubmission_duplicate_detected():
    """Resubmitting the same invoice for the same vendor must trigger duplicate risk detection."""
    raw_doc = """Invoice: INV-DUP-100
PO: PO-1001
Vendor: VEND-135
Line Items:
- item_id: ITEM-102, quantity: 6.0, unit_price: 200.0, total_price: 1200.0
Total: 1200"""

    # 1. First submission (completes & persists)
    state_1: FinanceState = {
        "workflow_id": "wf-dup-sub-1",
        "workflow_type": "AP",
        "status": "PENDING",
        "raw_document": raw_doc,
    }
    res_1 = await ap_graph.ainvoke(state_1, config={"configurable": {"thread_id": "wf-dup-sub-1"}})
    assert res_1["status"] == "COMPLETED"

    # 2. Second submission (same invoice_number and vendor_id)
    state_2: FinanceState = {
        "workflow_id": "wf-dup-sub-2",
        "workflow_type": "AP",
        "status": "PENDING",
        "raw_document": raw_doc,
    }
    res_2 = await ap_graph.ainvoke(state_2, config={"configurable": {"thread_id": "wf-dup-sub-2"}})

    # Should NOT silently complete! Should require checker approval due to high risk.
    assert res_2["status"] != "COMPLETED"
    assert res_2["risk_level"] in ("HIGH", "CRITICAL")
    assert res_2["risk_score"] >= 75.0
    
    risk_flags = res_2.get("risk_flags", [])
    dup_flags = [f for f in risk_flags if f.get("code") == "DUPLICATE_INVOICE_DETECTED"]
    assert len(dup_flags) == 1
    assert "already processed" in dup_flags[0]["message"]


@pytest.mark.asyncio
async def test_duplicate_pipeline_same_number_different_vendor():
    """Same invoice number for a DIFFERENT vendor must NOT trigger a duplicate flag."""
    raw_doc_1 = """Invoice: INV-SHARED-001
PO: PO-1001
Vendor: VEND-135
Line Items:
- item_id: ITEM-102, quantity: 6.0, unit_price: 200.0, total_price: 1200.0
Total: 1200"""

    state_1: FinanceState = {
        "workflow_id": "wf-shared-v1",
        "workflow_type": "AP",
        "status": "PENDING",
        "raw_document": raw_doc_1,
    }
    res_1 = await ap_graph.ainvoke(state_1, config={"configurable": {"thread_id": "wf-shared-v1"}})
    assert res_1["status"] == "COMPLETED"

    raw_doc_2 = """Invoice: INV-SHARED-001
PO: PO-1002
Vendor: VEND-002
Line Items:
- item_id: ITEM-B, quantity: 5.0, unit_price: 1000.0, total_price: 5000.0
Total: 5000"""

    state_2: FinanceState = {
        "workflow_id": "wf-shared-v2",
        "workflow_type": "AP",
        "status": "PENDING",
        "raw_document": raw_doc_2,
    }
    res_2 = await ap_graph.ainvoke(state_2, config={"configurable": {"thread_id": "wf-shared-v2"}})

    risk_flags = res_2.get("risk_flags", [])
    dup_flags = [f for f in risk_flags if f.get("code") == "DUPLICATE_INVOICE_DETECTED"]
    assert len(dup_flags) == 0


@pytest.mark.asyncio
async def test_duplicate_pipeline_different_invoice_number():
    """Different invoice numbers for the same vendor must NOT trigger a duplicate flag."""
    raw_doc_1 = """Invoice: INV-VAR-001
PO: PO-1001
Vendor: VEND-135
Line Items:
- item_id: ITEM-102, quantity: 6.0, unit_price: 200.0, total_price: 1200.0
Total: 1200"""

    state_1: FinanceState = {
        "workflow_id": "wf-var-1",
        "workflow_type": "AP",
        "status": "PENDING",
        "raw_document": raw_doc_1,
    }
    await ap_graph.ainvoke(state_1, config={"configurable": {"thread_id": "wf-var-1"}})

    raw_doc_2 = """Invoice: INV-VAR-002
PO: PO-1001
Vendor: VEND-135
Line Items:
- item_id: ITEM-102, quantity: 6.0, unit_price: 200.0, total_price: 1200.0
Total: 1200"""

    state_2: FinanceState = {
        "workflow_id": "wf-var-2",
        "workflow_type": "AP",
        "status": "PENDING",
        "raw_document": raw_doc_2,
    }
    res_2 = await ap_graph.ainvoke(state_2, config={"configurable": {"thread_id": "wf-var-2"}})

    risk_flags = res_2.get("risk_flags", [])
    dup_flags = [f for f in risk_flags if f.get("code") == "DUPLICATE_INVOICE_DETECTED"]
    assert len(dup_flags) == 0


@pytest.mark.asyncio
async def test_duplicate_pipeline_pending_and_rejected_not_persisted():
    """Invoices that require approval or fail matching are NOT saved to the historical invoice database."""
    # Invoice with 3-way mismatch (PO-1002 expects $5000, invoice claims $99999)
    raw_doc_fail = """Invoice: INV-REJECTED-001
PO: PO-1002
Vendor: VEND-002
Line Items:
- item_id: ITEM-B, quantity: 1.0, unit_price: 99999.0, total_price: 99999.0
Total: 99999"""

    state: FinanceState = {
        "workflow_id": "wf-unpersisted-1",
        "workflow_type": "AP",
        "status": "PENDING",
        "raw_document": raw_doc_fail,
    }
    res = await ap_graph.ainvoke(state, config={"configurable": {"thread_id": "wf-unpersisted-1"}})

    assert res["status"] != "COMPLETED"

    # Verify NOT persisted
    history = await ap_repository.get_historical_invoices_by_vendor("VEND-002")
    assert not any(inv["invoice_number"] == "INV-REJECTED-001" for inv in history)
