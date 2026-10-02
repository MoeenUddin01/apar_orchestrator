import statistics
from typing import Any, Dict, List, Optional, Tuple
from src.domain.risk_state import RiskCategory, RiskFlag, RiskLevel, RiskScore


def check_duplicate_invoice(
    invoice_number: str,
    vendor_id: str,
    historical_invoices: List[Dict[str, Any]],
    amount: Optional[float] = None,
) -> Optional[RiskFlag]:
    """Scans historical invoices to check for exact duplicate invoice number and vendor ID combinations."""
    if not invoice_number or not vendor_id or not historical_invoices:
        return None

    norm_number = str(invoice_number).strip().upper()
    norm_vendor = str(vendor_id).strip().upper()

    for inv in historical_invoices:
        h_vendor = str(inv.get("vendor_id") or inv.get("vendor_name") or "").strip().upper()
        h_number = str(inv.get("invoice_number") or "").strip().upper()
        h_amount = float(inv.get("amount") or inv.get("invoice_total") or 0.0)

        # Require BOTH vendor_id AND invoice_number to match
        if h_vendor == norm_vendor and h_number == norm_number:
            match_details = {
                "duplicate_invoice_number": invoice_number,
                "vendor_id": vendor_id,
                "historical_amount": h_amount,
            }
            if amount is not None and abs(amount - h_amount) < 0.01:
                match_details["exact_amount_match"] = True

            return RiskFlag(
                code="DUPLICATE_INVOICE_DETECTED",
                category=RiskCategory.DUPLICATE,
                message=f"Duplicate invoice detected: Invoice number '{invoice_number}' already processed for vendor '{vendor_id}'.",
                severity=RiskLevel.HIGH,
                source="financial_rules_engine",
                details=match_details,
            )
    return None


def check_vendor_bank_change(
    vendor_id: str,
    current_bank_account: Optional[str],
    baseline_bank_account: Optional[str],
) -> Optional[RiskFlag]:
    """Flags risk if vendor bank account details differ from baseline records, recommending verification."""
    if not current_bank_account or not baseline_bank_account:
        return None

    norm_current = current_bank_account.strip().replace(" ", "").replace("-", "").upper()
    norm_baseline = baseline_bank_account.strip().replace(" ", "").replace("-", "").upper()

    if norm_current != norm_baseline:
        return RiskFlag(
            code="VENDOR_BANK_ACCOUNT_MODIFIED",
            category=RiskCategory.VENDOR,
            message=f"Vendor '{vendor_id}' bank account '{current_bank_account}' differs from baseline record '{baseline_bank_account}'. Recommend manual verification.",
            severity=RiskLevel.CRITICAL,
            source="vendor_master_check",
            details={
                "vendor_id": vendor_id,
                "provided_bank": current_bank_account,
                "baseline_bank": baseline_bank_account,
                "recommendation": "VERIFY_BANK_ACCOUNT_BEFORE_PAYMENT",
            },
        )
    return None


def calculate_transaction_anomaly_score(
    amount: float,
    historical_amounts: List[float],
) -> Tuple[float, Optional[RiskFlag]]:
    """
    Calculates statistical anomaly score based on historical vendor transaction amounts.
    Handles edge cases: empty history, 1 historical value, zero stdev, negative amounts.
    """
    if amount < 0:
        return 0.0, RiskFlag(
            code="INVALID_TRANSACTION_AMOUNT",
            category=RiskCategory.FINANCIAL,
            message=f"Negative transaction amount (${amount:,.2f}) detected.",
            severity=RiskLevel.HIGH,
            source="financial_rules_engine",
            details={"amount": amount},
        )

    if not historical_amounts or amount == 0.0:
        return 0.0, None

    valid_history = [float(a) for a in historical_amounts if float(a) >= 0]
    if not valid_history:
        return 0.0, None

    avg_amount = statistics.mean(valid_history)

    if len(valid_history) == 1:
        hist_val = valid_history[0]
        if hist_val > 0 and amount > (hist_val * 2.5):
            ratio = amount / hist_val
            flag = RiskFlag(
                code="UNUSUAL_TRANSACTION_AMOUNT",
                category=RiskCategory.FINANCIAL,
                message=f"Transaction amount ${amount:,.2f} is {ratio:.1f}x single historical transaction baseline (${hist_val:,.2f}).",
                severity=RiskLevel.MEDIUM if ratio < 4.0 else RiskLevel.HIGH,
                source="anomaly_detector",
                details={"amount": amount, "single_historical_baseline": hist_val, "ratio": round(ratio, 2)},
            )
            return min(100.0, ratio * 20.0), flag
        return 0.0, None

    # Multi-value history
    stdev = statistics.stdev(valid_history)

    if stdev == 0.0:
        if amount != avg_amount:
            ratio = amount / avg_amount if avg_amount > 0 else 2.0
            flag = RiskFlag(
                code="UNUSUAL_TRANSACTION_AMOUNT",
                category=RiskCategory.FINANCIAL,
                message=f"Transaction amount ${amount:,.2f} deviates from constant historical baseline (${avg_amount:,.2f}).",
                severity=RiskLevel.MEDIUM if ratio < 3.0 else RiskLevel.HIGH,
                source="anomaly_detector",
                details={"amount": amount, "constant_baseline": avg_amount},
            )
            return min(100.0, ratio * 25.0), flag
        return 0.0, None

    # Calculate z-score
    z_score = abs(amount - avg_amount) / stdev

    if z_score >= 2.5 or amount > (avg_amount * 3.0):
        flag = RiskFlag(
            code="UNUSUAL_TRANSACTION_AMOUNT",
            category=RiskCategory.FINANCIAL,
            message=f"Transaction amount ${amount:,.2f} is unusually high compared to historical baseline avg ${avg_amount:,.2f} (z-score: {z_score:.2f}).",
            severity=RiskLevel.MEDIUM if z_score < 4.0 else RiskLevel.HIGH,
            source="anomaly_detector",
            details={"amount": amount, "average_amount": avg_amount, "z_score": round(z_score, 2), "stdev": round(stdev, 2)},
        )
        return min(100.0, z_score * 20.0), flag

    return min(100.0, z_score * 10.0), None


def evaluate_operational_risk(
    invoice_number: str,
    vendor_id: str,
    amount: float,
    current_bank_account: Optional[str] = None,
    baseline_bank_account: Optional[str] = None,
    historical_invoices: Optional[List[Dict[str, Any]]] = None,
    historical_amounts: Optional[List[float]] = None,
    high_value_threshold: float = 10000.0,
) -> RiskScore:
    """Combines operational risk rules to calculate an overall RiskScore and generate flags."""
    flags: List[RiskFlag] = []
    scores: Dict[str, float] = {}

    # 1. Duplicate check
    dup_flag = check_duplicate_invoice(invoice_number, vendor_id, historical_invoices or [], amount)
    if dup_flag:
        flags.append(dup_flag)
        scores["duplicate_risk"] = 80.0
    else:
        scores["duplicate_risk"] = 0.0

    # 2. Bank modification check
    bank_flag = check_vendor_bank_change(vendor_id, current_bank_account, baseline_bank_account)
    if bank_flag:
        flags.append(bank_flag)
        scores["bank_change_risk"] = 90.0
    else:
        scores["bank_change_risk"] = 0.0

    # 3. Transaction anomaly check
    anomaly_score, anomaly_flag = calculate_transaction_anomaly_score(amount, historical_amounts or [])
    scores["anomaly_risk"] = anomaly_score
    if anomaly_flag:
        flags.append(anomaly_flag)

    # 4. High-value transaction check
    if amount >= high_value_threshold:
        flags.append(
            RiskFlag(
                code="HIGH_VALUE_TRANSACTION",
                category=RiskCategory.FINANCIAL,
                message=f"Transaction amount ${amount:,.2f} exceeds standard approval threshold ${high_value_threshold:,.2f}.",
                severity=RiskLevel.MEDIUM,
                source="financial_rules_engine",
                details={"amount": amount, "threshold": high_value_threshold},
            )
        )
        scores["threshold_risk"] = 40.0
    else:
        scores["threshold_risk"] = 0.0

    # Calculate overall aggregated risk score
    total_score = min(100.0, max(scores.values()) if scores else 0.0)

    # Determine risk level
    if any(f.severity == RiskLevel.CRITICAL for f in flags) or total_score >= 85.0:
        level = RiskLevel.CRITICAL
    elif any(f.severity == RiskLevel.HIGH for f in flags) or total_score >= 60.0:
        level = RiskLevel.HIGH
    elif any(f.severity == RiskLevel.MEDIUM for f in flags) or total_score >= 30.0:
        level = RiskLevel.MEDIUM
    else:
        level = RiskLevel.LOW

    return RiskScore(
        score=round(total_score, 2),
        level=level,
        flags=flags,
        breakdown=scores,
    )
