from typing import Literal, Optional
from pydantic import BaseModel
from src.core.config import yaml_config

class RoutingDecision(BaseModel):
    requires_hitl: bool
    hitl_reason: Optional[Literal["HIGH_VALUE", "TOLERANCE_EXCEPTION", "MISSING_DOCS"]]

def evaluate_hitl_rules(amount: float, tolerance_exceeded: bool, missing_docs: bool = False) -> RoutingDecision:
    """Evaluates deterministic rules to decide if human-in-the-loop (HITL) intervention is required."""
    high_value_threshold = yaml_config.get("finance", {}).get("high_value_threshold", 10000.0)
    
    if amount > high_value_threshold:
        return RoutingDecision(requires_hitl=True, hitl_reason="HIGH_VALUE")
    if tolerance_exceeded:
        return RoutingDecision(requires_hitl=True, hitl_reason="TOLERANCE_EXCEPTION")
    if missing_docs:
        return RoutingDecision(requires_hitl=True, hitl_reason="MISSING_DOCS")
    
    return RoutingDecision(requires_hitl=False, hitl_reason=None)
