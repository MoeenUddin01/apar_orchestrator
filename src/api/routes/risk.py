from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.graph.ap.graph import ap_graph
from src.graph.ar.graph import ar_graph
from src.graph.shared.nodes.risk_assessment import risk_assessment_node

router = APIRouter(prefix="/risk", tags=["Risk Management"])


class RiskEvaluationRequest(BaseModel):
    vendor_id: Optional[str] = "VEND-DEFAULT"
    invoice_number: Optional[str] = "INV-001"
    amount: float = Field(default=0.0, description="Transaction amount")
    current_bank_account: Optional[str] = None
    baseline_bank_account: Optional[str] = None
    raw_input: Optional[str] = None
    extracted_data: Optional[Dict[str, Any]] = None
    deterministic_context: Optional[Dict[str, Any]] = None


class RiskEvaluationResponse(BaseModel):
    risk_level: str
    risk_score: float
    risk_flags: List[Dict[str, Any]]
    recommended_action: str
    requires_human_review: bool
    validation_failures: List[str] = Field(default_factory=list)
    security_findings: List[str] = Field(default_factory=list)
    assessment_timestamp: Optional[str] = None


@router.post("/evaluate", response_model=RiskEvaluationResponse)
async def evaluate_risk(payload: RiskEvaluationRequest) -> RiskEvaluationResponse:
    """Runs instant risk assessment node on incoming transaction payload without exposing system secrets."""
    state = payload.model_dump()
    evaluated_state = risk_assessment_node(state)

    val_res = evaluated_state.get("validation_results") or {}

    return RiskEvaluationResponse(
        risk_level=evaluated_state.get("risk_level", "LOW"),
        risk_score=evaluated_state.get("risk_score", 0.0),
        risk_flags=evaluated_state.get("risk_flags", []),
        recommended_action=evaluated_state.get("recommended_action", "CONTINUE"),
        requires_human_review=evaluated_state.get("requires_human_review", False),
        validation_failures=val_res.get("validation_failures", []),
        security_findings=evaluated_state.get("security_findings", []),
        assessment_timestamp=evaluated_state.get("assessment_timestamp"),
    )


@router.get("/assessments/{workflow_id}", response_model=RiskEvaluationResponse)
async def get_workflow_risk_assessment(
    workflow_id: str,
    workflow_type: str = "AP",
) -> RiskEvaluationResponse:
    """Fetches structured risk assessment details from a running or completed AP/AR workflow instance."""
    target_graph = ap_graph if workflow_type.upper() == "AP" else ar_graph
    config = {"configurable": {"thread_id": workflow_id}}

    state_snapshot = await target_graph.aget_state(config)
    if not state_snapshot or not state_snapshot.values:
        raise HTTPException(status_code=404, detail=f"Workflow instance '{workflow_id}' not found.")

    values = state_snapshot.values
    val_res = values.get("validation_results") or {}

    return RiskEvaluationResponse(
        risk_level=values.get("risk_level", "LOW"),
        risk_score=values.get("risk_score", 0.0),
        risk_flags=values.get("risk_flags", []),
        recommended_action=values.get("recommended_action", "CONTINUE"),
        requires_human_review=values.get("requires_human_review", False),
        validation_failures=val_res.get("validation_failures", []),
        security_findings=values.get("security_findings", []),
        assessment_timestamp=values.get("assessment_timestamp"),
    )
