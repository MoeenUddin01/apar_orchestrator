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
async def test_ar_workflow_high_value_requires_approval():
    """Scenario B: High-value AR remittance ($60,000) -> Governance requires approval -> Pauses at maker_checker."""
    raw_doc = json.dumps({
        "customer_identifier": "CUST-002",
        "referenced_invoices": ["INV-3001"],
        "total_payment": 60000.0,
    })
    initial_state: FinanceState = {
        "workflow_id": "test-ar-high-1",
        "workflow_type": "AR",
        "status": "PENDING",
        "raw_document": raw_doc,
        "validation_errors": [],
        "financial_facts": {},
    }
    config = {"configurable": {"thread_id": "test-ar-high-1"}}
    
    await ar_graph.ainvoke(initial_state, config=config)
    state = await ar_graph.aget_state(config)
    
    assert state.next[0] == "maker_checker"
    assert state.values["governance_status"]["requires_checker_approval"] is True
    assert state.values["governance_status"]["approval_status"] == "PENDING"


@pytest.mark.asyncio
async def test_ar_workflow_checker_approves():
    """Scenario C: Paused AR workflow -> Checker APPROVES -> Resumes checkpoint -> COMPLETED."""
    raw_doc = json.dumps({
        "customer_identifier": "CUST-002",
        "referenced_invoices": ["INV-3001"],
        "total_payment": 60000.0,
    })
    initial_state: FinanceState = {
        "workflow_id": "test-ar-approve-1",
        "workflow_type": "AR",
        "status": "PENDING",
        "raw_document": raw_doc,
        "validation_errors": [],
        "financial_facts": {},
    }
    config = {"configurable": {"thread_id": "test-ar-approve-1"}}
    
    await ar_graph.ainvoke(initial_state, config=config)
    
    # Checkpoint state contains risk and compliance before approval
    state_paused = await ar_graph.aget_state(config)
    assert state_paused.values.get("risk_score") is not None
    
    # Resume with Checker approval
    hitl_input = {
        "hitl_input": {
            "action": "APPROVED",
            "checker_id": "ar_checker_01",
            "comments": "AR remittance approved"
        }
    }
    await ar_graph.aupdate_state(config, hitl_input)
    final_state = await ar_graph.ainvoke(None, config=config)
    
    assert final_state["status"] == "COMPLETED"
    assert final_state["governance_status"]["approval_status"] == "APPROVED"
    assert final_state["governance_status"]["approved_by"] == "ar_checker_01"


@pytest.mark.asyncio
async def test_ar_workflow_checker_rejects():
    """Scenario D: Paused AR workflow -> Checker REJECTS -> ERROR."""
    raw_doc = json.dumps({
        "customer_identifier": "CUST-002",
        "referenced_invoices": ["INV-3001"],
        "total_payment": 60000.0,
    })
    initial_state: FinanceState = {
        "workflow_id": "test-ar-reject-1",
        "workflow_type": "AR",
        "status": "PENDING",
        "raw_document": raw_doc,
        "validation_errors": [],
        "financial_facts": {},
    }
    config = {"configurable": {"thread_id": "test-ar-reject-1"}}
    
    await ar_graph.ainvoke(initial_state, config=config)
    
    # Resume with Checker rejection
    hitl_input = {
        "hitl_input": {
            "action": "REJECTED",
            "checker_id": "ar_checker_01",
            "comments": "Unverified customer remittance"
        }
    }
    await ar_graph.aupdate_state(config, hitl_input)
    final_state = await ar_graph.ainvoke(None, config=config)
    
    assert final_state["status"] == "ERROR"
    assert final_state["governance_status"]["approval_status"] == "REJECTED"


@pytest.mark.asyncio
async def test_ar_unauthorized_user_api():
    """Scenario E: MAKER / AUDITOR attempts AR approval -> HTTP 403 Forbidden."""
    from httpx import ASGITransport, AsyncClient
    from src.api.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "workflow_id": "test-ar-rbac-1",
            "workflow_type": "AR",
            "decision": "APPROVED",
            "user_role": "MAKER",
            "checker_id": "maker_user"
        }
        res_maker = await client.post("/governance/decide", json=payload, headers={"x-user-role": "MAKER"})
        assert res_maker.status_code == 403

        res_auditor = await client.post("/governance/decide", json=payload, headers={"x-user-role": "AUDITOR"})
        assert res_auditor.status_code == 403


@pytest.mark.asyncio
async def test_ar_privacy_sanitization():
    """Scenario H: PII in AR raw document -> Redacted before extraction."""
    raw_doc = (
        "Customer ID: CUST-002\n"
        "Contact Email: customer_contact@domain.com\n"
        "Phone: 555-019-2834\n"
        "Total Paid: $1,500.00"
    )
    initial_state: FinanceState = {
        "workflow_id": "test-ar-privacy-1",
        "workflow_type": "AR",
        "status": "PENDING",
        "raw_document": raw_doc,
        "validation_errors": [],
        "financial_facts": {},
    }
    config = {"configurable": {"thread_id": "test-ar-privacy-1"}}
    final_state = await ar_graph.ainvoke(initial_state, config=config)
    
    assert final_state["redaction_result"]["pii_detected"] is True
    assert "customer_contact@domain.com" not in final_state["sanitized_input"]
    assert "[REDACTED_EMAIL]" in final_state["sanitized_input"]

