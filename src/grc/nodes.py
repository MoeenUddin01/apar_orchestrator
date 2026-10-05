from typing import Any, Dict
from src.core.logging import logger
from src.graph.state import FinanceState
from src.grc.models import ApprovalStatus, GovernanceStatus
from src.grc.policy_rules import (
    validate_post_execution_policy,
    validate_pre_execution_policy,
)
from src.graph.shared.callbacks.audit_logger import default_audit_callback


def governance_policy_check_node(state: FinanceState) -> Dict[str, Any]:
    """Evaluates pre and post execution policy rules and sets governance status in AP graph."""
    logger.info(f"AP Graph [governance_policy_check]: Evaluating policy rules.")
    
    pre_result = validate_pre_execution_policy(state)
    post_result = validate_post_execution_policy(state)
    
    all_violations = pre_result.violations + post_result.violations
    policy_passed = pre_result.policy_passed and post_result.policy_passed
    requires_approval = pre_result.requires_approval or post_result.requires_approval

    gov_status = GovernanceStatus(
        policy_passed=policy_passed,
        policy_violations=all_violations,
        requires_checker_approval=requires_approval,
        approval_status=ApprovalStatus.PENDING if requires_approval else ApprovalStatus.BYPASSED,
    )
    
    workflow_id = state.get("workflow_id", "UNKNOWN_WF")
    
    default_audit_callback.on_governance_decision(
        workflow_id=workflow_id,
        decision="APPROVAL_REQUIRED" if requires_approval else "PASSED",
        policy_code="AP_GOVERNANCE_POLICY"
    )
    
    if requires_approval:
        default_audit_callback.on_maker_checker_action(
            workflow_id=workflow_id,
            action="REQUESTED",
            checker_id="Financial Controller",
            reason="; ".join(all_violations)
        )
    
    return {
        "governance_status": gov_status.model_dump(),
        "status": "REQUIRES_APPROVAL" if requires_approval else state.get("status", "PROCESSING"),
    }



def maker_checker_review_node(state: FinanceState) -> Dict[str, Any]:
    """Applies the human Checker API decision to finalize AP governance approval."""
    logger.info(f"AP Graph [maker_checker_review]: Applying Checker approval decision.")
    hitl_input = state.get("hitl_input") or {}
    action = hitl_input.get("action", "REJECT")
    checker_id = hitl_input.get("checker_id", "UNKNOWN_CHECKER")
    user_role = hitl_input.get("user_role", "CHECKER")
    comments = hitl_input.get("comments", "")
    workflow_id = state.get("workflow_id", "UNKNOWN_WF")

    existing_gov = state.get("governance_status") or {}
    updated_gov = dict(existing_gov)
    updated_gov["approved_by_role"] = user_role
    
    if action in ["APPROVE", "APPROVED"]:
        updated_gov["approval_status"] = ApprovalStatus.APPROVED.value
        updated_gov["approved_by"] = checker_id
        updated_gov["approval_comments"] = comments
        status = "COMPLETED"
        routing_decision = "APPROVE"
    else:
        updated_gov["approval_status"] = ApprovalStatus.REJECTED.value
        updated_gov["approval_comments"] = comments
        status = "ERROR"
        routing_decision = "EXCEPTION"

    default_audit_callback.on_maker_checker_action(
        workflow_id=workflow_id,
        action=action if action in ["APPROVED", "REJECTED"] else ("APPROVED" if action == "APPROVE" else "REJECTED"),
        checker_id=checker_id,
        reason=comments,
        role=user_role
    )

    return {
        "governance_status": updated_gov,
        "status": status,
        "routing_decision": routing_decision,
    }



def ar_governance_policy_check_node(state: FinanceState) -> Dict[str, Any]:
    """Evaluates policy rules for AR workflow."""
    logger.info(f"AR Graph [governance_policy_check]: Evaluating policy rules.")
    
    pre_result = validate_pre_execution_policy(state)
    post_result = validate_post_execution_policy(state)
    
    all_violations = pre_result.violations + post_result.violations
    policy_passed = pre_result.policy_passed and post_result.policy_passed
    requires_approval = pre_result.requires_approval or post_result.requires_approval

    gov_status = GovernanceStatus(
        policy_passed=policy_passed,
        policy_violations=all_violations,
        requires_checker_approval=requires_approval,
        approval_status=ApprovalStatus.PENDING if requires_approval else ApprovalStatus.BYPASSED,
    )
    
    workflow_id = state.get("workflow_id", "UNKNOWN_WF")
    
    default_audit_callback.on_governance_decision(
        workflow_id=workflow_id,
        decision="APPROVAL_REQUIRED" if requires_approval else "PASSED",
        policy_code="AR_GOVERNANCE_POLICY"
    )
    
    if requires_approval:
        default_audit_callback.on_maker_checker_action(
            workflow_id=workflow_id,
            action="REQUESTED",
            checker_id="Financial Controller",
            reason="; ".join(all_violations)
        )
    
    return {
        "governance_status": gov_status.model_dump(),
        "status": "REQUIRES_APPROVAL" if requires_approval else state.get("status", "PROCESSING"),
    }


def ar_maker_checker_review_node(state: FinanceState) -> Dict[str, Any]:
    """Applies the human Checker decision for AR actions."""
    logger.info(f"AR Graph [maker_checker_review]: Applying Checker approval decision.")
    hitl_input = state.get("hitl_input") or {}
    action = hitl_input.get("action", "REJECT")
    checker_id = hitl_input.get("checker_id", "UNKNOWN_CHECKER")
    user_role = hitl_input.get("user_role", "CHECKER")
    comments = hitl_input.get("comments", "")
    workflow_id = state.get("workflow_id", "UNKNOWN_WF")

    existing_gov = state.get("governance_status") or {}
    updated_gov = dict(existing_gov)
    updated_gov["approved_by_role"] = user_role
    
    if action in ["APPROVE", "APPROVED"]:
        updated_gov["approval_status"] = ApprovalStatus.APPROVED.value
        updated_gov["approved_by"] = checker_id
        updated_gov["approval_comments"] = comments
        status = "COMPLETED"
        routing_decision = "APPROVED"
    else:
        updated_gov["approval_status"] = ApprovalStatus.REJECTED.value
        updated_gov["approval_comments"] = comments
        status = "ERROR"
        routing_decision = "CANCELLED"

    default_audit_callback.on_maker_checker_action(
        workflow_id=workflow_id,
        action="APPROVED" if action in ["APPROVE", "APPROVED"] else "REJECTED",
        checker_id=checker_id,
        reason=comments,
        role=user_role
    )

    return {
        "governance_status": updated_gov,
        "status": status,
        "routing_decision": routing_decision,
    }

