import logging
from typing import Any, Dict, Optional
from src.database.audit_repository import AuditRepository, default_audit_repository
from src.domain.audit_schema import ActorType, AuditEvent, EventType, GRCDomain

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
        workflow_type: Optional[str] = None,
        transaction_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        event = AuditEvent(
            workflow_id=workflow_id,
            workflow_type=workflow_type or ("AP" if "ap" in workflow_id.lower() else ("AR" if "ar" in workflow_id.lower() else None)),
            transaction_id=transaction_id,
            correlation_id=correlation_id,
            actor_type=ActorType.SYSTEM,
            actor_id="orchestrator-engine",
            actor_role="SYSTEM",
            event_type=EventType.WORKFLOW_STARTED,
            grc_domain=GRCDomain.WORKFLOW,
            action="START_WORKFLOW",
            status="STARTED",
            summary=f"Workflow {workflow_id} started.",
            metadata=metadata or {},
        )
        return self.repository.log_event(event)

    def on_workflow_complete(
        self,
        workflow_id: str,
        workflow_type: Optional[str] = None,
        transaction_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        result: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        event = AuditEvent(
            workflow_id=workflow_id,
            workflow_type=workflow_type or ("AP" if "ap" in workflow_id.lower() else ("AR" if "ar" in workflow_id.lower() else None)),
            transaction_id=transaction_id,
            correlation_id=correlation_id,
            actor_type=ActorType.SYSTEM,
            actor_id="orchestrator-engine",
            actor_role="SYSTEM",
            event_type=EventType.WORKFLOW_COMPLETED,
            grc_domain=GRCDomain.WORKFLOW,
            action="COMPLETE_WORKFLOW",
            decision="COMPLETED",
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
        workflow_type: Optional[str] = None,
        transaction_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        event = AuditEvent(
            workflow_id=workflow_id,
            workflow_type=workflow_type,
            transaction_id=transaction_id,
            correlation_id=correlation_id,
            actor_type=ActorType.SYSTEM,
            actor_id=f"node:{node_name}",
            actor_role="SYSTEM",
            event_type=EventType.NODE_ENTRY,
            grc_domain=GRCDomain.WORKFLOW,
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
        workflow_type: Optional[str] = None,
        transaction_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        status: str = "SUCCESS",
        result: Optional[str] = None,
        evidence_refs: Optional[list] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        event = AuditEvent(
            workflow_id=workflow_id,
            workflow_type=workflow_type,
            transaction_id=transaction_id,
            correlation_id=correlation_id,
            actor_type=ActorType.SYSTEM,
            actor_id=f"node:{node_name}",
            actor_role="SYSTEM",
            event_type=EventType.NODE_EXIT,
            grc_domain=GRCDomain.WORKFLOW,
            node_name=node_name,
            status=status,
            result=result,
            summary=f"Exiting graph node '{node_name}' with status {status}.",
            evidence_refs=evidence_refs or [],
            metadata=metadata or {},
        )
        return self.repository.log_event(event)

    def on_privacy_redaction(
        self,
        workflow_id: str,
        workflow_type: Optional[str] = None,
        transaction_id: Optional[str] = None,
        redaction_count: int = 0,
        entities_found: Optional[Dict[str, int]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        event = AuditEvent(
            workflow_id=workflow_id,
            workflow_type=workflow_type,
            transaction_id=transaction_id,
            actor_type=ActorType.SERVICE,
            actor_id="privacy-middleware",
            actor_role="SECURITY_MIDDLEWARE",
            event_type=EventType.COMPLIANCE_ASSESSMENT,
            grc_domain=GRCDomain.PRIVACY,
            node_name="Privacy_Middleware",
            action="PII_REDACTION",
            decision="REDACTED",
            status="PASS",
            reason=f"Redacted {redaction_count} PII entity instances before LLM processing.",
            summary=f"Redacted {redaction_count} PII entities. Types: {list((entities_found or {}).keys())}.",
            metadata={
                **(metadata or {}),
                "pii_detected": redaction_count > 0,
                "redaction_count": redaction_count,
                "entities_found": entities_found or {},
            },
        )
        return self.repository.log_event(event)

    def on_llm_call(
        self,
        workflow_id: str,
        node_name: str,
        model_name: str,
        workflow_type: Optional[str] = None,
        transaction_id: Optional[str] = None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        event = AuditEvent(
            workflow_id=workflow_id,
            workflow_type=workflow_type,
            transaction_id=transaction_id,
            actor_type=ActorType.LLM_AGENT,
            actor_id=model_name,
            actor_role="LLM_PROBABILISTIC_BOUNDARY",
            event_type=EventType.LLM_CALL,
            grc_domain=GRCDomain.WORKFLOW,
            node_name=node_name,
            action="LLM_EXTRACTION",
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
        workflow_type: Optional[str] = None,
        transaction_id: Optional[str] = None,
        risk_score: Optional[float] = None,
        recommended_action: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        flags_list = [getattr(f, "value", str(f)) for f in risk_flags]
        flags_str = ", ".join(flags_list) or "None"
        event = AuditEvent(
            workflow_id=workflow_id,
            workflow_type=workflow_type,
            transaction_id=transaction_id,
            actor_type=ActorType.SERVICE,
            actor_id="risk-engine",
            actor_role="RISK_ENGINE",
            event_type=EventType.RISK_ASSESSMENT,
            grc_domain=GRCDomain.RISK,
            node_name="Risk_Assessment",
            action="EVALUATE_RISK",
            decision=risk_level.upper(),
            status=risk_level.upper(),
            reason=f"Risk level {risk_level}. Risk score: {risk_score or 0.0}. Risk flags: {flags_str}.",
            summary=f"Risk assessment computed level {risk_level} (recommended action: {recommended_action or action}).",
            risk_level=risk_level.upper(),
            risk_score=risk_score,
            risk_flags=flags_list,
            metadata={
                **(metadata or {}),
                "risk_score": risk_score,
                "risk_level": risk_level,
                "risk_flags": flags_list,
                "recommended_action": recommended_action or action,
            },
        )
        return self.repository.log_event(event)

    def on_compliance_assessment(
        self,
        workflow_id: str,
        status: str,
        findings: list,
        workflow_type: Optional[str] = None,
        transaction_id: Optional[str] = None,
        reconciliation_status: Optional[str] = None,
        discrepancy_reason: Optional[str] = None,
        evidence_refs: Optional[list] = None,
    ) -> AuditEvent:
        reason_str = discrepancy_reason or ("; ".join(findings) if findings else f"Reconciliation status: {status}")
        event = AuditEvent(
            workflow_id=workflow_id,
            workflow_type=workflow_type,
            transaction_id=transaction_id,
            actor_type=ActorType.SERVICE,
            actor_id="compliance-engine",
            actor_role="COMPLIANCE_ENGINE",
            event_type=EventType.COMPLIANCE_ASSESSMENT,
            grc_domain=GRCDomain.COMPLIANCE,
            node_name="Compliance_Assessment",
            action="RECONCILE",
            decision=status.upper(),
            status=status.upper(),
            result=reconciliation_status,
            reason=reason_str,
            summary=f"Compliance assessment status: {status}.",
            evidence_refs=evidence_refs or [],
            metadata={"findings_count": len(findings), "reconciliation_status": reconciliation_status},
        )
        return self.repository.log_event(event)

    def on_governance_decision(
        self,
        workflow_id: str,
        decision: str,
        policy_code: str,
        workflow_type: Optional[str] = None,
        transaction_id: Optional[str] = None,
        reason: Optional[str] = None,
        actor_id: str = "governance-policy-engine",
        actor_role: str = "GOVERNANCE_ENGINE",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        requires_approval = decision.upper() in ["APPROVAL_REQUIRED", "REQUIRES_APPROVAL", "PENDING"]
        appr_status = "PENDING" if requires_approval else "NOT_REQUIRED"
        event = AuditEvent(
            workflow_id=workflow_id,
            workflow_type=workflow_type,
            transaction_id=transaction_id,
            actor_type=ActorType.SYSTEM,
            actor_id=actor_id,
            actor_role=actor_role,
            event_type=EventType.GOVERNANCE_DECISION,
            grc_domain=GRCDomain.GOVERNANCE,
            node_name="Policy_Evaluation",
            action="EVALUATE_POLICY",
            decision=decision.upper(),
            status=decision.upper(),
            reason=reason or f"Policy rule evaluation for {policy_code}.",
            summary=f"Policy evaluation result: {decision} ({policy_code}).",
            approval_required=requires_approval,
            approval_status=appr_status,
            metadata={**(metadata or {}), "policy_code": policy_code},
        )
        return self.repository.log_event(event)

    def on_maker_checker_action(
        self,
        workflow_id: str,
        action: str,  # "REQUESTED", "APPROVED", "REJECTED"
        checker_id: str,
        workflow_type: Optional[str] = None,
        transaction_id: Optional[str] = None,
        reason: Optional[str] = None,
        role: Optional[str] = None,
    ) -> AuditEvent:
        event_type_map = {
            "REQUESTED": EventType.MAKER_CHECKER_REQUESTED,
            "APPROVED": EventType.MAKER_APPROVED,
            "REJECTED": EventType.MAKER_REJECTED,
        }
        ev_type = event_type_map.get(action.upper(), EventType.GOVERNANCE_DECISION)
        
        actor_role = role.upper() if role else ("CHECKER" if action != "REQUESTED" else "FINANCIAL_CONTROLLER")
        actor_type = ActorType.USER

        appr_status_map = {
            "REQUESTED": "PENDING",
            "APPROVED": "APPROVED",
            "REJECTED": "REJECTED",
        }
        appr_status = appr_status_map.get(action.upper(), action.upper())

        event = AuditEvent(
            workflow_id=workflow_id,
            workflow_type=workflow_type,
            transaction_id=transaction_id,
            actor_type=actor_type,
            actor_id=checker_id,
            actor_role=actor_role,
            event_type=ev_type,
            grc_domain=GRCDomain.MAKER_CHECKER,
            node_name="Maker_Checker",
            action=action.upper(),
            decision=action.upper(),
            status=action.upper(),
            reason=reason or f"Maker-Checker {action} by {checker_id}",
            result=reason,
            summary=f"Maker-Checker action {action} by {checker_id} (Role: {actor_role}).",
            approval_required=True,
            approval_status=appr_status,
            metadata={"user_role": actor_role, "reason": reason or ""},
        )
        return self.repository.log_event(event)

    def on_error(
        self,
        workflow_id: str,
        node_name: Optional[str],
        error_msg: str,
        workflow_type: Optional[str] = None,
        transaction_id: Optional[str] = None,
        error_type: str = "SYSTEM_ERROR",
    ) -> AuditEvent:
        is_security = "SECURITY" in error_type.upper()
        ev_type = EventType.SECURITY_ERROR if is_security else EventType.ERROR
        domain = GRCDomain.SECURITY if is_security else GRCDomain.WORKFLOW
        event = AuditEvent(
            workflow_id=workflow_id,
            workflow_type=workflow_type,
            transaction_id=transaction_id,
            actor_type=ActorType.SYSTEM,
            actor_id="orchestrator-system",
            actor_role="SYSTEM",
            event_type=ev_type,
            grc_domain=domain,
            node_name=node_name,
            action="HANDLE_ERROR",
            decision="ERROR",
            status="ERROR",
            reason=error_msg,
            summary=f"Error in node '{node_name}': {error_msg}",
            metadata={"error_type": error_type, "error_detail": error_msg},
        )
        return self.repository.log_event(event)


# Global default callback instance
default_audit_callback = AuditLoggerCallbackHandler()
