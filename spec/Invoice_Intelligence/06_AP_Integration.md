# 🔗 AP Workflow Integration Specification

This document defines how the Invoice Intelligence boundary and target GRC pipeline integrate with the Accounts Payable (AP) LangGraph workflow.

---

## 🎯 1. Actual Current AP Graph (`src/graph/ap/graph.py`)

The existing compiled AP graph in `src/graph/ap/graph.py` consists of 6 nodes:

```text
START
  ↓
extract_invoice          (LLM raw text extraction)
  ↓
validate_invoice         (Deterministic ExtractedInvoice schema validation)
  ↓
lookup_db                (Retrieves PO & Goods Receipt from DB)
  ↓
match_3_way              (Deterministic 3-way financial match)
  ↓
route_ap_decision
  ├─ approve ───────────► END
  ├─ exception ─────────► END
  └─ hitl ──────────────► generate_discrepancy ──► human_review (Approve/Reject) ──► END
```

> **IMPORTANT Architectural Fact**: Standalone modules exist in `src/grc/` for Policy Rules, RBAC, and GRC models, but Security, Risk, Compliance, and Governance are **NOT currently compiled into the AP graph**.

---

## 🏗️ 2. Target Workflow Integration

The target architecture introduces Invoice Intelligence upfront, adds a cyclic HITL correction loop, and chains GRC authorization nodes post-matching.

### 2.1 Complete Target AP Graph

```text
START / API Document Upload
  ↓
Document Storage Abstraction (Generates document_id)
  ↓
[TARGET] Security Pre-Check
  ↓
[TARGET] ingest_document
  ↓
[TARGET] extract_invoice (OCR / Provider Adapter)
  ↓
[TARGET] evaluate_confidence
  │
  ├─ HIGH CONFIDENCE ────────────────────────────────────────────────────────┐
  │                                                                          │
  └─ LOW CONFIDENCE / MISSING CRITICALS ──► human_review (HITL Node)         │
                                                 │                           │
                                                 ├─► REJECT ──► END          │
                                                 │                           │
                                                 └─► CORRECT DATA            │
                                                         │                   │
                                                         ▼                   │
                                                  corrected_data             │
                                                         │                   │
  ┌──────────────────────────────────────────────────────┘                   │
  ▼                                                                          ▼
[EXISTING] validate_invoice (Deterministic validation against ExtractedInvoice)
  ↓
[EXISTING] lookup_db
  ↓
[EXISTING] match_3_way
  ↓
[TARGET GRC] risk_assessment        (Evaluates vendor risk & anomaly scores)
  ↓
[TARGET GRC] compliance_check       (Verifies tax compliance & duplicate checks)
  ↓
[TARGET GRC] governance_authorize  (Checks spending limits & Segregation of Duties)
  ↓
[TARGET GRC] maker_checker_approval (Human approval for high-value transactions)
  ↓
[TARGET] financial_action           (Executes ERP payment posting)
  ↓
END
```

---

## ⚙️ 3. Node Integration Details

### 3.1 `ingest_document` Node (New Target Node)
- **State Read**: `FinanceState.document_id`.
- **Action**: Verifies document exists in `DocumentStorageInterface` and loads file metadata into state.
- **State Write**: `FinanceState.raw_document` (optional plain text preview).

### 3.2 `extract_invoice` Node (Updated Target Node)
- **State Read**: `FinanceState.document_id`.
- **Action**: Invokes `InvoiceExtractor` adapter (e.g. Azure AI Document Intelligence) to parse stream and normalize numbers/dates into `ExtractedInvoice` Pydantic model.
- **State Write**: `FinanceState.extracted_data` (Canonical Invoice Schema).

### 3.3 `evaluate_confidence` Node (New Target Node)
- **State Read**: `FinanceState.extracted_data`, confidence scores metadata.
- **Action**: Compares critical field scores against `CONFIDENCE_THRESHOLD_CRITICAL`.
- **Routing Decision**:
  - `HIGH_CONFIDENCE` → Edge to `validate_invoice`.
  - `LOW_CONFIDENCE` → Edge to `human_review`.

### 3.4 `human_review` Node (Updated Target Node)
- **Current State**: Accepts `APPROVE` or `REJECT`.
- **Target Upgrade**: Accepts `CORRECT_DATA` with `corrected_data` dictionary. Emits `HUMAN_CORRECTION_APPLIED` audit event and routes back to `validate_invoice`.

### 3.5 Downstream Deterministic Nodes (`validate_invoice`, `lookup_db`, `match_3_way`)
- **Compatibility**: Remain untouched. Receive standardized `ExtractedInvoice` format regardless of whether data was auto-extracted or human-corrected.
