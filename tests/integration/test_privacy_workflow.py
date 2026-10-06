import pytest
import json
from unittest.mock import patch, MagicMock

from src.graph.ap.nodes import extract_invoice_node
from src.llm.middleware import privacy_middleware

# Mock ExtractedInvoice return
from src.domain.ap.models import ExtractedInvoice, LineItem

mock_extracted_invoice = ExtractedInvoice(
    invoice_number="INV-1001",
    vendor_id="VEND-001",
    po_number="PO-1001",
    invoice_total=1000.0,
    line_items=[LineItem(item_id="1", quantity=1.0, unit_price=1000.0, total_price=1000.0)]
)

@pytest.mark.asyncio
async def test_case_a_no_pii():
    """Test A — No PII: LLM call proceeds, Invoice extraction works"""
    raw = "Invoice Number: INV-1001\nDescription: Office Chairs\nQuantity: 5\nTotal: $1,000"
    state = {"workflow_id": "wf-privacy-1", "raw_document": raw}
    
    with patch("src.graph.ap.nodes.extract_invoice_from_raw_document", return_value=mock_extracted_invoice) as mock_llm:
        res = extract_invoice_node(state)
        
        assert res["status"] == "PROCESSING"
        assert res["redaction_result"]["pii_detected"] is False
        assert res["sanitized_input"] is None
        mock_llm.assert_called_once_with(raw)

@pytest.mark.asyncio
async def test_case_b_email_pii():
    """Test B — Email PII: Email is redacted before LLM call"""
    raw = "Invoice Number: INV-1001\nCustomer Email: customer@example.com\nTotal: $1,000"
    state = {"workflow_id": "wf-privacy-2", "raw_document": raw}
    
    with patch("src.graph.ap.nodes.extract_invoice_from_raw_document", return_value=mock_extracted_invoice) as mock_llm:
        res = extract_invoice_node(state)
        
        assert res["status"] == "PROCESSING"
        assert res["redaction_result"]["pii_detected"] is True
        assert "customer@example.com" not in res["sanitized_input"]
        assert "[REDACTED_EMAIL]" in res["sanitized_input"]
        
        # Verify LLM receives sanitized content
        mock_llm.assert_called_once_with(res["sanitized_input"])

@pytest.mark.asyncio
async def test_case_c_phone_pii():
    """Test C — Phone PII: Phone redacted before LLM call"""
    raw = "Invoice Number: INV-1001\nPhone: 1-800-555-1234\nTotal: $1,000"
    state = {"workflow_id": "wf-privacy-3", "raw_document": raw}
    
    with patch("src.graph.ap.nodes.extract_invoice_from_raw_document", return_value=mock_extracted_invoice) as mock_llm:
        res = extract_invoice_node(state)
        
        assert res["status"] == "PROCESSING"
        assert res["redaction_result"]["pii_detected"] is True
        assert "1-800-555-1234" not in res["sanitized_input"]
        assert "[REDACTED_PHONE]" in res["sanitized_input"]

@pytest.mark.asyncio
async def test_case_d_multiple_pii_types():
    """Test D — Multiple PII types (email, phone, SSN, credit card)"""
    raw = (
        "Invoice INV-1001\n"
        "Email: test@example.com\n"
        "Phone: 555-019-2834\n"
        "SSN: 123-45-6789\n"
        "Card: 4111-1111-1111-1111\n"
        "Total: $1,000"
    )
    state = {"workflow_id": "wf-privacy-4", "raw_document": raw}
    
    with patch("src.graph.ap.nodes.extract_invoice_from_raw_document", return_value=mock_extracted_invoice) as mock_llm:
        res = extract_invoice_node(state)
        
        assert res["redaction_result"]["pii_detected"] is True
        sanitized = res["sanitized_input"]
        
        assert "test@example.com" not in sanitized
        assert "555-019-2834" not in sanitized
        assert "123-45-6789" not in sanitized
        assert "4111-1111-1111-1111" not in sanitized
        
        assert "[REDACTED_EMAIL]" in sanitized
        assert "[REDACTED_PHONE]" in sanitized
        assert "[REDACTED_SSN]" in sanitized
        assert "[REDACTED_CREDIT_CARD]" in sanitized

@pytest.mark.asyncio
async def test_case_e_verify_actual_llm_payload():
    """Test E — Verify the actual LLM payload"""
    raw = "Invoice INV-1001\nSecret Email: secret@domain.com"
    state = {"workflow_id": "wf-privacy-5", "raw_document": raw}
    
    with patch("src.graph.ap.nodes.extract_invoice_from_raw_document", return_value=mock_extracted_invoice) as mock_llm:
        extract_invoice_node(state)
        
        # Verify the actual argument passed to the LLM extractor
        args, kwargs = mock_llm.call_args
        prompt_passed = args[0]
        
        assert "secret@domain.com" not in prompt_passed
        assert "[REDACTED_EMAIL]" in prompt_passed

@pytest.mark.asyncio
async def test_case_f_sanitization_failure():
    """Test F — Sanitization failure -> LLM NOT called, status = ERROR"""
    state = {"workflow_id": "wf-privacy-6", "raw_document": "Valid Doc"}
    
    with patch("src.graph.ap.nodes.privacy_middleware.process_prompt", side_effect=Exception("Simulated failure")):
        with patch("src.graph.ap.nodes.extract_invoice_from_raw_document") as mock_llm:
            res = extract_invoice_node(state)
            
            assert res["status"] == "ERROR"
            assert "Privacy Sanitization Failure: Simulated failure" in res["validation_errors"][0]
            # Verify LLM was NOT called with raw input
            mock_llm.assert_not_called()
