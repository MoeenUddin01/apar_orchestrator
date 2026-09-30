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
    Uses the Groq LLM to draft a highly professional, polite overdue reminder for customers.
    """
    logger.info("Executing LLM generation for overdue reminder.")
    invoice_id = context.get("invoice_id", "UNKNOWN")
    days_overdue = context.get("days_overdue", 0)
    remaining_balance = context.get("remaining_balance", 0.0)
    customer_name = context.get("customer_name", "Valued Customer")
    
    escalate_days = yaml_config.get("workflow", {}).get("auto_escalate_overdue_days", 30)
    default_tone = yaml_config.get("llm", {}).get("default_tone", "PROFESSIONAL")
    tone: Literal["PROFESSIONAL", "URGENT"] = "URGENT" if days_overdue > escalate_days else default_tone
    
    if yaml_config.get("llm", {}).get("provider", "groq") == "groq" and yaml_config.get("llm", {}).get("api_key"):
        try:
            from langchain_groq import ChatGroq
            from src.core.config import settings
            
            llm = ChatGroq(
                model="qwen/qwen3.8-27b", 
                temperature=0.3, 
                api_key=settings.GROQ_API_KEY
            )
            structured_llm = llm.with_structured_output(DraftedCommunication)
            
            prompt = f"""
            You are a polite, professional Accounts Receivable associate. 
            Draft an email to a customer regarding an outstanding balance.
            
            Context:
            - Customer: {customer_name}
            - Invoice Number: {invoice_id}
            - Days Overdue: {days_overdue} days
            - Remaining Balance: ${remaining_balance:.2f}
            
            Write a clear, concise, and professional email subject and body.
            The tone should be {tone.lower()}.
            """
            
            return structured_llm.invoke(prompt)
        except Exception as e:
            logger.error(f"LLM communication generation failed: {e}")
            
    # Fallback if LLM fails
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
    Uses the Groq LLM to draft a highly professional, polite, and contextual discrepancy notice.
    """
    logger.info("Executing LLM generation for discrepancy notice.")
    invoice_id = context.get("invoice_id", "UNKNOWN")
    vendor_id = context.get("vendor_id", "UNKNOWN")
    po_number = context.get("po_number", "UNKNOWN")
    raw_reason = context.get("reason", "A discrepancy was found")
    variance_amount = context.get("variance_amount", 0.0)
    
    # Translate technical ENUM to human context
    reason_context = "An unknown error occurred."
    if raw_reason == "HIGH_VALUE":
        reason_context = "The invoice exceeds our standard high-value threshold and requires manual executive approval. Please expect a slight delay."
    elif raw_reason == "TOLERANCE_EXCEPTION":
        reason_context = f"There is a price variance of ${variance_amount:,.2f} between the billed amount and our Purchase Order records."
    elif raw_reason == "MISSING_DOCS":
        reason_context = "We have no record of receiving the physical goods at our warehouse (Missing Goods Receipt)."

    if yaml_config.get("llm", {}).get("provider", "groq") == "groq" and yaml_config.get("llm", {}).get("api_key"):
        try:
            from langchain_groq import ChatGroq
            from src.core.config import settings
            
            llm = ChatGroq(
                model="qwen/qwen3.8-27b", 
                temperature=0.3, 
                api_key=settings.GROQ_API_KEY
            )
            structured_llm = llm.with_structured_output(DraftedCommunication)
            
            prompt = f"""
            You are a polite, professional Accounts Payable associate. 
            Draft an email to a vendor regarding a paused invoice workflow.
            
            Context:
            - Vendor: {vendor_id}
            - Invoice Number: {invoice_id}
            - PO Number: {po_number}
            - Issue: {reason_context}
            
            Write a clear, concise, and professional email subject and body. 
            Do not use aggressive language. Do not mention internal codes like TOLERANCE_EXCEPTION.
            """
            
            return structured_llm.invoke(prompt)
        except Exception as e:
            logger.error(f"LLM communication generation failed: {e}")

    # Fallback if LLM fails
    subject = f"Action Required: Discrepancy on Invoice {invoice_id}"
    body = (
        f"Dear Vendor {vendor_id},\n\n"
        f"We are reaching out regarding invoice {invoice_id} referencing PO {po_number}.\n\n"
        f"{reason_context}\n\n"
        f"Please review this and provide clarification so we may proceed with processing.\n\n"
        f"Thank you,\nAccounts Payable"
    )
    
    return DraftedCommunication(
        subject=subject,
        body=body,
        tone="PROFESSIONAL"
    )
