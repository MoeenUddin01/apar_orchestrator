from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    MAKER = "MAKER"
    CHECKER = "CHECKER"
    AUDITOR = "AUDITOR"


class ApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    BYPASSED = "BYPASSED"


class PolicyResult(BaseModel):
    policy_passed: bool = True
    violations: List[str] = Field(default_factory=list)
    requires_approval: bool = False
    details: Dict[str, Any] = Field(default_factory=dict)


class MakerCheckerAction(BaseModel):
    action_id: str
    thread_id: str
    maker_id: str
    checker_id: Optional[str] = None
    action_type: str  # e.g., "INVOICE_PAYMENT_APPROVAL", "CREDIT_MEMO_APPROVAL"
    amount: Optional[float] = None
    status: ApprovalStatus = ApprovalStatus.PENDING
    comments: Optional[str] = None


class GovernanceStatus(BaseModel):
    policy_passed: bool = True
    policy_violations: List[str] = Field(default_factory=list)
    requires_checker_approval: bool = False
    checker_role_required: UserRole = UserRole.CHECKER
    approved_by: Optional[str] = None
    approval_status: ApprovalStatus = ApprovalStatus.PENDING
    approval_comments: Optional[str] = None
