from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field


class ActorType(str, Enum):
    SYSTEM = "SYSTEM"
    USER = "USER"
    LLM_AGENT = "LLM_AGENT"
    SERVICE = "SERVICE"
    CHECKER = "CHECKER"
    ADMIN = "ADMIN"
    MAKER = "MAKER"
    AUDITOR = "AUDITOR"


class GRCDomain(str, Enum):
    WORKFLOW = "WORKFLOW"
    SECURITY = "SECURITY"
    PRIVACY = "PRIVACY"
    RISK = "RISK"
    COMPLIANCE = "COMPLIANCE"
    GOVERNANCE = "GOVERNANCE"
    MAKER_CHECKER = "MAKER_CHECKER"


class EventType(str, Enum):
    # Workflow Events
    WORKFLOW_STARTED = "WORKFLOW_STARTED"
    WORKFLOW_COMPLETED = "WORKFLOW_COMPLETED"
    WORKFLOW_FAILED = "WORKFLOW_FAILED"

    # Node Transitions
    NODE_ENTRY = "NODE_ENTRY"
    NODE_EXIT = "NODE_EXIT"

    # Document Intelligence Events
    DOCUMENT_RECEIVED = "DOCUMENT_RECEIVED"
    EXTRACTION_STARTED = "EXTRACTION_STARTED"
    EXTRACTION_COMPLETED = "EXTRACTION_COMPLETED"
    LOW_CONFIDENCE_ROUTING = "LOW_CONFIDENCE_ROUTING"
    HUMAN_CORRECTION_APPLIED = "HUMAN_CORRECTION_APPLIED"
    RE_EXTRACTION = "RE_EXTRACTION"
    REVALIDATION = "REVALIDATION"

    # LLM Events
    LLM_CALL = "LLM_CALL"
    LLM_VALIDATION = "LLM_VALIDATION"

    # Security & Risk Events
    SECURITY_FINDING = "SECURITY_FINDING"
    RISK_ASSESSMENT = "RISK_ASSESSMENT"
    RISK_FLAGGED = "RISK_FLAGGED"
    SECURITY_ERROR = "SECURITY_ERROR"

    # Compliance Events
    COMPLIANCE_ASSESSMENT = "COMPLIANCE_ASSESSMENT"
    COMPLIANCE_FINDING = "COMPLIANCE_FINDING"
    RECONCILIATION_RESULT = "RECONCILIATION_RESULT"

    # Governance & Approval Events
    GOVERNANCE_DECISION = "GOVERNANCE_DECISION"
    MAKER_CHECKER_REQUESTED = "MAKER_CHECKER_REQUESTED"
    MAKER_APPROVED = "MAKER_APPROVED"
    MAKER_REJECTED = "MAKER_REJECTED"

    # Financial Action Events
    FINANCIAL_ACTION_REQUESTED = "FINANCIAL_ACTION_REQUESTED"
    FINANCIAL_ACTION_EXECUTED = "FINANCIAL_ACTION_EXECUTED"
    FINANCIAL_ACTION_FAILED = "FINANCIAL_ACTION_FAILED"

    # External & System Error Events
    EXTERNAL_API_CALL = "EXTERNAL_API_CALL"
    EXTERNAL_API_FAILURE = "EXTERNAL_API_FAILURE"
    ERROR = "ERROR"


class AuditEvent(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    workflow_id: str
    workflow_type: Optional[str] = None
    transaction_id: Optional[str] = None
    correlation_id: Optional[str] = None
    
    actor_type: ActorType = ActorType.SYSTEM
    actor_id: str = "orchestrator-system"
    actor_role: Optional[str] = None
    
    event_type: EventType
    grc_domain: Optional[GRCDomain] = None
    node_name: Optional[str] = None
    
    action: Optional[str] = None
    decision: Optional[str] = None
    status: str = "SUCCESS"
    
    reason: Optional[str] = None
    summary: Optional[str] = None
    result: Optional[str] = None
    
    # Backcheck & Risk / Governance Fields
    risk_level: Optional[str] = None
    risk_score: Optional[float] = None
    risk_flags: List[str] = Field(default_factory=list)
    approval_required: Optional[bool] = None
    approval_status: Optional[str] = None

    evidence_refs: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    previous_hash: Optional[str] = None
    event_hash: Optional[str] = None

