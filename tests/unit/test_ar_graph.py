import json
import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import app
from src.graph.ar.graph import ar_graph


@pytest.mark.asyncio
async def test_ar_graph_execution_closed():
    raw_doc = json.dumps({
        "customer_identifier": "CUST-002",
        "referenced_invoices": ["INV-3001"],
        "total_payment": 1500.0,
    })

    initial_state = {
        "workflow_id": "ar-test-1",
        "workflow_type": "AR",
        "status": "PENDING",
        "raw_document": raw_doc,
        "validation_errors": [],
        "financial_facts": {},
    }

    config = {"configurable": {"thread_id": "ar-test-1"}}
    final_state = await ar_graph.ainvoke(initial_state, config=config)
    assert final_state["status"] == "COMPLETED"
    assert final_state["routing_decision"] == "CLOSED"
    assert final_state["financial_facts"]["reconciliation_result"]["is_fully_paid"] is True


@pytest.mark.asyncio
async def test_ar_graph_execution_overdue():
    raw_doc = json.dumps({
        "customer_identifier": "CUST-001",
        "referenced_invoices": ["INV-2001"],
        "total_payment": 1000.0,  # Leaves balance on overdue INV-2001
    })

    initial_state = {
        "workflow_id": "ar-test-2",
        "workflow_type": "AR",
        "status": "PENDING",
        "raw_document": raw_doc,
        "validation_errors": [],
        "financial_facts": {},
    }

    config = {"configurable": {"thread_id": "ar-test-2"}}
    final_state = await ar_graph.ainvoke(initial_state, config=config)
    assert final_state["routing_decision"] == "OVERDUE"
    assert final_state["financial_facts"]["reconciliation_result"]["remaining_balance"] > 0


@pytest.mark.asyncio
async def test_ar_process_payment_api_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "raw_document": json.dumps({
                "customer_identifier": "CUST-002",
                "referenced_invoices": ["INV-3001"],
                "total_payment": 1500.0,
            })
        }
        response = await client.post("/ar/process-payment", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["routing_decision"] == "CLOSED"
        assert data["status"] == "COMPLETED"
