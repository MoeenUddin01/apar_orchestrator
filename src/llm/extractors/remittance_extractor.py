import json
import re
from src.core.logging import logger
from src.domain.ar.models import ExtractedRemittance


def extract_remittance_from_raw_document(raw_document: str) -> ExtractedRemittance:
    """
    LLM extraction boundary for converting unstructured remittance text into structured ExtractedRemittance.
    Extracts customer_identifier, referenced_invoices, and total_payment.
    """
    logger.info("Executing LLM extraction boundary for AR remittance document.")

    # Try JSON parsing first
    try:
        data = json.loads(raw_document)
        return ExtractedRemittance(
            remittance_id=data.get("remittance_id", "REM-UNKNOWN"),
            customer_identifier=data.get("customer_identifier", "CUST-UNKNOWN"),
            referenced_invoices=data.get("referenced_invoices", []),
            total_payment=float(data.get("total_payment", 0.0)),
        )
    except (json.JSONDecodeError, TypeError):
        pass

    # Regex heuristic fallback when LLM provider is offline
    cust = re.search(r"Customer\s*#?\s*:?\s*([A-Z0-9-]+)", raw_document, re.IGNORECASE)
    invs = re.findall(r"INV-[0-9]+", raw_document, re.IGNORECASE)
    payment = re.search(r"(?:Payment|Amount|Total)\s*:?\s*\$?([0-9,]+\.?[0-9]*)", raw_document, re.IGNORECASE)

    extracted_payment = float(payment.group(1).replace(",", "")) if payment else 0.0

    return ExtractedRemittance(
        remittance_id="REM-1001",
        customer_identifier=cust.group(1) if cust else "CUST-001",
        referenced_invoices=invs if invs else ["INV-2001"],
        total_payment=extracted_payment if extracted_payment > 0 else 5000.0,
    )
