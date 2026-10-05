import streamlit as st
import requests
import json
from datetime import datetime

# Configuration
API_BASE_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="AP/AR Orchestrator HITL Dashboard", layout="wide")

st.title("💸 AP/AR Orchestrator Dashboard")
st.markdown("Monitor Accounts Payable (AP) and Accounts Receivable (AR) workflows and handle Human-in-the-Loop (HITL) approvals.")

# Initialize session state for workflows
if "workflows" not in st.session_state:
    st.session_state.workflows = []

# Sidebar for User Context and new submissions
with st.sidebar:
    st.header("👤 User Context")
    user_role = st.selectbox("Simulate Role", ["MAKER", "CHECKER", "AUDITOR", "ADMIN"], index=0)
    st.session_state.current_role = user_role
    st.markdown(f"**Current Role:** {user_role}")
    
    st.divider()

    st.header("📝 Submit New Document")
    doc_type = st.selectbox("Document Type", ["AP Invoice", "AR Remittance"])
    
    if doc_type == "AP Invoice":
        placeholder = "Paste invoice text here...\n\ne.g.\nPO: PO-1002\nVendor: VEND-111\nTotal: $15000"
        api_endpoint = "/ap/process-invoice"
        type_tag = "AP"
    else:
        placeholder = "Paste payment text here...\n\ne.g.\nCustomer: CUST-012\nAmount Paid: $2500\nReference Invoices: INV-2005"
        api_endpoint = "/ar/process-payment"
        type_tag = "AR"
        
    raw_text = st.text_area("Raw Document Text", height=200, placeholder=placeholder)
    
    if st.button("Submit Document"):
        with st.spinner("Processing through LangGraph via FastAPI..."):
            try:
                payload = {"raw_document": raw_text}
                res = requests.post(f"{API_BASE_URL}{api_endpoint}", json=payload)
                res.raise_for_status()
                data = res.json()
                
                st.session_state.workflows.append({
                    "id": data["workflow_id"],
                    "type": type_tag
                })
                st.success(f"Submitted successfully! ID: {data['workflow_id']}")
            except requests.exceptions.RequestException as e:
                error_msg = str(e)
                if getattr(e, 'response', None) is not None:
                    error_msg += f"\n\n**Server Details:** {e.response.text}"
                st.error(f"Failed to submit: {error_msg}")

st.header("📋 Active Workflows")

if not st.session_state.workflows:
    st.info("No workflows tracked yet. Submit a document from the sidebar!")
else:
    for wf in reversed(st.session_state.workflows):
        wf_id = wf["id"]
        wf_type = wf["type"].lower()
        
        with st.expander(f"{wf['type']} Workflow: {wf_id}", expanded=True):
            try:
                state_res = requests.get(f"{API_BASE_URL}/{wf_type}/{wf_id}/state")
                if state_res.status_code == 200:
                    state_data = state_res.json()
                    current_state = state_data["state"]
                    next_nodes = state_data["next_nodes"]
                    
                    status = current_state.get("status", "UNKNOWN")
                    
                    # Fetch Audit events
                    audit_events = []
                    try:
                        audit_res = requests.get(f"{API_BASE_URL}/audit/workflows/{wf_id}")
                        if audit_res.status_code == 200:
                            audit_events = audit_res.json()
                    except:
                        pass
                    
                    if status == "PENDING":
                        st.info(f"**Status:** 🔄 Processing...")
                    elif status in ["APPROVED", "COMPLETED"]:
                        st.success(f"**Status:** ✅ {status}")
                    elif status == "REQUIRES_APPROVAL":
                        st.warning(f"**Status:** ⚠️ {status}")
                    else:
                        st.error(f"**Status:** ❌ {status}")
                    
                    st.divider()
                    
                    ext = current_state.get("extracted_data", {})
                    ff = current_state.get("financial_facts", {})
                    
                    if wf_type == "ap":
                        st.subheader("🧾 Extracted Invoice Details")
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Invoice #", ext.get("invoice_number", "N/A"))
                        c2.metric("Vendor ID", ext.get("vendor_id", "N/A"))
                        c3.metric("PO Reference", ext.get("po_number", "N/A"))
                        c4.metric("Billed Total", f"${ext.get('invoice_total', 0.0):,.2f}")
                        
                        st.subheader("⚖️ Database 3-Way Match Verification")
                        m_res = ff.get("match_result", {})
                        is_match = m_res.get("is_match", False)
                        
                        if is_match:
                            st.success("✅ **PASSED**")
                        else:
                            st.error(f"❌ **FAILED!** Variance Amount: **${m_res.get('variance_amount', 0.0):,.2f}**")
                    else:
                        st.subheader("💸 Extracted Remittance Details")
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Customer ID", ext.get("customer_identifier", "N/A"))
                        c2.metric("Ref Invoices", ", ".join(ext.get("referenced_invoices", [])) or "None")
                        c3.metric("Amount Paid", f"${ext.get('total_payment', 0.0):,.2f}")
                        st.subheader("📊 Payment Reconciliation")
                        rec = ff.get("reconciliation_result", {})
                        if rec.get("is_fully_paid"):
                            st.success(f"✅ **PASSED**")
                        else:
                            st.warning(f"⚠️ **FAILED**")

                    st.divider()
                    
                    st.subheader("🛡️ GRC CONTROL STATUS")
                    col_risk, col_comp, col_gov, col_mc = st.columns(4)
                    
                    with col_risk:
                        st.markdown("### Risk")
                        risk_data = current_state.get("risk_assessment", {})
                        if risk_data:
                            risk_score = risk_data.get("risk_score", {})
                            level = risk_score.get("level", "UNKNOWN")
                            score = risk_score.get("score", 0)
                            if level in ["HIGH", "CRITICAL"]:
                                st.error(f"● Review Required\n\nRisk Score: {score}")
                            elif level == "MEDIUM":
                                st.warning(f"● Monitor\n\nRisk Score: {score}")
                            else:
                                st.success(f"● Passed\n\nRisk Score: {score}")
                            
                            flags = risk_score.get("flags", [])
                            if flags:
                                st.markdown("**Reason:**")
                                for f in flags:
                                    st.write(f"- {f.get('message', '')}")
                        else:
                            st.write("Not Evaluated")

                    with col_comp:
                        st.markdown("### Compliance")
                        is_reconciled = current_state.get("is_reconciled")
                        rec_res = current_state.get("reconciliation_result", {})
                        
                        if is_reconciled is True:
                            st.success("● MATCHED\n\nDeterministic financial reconciliation passed.")
                        elif is_reconciled is False:
                            st.error("● DISCREPANCY")
                            st.markdown("**Reason:**")
                            discrepancies = rec_res.get("discrepancies", [])
                            for d in discrepancies:
                                st.write(f"- {d.get('description', 'Discrepancy detected')}")
                        else:
                            st.write("Not Evaluated")
                            
                    with col_gov:
                        st.markdown("### Governance")
                        gov = current_state.get("governance_status", {})
                        if gov:
                            if gov.get("requires_checker_approval"):
                                st.warning("● Approval Required")
                                st.markdown("**Policy:** High-Value Invoice / Violations")
                                for v in gov.get("policy_violations", []):
                                    st.write(f"- {v}")
                            else:
                                st.success("● Passed")
                        else:
                            st.write("Not Evaluated")
                            
                    with col_mc:
                        st.markdown("### Maker-Checker")
                        gov = current_state.get("governance_status", {})
                        if gov and gov.get("requires_checker_approval"):
                            approval_status = gov.get("approval_status", "PENDING")
                            if approval_status == "PENDING":
                                st.warning("● Pending Approval")
                            elif approval_status == "APPROVED":
                                st.success("● Approved")
                            else:
                                st.error(f"● {approval_status}")
                            st.write(f"Required Role: {gov.get('checker_role_required', 'CHECKER')}")
                            if gov.get("approved_by"):
                                st.write(f"By: {gov.get('approved_by')}")
                        else:
                            st.write("N/A")

                    st.divider()

                    # Handle Maker Checker Approval Block
                    if "maker_checker" in next_nodes:
                        st.warning("┌──────────────────────────────────────────────┐\n\n"
                                   "│          CHECKER APPROVAL REQUIRED           │\n\n"
                                   "└──────────────────────────────────────────────┘")
                        
                        st.markdown(f"**Invoice**: {ext.get('invoice_number', 'N/A')}\n\n**Vendor**: {ext.get('vendor_id', 'N/A')}\n\n**Amount**: ${ext.get('invoice_total', ext.get('total_payment', 0.0)):,.2f}")
                        
                        gov = current_state.get("governance_status", {})
                        st.markdown("**Reason:**")
                        for v in gov.get("policy_violations", []):
                            st.write(f"- {v}")
                        
                        st.markdown(f"**Required Role:** {gov.get('checker_role_required', 'CHECKER')}\n\n**Status:** PENDING APPROVAL")
                        
                        if st.session_state.current_role != "CHECKER" and st.session_state.current_role != "ADMIN":
                            st.error(f"🔒 Unauthorized: You are currently a '{st.session_state.current_role}'. Only a CHECKER can approve this.")
                        else:
                            action_col1, action_col2 = st.columns(2)
                            comments = st.text_input("Reviewer Comments (Checker)", key=f"checker_comments_{wf_id}")
                            
                            with action_col1:
                                if st.button("✅ Approve", key=f"checker_approve_{wf_id}"):
                                    try:
                                        res = requests.post(
                                            f"{API_BASE_URL}/governance/decide", 
                                            headers={"x-user-role": st.session_state.current_role},
                                            json={
                                                "workflow_id": wf_id,
                                                "workflow_type": wf_type.upper(),
                                                "decision": "APPROVED",
                                                "comments": comments,
                                                "checker_id": f"User_{st.session_state.current_role}"
                                            }
                                        )
                                        if res.status_code == 403:
                                            st.error("🔒 Server rejected approval: Unauthorized role.")
                                        else:
                                            res.raise_for_status()
                                            st.success("Governance approved!")
                                            st.rerun()
                                    except Exception as e:
                                        st.error(f"Failed to resume: {e}")
                                        
                            with action_col2:
                                if st.button("❌ Reject", key=f"checker_reject_{wf_id}"):
                                    try:
                                        res = requests.post(
                                            f"{API_BASE_URL}/governance/decide", 
                                            headers={"x-user-role": st.session_state.current_role},
                                            json={
                                                "workflow_id": wf_id,
                                                "workflow_type": wf_type.upper(),
                                                "decision": "REJECTED",
                                                "comments": comments,
                                                "checker_id": f"User_{st.session_state.current_role}"
                                            }
                                        )
                                        if res.status_code == 403:
                                            st.error("🔒 Server rejected rejection: Unauthorized role.")
                                        else:
                                            res.raise_for_status()
                                            st.success("Governance rejected!")
                                            st.rerun()
                                    except Exception as e:
                                        st.error(f"Failed to resume: {e}")

                    # Handle Human Review Pause (for discrepancies)
                    elif "human_review" in next_nodes:
                        st.warning("⚠️ Workflow paused for discrepancy review.")
                        action_col1, action_col2 = st.columns(2)
                        comments = st.text_input("Reviewer Comments", key=f"comments_{wf_id}")
                        
                        with action_col1:
                            if st.button("✅ Approve Exception", key=f"approve_{wf_id}"):
                                try:
                                    res = requests.post(f"{API_BASE_URL}/{wf_type}/{wf_id}/resume", json={
                                        "action": "APPROVE",
                                        "comments": comments
                                    })
                                    res.raise_for_status()
                                    st.success("Workflow approved and resumed!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Failed to resume: {e}")
                                    
                        with action_col2:
                            if st.button("❌ Reject", key=f"reject_{wf_id}"):
                                try:
                                    res = requests.post(f"{API_BASE_URL}/{wf_type}/{wf_id}/resume", json={
                                        "action": "REJECT",
                                        "comments": comments
                                    })
                                    res.raise_for_status()
                                    st.success("Workflow rejected!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Failed to resume: {e}")

                    st.divider()
                    
                    st.subheader("📜 AUDIT TRAIL / TIMELINE")
                    if audit_events:
                        for event in audit_events:
                            ts = event.get("timestamp", "").split("T")[1][:8] if "T" in event.get("timestamp", "") else ""
                            summary = event.get("summary", "")
                            st.markdown(f"`{ts}` **{summary}**")
                    else:
                        st.write("No audit events found.")

                else:
                    st.error("Could not fetch state from API.")
            except Exception as e:
                st.error(f"Error fetching state: {e}")
