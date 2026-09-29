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
