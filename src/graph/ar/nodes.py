from typing import Any, Dict
from src.core.logging import logger
from src.database.repositories.ar_repository import ar_repository
from src.domain.ar.models import CustomerInvoice, ExtractedRemittance
from src.finance.matching import reconcile_ar_payment
from src.graph.state import FinanceState
from src.llm.extractors.remittance_extractor import extract_remittance_from_raw_document
from src.finance.routing import evaluate_hitl_rules
from src.llm.generators.communications import generate_overdue_reminder_llm


def extract_remittance_node(state: FinanceState) -> Dict[str, Any]:
    """Node 1: Extract structured remittance info from raw document using LLM boundary."""
    logger.info(f"AR Graph [extract_remittance]: Processing workflow {state.get('workflow_id')}")
    raw_doc = state.get("raw_document") or ""
    extracted = extract_remittance_from_raw_document(raw_doc)

    return {
        "status": "PROCESSING",
        "extracted_data": extracted.model_dump(),
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

    hitl_decision = evaluate_hitl_rules(
        amount=remittance.payment_amount,
        tolerance_exceeded=not result.is_fully_paid,
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
        status = "COMPLETED" if result.is_fully_paid else ("REQUIRES_APPROVAL" if routing == "OVERDUE" else "PROCESSING")

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
    
    # We map APPROVE to CLOSED and REJECT to OVERDUE for AR, or something simple
    new_routing = "CLOSED" if action == "APPROVE" else "OVERDUE"
    return {
        "routing_decision": new_routing,
        "status": "COMPLETED" if new_routing == "CLOSED" else "REQUIRES_APPROVAL",
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
    
    context = {
        "invoice_id": data.get("invoice_number", "UNKNOWN"),
        "customer_name": data.get("customer_name", "Valued Customer"),
        "days_overdue": rec_result.get("days_overdue", 0),
        "remaining_balance": rec_result.get("remaining_balance", 0.0),
    }
    
    draft = generate_overdue_reminder_llm(context)
    
    drafts = list(state.get("drafted_communications") or [])
    drafts.append(draft.model_dump())
    
    return {
        "drafted_communications": drafts
    }
