from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class ReconciliationStatus(str, Enum):
    MATCHED = "MATCHED"
    DISCREPANCY = "DISCREPANCY"
    FAILED = "FAILED"


class ComplianceRationale(BaseModel):
    """
    Enforces explainability and traceability for automated and LLM-driven financial decisions.
    """
    decision_id: Optional[str] = None
    component: str = Field(..., description="System component or node originating the decision")
    decision: str = Field(..., description="The outcome or classification made (e.g., APPROVED, MATCHED, REDACTED)")
    rationale: str = Field(..., description="Human-readable rationale explaining why this decision was reached")
    confidence_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    factors: List[str] = Field(default_factory=list, description="Key input factors or rules supporting the decision")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @field_validator("rationale")
    @classmethod
    def validate_rationale_not_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Compliance rationale cannot be empty or whitespace.")
        return value.strip()


class RedactedEntity(BaseModel):
    entity_type: str
    count: int = 1


class RedactionResult(BaseModel):
    """
    Tracks PII redaction details for data privacy compliance (GDPR/CCPA).
    """
    original_text_hash: Optional[str] = None
    redacted_text: str = ""
    pii_detected: bool = False
    entities_found: Dict[str, int] = Field(default_factory=dict)
    total_redactions: int = 0
    redacted_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ReconciliationItem(BaseModel):
    item_id: str
    description: str = ""
    expected_amount: float
    actual_amount: float
    difference: float
    matched: bool = False


class ReconciliationResult(BaseModel):
    """
    Tracks financial accuracy and deterministic reconciliation output across line items and balances.
    """
    status: ReconciliationStatus = ReconciliationStatus.MATCHED
    total_expected: float = 0.0
    total_actual: float = 0.0
    difference: float = 0.0
    is_balanced: bool = True
    discrepancies: List[ReconciliationItem] = Field(default_factory=list)
    rationale: Optional[ComplianceRationale] = None
    reconciled_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
