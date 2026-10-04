# 🏛️ Invoice Intelligence Architecture Specification

This document defines the overall architecture for the Invoice Intelligence layer in the AP/AR Orchestrator. Invoice Intelligence acts as the intelligent ingestion, extraction, and normalization boundary for vendor invoices before deterministic validation occurs.

---

## 🎯 1. Purpose & Scope

- **Purpose**: Ingest multi-format (PDF, JPEG, PNG, TIFF) and multilingual (English, Arabic, mixed) invoice documents, store them securely via a storage abstraction, and extract structured data that normalizes into the internal `ExtractedInvoice` contract.
- **Scope**: Document ingestion API, Document Storage abstraction (`document_id`), OCR/LLM adapter, multilingual & digit normalization, confidence evaluation, and HITL data correction routing.
- **Out of Scope**: Deterministic financial validation (handled by `validate_invoice`), 3-way matching (handled by `match_3_way`), risk scoring, policy enforcement, and payment execution.

---

## 🏗️ 2. Current vs. Target Architecture

### 2.1 Actual Current AP Graph (`src/graph/ap/graph.py`)

The existing AP workflow operates deterministically on raw text injected directly into `FinanceState.raw_document`:

```text
START
  ↓
extract_invoice          (LLM extraction from raw text)
  ↓
validate_invoice         (Deterministic validation against ExtractedInvoice schema)
  ↓
lookup_db                (Database retrieval of PO & Goods Receipt)
  ↓
match_3_way              (Deterministic 3-way financial matching)
  ↓
route_ap_decision
  ├─ approve ───────────► END
  ├─ exception ─────────► END
  └─ hitl ──────────────► generate_discrepancy ──► human_review (Approve/Reject only) ──► END
```

> **Note**: GRC components (Security, Risk, Compliance, Governance) exist in `src/grc/` as standalone modules and REST endpoints, but are **not yet compiled as nodes into the AP graph**.

---

### 2.2 Target Invoice Intelligence & AP Pipeline Architecture

```text
Client / API Upload
       ↓
Document Storage Abstraction  ──► Assigns document_id (Binary files stored out-of-state)
       ↓
FinanceState (carries document_id & workflow_id)
       ↓
Security Pre-Check            (File validation & sanitization)
       ↓
[TARGET] ingest_document       (Loads document metadata & stream reference)
       ↓
[TARGET] extract_invoice       (OCR / Provider Adapter: Azure / Textract / LLM)
       ↓
[TARGET] Normalization         (Arabic digit conversion, decimal & currency normalization)
       ↓
[TARGET] evaluate_confidence   (Field-level & document-level confidence check)
       │
       ├─ HIGH CONFIDENCE ────────────────────────────────────────────────────────┐
       │                                                                          │
       └─ LOW CONFIDENCE / MISSING CRITICALS ──► human_review (HITL Correction)  │
                                                       │                          │
                                                       ▼                          │
                                                 corrected_data                   │
                                                       │                          │
       ┌───────────────────────────────────────────────┘                          │
       ▼                                                                          ▼
[EXISTING] validate_invoice   (Deterministic validation against ExtractedInvoice contract)
       ↓
[EXISTING] lookup_db          (DB retrieval of PO & Goods Receipt)
       ↓
[EXISTING] match_3_way        (Deterministic 3-way financial matching)
       ↓
[TARGET GRC] Risk Assessment  (Standalone module → target graph node)
       ↓
[TARGET GRC] Compliance Verification (Standalone module → target graph node)
       ↓
[TARGET GRC] Governance Authorization (Policy rules & threshold authorization)
       ↓
[TARGET GRC] Maker-Checker Approval   (Human authorization for high-value / policy exceptions)
       ↓
[TARGET] Financial Action             (Payment execution / ERP posting)
```

---

## ⚖️ 3. Core Architectural Principle & Responsibility Boundary

All components across the AP workflow must adhere to the following strict boundary:

> **AI/OCR extracts data. Normalization converts it into the internal invoice contract (`ExtractedInvoice`). Deterministic logic validates financial correctness. Risk assesses risk. Compliance verifies controls. Governance authorizes. Humans approve where required. Financial Action executes. Audit Trail records evidence.**

### Detailed Responsibility Mapping

1. **Document Intelligence & Ingestion**:
   - Ingests binary files into storage, returns `document_id`.
   - Extracts raw document text and bounding boxes via OCR/AI adapters.
   - **Does NOT** perform financial calculations or approve payments.

2. **Normalization & Adapter**:
   - Converts provider output (e.g. Arabic digits `١٢٣٤` → `1234`, localized decimals) into standard schema.
   - Maps raw extracted fields strictly into the internal `ExtractedInvoice` Pydantic model (`invoice_number`, `po_number`, `vendor_id`, `invoice_total`, `line_items`).
   - Executes **BEFORE** downstream deterministic validation.

3. **Deterministic Validation (`validate_invoice`)**:
   - Source of truth for financial mathematical consistency (e.g., `quantity * unit_price == total_price`, sum of line items == `invoice_total`).
   - Never bypassed by AI confidence scores.

4. **Human-in-the-Loop (HITL)**:
   - Evaluates low-confidence extractions or missing critical fields.
   - Allows operators to submit `corrected_data`, which loops back into `validate_invoice`.

5. **GRC Layer (Security, Risk, Compliance, Governance)**:
   - **Security**: Sanitizes inputs and scans extracted text for prompt injection and PII.
   - **Risk**: Assesses vendor risk scores and anomaly indicators.
   - **Compliance**: Verifies tax compliance, regulatory rules, and duplicate invoice checks.
   - **Governance**: Enforces approval limits (SoD) and authorization policies.

6. **Audit Trail**:
   - Intercepts all state transitions and emits immutable audit events (`DOCUMENT_RECEIVED`, `EXTRACTION_STARTED`, `EXTRACTION_COMPLETED`, `LOW_CONFIDENCE_ROUTING`, `HUMAN_CORRECTION_APPLIED`, `RE_EXTRACTION`, `REVALIDATION`).

---

## 🤝 4. Backward Compatibility Guarantee

- **Pipeline Contract**: Invoice Intelligence MUST output data that is fully compatible with the existing `ExtractedInvoice` model and `FinanceState` definition.
- **No Direct Binary In State**: `FinanceState` carries `document_id` string references, keeping graph state serializable and lightweight.
- **Existing Nodes Preserved**: `validate_invoice`, `lookup_db`, and `match_3_way` remain untouched in logic and schema.
