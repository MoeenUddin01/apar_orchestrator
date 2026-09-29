from typing import Literal, Optional
from pydantic import BaseModel

class RoutingDecision(BaseModel):
    requires_hitl: bool
    hitl_reason: Optional[Literal["HIGH_VALUE", "TOLERANCE_EXCEPTION", "MISSING_DOCS"]]

def evaluate_hitl_rules(amount: float, tolerance_exceeded: bool, missing_docs: bool = False) -> RoutingDecision:
    """Evaluates deterministic rules to decide if human-in-the-loop (HITL) intervention is required."""
    if amount > 10000.0:
        return RoutingDecision(requires_hitl=True, hitl_reason="HIGH_VALUE")
    if tolerance_exceeded:
        return RoutingDecision(requires_hitl=True, hitl_reason="TOLERANCE_EXCEPTION")
    if missing_docs:
        return RoutingDecision(requires_hitl=True, hitl_reason="MISSING_DOCS")
    
    return RoutingDecision(requires_hitl=False, hitl_reason=None)
