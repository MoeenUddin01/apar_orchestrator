from typing import Any, Dict
from src.grc.models import PolicyResult, UserRole

DEFAULT_HIGH_VALUE_THRESHOLD = 10000.0


def validate_pre_execution_policy(state: Dict[str, Any]) -> PolicyResult:
    """Validates input data completeness and authorization before graph execution."""
    violations = []
    extracted_data = state.get("extracted_data") or {}
    raw_doc = state.get("raw_document")

    if not raw_doc and not extracted_data:
        violations.append("Empty workflow payload: Missing both raw_document and extracted_data.")

    passed = len(violations) == 0
    return PolicyResult(
        policy_passed=passed,
        violations=violations,
        requires_approval=not passed,
        details={"phase": "pre_execution"}
    )


def validate_post_execution_policy(
    state: Dict[str, Any],
    threshold: float = DEFAULT_HIGH_VALUE_THRESHOLD
) -> PolicyResult:
    """
    Validates financial limits and output data integrity after extraction/matching nodes.
    Requires Checker approval if transaction amount exceeds threshold or if validation errors exist.
    """
    violations = []
    requires_approval = False
    extracted_data = state.get("extracted_data") or {}
    total_amount = float(
        extracted_data.get("invoice_total")
        or extracted_data.get("total_payment")
        or extracted_data.get("total_amount")
        or extracted_data.get("amount")
        or 0.0
    )




    # Threshold Policy Check
    if total_amount > threshold:
        requires_approval = True
        violations.append(f"High-value transaction: Amount ${total_amount:,.2f} exceeds policy limit ${threshold:,.2f}.")

    # Risk Policy Check
    risk_level = state.get("risk_level")
    risk_assessment = state.get("risk_assessment") or {}
    requires_human_review = state.get("requires_human_review") or risk_assessment.get("requires_manual_approval")
    if risk_level in ["HIGH", "CRITICAL"] or requires_human_review:
        requires_approval = True
        violations.append(f"Risk policy threshold: Risk level '{risk_level or 'HIGH'}' requires Checker authorization.")

    # Validation errors check
    validation_errors = state.get("validation_errors") or []
    if validation_errors:
        requires_approval = True
        violations.extend([f"Validation error: {err}" for err in validation_errors])


    passed = len(violations) == 0
    return PolicyResult(
        policy_passed=passed,
        violations=violations,
        requires_approval=requires_approval,
        details={
            "phase": "post_execution",
            "transaction_amount": total_amount,
            "threshold": threshold,
        }
    )
