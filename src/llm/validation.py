from typing import Any, Dict, List, Tuple
from src.domain.risk_state import RiskCategory, RiskFlag, RiskLevel


def validate_llm_invoice_extraction(
    extracted_data: Dict[str, Any],
    tolerance: float = 0.05,
) -> Tuple[bool, List[RiskFlag]]:
    """
    Deterministic validation of LLM-extracted financial data.
    Ensures mathematical accuracy and flags discrepancies without allowing LLM output to override deterministic math.
    """
    flags: List[RiskFlag] = []
    is_valid = True

    if not extracted_data or not isinstance(extracted_data, dict):
        return False, [
            RiskFlag(
                code="LLM_EMPTY_EXTRACTION",
                category=RiskCategory.AI_VALIDATION,
                message="LLM extraction returned empty or non-dictionary payload.",
                severity=RiskLevel.HIGH,
                source="llm_validator",
            )
        ]

    # Required field presence check
    has_vendor = any(extracted_data.get(k) for k in ["vendor_id", "vendor_name", "customer_identifier"])
    has_inv_num = bool(extracted_data.get("invoice_number") or extracted_data.get("referenced_invoices") or extracted_data.get("remittance_id"))
    has_total = any(extracted_data.get(k) is not None for k in ["invoice_total", "total_amount", "amount", "total_payment"])

    if not (has_vendor and has_inv_num and has_total):
        missing = []
        if not has_vendor:
            missing.append("vendor_id/customer_identifier")
        if not has_inv_num:
            missing.append("invoice_number/referenced_invoices")
        if not has_total:
            missing.append("invoice_total/total_payment")


        is_valid = False
        flags.append(
            RiskFlag(
                code="LLM_MISSING_REQUIRED_FIELDS",
                category=RiskCategory.AI_VALIDATION,
                message=f"LLM extraction is missing required invoice fields: {', '.join(missing)}.",
                severity=RiskLevel.HIGH,
                source="llm_validator",
                details={"missing_fields": missing},
            )
        )

    # Parse numeric amounts
    try:
        invoice_total = float(extracted_data.get("invoice_total") or extracted_data.get("total_amount") or extracted_data.get("amount") or 0.0)
        subtotal = float(extracted_data.get("subtotal") or 0.0)
        tax_amount = float(extracted_data.get("tax_amount") or extracted_data.get("tax") or 0.0)
    except (ValueError, TypeError) as exc:
        return False, [
            RiskFlag(
                code="LLM_INVALID_NUMERIC_TYPES",
                category=RiskCategory.AI_VALIDATION,
                message=f"LLM extraction contained non-numeric financial values: {str(exc)}.",
                severity=RiskLevel.HIGH,
                source="llm_validator",
            )
        ]

    # Negative value checks
    if invoice_total < 0 or subtotal < 0 or tax_amount < 0:
        is_valid = False
        flags.append(
            RiskFlag(
                code="LLM_NEGATIVE_FINANCIAL_VALUES",
                category=RiskCategory.AI_VALIDATION,
                message="LLM extraction contains invalid negative financial totals.",
                severity=RiskLevel.HIGH,
                source="llm_validator",
                details={"invoice_total": invoice_total, "subtotal": subtotal, "tax_amount": tax_amount},
            )
        )

    # 1. Line Items Unit Price * Quantity and Sum Validation
    line_items = extracted_data.get("line_items") or []
    if line_items and isinstance(line_items, list):
        items_sum = 0.0
        currency_set = set()

        for idx, item in enumerate(line_items):
            if not isinstance(item, dict):
                continue

            qty = float(item.get("quantity") or 0.0)
            unit_price = float(item.get("unit_price") or item.get("rate") or 0.0)
            item_total = float(item.get("total") or item.get("amount") or 0.0)

            # Currency tracking
            item_currency = str(item.get("currency") or extracted_data.get("currency") or "USD").upper().strip()
            currency_set.add(item_currency)

            # Item math check: qty * unit_price == item_total
            if qty > 0 and unit_price > 0 and item_total > 0:
                expected_item_total = qty * unit_price
                if abs(expected_item_total - item_total) > tolerance:
                    is_valid = False
                    flags.append(
                        RiskFlag(
                            code="LLM_LINE_ITEM_MATH_MISMATCH",
                            category=RiskCategory.AI_VALIDATION,
                            message=f"Line item #{idx+1} calculation mismatch: {qty:.2f} x ${unit_price:.2f} = ${expected_item_total:.2f}, but extracted total was ${item_total:.2f}.",
                            severity=RiskLevel.HIGH,
                            source="llm_validator",
                            details={"item_index": idx, "qty": qty, "unit_price": unit_price, "extracted_total": item_total},
                        )
                    )

            items_sum += item_total if item_total > 0 else (qty * unit_price)

        # Currency consistency check across line items
        main_currency = str(extracted_data.get("currency") or "USD").upper().strip()
        if any(c != main_currency for c in currency_set):
            is_valid = False
            flags.append(
                RiskFlag(
                    code="LLM_CURRENCY_INCONSISTENCY",
                    category=RiskCategory.AI_VALIDATION,
                    message=f"Inconsistent currencies detected across line items: {list(currency_set)} vs invoice currency '{main_currency}'.",
                    severity=RiskLevel.MEDIUM,
                    source="llm_validator",
                    details={"line_item_currencies": list(currency_set), "invoice_currency": main_currency},
                )
            )

        # Line items sum vs declared subtotal/total check
        target_check = subtotal if subtotal > 0 else invoice_total
        if items_sum > 0 and abs(items_sum - target_check) > tolerance:
            is_valid = False
            flags.append(
                RiskFlag(
                    code="LLM_LINE_ITEM_SUM_MISMATCH",
                    category=RiskCategory.AI_VALIDATION,
                    message=f"Sum of extracted line items (${items_sum:,.2f}) does not match declared financial total (${target_check:,.2f}). Possible LLM calculation hallucination.",
                    severity=RiskLevel.HIGH,
                    source="llm_validator",
                    details={
                        "line_items_sum": round(items_sum, 2),
                        "declared_total": round(target_check, 2),
                        "difference": round(abs(items_sum - target_check), 2),
                    },
                )
            )

    # 2. Check subtotal + tax == invoice_total
    if subtotal > 0 and tax_amount >= 0 and invoice_total > 0:
        expected_total = subtotal + tax_amount
        if abs(expected_total - invoice_total) > tolerance:
            is_valid = False
            flags.append(
                RiskFlag(
                    code="LLM_MATH_TOTAL_MISMATCH",
                    category=RiskCategory.AI_VALIDATION,
                    message=f"Extracted subtotal (${subtotal:,.2f}) + tax (${tax_amount:,.2f}) = ${expected_total:,.2f}, which does not match declared total (${invoice_total:,.2f}).",
                    severity=RiskLevel.HIGH,
                    source="llm_validator",
                    details={
                        "subtotal": subtotal,
                        "tax_amount": tax_amount,
                        "expected_total": expected_total,
                        "declared_total": invoice_total,
                    },
                )
            )

    return is_valid, flags


def validate_against_deterministic_context(
    extracted_data: Dict[str, Any],
    deterministic_context: Dict[str, Any],
) -> Tuple[bool, List[RiskFlag]]:
    """Cross-references extracted LLM data against authoritative context (PO vendor, PO currency, PO total)."""
    flags: List[RiskFlag] = []
    is_valid = True

    if not deterministic_context:
        return True, []

    # Vendor verification
    extracted_vendor = str(extracted_data.get("vendor_name") or extracted_data.get("vendor_id") or "").lower().strip()
    expected_vendor = str(deterministic_context.get("vendor_name") or deterministic_context.get("vendor_id") or "").lower().strip()

    if extracted_vendor and expected_vendor and extracted_vendor not in expected_vendor and expected_vendor not in extracted_vendor:
        is_valid = False
        flags.append(
            RiskFlag(
                code="LLM_VENDOR_CONTEXT_MISMATCH",
                category=RiskCategory.AI_VALIDATION,
                message=f"Extracted vendor '{extracted_vendor}' does not match expected context vendor '{expected_vendor}'.",
                severity=RiskLevel.MEDIUM,
                source="llm_validator",
                details={"extracted_vendor": extracted_vendor, "expected_vendor": expected_vendor},
            )
        )

    # Currency verification
    extracted_currency = str(extracted_data.get("currency") or "USD").upper().strip()
    expected_currency = str(deterministic_context.get("currency") or "USD").upper().strip()

    if extracted_currency != expected_currency:
        is_valid = False
        flags.append(
            RiskFlag(
                code="LLM_CURRENCY_MISMATCH",
                category=RiskCategory.AI_VALIDATION,
                message=f"Extracted currency '{extracted_currency}' differs from expected context currency '{expected_currency}'.",
                severity=RiskLevel.MEDIUM,
                source="llm_validator",
                details={"extracted_currency": extracted_currency, "expected_currency": expected_currency},
            )
        )

    return is_valid, flags
