from typing import Any, Dict, List, Literal, Optional, TypedDict


class FinanceState(TypedDict, total=False):
    workflow_id: str
    workflow_type: Literal["AP", "AR"]
    status: Literal["PENDING", "PROCESSING", "REQUIRES_APPROVAL", "COMPLETED", "ERROR"]
    raw_document: Optional[str]
    extracted_data: Optional[Dict[str, Any]]
    validation_errors: List[str]
    financial_facts: Dict[str, Any]
    routing_decision: Optional[str]
