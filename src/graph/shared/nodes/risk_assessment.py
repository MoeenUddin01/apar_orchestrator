from datetime import datetime, timezone
from typing import Any, Dict, List
from src.api.integrations.risk_apis import VendorRiskClient
from src.core.security.sanitization import analyze_security_sanitization
from src.domain.risk_state import RiskAssessmentResult, RiskCategory, RiskFlag, RiskLevel, RiskScore
from src.finance.risk_scoring import evaluate_operational_risk
from src.llm.validation import validate_against_deterministic_context, validate_llm_invoice_extraction
from src.graph.shared.callbacks.audit_logger import default_audit_callback



def risk_assessment_node(state: Dict[str, Any]) -> Dict[str, Any]:

    """
    LangGraph node to assess input security, operational financial risk, LLM extraction accuracy,
    and external vendor sanction risk.
    Updates graph state with risk metrics, flags, security findings, and recommended action.
    """
    raw_text = state.get("raw_input") or state.get("raw_document") or state.get("email_body") or ""

    extracted = state.get("extracted_data") or state.get("invoice_data") or {}

    vendor_id = extracted.get("vendor_id") or extracted.get("customer_identifier") or state.get("vendor_id") or "UNKNOWN_VENDOR"
    ref_invs = extracted.get("referenced_invoices")
    invoice_number = extracted.get("invoice_number") or (ref_invs[0] if (ref_invs and isinstance(ref_invs, list)) else None) or state.get("invoice_number") or "INV-UNKNOWN"
    amount = float(extracted.get("invoice_total") or extracted.get("total_payment") or extracted.get("total_amount") or state.get("amount") or 0.0)


    current_bank = extracted.get("bank_account") or state.get("bank_account")
    baseline_bank = state.get("baseline_bank_account")

    historical_invoices = state.get("historical_invoices", [])
    historical_amounts = state.get("historical_amounts", [])

    all_flags: List[RiskFlag] = []
    security_findings: List[str] = []
    validation_failures: List[str] = []

    # 1. Security & Input Sanitization
    sanitization_res = analyze_security_sanitization(raw_text)
    sanitized_text = sanitization_res.sanitized_text

    if sanitization_res.is_suspicious:
        security_findings = sanitization_res.detected_patterns
        for pattern_msg in sanitization_res.detected_patterns:
            all_flags.append(
                RiskFlag(
                    code="PROMPT_INJECTION_ATTEMPT",
                    category=RiskCategory.SECURITY,
                    message=pattern_msg,
                    severity=sanitization_res.risk_level,
                    source="input_sanitizer",
                    details={"raw_input_snippet": raw_text[:200]},
                )
            )

    # 2. Operational & Financial Risk Rules
    op_risk_score = evaluate_operational_risk(
        invoice_number=invoice_number,
        vendor_id=vendor_id,
        amount=amount,
        current_bank_account=current_bank,
        baseline_bank_account=baseline_bank,
        historical_invoices=historical_invoices,
        historical_amounts=historical_amounts,
    )
    all_flags.extend(op_risk_score.flags)

    # 3. AI Extraction Validation
    is_llm_valid = True
    if extracted:
        is_llm_valid, llm_flags = validate_llm_invoice_extraction(extracted)
        all_flags.extend(llm_flags)
        for f in llm_flags:
            validation_failures.append(f.message)

        det_context = state.get("deterministic_context", {})
        if det_context:
            is_ctx_valid, ctx_flags = validate_against_deterministic_context(extracted, det_context)
            all_flags.extend(ctx_flags)
            for f in ctx_flags:
                validation_failures.append(f.message)

    # 4. External Vendor Sanction & Risk Profile Lookup
    vendor_client = state.get("vendor_risk_client") or VendorRiskClient()
    ext_vendor_flag = vendor_client.evaluate_vendor_external_risk(vendor_id)
    if ext_vendor_flag:
        all_flags.append(ext_vendor_flag)

    # Determine highest severity level
    highest_severity = RiskLevel.LOW
    for flag in all_flags:
        if flag.severity == RiskLevel.CRITICAL:
            highest_severity = RiskLevel.CRITICAL
            break
        elif flag.severity == RiskLevel.HIGH and highest_severity != RiskLevel.CRITICAL:
            highest_severity = RiskLevel.HIGH
        elif flag.severity == RiskLevel.MEDIUM and highest_severity not in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            highest_severity = RiskLevel.MEDIUM

    # Aggregate numeric score
    score_floor = (
        95.0 if highest_severity == RiskLevel.CRITICAL
        else (75.0 if highest_severity == RiskLevel.HIGH
        else (45.0 if highest_severity == RiskLevel.MEDIUM else 0.0))
    )
    final_score_value = max(op_risk_score.score, score_floor)

    # Map Workflow Action Recommendation according to Risk Level
    if highest_severity == RiskLevel.CRITICAL:
        recommended_action = "BLOCK_UNTIL_AUTHORIZED"
        requires_approval = True
    elif highest_severity == RiskLevel.HIGH:
        recommended_action = "HUMAN_REVIEW_RECOMMENDED"
        requires_approval = True
    elif highest_severity == RiskLevel.MEDIUM:
        recommended_action = "MONITOR"
        requires_approval = False
    else:
        recommended_action = "CONTINUE"
        requires_approval = False

    risk_score_obj = RiskScore(
        score=round(final_score_value, 2),
        level=highest_severity,
        flags=all_flags,
        breakdown=op_risk_score.breakdown,
    )

    assessment_timestamp = datetime.now(timezone.utc).isoformat()

    result = RiskAssessmentResult(
        risk_score=risk_score_obj,
        requires_manual_approval=requires_approval,
        recommended_action=recommended_action,
        sanitized_input=sanitized_text,
        security_findings=security_findings,
        validation_failures=validation_failures,
        evaluated_at=assessment_timestamp,
        details={"vendor_id": vendor_id, "invoice_number": invoice_number, "amount": amount},
    )

    # Update state immutably
    updated_state = dict(state)
    updated_state["risk_assessment"] = result.model_dump()
    updated_state["risk_score"] = risk_score_obj.score
    updated_state["risk_level"] = highest_severity.value
    updated_state["risk_flags"] = [f.model_dump() for f in all_flags]
    updated_state["validation_results"] = {
        "is_llm_valid": is_llm_valid and len(validation_failures) == 0,
        "validation_failures": validation_failures,
    }
    updated_state["security_findings"] = security_findings
    updated_state["assessment_timestamp"] = assessment_timestamp
    updated_state["recommended_action"] = recommended_action
    updated_state["requires_human_review"] = requires_approval
    if sanitized_text and not updated_state.get("sanitized_input"):
        updated_state["sanitized_input"] = sanitized_text


    workflow_id = state.get("workflow_id", "UNKNOWN_WF")
    workflow_type = state.get("workflow_type", "AP" if "ap" in str(workflow_id).lower() else "AR")
    transaction_id = invoice_number if invoice_number != "INV-UNKNOWN" else (vendor_id if vendor_id != "UNKNOWN_VENDOR" else None)
    
    default_audit_callback.on_risk_assessment(
        workflow_id=workflow_id,
        workflow_type=workflow_type,
        transaction_id=transaction_id,
        risk_level=highest_severity.value,
        risk_flags=[f.code for f in all_flags],
        action=recommended_action,
        risk_score=round(final_score_value, 2),
        recommended_action=recommended_action,
        metadata={"risk_score": round(final_score_value, 2), "vendor_id": vendor_id, "amount": amount}
    )

    return updated_state


