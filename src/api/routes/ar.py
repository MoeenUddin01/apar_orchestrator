import uuid
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.graph.ar.graph import ar_graph
from src.graph.state import FinanceState

router = APIRouter(prefix="/ar", tags=["Accounts Receivable"])


class RemittanceProcessingRequest(BaseModel):
    """Payload for submitting a remittance/payment document to the AR workflow."""
    raw_document: str
    workflow_id: Optional[str] = None


class RemittanceProcessingResponse(BaseModel):
    """Response returned after executing the AR workflow graph."""
    workflow_id: str
    status: str
    routing_decision: Optional[str] = None
    extracted_data: Optional[Dict[str, Any]] = None
    financial_facts: Optional[Dict[str, Any]] = None


@router.post("/process-payment", response_model=RemittanceProcessingResponse)
async def process_payment(payload: RemittanceProcessingRequest) -> RemittanceProcessingResponse:
    """Intake a remittance / payment document, run the AR LangGraph workflow, and return results."""
    workflow_id = payload.workflow_id or f"ar-wf-{uuid.uuid4().hex[:8]}"

    initial_state: FinanceState = {
        "workflow_id": workflow_id,
        "workflow_type": "AR",
        "status": "PENDING",
        "raw_document": payload.raw_document,
        "validation_errors": [],
        "financial_facts": {},
    }

    try:
        final_state = await ar_graph.ainvoke(initial_state)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"AR workflow execution failed: {str(exc)}")

    return RemittanceProcessingResponse(
        workflow_id=final_state.get("workflow_id", workflow_id),
        status=final_state.get("status", "UNKNOWN"),
        routing_decision=final_state.get("routing_decision"),
        extracted_data=final_state.get("extracted_data"),
        financial_facts=final_state.get("financial_facts"),
    )
