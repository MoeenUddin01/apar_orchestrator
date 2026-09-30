import streamlit as st
import requests
import json

# Configuration
API_BASE_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="AP/AR Orchestrator HITL Dashboard", layout="wide")

st.title("💸 AP/AR Orchestrator Dashboard")
st.markdown("Monitor Accounts Payable (AP) and Accounts Receivable (AR) workflows and handle Human-in-the-Loop (HITL) approvals.")

# Initialize session state for workflows
if "workflows" not in st.session_state:
    st.session_state.workflows = []

# Sidebar for new submissions
with st.sidebar:
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
                    
                    if status == "PENDING":
                        st.info(f"**Status:** 🔄 Processing...")
                    elif status in ["APPROVED", "COMPLETED"]:
                        st.success(f"**Status:** ✅ {status}")
                    elif status == "REQUIRES_APPROVAL":
                        st.warning(f"**Status:** ⚠️ {status}")
                    else:
                        st.error(f"**Status:** ❌ {status}")
                    
                    st.divider()
                    
                    # Beautiful UI Rendering instead of Raw JSON
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
                            st.success("✅ **Perfect Match!** The billed amounts and quantities exactly match our database records.")
                        else:
                            st.error(f"❌ **Discrepancy Detected!** Variance Amount: **${m_res.get('variance_amount', 0.0):,.2f}**")
                            if m_res.get("missing_documents"):
                                st.warning(f"🚨 Missing Database Documents: {', '.join(m_res['missing_documents'])}")
                        
                        c_po, c_gr = st.columns(2)
                        with c_po:
                            st.write("**Purchase Order (Expected)**")
                            if ff.get("po"):
                                st.metric("Expected Total", f"${ff['po'].get('expected_total', 0.0):,.2f}")
                            else:
                                st.error("PO Record Not Found in DB")
                                
                        with c_gr:
                            st.write("**Goods Receipt (Actual Delivery)**")
                            if ff.get("goods_receipt"):
                                st.metric("Total Qty Received", ff['goods_receipt'].get('received_quantity', 0.0))
                            else:
                                st.error("No Goods Receipt Found in DB (Not Delivered)")
                    else:
                        st.subheader("💸 Extracted Remittance Details")
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Customer ID", ext.get("customer_identifier", "N/A"))
                        c2.metric("Ref Invoices", ", ".join(ext.get("referenced_invoices", [])) or "None")
                        c3.metric("Amount Paid", f"${ext.get('total_payment', 0.0):,.2f}")
                        
                        st.subheader("📊 Payment Reconciliation")
                        rec = ff.get("reconciliation_result", {})
                        
                        if rec.get("is_fully_paid"):
                            st.success(f"✅ **Account Paid in Full!** Applied ${rec.get('applied_amount', 0.0):,.2f}.")
                        else:
                            st.warning(f"⚠️ **Outstanding Balance:** ${rec.get('remaining_balance', 0.0):,.2f} remains unpaid. Days Overdue: **{rec.get('days_overdue', 0)}**")
                        
                        st.write("**Unpaid Invoices Fetched From DB:**")
                        for inv in ff.get("invoices", []):
                            st.markdown(f"- **{inv.get('invoice_number')}**: Due {inv.get('due_date')} (${inv.get('total_amount'):,.2f} total, ${inv.get('amount_paid'):,.2f} already paid)")

                    st.divider()
                        
                    if current_state.get("validation_errors"):
                        st.error("Validation Errors:")
                        for err in current_state["validation_errors"]:
                            st.write(f"- {err}")

                    # Handle HITL Pause
                    if "human_review" in next_nodes:
                        st.warning("⚠️ This workflow is paused and requires Human-in-the-Loop approval!")
                        
                        if current_state.get("drafted_communications"):
                            email_target = "Customer" if wf_type == "ar" else "Vendor"
                            st.info(f"**Drafted Email to {email_target}:**")
                            st.text(current_state["drafted_communications"][-1].get("body", "No email body generated."))
                            
                        action_col1, action_col2 = st.columns(2)
                        comments = st.text_input("Reviewer Comments", key=f"comments_{wf_id}")
                        
                        with action_col1:
                            if st.button("✅ Approve & Send Email", key=f"approve_{wf_id}"):
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
                    elif status in ["APPROVED", "REJECTED", "EXCEPTION"]:
                        st.success(f"Workflow Complete: {status}")
                else:
                    st.error("Could not fetch state from API.")
            except Exception as e:
                st.error(f"Error fetching state: {e}")
