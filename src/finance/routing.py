from typing import Literal, Optional, List
from pydantic import BaseModel
from src.core.config import yaml_config

class RoutingDecision(BaseModel):
    requires_hitl: bool
    hitl_reasons: List[str] = []
    hitl_reason: Optional[str] = None

def evaluate_hitl_rules(amount: float, tolerance_exceeded: bool, missing_docs: bool = False) -> RoutingDecision:
    """Evaluates deterministic rules to decide if human-in-the-loop (HITL) intervention is required."""
    high_value_threshold = yaml_config.get("finance", {}).get("high_value_threshold", 10000.0)
    
    reasons = []
    if missing_docs:
        reasons.append("MISSING_DOCS")
    if tolerance_exceeded:
        reasons.append("TOLERANCE_EXCEPTION")
    if amount > high_value_threshold:
        reasons.append("HIGH_VALUE")
        
    if reasons:
        return RoutingDecision(requires_hitl=True, hitl_reasons=reasons, hitl_reason=reasons[0])
    
    return RoutingDecision(requires_hitl=False, hitl_reasons=[], hitl_reason=None)
