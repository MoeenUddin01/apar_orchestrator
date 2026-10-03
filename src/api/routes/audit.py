from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.database.audit_repository import default_audit_repository
from src.domain.audit_schema import AuditEvent

router = APIRouter(prefix="/audit", tags=["Audit Trail & Verification"])


class VerificationResponse(BaseModel):
    workflow_id: str
    is_valid: bool
    event_count: int
    error: Optional[str] = None


@router.get("/events/{event_id}", response_model=AuditEvent)
async def get_audit_event(event_id: str) -> AuditEvent:
    """Retrieves a single audit log event by its unique event_id."""
    event = default_audit_repository.get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail=f"Audit event '{event_id}' not found.")
    return event


@router.get("/workflows/{workflow_id}", response_model=List[AuditEvent])
async def get_workflow_audit_trail(workflow_id: str) -> List[AuditEvent]:
    """Retrieves all chronological audit trail events associated with a specific workflow."""
    events = default_audit_repository.get_workflow_events(workflow_id)
    if not events:
        raise HTTPException(
            status_code=404, detail=f"No audit records found for workflow '{workflow_id}'."
        )
    return events


@router.get("/workflows/{workflow_id}/verify", response_model=VerificationResponse)
async def verify_workflow_audit_integrity(workflow_id: str) -> VerificationResponse:
    """
    Cryptographically verifies the SHA-256 hash chain integrity of a workflow's audit log sequence.
    Detects any unauthorized tampering or sequence breaks.
    """
    events = default_audit_repository.get_workflow_events(workflow_id)
    if not events:
        raise HTTPException(
            status_code=404, detail=f"No audit records found for workflow '{workflow_id}'."
        )

    is_valid, error_msg = default_audit_repository.verify_chain(workflow_id)
    return VerificationResponse(
        workflow_id=workflow_id,
        is_valid=is_valid,
        event_count=len(events),
        error=error_msg,
    )


@router.get("/correlations/{correlation_id}", response_model=List[AuditEvent])
async def get_correlation_audit_trail(correlation_id: str) -> List[AuditEvent]:
    """Retrieves cross-workflow audit events linked by correlation_id."""
    events = default_audit_repository.get_correlation_events(correlation_id)
    if not events:
        raise HTTPException(
            status_code=404,
            detail=f"No audit records found for correlation_id '{correlation_id}'.",
        )
    return events


@router.get("/reports", response_model=List[AuditEvent])
async def query_audit_reports(
    event_type: Optional[str] = Query(None, description="Filter by event_type"),
    start_time: Optional[str] = Query(None, description="Filter ISO-8601 start time"),
    end_time: Optional[str] = Query(None, description="Filter ISO-8601 end time"),
) -> List[AuditEvent]:
    """Queries audit log events for compliance reporting."""
    return default_audit_repository.query_reports(
        event_type=event_type, start_time=start_time, end_time=end_time
    )
