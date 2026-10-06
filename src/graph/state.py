from typing import Any, Dict, List, Literal, Optional, TypedDict


class FinanceState(TypedDict, total=False):
    """
    Shared LangGraph workflow state container for AP and AR operations.

    Attributes:
        workflow_id: Unique string identifier for the active workflow run.
        workflow_type: Discriminator for workflow category ("AP" or "AR").
        status: Execution status ("PENDING", "PROCESSING", "REQUIRES_APPROVAL", "COMPLETED", "ERROR").
        raw_document: Unstructured input document (e.g. raw text or JSON string).
        extracted_data: Structured output produced by LLM extraction boundaries.
        validation_errors: List of strings detailing validation failures.
        financial_facts: Dictionary holding retrieved database records and deterministic calculation outputs.
        routing_decision: Decision tag determining conditional edge transitions.
    """
    workflow_id: str
    workflow_type: Literal["AP", "AR"]
    status: Literal["PENDING", "PROCESSING", "REQUIRES_APPROVAL", "COMPLETED", "ERROR"]
    raw_document: Optional[str]
    extracted_data: Optional[Dict[str, Any]]
    validation_errors: List[str]
    financial_facts: Dict[str, Any]
    routing_decision: Optional[str]
    hitl_decision: Optional[Dict[str, Any]]
    hitl_input: Optional[Dict[str, Any]]
    drafted_communications: Optional[List[Dict[str, Any]]]
    governance_status: Optional[Dict[str, Any]]

    # Risk Assessment Persistence
    risk_assessment: Optional[Dict[str, Any]]
    risk_score: Optional[float]
    risk_level: Optional[str]
    risk_flags: Optional[List[Dict[str, Any]]]
    validation_results: Optional[Dict[str, Any]]
    security_findings: Optional[List[str]]
    assessment_timestamp: Optional[str]
    recommended_action: Optional[str]
    requires_human_review: Optional[bool]
    sanitized_input: Optional[str]

    # Historical Invoices for Risk Scoring
    historical_invoices: Optional[List[Dict[str, Any]]]
    historical_amounts: Optional[List[float]]


    # Compliance & Reconciliation Persistence
    reconciliation_result: Optional[Dict[str, Any]]
    is_reconciled: Optional[bool]
    compliance_rationale: Optional[Dict[str, Any]]
    
    # Privacy / Data Security
    redaction_result: Optional[Dict[str, Any]]
