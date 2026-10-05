import logging
from typing import Any, Dict, Optional
from src.database.audit_repository import AuditRepository, default_audit_repository
from src.domain.audit_schema import ActorType, AuditEvent, EventType

logger = logging.getLogger(__name__)


class AuditLoggerCallbackHandler:
    """
    LangGraph execution listener callback handler.
    Automatically captures graph node entries/exits, LLM invocations,
    risk/compliance assessments, governance actions, and system errors.
    """

    def __init__(self, repository: Optional[AuditRepository] = None):
        self.repository = repository or default_audit_repository

    def on_workflow_start(
        self,
        workflow_id: str,
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        event = AuditEvent(
            workflow_id=workflow_id,
            correlation_id=correlation_id,
            actor_type=ActorType.SYSTEM,
            actor_id="orchestrator-engine",
            event_type=EventType.WORKFLOW_STARTED,
            status="STARTED",
            summary=f"Workflow {workflow_id} started.",
            metadata=metadata or {},
        )
        return self.repository.log_event(event)

    def on_workflow_complete(
        self,
        workflow_id: str,
        correlation_id: Optional[str] = None,
        result: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        event = AuditEvent(
            workflow_id=workflow_id,
            correlation_id=correlation_id,
            actor_type=ActorType.SYSTEM,
            actor_id="orchestrator-engine",
            event_type=EventType.WORKFLOW_COMPLETED,
            status="COMPLETED",
            result=result,
            summary=f"Workflow {workflow_id} completed successfully.",
            metadata=metadata or {},
        )
        return self.repository.log_event(event)

    def on_node_entry(
        self,
        node_name: str,
        workflow_id: str,
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        event = AuditEvent(
            workflow_id=workflow_id,
            correlation_id=correlation_id,
            actor_type=ActorType.SYSTEM,
            actor_id=f"node:{node_name}",
            event_type=EventType.NODE_ENTRY,
            node_name=node_name,
            status="ENTERING",
            summary=f"Entering graph node '{node_name}'.",
            metadata=metadata or {},
        )
        return self.repository.log_event(event)

    def on_node_exit(
        self,
        node_name: str,
        workflow_id: str,
        correlation_id: Optional[str] = None,
        status: str = "SUCCESS",
        result: Optional[str] = None,
        evidence_refs: Optional[list] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        event = AuditEvent(
            workflow_id=workflow_id,
            correlation_id=correlation_id,
            actor_type=ActorType.SYSTEM,
            actor_id=f"node:{node_name}",
            event_type=EventType.NODE_EXIT,
            node_name=node_name,
            status=status,
            result=result,
            summary=f"Exiting graph node '{node_name}' with status {status}.",
            evidence_refs=evidence_refs or [],
            metadata=metadata or {},
        )
        return self.repository.log_event(event)

    def on_llm_call(
        self,
        workflow_id: str,
        node_name: str,
        model_name: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        event = AuditEvent(
            workflow_id=workflow_id,
            actor_type=ActorType.LLM_AGENT,
            actor_id=model_name,
            event_type=EventType.LLM_CALL,
            node_name=node_name,
            status="SUCCESS",
            summary=f"LLM call executed in '{node_name}' using '{model_name}'.",
            metadata={
                **(metadata or {}),
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
            },
        )
        return self.repository.log_event(event)

    def on_risk_assessment(
        self,
        workflow_id: str,
        risk_level: str,
        risk_flags: list,
        action: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        event = AuditEvent(
            workflow_id=workflow_id,
            actor_type=ActorType.SERVICE,
            actor_id="risk-engine",
            event_type=EventType.RISK_ASSESSMENT,
            node_name="Risk_Assessment",
            status=risk_level,
            result=action,
            summary=f"Risk assessment computed level {risk_level}.",
            metadata={
                **(metadata or {}),
                "risk_flags": [getattr(f, "value", str(f)) for f in risk_flags],
            },
        )
        return self.repository.log_event(event)

    def on_compliance_assessment(
        self,
        workflow_id: str,
        status: str,
        findings: list,
        reconciliation_status: Optional[str] = None,
        evidence_refs: Optional[list] = None,
    ) -> AuditEvent:
        event = AuditEvent(
            workflow_id=workflow_id,
            actor_type=ActorType.SERVICE,
            actor_id="compliance-engine",
            event_type=EventType.COMPLIANCE_ASSESSMENT,
            node_name="Compliance_Assessment",
            status=status,
            result=reconciliation_status,
            summary=f"Compliance assessment status: {status}.",
            evidence_refs=evidence_refs or [],
            metadata={"findings_count": len(findings)},
        )
        return self.repository.log_event(event)

    def on_governance_decision(
        self,
        workflow_id: str,
        decision: str,
        policy_code: str,
        actor_id: str = "governance-policy-engine",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        event = AuditEvent(
            workflow_id=workflow_id,
            actor_type=ActorType.SYSTEM,
            actor_id=actor_id,
            event_type=EventType.GOVERNANCE_DECISION,
            node_name="Policy_Evaluation",
            status=decision,
            summary=f"Policy evaluation result: {decision} ({policy_code}).",
            metadata={**(metadata or {}), "policy_code": policy_code},
        )
        return self.repository.log_event(event)

    def on_maker_checker_action(
        self,
        workflow_id: str,
        action: str,  # "REQUESTED", "APPROVED", "REJECTED"
        checker_id: str,
        reason: Optional[str] = None,
        role: Optional[str] = None,
    ) -> AuditEvent:
        event_type_map = {
            "REQUESTED": EventType.MAKER_CHECKER_REQUESTED,
            "APPROVED": EventType.MAKER_APPROVED,
            "REJECTED": EventType.MAKER_REJECTED,
        }
        ev_type = event_type_map.get(action.upper(), EventType.GOVERNANCE_DECISION)
        
        actor_role = role.upper() if role else ("CHECKER" if action != "REQUESTED" else "USER")
        try:
            actor_type = ActorType(actor_role)
        except ValueError:
            actor_type = ActorType.CHECKER if action != "REQUESTED" else ActorType.USER

        event = AuditEvent(
            workflow_id=workflow_id,
            actor_type=actor_type,
            actor_id=checker_id,
            event_type=ev_type,
            node_name="Maker_Checker",
            status=action.upper(),
            result=reason,
            summary=f"Maker-Checker action {action} by {checker_id} (Role: {actor_role}).",
            metadata={"user_role": actor_role, "reason": reason or ""},
        )
        return self.repository.log_event(event)

    def on_error(
        self,
        workflow_id: str,
        node_name: Optional[str],
        error_msg: str,
        error_type: str = "SYSTEM_ERROR",
    ) -> AuditEvent:
        ev_type = EventType.SECURITY_ERROR if "SECURITY" in error_type.upper() else EventType.ERROR
        event = AuditEvent(
            workflow_id=workflow_id,
            actor_type=ActorType.SYSTEM,
            actor_id="orchestrator-system",
            event_type=ev_type,
            node_name=node_name,
            status="ERROR",
            summary=f"Error in node '{node_name}': {error_msg}",
            metadata={"error_type": error_type, "error_detail": error_msg},
        )
        return self.repository.log_event(event)


# Global default callback instance
default_audit_callback = AuditLoggerCallbackHandler()
