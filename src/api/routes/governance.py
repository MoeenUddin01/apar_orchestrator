from typing import Any, Dict, Optional
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from src.grc.models import ApprovalStatus, UserRole
from src.grc.rbac import Permission, PermissionDeniedError, enforce_permission
from src.graph.ap.graph import ap_graph
from src.graph.ar.graph import ar_graph

router = APIRouter(prefix="/governance", tags=["Governance & Policy"])


class GovernanceDecisionRequest(BaseModel):
    workflow_id: str
    workflow_type: str = "AP"  # "AP" or "AR"
    decision: ApprovalStatus  # APPROVED or REJECTED
    comments: Optional[str] = None
    user_role: UserRole = UserRole.CHECKER
    checker_id: str = "checker_01"


class GovernanceDecisionResponse(BaseModel):
    workflow_id: str
    status: str
    governance_status: Optional[Dict[str, Any]] = None


@router.post("/decide", response_model=GovernanceDecisionResponse)
async def submit_governance_decision(
    payload: GovernanceDecisionRequest,
    x_user_role: Optional[str] = Header(None)
) -> GovernanceDecisionResponse:
    """Submits a Maker-Checker approval or rejection decision for a paused workflow."""
    role = UserRole(x_user_role) if x_user_role else payload.user_role

    try:
        if payload.decision == ApprovalStatus.APPROVED:
            enforce_permission(role, Permission.APPROVE_MAKER_CHECKER)
        elif payload.decision == ApprovalStatus.REJECTED:
            enforce_permission(role, Permission.REJECT_MAKER_CHECKER)
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=403, detail=str(exc))

    target_graph = ap_graph if payload.workflow_type.upper() == "AP" else ar_graph
    config = {"configurable": {"thread_id": payload.workflow_id}}

    state_snapshot = await target_graph.aget_state(config)
    if not state_snapshot or not state_snapshot.values:
        raise HTTPException(status_code=404, detail="Workflow instance not found.")

    human_input_update = {
        "hitl_input": {
            "action": payload.decision.value,
            "checker_id": payload.checker_id,
            "comments": payload.comments,
        }
    }

    try:
        final_state = await target_graph.ainvoke(human_input_update, config=config)
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to process governance decision: {str(exc)}"
        )

    return GovernanceDecisionResponse(
        workflow_id=final_state.get("workflow_id", payload.workflow_id),
        status=final_state.get("status", "UNKNOWN"),
        governance_status=final_state.get("governance_status"),
    )
