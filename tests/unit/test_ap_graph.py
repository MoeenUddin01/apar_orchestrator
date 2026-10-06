import json
import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import app
from src.database.repositories.ap_repository import ap_repository
from src.graph.ap.graph import ap_graph


@pytest.fixture(autouse=True)
def clear_ap_repo():
    """Clear in-memory AP repository between tests for isolation."""
    ap_repository.clear()
    yield
    ap_repository.clear()


@pytest.mark.asyncio

async def test_ap_graph_execution_perfect_match():
    raw_doc = json.dumps({
        "invoice_number": "INV-1001",
        "vendor_id": "VEND-135",
        "po_number": "PO-1001",
        "invoice_total": 1200.0,
        "line_items": [
            {"item_id": "ITEM-102", "quantity": 6.0, "unit_price": 200.0, "total_price": 1200.0}
        ]
    })

    initial_state = {
        "workflow_id": "ap-test-1",
        "workflow_type": "AP",
        "status": "PENDING",
        "raw_document": raw_doc,
        "validation_errors": [],
        "financial_facts": {},
    }

    config = {"configurable": {"thread_id": "ap-test-1"}}
    final_state = await ap_graph.ainvoke(initial_state, config=config)
    assert final_state["status"] == "COMPLETED"
    assert final_state["routing_decision"] == "APPROVE"
    assert final_state["financial_facts"]["match_result"]["is_match"] is True


@pytest.mark.asyncio
async def test_ap_graph_execution_exception_routing():
    raw_doc = json.dumps({
        "invoice_number": "INV-1002",
        "vendor_id": "VEND-002",
        "po_number": "PO-1002",
        "invoice_total": 9999.0,  # Mismatch with PO-1002 total of 5000.0
    })

    initial_state = {
        "workflow_id": "ap-test-2",
        "workflow_type": "AP",
        "status": "PENDING",
        "raw_document": raw_doc,
        "validation_errors": [],
        "financial_facts": {},
    }

    config = {"configurable": {"thread_id": "ap-test-2"}}
    final_state = await ap_graph.ainvoke(initial_state, config=config)
    assert final_state["status"] == "REQUIRES_APPROVAL"
    assert final_state["routing_decision"] == "HITL"
    assert final_state["financial_facts"]["match_result"]["is_match"] is False


@pytest.mark.asyncio
async def test_ap_process_invoice_api_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "raw_document": json.dumps({
                "invoice_number": "INV-1001",
                "vendor_id": "VEND-135",
                "po_number": "PO-1001",
                "invoice_total": 1200.0,
            })
        }
        response = await client.post("/ap/process-invoice", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["routing_decision"] == "APPROVE"
        assert data["status"] == "COMPLETED"
