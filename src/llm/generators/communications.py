from typing import Dict, Any, Literal
from pydantic import BaseModel
from src.core.logging import logger

class DraftedCommunication(BaseModel):
    subject: str
    body: str
    tone: Literal["PROFESSIONAL", "URGENT"]

from src.core.config import yaml_config

def generate_overdue_reminder_llm(context: Dict[str, Any]) -> DraftedCommunication:
    """
    Simulates an LLM drafting an overdue reminder using deterministic financial facts.
    """
    logger.info("Executing LLM generation for overdue reminder.")
    invoice_id = context.get("invoice_id", "UNKNOWN")
    days_overdue = context.get("days_overdue", 0)
    remaining_balance = context.get("remaining_balance", 0.0)
    customer_name = context.get("customer_name", "Valued Customer")
    
    escalate_days = yaml_config.get("workflow", {}).get("auto_escalate_overdue_days", 30)
    default_tone = yaml_config.get("llm", {}).get("default_tone", "PROFESSIONAL")
    
    tone: Literal["PROFESSIONAL", "URGENT"] = "URGENT" if days_overdue > escalate_days else default_tone
    
    subject = f"URGENT: Overdue Invoice {invoice_id}" if tone == "URGENT" else f"Reminder: Invoice {invoice_id} is overdue"
    
    body = (
        f"Dear {customer_name},\n\n"
        f"This is a {tone.lower()} reminder that invoice {invoice_id} is currently {days_overdue} days overdue. "
        f"Our records indicate an outstanding balance of ${remaining_balance:.2f}.\n\n"
        f"Please arrange payment at your earliest convenience. If you have already made this payment, please disregard this notice.\n\n"
        f"Thank you,\nFinance Team"
    )
    
    return DraftedCommunication(
        subject=subject,
        body=body,
        tone=tone
    )

def generate_discrepancy_notice_llm(context: Dict[str, Any]) -> DraftedCommunication:
    """
    Simulates an LLM drafting a discrepancy notice using deterministic financial facts.
    """
    logger.info("Executing LLM generation for discrepancy notice.")
    invoice_id = context.get("invoice_id", "UNKNOWN")
    vendor_id = context.get("vendor_id", "UNKNOWN")
    po_number = context.get("po_number", "UNKNOWN")
    reason = context.get("reason", "A discrepancy was found")
    variance_amount = context.get("variance_amount", 0.0)
    
    subject = f"Action Required: Discrepancy on Invoice {invoice_id}"
    
    body = (
        f"Dear Vendor {vendor_id},\n\n"
        f"We are reaching out regarding invoice {invoice_id} referencing PO {po_number}. "
        f"{reason}.\n\n"
    )
    
    if variance_amount > 0:
        body += f"There is a variance amount of ${variance_amount:.2f} that exceeds our acceptable tolerance.\n\n"
        
    body += "Please review and provide an updated invoice or clarification so we may proceed with processing.\n\nThank you,\nAccounts Payable"
    
    return DraftedCommunication(
        subject=subject,
        body=body,
        tone="PROFESSIONAL"
    )
