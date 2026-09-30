import json
import pytest
from src.graph.ap.graph import ap_graph
from src.graph.state import FinanceState
from tests.fixtures.test_data import PERFECT_INVOICE_JSON, TOLERANCE_EXCEEDED_INVOICE_JSON

@pytest.mark.asyncio
async def test_ap_workflow_perfect_match():
    """Test a perfect 3-way match which should route directly to 'approve' (COMPLETED)."""
    initial_state: FinanceState = {
        "workflow_id": "test-wf-1",
        "workflow_type": "AP",
        "status": "PENDING",
        "raw_document": json.dumps(PERFECT_INVOICE_JSON),
        "validation_errors": [],
        "financial_facts": {},
    }

    config = {"configurable": {"thread_id": "test-wf-1"}}
    final_state = await ap_graph.ainvoke(initial_state, config=config)

    assert final_state["status"] == "COMPLETED"
    assert final_state["routing_decision"] == "APPROVE"
    assert final_state["financial_facts"]["match_result"]["is_match"] is True


@pytest.mark.asyncio
async def test_ap_workflow_tolerance_exceeded():
    """Test an invoice that exceeds tolerance, which should route to HITL (REQUIRES_APPROVAL)."""
    initial_state: FinanceState = {
        "workflow_id": "test-wf-2",
        "workflow_type": "AP",
        "status": "PENDING",
        "raw_document": json.dumps(TOLERANCE_EXCEEDED_INVOICE_JSON),
        "validation_errors": [],
        "financial_facts": {},
    }

    config = {"configurable": {"thread_id": "test-wf-2"}}
    final_state = await ap_graph.ainvoke(initial_state, config=config)

    assert final_state["status"] == "REQUIRES_APPROVAL"
    assert final_state["routing_decision"] == "HITL"
    assert final_state["hitl_decision"]["requires_hitl"] is True
    assert final_state["hitl_decision"]["hitl_reason"] == "TOLERANCE_EXCEPTION"
    
    # Verify that a communication was drafted
    drafts = final_state.get("drafted_communications", [])
    assert len(drafts) > 0
    assert drafts[0]["tone"] == "PROFESSIONAL"
    assert "variance amount" in drafts[0]["body"]
