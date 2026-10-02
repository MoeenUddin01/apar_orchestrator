from datetime import datetime, timedelta, timezone
import pytest
from pydantic import ValidationError

from src.core.security.redaction import Redactor, default_redactor
from src.database.retention_jobs import (
    cleanup_in_memory_checkpoints,
    run_data_retention_job,
)
from src.domain.compliance_state import (
    ComplianceRationale,
    ReconciliationResult,
    ReconciliationStatus,
    RedactionResult,
)
from src.finance.reconciliation import (
    reconcile_invoice_totals,
    reconcile_payment_request,
    reconciliation_node,
)
from src.llm.middleware import LLMPrivacyMiddleware, privacy_interceptor


# ============================================================================
# 1. Compliance Domain Models Tests
# ============================================================================

def test_compliance_rationale_validation():
    # Valid rationale
    rationale = ComplianceRationale(
        component="test_component",
        decision="MATCHED",
        rationale="Calculated totals match declared invoice total.",
    )
    assert rationale.component == "test_component"
    assert rationale.decision == "MATCHED"
    assert "Calculated totals" in rationale.rationale

    # Empty rationale should fail validation
    with pytest.raises(ValidationError):
        ComplianceRationale(
            component="test_component",
            decision="MATCHED",
            rationale="   ",
        )


def test_redaction_result_defaults():
    result = RedactionResult(redacted_text="Sample text")
    assert result.pii_detected is False
    assert result.total_redactions == 0
    assert result.entities_found == {}
    assert result.redacted_at is not None


# ============================================================================
# 2. PII Redactor Tests
# ============================================================================

def test_redactor_ssn_masking():
    redactor = Redactor()
    raw = "User SSN is 123-45-6789 for identification."
    result = redactor.redact_text(raw)
    assert result.pii_detected is True
    assert result.total_redactions == 1
    assert result.entities_found.get("SSN") == 1
    assert "[REDACTED_SSN]" in result.redacted_text
    assert "123-45-6789" not in result.redacted_text


def test_redactor_email_and_phone():
    redactor = Redactor()
    raw = "Contact support@company.com or call +1-800-555-0199."
    result = redactor.redact_text(raw)
    assert result.pii_detected is True
    assert "[REDACTED_EMAIL]" in result.redacted_text
    assert "[REDACTED_PHONE]" in result.redacted_text
    assert "support@company.com" not in result.redacted_text
    assert "+1-800-555-0199" not in result.redacted_text


def test_redactor_credit_card():
    redactor = Redactor()
    raw = "Payment card 4111-1111-1111-1111 processed."
    result = redactor.redact_text(raw)
    assert result.pii_detected is True
    assert "[REDACTED_CREDIT_CARD]" in result.redacted_text


def test_redactor_preserves_financial_figures():
    """
    CRITICAL: Ensures PII redactor does not corrupt financial figures, PO numbers, prices, or dates.
    """
    redactor = Redactor()
    financial_text = "Invoice total is $1,234.56 for PO-10045 dated 2026-10-02. Item qty 10 @ $25.50 = $255.00."
    result = redactor.redact_text(financial_text)
    
    assert result.pii_detected is False
    assert result.total_redactions == 0
    assert result.redacted_text == financial_text
    assert "$1,234.56" in result.redacted_text
    assert "PO-10045" in result.redacted_text
    assert "2026-10-02" in result.redacted_text
    assert "$255.00" in result.redacted_text


def test_redact_dict_recursive():
    redactor = Redactor()
    payload = {
        "invoice_id": "INV-99",
        "vendor": "Acme Corp",
        "amount": 1500.0,
        "contact": {
            "email": "user@example.com",
            "phone": "555-123-4567",
        },
    }
    redacted_payload, result = redactor.redact_dict(payload)
    assert result.pii_detected is True
    assert redacted_payload["contact"]["email"] == "[REDACTED_EMAIL]"
    assert redacted_payload["contact"]["phone"] == "[REDACTED_PHONE]"
    assert redacted_payload["amount"] == 1500.0


# ============================================================================
# 3. LLM Privacy Middleware Tests
# ============================================================================

def test_llm_privacy_middleware_wrap_call():
    middleware = LLMPrivacyMiddleware()

    def mock_llm(prompt: str) -> str:
        return f"LLM Response to: {prompt}"

    raw_prompt = "Process invoice for john.doe@acme.com with SSN 123-45-6789."
    response, redaction_res, rationale = middleware.wrap_llm_call(mock_llm, raw_prompt)

    assert redaction_res.pii_detected is True
    assert "[REDACTED_EMAIL]" in response
    assert "[REDACTED_SSN]" in response
    assert rationale.component == "LLMPrivacyMiddleware"
    assert rationale.decision == "PROMPT_REDACTED_AND_DISPATCHED"


def test_privacy_interceptor_decorator():
    @privacy_interceptor
    def dummy_llm_call(prompt: str) -> str:
        return prompt

    raw = "Send update to test@domain.org"
    output = dummy_llm_call(raw)
    assert "[REDACTED_EMAIL]" in output
    assert "test@domain.org" not in output


# ============================================================================
# 4. Financial Accuracy & Reconciliation Tests
# ============================================================================

def test_reconcile_invoice_totals_success():
    line_items = [
        {"item_id": "1", "description": "Widget A", "quantity": 10, "unit_price": 25.0, "total": 250.0},
        {"item_id": "2", "description": "Widget B", "quantity": 5, "unit_price": 50.0, "total": 250.0},
    ]
    res = reconcile_invoice_totals(
        line_items=line_items,
        declared_subtotal=500.0,
        declared_tax=50.0,
        declared_total=550.0,
    )

    assert res.status == ReconciliationStatus.MATCHED
    assert res.is_balanced is True
    assert res.difference == 0.0
    assert len(res.discrepancies) == 0
    assert res.rationale is not None
    assert res.rationale.decision == "RECONCILED_MATCH"


def test_reconcile_invoice_totals_discrepancy():
    line_items = [
        {"item_id": "1", "description": "Widget A", "quantity": 10, "unit_price": 25.0, "total": 250.0},
    ]
    # Declared total is 400.0 but subtotal 250.0 + tax 25.0 = 275.0
    res = reconcile_invoice_totals(
        line_items=line_items,
        declared_subtotal=250.0,
        declared_tax=25.0,
        declared_total=400.0,
    )

    assert res.status == ReconciliationStatus.DISCREPANCY
    assert res.is_balanced is False
    assert res.difference == 125.0
    assert len(res.discrepancies) == 1
    assert res.discrepancies[0].item_id == "grand_total_mismatch"


def test_reconcile_payment_request():
    # Successful match
    res_success = reconcile_payment_request(
        requested_amount=1000.0,
        invoice_total=1000.0,
        ledger_balance=5000.0,
    )
    assert res_success.is_balanced is True

    # Failure due to insufficient ledger balance
    res_insufficient = reconcile_payment_request(
        requested_amount=10000.0,
        invoice_total=10000.0,
        ledger_balance=5000.0,
    )
    assert res_insufficient.is_balanced is False
    assert any(d.item_id == "insufficient_ledger_balance" for d in res_insufficient.discrepancies)


def test_reconciliation_node():
    state = {
        "extracted_invoice": {
            "subtotal": 1000.0,
            "tax_amount": 100.0,
            "invoice_total": 1100.0,
            "line_items": [
                {"quantity": 10, "unit_price": 100.0, "total": 1000.0}
            ],
        }
    }
    update = reconciliation_node(state)
    assert update["is_reconciled"] is True
    assert update["reconciliation_result"]["status"] == "MATCHED"
    assert update["compliance_rationale"] is not None


# ============================================================================
# 5. Data Retention Jobs Tests
# ============================================================================

def test_cleanup_in_memory_checkpoints():
    now_ts = datetime.now(timezone.utc).timestamp()
    old_ts = (datetime.now(timezone.utc) - timedelta(days=40)).timestamp()

    store = {
        "active_thread_1": {"timestamp": now_ts, "state": "active"},
        "old_thread_2": {"timestamp": old_ts, "state": "expired"},
    }

    # TTL of 30 days (2592000 seconds)
    res = cleanup_in_memory_checkpoints(store, retention_seconds=2592000)

    assert res["status"] == "SUCCESS"
    assert res["total_records_deleted"] == 1
    assert "old_thread_2" in res["deleted_thread_ids"]
    assert "active_thread_1" in store
    assert "old_thread_2" not in store


@pytest.mark.asyncio
async def test_run_data_retention_job():
    now_ts = datetime.now(timezone.utc).timestamp()
    old_ts = (datetime.now(timezone.utc) - timedelta(days=60)).timestamp()

    store = {
        "thread_active": {"ts": now_ts},
        "thread_expired": {"ts": old_ts},
    }

    job_result = await run_data_retention_job(retention_days=30, memory_store=store)

    assert job_result["retention_days"] == 30
    assert job_result["memory_cleanup"]["total_records_deleted"] == 1
    assert "thread_expired" not in store
    assert "thread_active" in store
