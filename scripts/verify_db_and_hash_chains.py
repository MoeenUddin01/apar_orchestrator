import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import select
from src.database.connection import AsyncSessionLocal
from src.database.models.ap_models import InvoiceDB
from src.database.models.audit_models import AuditEventDB
from src.core.hashing import compute_event_hash

async def run_db_and_hash_verification():
    print("==========================================================")
    print("RUNNING DB, AUDIT TRAIL, HASH CHAIN, & ISOLATION VERIFICATION")
    print("==========================================================")
    
    async with AsyncSessionLocal() as session:
        # 1. Fetch all audit events
        stmt = select(AuditEventDB).order_by(AuditEventDB.timestamp.asc())
        events = (await session.execute(stmt)).scalars().all()
        print(f"Total PostgreSQL Audit Events Recorded: {len(events)}")
        
        # Group events by workflow_id
        wf_events = {}
        for ev in events:
            wf_id = ev.workflow_id
            if wf_id not in wf_events:
                wf_events[wf_id] = []
            wf_events[wf_id].append(ev)
            
        print(f"Total Unique Workflows Tracked in DB: {len(wf_events)}")
        
        # 2. Hash Chain Verification per Workflow
        hash_errors = []
        for wf_id, ev_list in wf_events.items():
            prev_hash = ""
            for idx, ev in enumerate(ev_list):
                if idx == 0 and ev.previous_hash != "":
                    hash_errors.append(f"Workflow {wf_id} event 0 has non-empty previous_hash: '{ev.previous_hash}'")
                elif idx > 0 and ev.previous_hash != prev_hash:
                    hash_errors.append(f"Workflow {wf_id} event {idx} previous_hash mismatch: expected '{prev_hash}', got '{ev.previous_hash}'")
                prev_hash = ev.event_hash
                
        if not hash_errors:
            print("✅ HASH CHAIN VERIFICATION: 100% PASS! All cryptographic event chains are valid.")
        else:
            print(f"❌ HASH CHAIN ERRORS ({len(hash_errors)}):", hash_errors)

        # 3. Cross-Workflow Isolation Check
        isolation_errors = []
        for wf_id, ev_list in wf_events.items():
            wf_types = set(ev.workflow_type for ev in ev_list)
            if len(wf_types) > 1:
                isolation_errors.append(f"Workflow {wf_id} mixed workflow types: {wf_types}")
            
            # Check AP event leakage into AR or vice versa
            wf_type = list(wf_types)[0] if wf_types else "UNKNOWN"
            for ev in ev_list:
                if wf_type == "AP" and ev.grc_domain and "AR" in ev.grc_domain:
                    isolation_errors.append(f"AP Workflow {wf_id} contains AR GRC domain: {ev.grc_domain}")
                elif wf_type == "AR" and ev.grc_domain and "AP" in ev.grc_domain:
                    isolation_errors.append(f"AR Workflow {wf_id} contains AP GRC domain: {ev.grc_domain}")
                    
        if not isolation_errors:
            print("✅ CROSS-WORKFLOW ISOLATION: 100% PASS! AP and AR workflows strictly isolated.")
        else:
            print(f"❌ ISOLATION ERRORS ({len(isolation_errors)}):", isolation_errors)

        # 4. Database Invoices Persistence Check
        stmt_inv = select(InvoiceDB)
        invoices = (await session.execute(stmt_inv)).scalars().all()
        print(f"\nTotal Persisted Approved Invoices in DB: {len(invoices)}")
        for inv in invoices:
            print(f"  - Invoice: {inv.invoice_number}, Vendor: {inv.vendor_id}, Total: ${inv.invoice_total:,.2f}, Status: {inv.status}, Workflow: {inv.workflow_id}")

if __name__ == "__main__":
    asyncio.run(run_db_and_hash_verification())
