from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RiskCategory(str, Enum):
    SECURITY = "SECURITY"
    FRAUD = "FRAUD"
    DUPLICATE = "DUPLICATE"
    FINANCIAL = "FINANCIAL"
    VENDOR = "VENDOR"
    OPERATIONAL = "OPERATIONAL"
    AI_VALIDATION = "AI_VALIDATION"
    EXTERNAL = "EXTERNAL"


class RiskFlag(BaseModel):
    code: str
    category: RiskCategory
    message: str
    severity: RiskLevel = RiskLevel.LOW
    source: str = "internal"
    details: Dict[str, Any] = Field(default_factory=dict)


class RiskScore(BaseModel):
    score: float = Field(default=0.0, ge=0.0, le=100.0)
    level: RiskLevel = RiskLevel.LOW
    flags: List[RiskFlag] = Field(default_factory=list)
    breakdown: Dict[str, float] = Field(default_factory=dict)


class RiskAssessmentResult(BaseModel):
    risk_score: RiskScore = Field(default_factory=RiskScore)
    requires_manual_approval: bool = False
    recommended_action: str = "CONTINUE"  # CONTINUE, MONITOR, HUMAN_REVIEW_RECOMMENDED, BLOCK_UNTIL_AUTHORIZED
    sanitized_input: Optional[str] = None
    security_findings: List[str] = Field(default_factory=list)
    validation_failures: List[str] = Field(default_factory=list)
    evaluated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    details: Dict[str, Any] = Field(default_factory=dict)
