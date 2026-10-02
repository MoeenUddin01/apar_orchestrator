from typing import Set
from src.core.exceptions import OrchestratorError
from src.grc.models import UserRole


class PermissionDeniedError(OrchestratorError):
    """Raised when a user attempts an action without appropriate permissions."""

    def __init__(self, role: str, permission: str):
        super().__init__(
            f"Role '{role}' is not granted required permission '{permission}'."
        )


class Permission:
    INITIATE_WORKFLOW = "workflow:initiate"
    READ_WORKFLOW = "workflow:read"
    APPROVE_MAKER_CHECKER = "governance:approve"
    REJECT_MAKER_CHECKER = "governance:reject"
    VIEW_AUDIT_LOGS = "audit:read"
    MANAGE_POLICY_RULES = "policy:manage"


ROLE_PERMISSIONS: dict[UserRole, Set[str]] = {
    UserRole.ADMIN: {
        Permission.INITIATE_WORKFLOW,
        Permission.READ_WORKFLOW,
        Permission.APPROVE_MAKER_CHECKER,
        Permission.REJECT_MAKER_CHECKER,
        Permission.VIEW_AUDIT_LOGS,
        Permission.MANAGE_POLICY_RULES,
    },
    UserRole.MAKER: {
        Permission.INITIATE_WORKFLOW,
        Permission.READ_WORKFLOW,
    },
    UserRole.CHECKER: {
        Permission.READ_WORKFLOW,
        Permission.APPROVE_MAKER_CHECKER,
        Permission.REJECT_MAKER_CHECKER,
    },
    UserRole.AUDITOR: {
        Permission.READ_WORKFLOW,
        Permission.VIEW_AUDIT_LOGS,
    },
}


def verify_role_permission(role: UserRole, permission: str) -> bool:
    """Verifies whether the given role holds the requested permission."""
    allowed_permissions = ROLE_PERMISSIONS.get(role, set())
    return permission in allowed_permissions


def enforce_permission(role: UserRole, permission: str) -> None:
    """Enforces that a role has permission, raising PermissionDeniedError if not."""
    if not verify_role_permission(role, permission):
        raise PermissionDeniedError(role=role.value, permission=permission)
