import pytest
from src.grc.models import ApprovalStatus, UserRole
from src.grc.policy_rules import validate_post_execution_policy, validate_pre_execution_policy
from src.grc.rbac import Permission, PermissionDeniedError, enforce_permission, verify_role_permission


def test_rbac_role_permissions():
    """Verify that roles have correct permissions assigned."""
    # Maker can initiate workflows but cannot approve Maker-Checker
    assert verify_role_permission(UserRole.MAKER, Permission.INITIATE_WORKFLOW) is True
    assert verify_role_permission(UserRole.MAKER, Permission.APPROVE_MAKER_CHECKER) is False

    # Checker can approve Maker-Checker but cannot manage policy rules
    assert verify_role_permission(UserRole.CHECKER, Permission.APPROVE_MAKER_CHECKER) is True
    assert verify_role_permission(UserRole.CHECKER, Permission.MANAGE_POLICY_RULES) is False

    # Admin has all permissions
    assert verify_role_permission(UserRole.ADMIN, Permission.APPROVE_MAKER_CHECKER) is True
    assert verify_role_permission(UserRole.ADMIN, Permission.MANAGE_POLICY_RULES) is True

    # Auditor has read access only
    assert verify_role_permission(UserRole.AUDITOR, Permission.VIEW_AUDIT_LOGS) is True
    assert verify_role_permission(UserRole.AUDITOR, Permission.APPROVE_MAKER_CHECKER) is False


def test_rbac_enforcement():
    """Verify that enforce_permission raises PermissionDeniedError when permission is missing."""
    # Should pass without exception
    enforce_permission(UserRole.CHECKER, Permission.APPROVE_MAKER_CHECKER)

    # Should raise exception
    with pytest.raises(PermissionDeniedError):
        enforce_permission(UserRole.MAKER, Permission.APPROVE_MAKER_CHECKER)


def test_pre_execution_policy_validation():
    """Verify pre-execution policy rule evaluation."""
    empty_state = {}
    result = validate_pre_execution_policy(empty_state)
    assert result.policy_passed is False
    assert result.requires_approval is True
    assert len(result.violations) > 0

    valid_state = {"raw_document": "INV-1001 vendor: VEND-1"}
    valid_result = validate_pre_execution_policy(valid_state)
    assert valid_result.policy_passed is True
    assert valid_result.requires_approval is False


def test_post_execution_policy_high_value_threshold():
    """Verify post-execution threshold checks."""
    low_value_state = {
        "extracted_data": {"total_amount": 5000.0}
    }
    low_result = validate_post_execution_policy(low_value_state, threshold=10000.0)
    assert low_result.policy_passed is True
    assert low_result.requires_approval is False

    high_value_state = {
        "extracted_data": {"total_amount": 25000.0}
    }
    high_result = validate_post_execution_policy(high_value_state, threshold=10000.0)
    assert high_result.policy_passed is False
    assert high_result.requires_approval is True
    assert any("exceeds policy limit" in v for v in high_result.violations)
