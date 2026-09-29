from typing import Any, Dict
from src.core.logging import logger
from src.database.repositories.ap_repository import ap_repository
from src.domain.ap.models import ExtractedInvoice
from src.finance.matching import perform_3_way_match
from src.graph.state import FinanceState
from src.llm.extractors.invoice_extractor import extract_invoice_from_raw_document
from src.finance.routing import evaluate_hitl_rules


def extract_invoice_node(state: FinanceState) -> Dict[str, Any]:
    """Node 1: Extract structured invoice data from raw document using LLM boundary."""
    logger.info(f"AP Graph [extract_invoice]: Processing workflow {state.get('workflow_id')}")
    raw_doc = state.get("raw_document") or ""
    extracted = extract_invoice_from_raw_document(raw_doc)
    
    return {
        "status": "PROCESSING",
        "extracted_data": extracted.model_dump(),
    }


def validate_invoice_node(state: FinanceState) -> Dict[str, Any]:
    """Node 2: Validate extracted data contains required financial fields using Python rules."""
    logger.info(f"AP Graph [validate_invoice]: Validating extracted fields.")
    data = state.get("extracted_data") or {}
    errors = []

    if not data.get("vendor_id") or data.get("vendor_id") == "VEND-UNKNOWN":
        errors.append("Missing required field: vendor_id")
    if not data.get("po_number") or data.get("po_number") == "PO-UNKNOWN":
        errors.append("Missing required field: po_number")
    if float(data.get("invoice_total", 0.0)) <= 0.0:
        errors.append("Invalid or non-positive invoice_total")

    return {
        "validation_errors": errors,
        "status": "ERROR" if errors else "PROCESSING",
    }


async def lookup_db_node(state: FinanceState) -> Dict[str, Any]:
    """Node 3: Retrieve PO and Goods Receipt from Postgres via AP repository."""
    logger.info(f"AP Graph [lookup_db]: Querying database records.")
    data = state.get("extracted_data") or {}
    po_number = data.get("po_number", "")

    po = await ap_repository.get_purchase_order(po_number)
    goods_receipt = await ap_repository.get_goods_receipt(po_number)

    facts = dict(state.get("financial_facts") or {})
    facts["po"] = po.model_dump() if po else None
    facts["goods_receipt"] = goods_receipt.model_dump() if goods_receipt else None

    return {
        "financial_facts": facts,
    }

def match_3_way_node(state: FinanceState) -> Dict[str, Any]:
    """Node 4: Execute deterministic 3-way match in Python."""
    logger.info(f"AP Graph [match_3_way]: Running deterministic 3-way match math.")
    data = state.get("extracted_data") or {}
    facts = state.get("financial_facts") or {}

    invoice = ExtractedInvoice(**data)
    po = facts.get("po")
    goods_receipt = facts.get("goods_receipt")

    match_result = perform_3_way_match(
        invoice=invoice,
        po=po if isinstance(po, dict) else (po.model_dump() if po else None),
        goods_receipt=goods_receipt if isinstance(goods_receipt, dict) else (goods_receipt.model_dump() if goods_receipt else None),
    )

    updated_facts = dict(facts)
    updated_facts["match_result"] = match_result.model_dump()

    hitl_decision = evaluate_hitl_rules(
        amount=invoice.invoice_total,
        tolerance_exceeded=not match_result.is_match,
        missing_docs=(po is None or goods_receipt is None)
    )

    if hitl_decision.requires_hitl:
        routing = "HITL"
        status = "REQUIRES_APPROVAL"
    else:
        routing = "APPROVE" if match_result.is_match else "EXCEPTION"
        status = "COMPLETED" if match_result.is_match else "REQUIRES_APPROVAL"

    return {
        "financial_facts": updated_facts,
        "routing_decision": routing,
        "hitl_decision": hitl_decision.model_dump(),
        "status": status,
    }

def human_review_node(state: FinanceState) -> Dict[str, Any]:
    """Node 5: Applies the human API input to finalize the routing decision."""
    logger.info(f"AP Graph [human_review]: Applying human decision from API.")
    hitl_input = state.get("hitl_input") or {}
    action = hitl_input.get("action", "REJECT")
    
    return {
        "routing_decision": "APPROVE" if action == "APPROVE" else "EXCEPTION",
        "status": "COMPLETED" if action == "APPROVE" else "ERROR",
    }

def route_ap_decision(state: FinanceState) -> str:
    """Conditional edge router: returns 'approve', 'exception', or 'hitl'."""
    decision = state.get("routing_decision")
    if decision == "HITL":
        return "hitl"
    if decision == "APPROVE":
        return "approve"
    return "exception"
