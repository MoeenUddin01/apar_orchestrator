import json
import pytest
from src.graph.ar.graph import ar_graph
from src.graph.state import FinanceState
from tests.fixtures.test_data import FULL_PAYMENT_REMITTANCE_JSON, PARTIAL_PAYMENT_REMITTANCE_JSON

@pytest.mark.asyncio
async def test_ar_workflow_full_payment():
    """Test a full payment which should route to 'closed' (COMPLETED)."""
    initial_state: FinanceState = {
        "workflow_id": "test-ar-wf-1",
        "workflow_type": "AR",
        "status": "PENDING",
        "raw_document": json.dumps(FULL_PAYMENT_REMITTANCE_JSON),
        "validation_errors": [],
        "financial_facts": {},
    }

    config = {"configurable": {"thread_id": "test-ar-wf-1"}}
    final_state = await ar_graph.ainvoke(initial_state, config=config)

    assert final_state["status"] == "COMPLETED"
    assert final_state["routing_decision"] == "CLOSED"
    assert final_state["financial_facts"]["reconciliation_result"]["is_fully_paid"] is True


@pytest.mark.asyncio
async def test_ar_workflow_partial_payment():
    """Test a partial payment which should route to 'partial' (PROCESSING)."""
    initial_state: FinanceState = {
        "workflow_id": "test-ar-wf-2",
        "workflow_type": "AR",
        "status": "PENDING",
        "raw_document": json.dumps(PARTIAL_PAYMENT_REMITTANCE_JSON),
        "validation_errors": [],
        "financial_facts": {},
    }

    config = {"configurable": {"thread_id": "test-ar-wf-2"}}
    final_state = await ar_graph.ainvoke(initial_state, config=config)

    assert final_state["status"] == "REQUIRES_APPROVAL"
    assert final_state["routing_decision"] == "HITL"
    assert final_state["financial_facts"]["reconciliation_result"]["is_fully_paid"] is False
    assert final_state["financial_facts"]["reconciliation_result"]["remaining_balance"] > 0
