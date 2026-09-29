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

    try:
        final_state = await ap_graph.ainvoke(initial_state)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"AP workflow execution failed: {str(exc)}")

    return InvoiceProcessingResponse(
        workflow_id=final_state.get("workflow_id", workflow_id),
        status=final_state.get("status", "UNKNOWN"),
        routing_decision=final_state.get("routing_decision"),
        extracted_data=final_state.get("extracted_data"),
        validation_errors=final_state.get("validation_errors"),
        financial_facts=final_state.get("financial_facts"),
    )
