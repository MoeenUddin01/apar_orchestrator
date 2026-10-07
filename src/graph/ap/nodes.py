from typing import Any, Dict
from src.core.logging import logger
from src.database.repositories.ap_repository import ap_repository
from src.domain.ap.models import ExtractedInvoice
from src.finance.matching import perform_3_way_match
from src.graph.state import FinanceState
from src.llm.extractors.invoice_extractor import extract_invoice_from_raw_document
from src.finance.routing import evaluate_hitl_rules
from src.finance.confidence import evaluate_extraction_confidence
from src.llm.generators.communications import generate_discrepancy_notice_llm


from src.llm.middleware import privacy_middleware
from src.graph.shared.callbacks.audit_logger import default_audit_callback
from src.domain.audit_schema import AuditEvent, ActorType, EventType, GRCDomain

def ingest_document_node(state: FinanceState) -> Dict[str, Any]:
    """Node 0: Ingests document from DocumentStorageInterface using document_id if provided."""
    logger.info("AP Graph [ingest_document]: Ingesting document from storage boundary.")
    doc_id = state.get("document_id")
    raw_doc = state.get("raw_document")

    if doc_id and not raw_doc:
        from src.domain.ap.storage import default_storage_provider
        content_bytes = default_storage_provider.get_document_stream(doc_id)
        metadata = default_storage_provider.get_document_metadata(doc_id)

        if content_bytes:
            raw_doc = content_bytes.decode("utf-8", errors="ignore")
            return {
                "raw_document": raw_doc,
                "status": "PROCESSING",
                "document_metadata": metadata.model_dump() if metadata else None
            }
        else:
            return {
                "status": "ERROR",
                "validation_errors": [f"Document storage retrieval failed for ID: {doc_id}"]
            }

    return {"status": "PROCESSING"}

def extract_invoice_node(state: FinanceState) -> Dict[str, Any]:
    """Node 1: Extract structured invoice data from raw document using LLM boundary."""
    workflow_id = state.get("workflow_id", "UNKNOWN_WF")
    logger.info(f"AP Graph [extract_invoice]: Processing workflow {workflow_id}")
    raw_doc = state.get("raw_document") or ""
    
    # 1. PII Sanitization
    try:
        clean_doc, redaction_res = privacy_middleware.process_prompt(raw_doc)
    except Exception as e:
        logger.error(f"Privacy middleware failed: {e}")
        return {
            "status": "ERROR",
            "validation_errors": [f"Privacy Sanitization Failure: {e}"]
        }
        
    # 3. External LLM / Extraction using Adapter
    from src.llm.extractors.invoice_extractor import LLMInvoiceExtractorAdapter
    import io
    adapter = LLMInvoiceExtractorAdapter()
    stream = io.BytesIO(clean_doc.encode('utf-8'))
    extraction_result = adapter.extract(stream)
    extracted = adapter.map_to_canonical(extraction_result)

    # 2. Audit Privacy Processing
    if redaction_res.pii_detected:
        default_audit_callback.on_privacy_redaction(
            workflow_id=workflow_id,
            workflow_type="AP",
            transaction_id=extracted.invoice_number or extracted.po_number,
            redaction_count=redaction_res.total_redactions,
            entities_found=redaction_res.entities_found
        )
    
    return {
        "status": "PROCESSING",
        "extracted_data": extracted.model_dump(),
        "extraction_metadata": extraction_result.model_dump(),
        "sanitized_input": clean_doc if redaction_res.pii_detected else None,
        "redaction_result": redaction_res.model_dump()
    }


def evaluate_confidence_node(state: FinanceState) -> Dict[str, Any]:
    """Node 1.5: Evaluate extraction confidence to determine if HITL is needed before validation."""
    logger.info(f"AP Graph [evaluate_confidence]: Evaluating extraction confidence.")
    metadata = state.get("extraction_metadata") or {}
    data = state.get("extracted_data") or {}
    
    evaluation = evaluate_extraction_confidence(metadata, data)
    
    if evaluation.get("passes_confidence"):
        return {"routing_decision": "APPROVE"}
    else:
        # Save reasons for the human reviewer
        hitl_decision = state.get("hitl_decision") or {}
        hitl_decision["hitl_reasons"] = evaluation.get("reasons", [])
        hitl_decision["requires_hitl"] = True
        return {
            "routing_decision": "HITL",
            "hitl_decision": hitl_decision,
            "status": "REQUIRES_APPROVAL"
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
    """Node 3: Retrieve PO, Goods Receipt, and historical invoices from Postgres via AP repository."""
    logger.info(f"AP Graph [lookup_db]: Querying database records.")
    data = state.get("extracted_data") or {}
    po_number = data.get("po_number", "")
    vendor_id = data.get("vendor_id", "") or state.get("vendor_id", "")

    po = await ap_repository.get_purchase_order(po_number)
    goods_receipt = await ap_repository.get_goods_receipt(po_number)

    historical_invoices = []
    if vendor_id and vendor_id != "VEND-UNKNOWN":
        historical_invoices = await ap_repository.get_historical_invoices_by_vendor(vendor_id)

    historical_amounts = [
        float(inv.get("amount") or inv.get("invoice_total") or 0.0)
        for inv in historical_invoices
        if (inv.get("amount") or inv.get("invoice_total")) is not None
    ]

    facts = dict(state.get("financial_facts") or {})
    facts["po"] = po.model_dump() if po else None
    facts["goods_receipt"] = goods_receipt.model_dump() if goods_receipt else None

    return {
        "financial_facts": facts,
        "historical_invoices": historical_invoices,
        "historical_amounts": historical_amounts,
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
    
    if action == "CORRECT_DATA":
        corrected_data = hitl_input.get("corrected_data", {})
        actor_id = hitl_input.get("corrected_by", "UNKNOWN_USER")
        
        # Merge corrected_data into extracted_data
        current_data = state.get("extracted_data") or {}
        merged_data = {**current_data, **corrected_data}
        
        # Emit Audit Event
        event = AuditEvent(
            workflow_id=state.get("workflow_id", "UNKNOWN_WF"),
            workflow_type="AP",
            actor_type=ActorType.USER,
            actor_id=actor_id,
            actor_role="OPERATOR",
            event_type=EventType.WORKFLOW_COMPLETED, # Use generic or map to HUMAN_CORRECTION_APPLIED
            grc_domain=GRCDomain.WORKFLOW,
            action="CORRECT_DATA",
            status="SUCCESS",
            summary=f"Human operator corrected {len(corrected_data)} fields.",
            metadata={"corrected_fields": list(corrected_data.keys()), "reason": hitl_input.get("correction_reason")}
        )
        # Hack to change event_type since HUMAN_CORRECTION_APPLIED might not be in EventType enum
        event.event_type = "HUMAN_CORRECTION_APPLIED" # type: ignore
        default_audit_callback.repository.log_event(event)
        
        return {
            "extracted_data": merged_data,
            "status": "PROCESSING",
            "routing_decision": "CORRECTED", # We will route back to validate_invoice
            "hitl_decision": {"requires_hitl": False} # Clear HITL status
        }
    
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

def generate_discrepancy_notice_node(state: FinanceState) -> Dict[str, Any]:
    """Node 6: Generate communication for discrepancies before entering HITL."""
    logger.info("AP Graph [generate_discrepancy]: Drafting discrepancy notice.")
    data = state.get("extracted_data") or {}
    facts = state.get("financial_facts") or {}
    hitl_decision = state.get("hitl_decision") or {}
    
    context = {
        "invoice_id": data.get("invoice_number", "UNKNOWN"),
        "vendor_id": data.get("vendor_id", "UNKNOWN"),
        "po_number": data.get("po_number", "UNKNOWN"),
        "reason": hitl_decision.get("hitl_reason", "Exception occurred"),
        "reasons": hitl_decision.get("hitl_reasons", []),
    }
    
    # Get variance amount from match result if available
    match_result = facts.get("match_result") or {}
    if match_result and not match_result.get("is_match"):
        context["variance_amount"] = match_result.get("variance_amount", 0.0)
        context["quantity_mismatch"] = match_result.get("details", {}).get("quantity_mismatch", False)
            
    draft = generate_discrepancy_notice_llm(context)
    
    drafts = list(state.get("drafted_communications") or [])
    drafts.append(draft.model_dump())
    
    return {
        "drafted_communications": drafts
    }

async def persist_invoice_node(state: FinanceState) -> Dict[str, Any]:
    """Node 7: Persist successfully processed invoice into AP database upon approval."""
    workflow_id = state.get("workflow_id", "UNKNOWN_WF")
    status = state.get("status")
    routing_decision = state.get("routing_decision")
    
    if status == "COMPLETED" and routing_decision == "APPROVE":
        extracted = state.get("extracted_data") or {}
        invoice_number = extracted.get("invoice_number")
        vendor_id = extracted.get("vendor_id")
        invoice_total = float(extracted.get("invoice_total") or 0.0)
        
        if invoice_number and vendor_id and invoice_total > 0:
            saved = await ap_repository.save_invoice({
                "invoice_number": invoice_number,
                "vendor_id": vendor_id,
                "invoice_total": invoice_total,
                "workflow_id": workflow_id,
                "status": "COMPLETED",
            })
            if saved:
                logger.info(f"AP Graph [persist_invoice]: Invoice {invoice_number} for vendor {vendor_id} persisted successfully.")
    
    return {}

