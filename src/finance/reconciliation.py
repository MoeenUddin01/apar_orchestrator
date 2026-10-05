from typing import Any, Dict, List, Optional
from src.domain.compliance_state import (
    ComplianceRationale,
    ReconciliationItem,
    ReconciliationResult,
    ReconciliationStatus,
)


def reconcile_invoice_totals(
    line_items: List[Dict[str, Any]],
    declared_subtotal: float,
    declared_tax: float,
    declared_total: float,
    tolerance: float = 0.01,
) -> ReconciliationResult:
    """
    Deterministic reconciliation function verifying line-item calculations, subtotals, tax, and declared totals.
    Guarantees mathematical accuracy before graph state finalization.
    """
    discrepancies: List[ReconciliationItem] = []
    line_items_sum = 0.0

    # 1. Verify line item calculations
    for idx, item in enumerate(line_items or []):
        qty = float(item.get("quantity") or 0.0)
        unit_price = float(item.get("unit_price") or item.get("rate") or 0.0)
        item_declared_total = float(item.get("total_price") or item.get("total") or item.get("amount") or 0.0)
        expected_item_total = round(qty * unit_price, 2) if (qty > 0 and unit_price > 0) else item_declared_total

        diff = round(abs(expected_item_total - item_declared_total), 2)
        item_matched = diff <= tolerance

        line_items_sum += item_declared_total if item_declared_total > 0 else expected_item_total

        if not item_matched:
            discrepancies.append(
                ReconciliationItem(
                    item_id=str(item.get("item_id") or f"line_item_{idx+1}"),
                    description=item.get("description") or f"Line Item #{idx+1}",
                    expected_amount=expected_item_total,
                    actual_amount=item_declared_total,
                    difference=diff,
                    matched=False,
                )
            )

    line_items_sum = round(line_items_sum, 2)
    subtotal_check = (
        declared_subtotal
        if declared_subtotal > 0
        else (line_items_sum if (line_items and line_items_sum > 0) else round(declared_total - declared_tax, 2))
    )


    # 2. Verify subtotal vs line items sum
    if line_items and abs(line_items_sum - subtotal_check) > tolerance:
        discrepancies.append(
            ReconciliationItem(
                item_id="line_items_subtotal_mismatch",
                description="Sum of line items does not match declared subtotal",
                expected_amount=line_items_sum,
                actual_amount=subtotal_check,
                difference=round(abs(line_items_sum - subtotal_check), 2),
                matched=False,
            )
        )

    # 3. Verify declared_total vs subtotal + tax
    expected_grand_total = round(subtotal_check + declared_tax, 2)
    grand_total_diff = round(abs(expected_grand_total - declared_total), 2)

    if grand_total_diff > tolerance:
        discrepancies.append(
            ReconciliationItem(
                item_id="grand_total_mismatch",
                description="Declared total does not equal subtotal + tax",
                expected_amount=expected_grand_total,
                actual_amount=declared_total,
                difference=grand_total_diff,
                matched=False,
            )
        )

    is_balanced = len(discrepancies) == 0
    status = ReconciliationStatus.MATCHED if is_balanced else ReconciliationStatus.DISCREPANCY

    rationale_text = (
        f"Line item math and totals reconciled successfully. Grand total: ${declared_total:,.2f}."
        if is_balanced
        else f"Reconciliation failed with {len(discrepancies)} discrepancy(ies). Expected ${expected_grand_total:,.2f} vs declared ${declared_total:,.2f}."
    )

    rationale = ComplianceRationale(
        component="ReconciliationEngine",
        decision="RECONCILED_MATCH" if is_balanced else "RECONCILED_DISCREPANCY",
        rationale=rationale_text,
        factors=[
            f"Line Items Sum: ${line_items_sum:,.2f}",
            f"Declared Subtotal: ${declared_subtotal:,.2f}",
            f"Declared Tax: ${declared_tax:,.2f}",
            f"Declared Total: ${declared_total:,.2f}",
            f"Total Discrepancies Found: {len(discrepancies)}",
        ],
    )

    return ReconciliationResult(
        status=status,
        total_expected=expected_grand_total,
        total_actual=declared_total,
        difference=grand_total_diff,
        is_balanced=is_balanced,
        discrepancies=discrepancies,
        rationale=rationale,
    )


def reconcile_payment_request(
    requested_amount: float,
    invoice_total: float,
    ledger_balance: float,
    discount_amount: float = 0.0,
    tolerance: float = 0.01,
) -> ReconciliationResult:
    """
    Verifies that requested payment amounts match expected invoice net amounts and ledger balances before approval.
    """
    discrepancies: List[ReconciliationItem] = []
    expected_payable = round(invoice_total - discount_amount, 2)
    amount_diff = round(abs(expected_payable - requested_amount), 2)

    # 1. Invoice vs Requested payment match
    if amount_diff > tolerance:
        discrepancies.append(
            ReconciliationItem(
                item_id="payment_amount_mismatch",
                description="Requested payment amount differs from net invoice payable",
                expected_amount=expected_payable,
                actual_amount=requested_amount,
                difference=amount_diff,
                matched=False,
            )
        )

    # 2. Ledger balance check
    if ledger_balance < requested_amount:
        discrepancies.append(
            ReconciliationItem(
                item_id="insufficient_ledger_balance",
                description="Ledger balance is insufficient for requested payment",
                expected_amount=requested_amount,
                actual_amount=ledger_balance,
                difference=round(requested_amount - ledger_balance, 2),
                matched=False,
            )
        )

    is_balanced = len(discrepancies) == 0
    status = ReconciliationStatus.MATCHED if is_balanced else ReconciliationStatus.DISCREPANCY

    rationale_text = (
        f"Payment request of ${requested_amount:,.2f} verified against invoice total (${invoice_total:,.2f}) and ledger balance (${ledger_balance:,.2f})."
        if is_balanced
        else f"Payment request reconciliation failed: {', '.join(d.description for d in discrepancies)}."
    )

    rationale = ComplianceRationale(
        component="PaymentReconciler",
        decision="PAYMENT_RECONCILED" if is_balanced else "PAYMENT_RECONCILIATION_FLAGGED",
        rationale=rationale_text,
        factors=[
            f"Requested Amount: ${requested_amount:,.2f}",
            f"Invoice Total: ${invoice_total:,.2f}",
            f"Allowed Discount: ${discount_amount:,.2f}",
            f"Ledger Balance: ${ledger_balance:,.2f}",
        ],
    )

    return ReconciliationResult(
        status=status,
        total_expected=expected_payable,
        total_actual=requested_amount,
        difference=amount_diff,
        is_balanced=is_balanced,
        discrepancies=discrepancies,
        rationale=rationale,
    )


from src.graph.shared.callbacks.audit_logger import default_audit_callback

def reconciliation_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node enforcing deterministic reconciliation on graph state.
    """
    invoice_data = state.get("extracted_data") or state.get("extracted_invoice") or state.get("invoice") or {}
    
    # Handle both object and dict forms (extracted_data might contain dicts or objects depending on state serialization)
    line_items = invoice_data.get("line_items", [])
    
    # Ensure line_items is a list of dicts for reconcile_invoice_totals
    processed_line_items = []
    for item in line_items:
        if hasattr(item, "model_dump"):
            processed_line_items.append(item.model_dump())
        elif isinstance(item, dict):
            processed_line_items.append(item)
            
    declared_subtotal = float(invoice_data.get("subtotal") or 0.0)
    declared_tax = float(invoice_data.get("tax_amount") or invoice_data.get("tax") or 0.0)
    declared_total = float(invoice_data.get("invoice_total") or invoice_data.get("total_amount") or invoice_data.get("amount") or 0.0)

    result = reconcile_invoice_totals(
        line_items=processed_line_items,
        declared_subtotal=declared_subtotal,
        declared_tax=declared_tax,
        declared_total=declared_total,
    )

    workflow_id = state.get("workflow_id", "UNKNOWN_WF")
    default_audit_callback.on_compliance_assessment(
        workflow_id=workflow_id,
        status="PASS" if result.is_balanced else "FAIL",
        findings=[d.description for d in result.discrepancies]
    )

    updates = {
        "reconciliation_result": result.model_dump(),
        "is_reconciled": result.is_balanced,
        "compliance_rationale": result.rationale.model_dump() if result.rationale else None,
    }

    if not result.is_balanced:
        # Route to HITL/Exception flow according to existing project conventions
        updates["routing_decision"] = "HITL"
        updates["status"] = "REQUIRES_APPROVAL"
        
        hitl = state.get("hitl_decision") or {}
        hitl["requires_hitl"] = True
        hitl["hitl_reason"] = "Financial Compliance Discrepancy"
        existing_reasons = hitl.get("hitl_reasons", [])
        hitl["hitl_reasons"] = existing_reasons + [d.description for d in result.discrepancies]
        updates["hitl_decision"] = hitl

    return updates
