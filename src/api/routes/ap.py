import uuid
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.graph.ap.graph import ap_graph
from src.graph.state import FinanceState

router = APIRouter(prefix="/ap", tags=["Accounts Payable"])


class InvoiceProcessingRequest(BaseModel):
    """Payload for submitting an invoice document to the AP workflow."""
    raw_document: str
    workflow_id: Optional[str] = None


class InvoiceProcessingResponse(BaseModel):
    """Response returned after executing the AP workflow graph."""
    workflow_id: str
    status: str
    routing_decision: Optional[str] = None
    extracted_data: Optional[Dict[str, Any]] = None
    validation_errors: Optional[list] = None
    financial_facts: Optional[Dict[str, Any]] = None
    drafted_communications: Optional[list] = None

class HITLResumeRequest(BaseModel):
    action: str  # e.g., "APPROVE", "REJECT"
    comments: Optional[str] = None


@router.post("/process-invoice", response_model=InvoiceProcessingResponse)
async def process_invoice(payload: InvoiceProcessingRequest) -> InvoiceProcessingResponse:
    """Intake an invoice document, run the AP LangGraph workflow, and return results."""
    workflow_id = payload.workflow_id or f"ap-wf-{uuid.uuid4().hex[:8]}"

    initial_state: FinanceState = {
        "workflow_id": workflow_id,
        "workflow_type": "AP",
        "status": "PENDING",
        "raw_document": payload.raw_document,
        "validation_errors": [],
        "financial_facts": {},
    }

    config = {"configurable": {"thread_id": workflow_id}}

    try:
        final_state = await ap_graph.ainvoke(initial_state, config=config)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"AP workflow execution failed: {str(exc)}")

    return InvoiceProcessingResponse(
        workflow_id=final_state.get("workflow_id", workflow_id),
        status=final_state.get("status", "UNKNOWN"),
        routing_decision=final_state.get("routing_decision"),
        extracted_data=final_state.get("extracted_data"),
        validation_errors=final_state.get("validation_errors"),
        financial_facts=final_state.get("financial_facts"),
        drafted_communications=final_state.get("drafted_communications"),
    )


@router.get("/{workflow_id}/state")
async def get_ap_state(workflow_id: str):
    """Retrieve the current state of a paused AP workflow."""
    config = {"configurable": {"thread_id": workflow_id}}
    state_snapshot = await ap_graph.aget_state(config)
    
    if not state_snapshot or not state_snapshot.values:
        raise HTTPException(status_code=404, detail="Workflow not found.")
        
    return {
        "workflow_id": workflow_id,
        "state": state_snapshot.values,
        "next_nodes": state_snapshot.next
    }


@router.post("/{workflow_id}/resume", response_model=InvoiceProcessingResponse)
async def resume_ap_workflow(workflow_id: str, payload: HITLResumeRequest) -> InvoiceProcessingResponse:
    """Resume a paused AP workflow by injecting human input."""
    config = {"configurable": {"thread_id": workflow_id}}
    
    state_snapshot = await ap_graph.aget_state(config)
    if not state_snapshot or not state_snapshot.values:
        raise HTTPException(status_code=404, detail="Workflow not found.")
        
    if not state_snapshot.next:
        raise HTTPException(status_code=400, detail="Workflow is not currently paused.")
    
    # Inject the human input into the state
    human_input_update = {
        "hitl_input": {
            "action": payload.action,
            "comments": payload.comments
        }
    }
    
    try:
        # We can just update the state as if from the user and invoke with None
        # OR invoke with the new state payload if the graph node expects it
        final_state = await ap_graph.ainvoke(human_input_update, config=config)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to resume AP workflow: {str(exc)}")

    return InvoiceProcessingResponse(
        workflow_id=final_state.get("workflow_id", workflow_id),
        status=final_state.get("status", "UNKNOWN"),
        routing_decision=final_state.get("routing_decision"),
        extracted_data=final_state.get("extracted_data"),
        validation_errors=final_state.get("validation_errors"),
        financial_facts=final_state.get("financial_facts"),
        drafted_communications=final_state.get("drafted_communications"),
    )
