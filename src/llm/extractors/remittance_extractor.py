import json
import re
from src.core.logging import logger
from src.domain.ar.models import ExtractedRemittance
from src.core.config import settings

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

    if settings.LLM_PROVIDER == "groq" and settings.GROQ_API_KEY:
        try:
            from langchain_groq import ChatGroq

            llm = ChatGroq(
                model="qwen/qwen3.8-27b",
                temperature=0,
                api_key=settings.GROQ_API_KEY
            )
            structured_llm = llm.with_structured_output(ExtractedRemittance)

            prompt = (
                "You are a financial document parser. Extract ONLY the fields present in the document below.\n"
                "RULES:\n"
                "- total_payment: the dollar amount the customer is PAYING NOW (look for 'Amount Paid', "
                "'Payment Amount', 'Total Paid'). Do NOT use invoice totals or any other amounts.\n"
                "- customer_identifier: the customer or account ID (e.g. CUST-001)\n"
                "- referenced_invoices: list of invoice numbers mentioned (e.g. ['INV-2001'])\n"
                "- remittance_id: remittance/payment ID if present, else 'REM-UNKNOWN'\n\n"
                f"Document:\n{raw_document}"
            )
            result = structured_llm.invoke(prompt)
            logger.info(
                f"LLM extracted: customer={result.customer_identifier}, "
                f"payment={result.total_payment}, invoices={result.referenced_invoices}"
            )
            return result
        except Exception as e:
            logger.error(f"Groq extraction failed: {e}. Falling back to regex.")

    # Robust regex fallback — handles multi-word labels like "Amount Paid:"
    # Customer ID
    cust = re.search(r"Customer\s*(?:ID|#|Number)?\s*:?\s*([A-Z0-9-]+)", raw_document, re.IGNORECASE)

    # Invoice references
    invs = re.findall(r"INV-[0-9]+", raw_document, re.IGNORECASE)

    # Payment amount — try specific multi-word labels first, then generic single-word
    payment = (
        re.search(r"Amount\s+Paid\s*:?\s*\$?\s*([0-9,]+\.?[0-9]*)", raw_document, re.IGNORECASE)
        or re.search(r"Payment\s+Amount\s*:?\s*\$?\s*([0-9,]+\.?[0-9]*)", raw_document, re.IGNORECASE)
        or re.search(r"Total\s+Paid\s*:?\s*\$?\s*([0-9,]+\.?[0-9]*)", raw_document, re.IGNORECASE)
        or re.search(r"(?:Payment|Amount|Total)\s*:\s*\$?\s*([0-9,]+\.?[0-9]*)", raw_document, re.IGNORECASE)
    )

    extracted_payment = float(payment.group(1).replace(",", "")) if payment else 0.0
    extracted_customer = cust.group(1) if cust else "CUST-UNKNOWN"

    logger.info(f"Regex extracted: customer={extracted_customer}, payment={extracted_payment}, invoices={invs}")

    return ExtractedRemittance(
        remittance_id="REM-UNKNOWN",
        customer_identifier=extracted_customer,
        referenced_invoices=invs if invs else [],
        total_payment=extracted_payment,
    )
