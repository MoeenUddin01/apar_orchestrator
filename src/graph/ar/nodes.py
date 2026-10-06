from typing import Any, Dict
from src.core.logging import logger
from src.database.repositories.ar_repository import ar_repository
from src.domain.ar.models import CustomerInvoice, ExtractedRemittance
from src.finance.matching import reconcile_ar_payment
from src.graph.state import FinanceState
from src.llm.extractors.remittance_extractor import extract_remittance_from_raw_document
from src.finance.routing import evaluate_hitl_rules
from src.llm.generators.communications import generate_overdue_reminder_llm


from src.llm.middleware import privacy_middleware
from src.graph.shared.callbacks.audit_logger import default_audit_callback


def extract_remittance_node(state: FinanceState) -> Dict[str, Any]:
    """Node 1: Extract structured remittance info from raw document using LLM boundary with PII sanitization."""
    workflow_id = state.get("workflow_id", "UNKNOWN_WF")
    logger.info(f"AR Graph [extract_remittance]: Processing workflow {workflow_id}")
    raw_doc = state.get("raw_document") or ""

    # 1. PII Sanitization
    try:
        clean_doc, redaction_res = privacy_middleware.process_prompt(raw_doc)
    except Exception as e:
        logger.error(f"Privacy middleware failed in AR extraction: {e}")
        default_audit_callback.on_error(workflow_id, "extract_remittance", str(e), "SECURITY_ERROR")
        return {
            "status": "ERROR",
            "validation_errors": [f"Privacy Sanitization Failure: {e}"]
        }

    # 2. Audit Privacy Processing
    if redaction_res.pii_detected:
        default_audit_callback.on_privacy_redaction(
            workflow_id=workflow_id,
            workflow_type="AR",
            redaction_count=redaction_res.total_redactions,
            entities_found=redaction_res.entities_found,
        )

    # 3. External LLM / Extraction
    extracted = extract_remittance_from_raw_document(clean_doc)

    return {
        "status": "PROCESSING",
        "extracted_data": extracted.model_dump(),
        "sanitized_input": clean_doc if redaction_res.pii_detected else None,
        "redaction_result": redaction_res.model_dump()
    }



async def lookup_invoices_node(state: FinanceState) -> Dict[str, Any]:
    """Node 2: Retrieve customer unpaid invoices from PostgreSQL."""
    logger.info("AR Graph [lookup_invoices]: Fetching customer unpaid invoices.")
    data = state.get("extracted_data") or {}
    cust_id = data.get("customer_identifier", "")

    invoices = await ar_repository.get_customer_invoices(cust_id)

    facts = dict(state.get("financial_facts") or {})
    facts["invoices"] = [inv.model_dump() for inv in invoices]

    return {
        "financial_facts": facts,
    }

def reconcile_payment_node(state: FinanceState) -> Dict[str, Any]:
    """Node 3: Reconcile payment against invoices using pure Python math."""
    logger.info("AR Graph [reconcile_payment]: Performing deterministic payment application.")
    data = state.get("extracted_data") or {}
    facts = state.get("financial_facts") or {}

    remittance = ExtractedRemittance(**data)
    invoices = [CustomerInvoice(**inv) for inv in facts.get("invoices", [])]

    result = reconcile_ar_payment(remittance, invoices)

    updated_facts = dict(facts)
    updated_facts["reconciliation_result"] = result.model_dump()

    # For AR, underpayment is automatically managed via remaining_balance/aging buckets.
    # It is not a tolerance exception requiring manual human investigation unless it's missing docs or high value.
    hitl_decision = evaluate_hitl_rules(
        amount=remittance.total_payment,
        tolerance_exceeded=False,
        missing_docs=(len(invoices) == 0)
    )

    if hitl_decision.requires_hitl:
        routing = "HITL"
        status = "REQUIRES_APPROVAL"
    else:
        # Determine routing
        if result.is_fully_paid:
            routing = "CLOSED"
        elif result.days_overdue > 0 and result.remaining_balance > 0:
            routing = "OVERDUE"
        else:
            routing = "PARTIAL"
            
        if routing == "OVERDUE":
            status = "REQUIRES_APPROVAL"
        else:
            status = "COMPLETED"

    return {
        "financial_facts": updated_facts,
        "routing_decision": routing,
        "hitl_decision": hitl_decision.model_dump(),
        "status": status,
    }


def calculate_aging_node(state: FinanceState) -> Dict[str, Any]:
    """Node 4: Audit and confirm aging calculations in state."""
    logger.info("AR Graph [calculate_aging]: Finalizing aging metrics.")
    facts = state.get("financial_facts") or {}
    rec_result = facts.get("reconciliation_result") or {}

    logger.info(f"AR Aging Result: bucket={rec_result.get('aging_bucket')}, days_overdue={rec_result.get('days_overdue')}")

    return {
        "financial_facts": facts,
    }

def ar_human_review_node(state: FinanceState) -> Dict[str, Any]:
    """Node 5: Applies the human API input to finalize the routing decision."""
    logger.info(f"AR Graph [human_review]: Applying human decision from API.")
    hitl_input = state.get("hitl_input") or {}
    action = hitl_input.get("action", "REJECT")
    
    new_routing = "APPROVED" if action == "APPROVE" else "CANCELLED"
    return {
        "routing_decision": new_routing,
        "status": "COMPLETED",
    }


def route_ar_decision(state: FinanceState) -> str:
    """Conditional edge router: returns 'closed', 'partial', 'overdue', or 'hitl'."""
    decision = state.get("routing_decision")
    if decision == "HITL":
        return "hitl"
    if decision == "CLOSED":
        return "closed"
    elif decision == "OVERDUE":
        return "overdue"
    return "partial"

def generate_overdue_reminder_node(state: FinanceState) -> Dict[str, Any]:
    """Node 6: Generate communication for overdue accounts."""
    logger.info("AR Graph [generate_overdue]: Drafting overdue reminder.")
    data = state.get("extracted_data") or {}
    facts = state.get("financial_facts") or {}
    rec_result = facts.get("reconciliation_result") or {}
    
    inv_list = data.get("referenced_invoices", [])
    invoice_ref = inv_list[0] if inv_list else "your recent invoices"
    
    context = {
        "invoice_id": invoice_ref,
        "customer_name": data.get("customer_identifier", "Valued Customer"),
        "days_overdue": rec_result.get("days_overdue", 0),
        "remaining_balance": rec_result.get("remaining_balance", 0.0),
    }
    
    draft = generate_overdue_reminder_llm(context)
    
    drafts = list(state.get("drafted_communications") or [])
    drafts.append(draft.model_dump())
    
    return {
        "drafted_communications": drafts
    }
