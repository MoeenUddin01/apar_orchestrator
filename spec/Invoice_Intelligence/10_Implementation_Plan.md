# 📅 Invoice Intelligence Implementation Plan

This document defines the phased implementation roadmap for Invoice Intelligence, ordering work to ensure backward compatibility and continuous verification against the existing AP deterministic pipeline.

---

## 🎯 1. Implementation Roadmap Overview

```text
Phase 1: Architecture + Data Contracts (ExtractedInvoice alignment)
   ↓
Phase 2: Document Storage Abstraction (DocumentStorageInterface & document_id)
   ↓
Phase 3: Document Input / Upload API (PDF/Image file validation & ingestion)
   ↓
Phase 4: OCR + Multilingual Extraction Adapter (Digit normalization & provider integration)
   ↓
Phase 5: Confidence Evaluation (Threshold scoring & field validation)
   ↓
Phase 6: HITL Correction + Re-validation (Cyclic data correction loop)
   ↓
Phase 7: AP LangGraph Integration (Wiring new nodes into ap_graph)
   ↓
Phase 8: Security Integration (Pre-check sanitization & prompt injection defense)
   ↓
Phase 9: Risk / Compliance / Governance Integration (Wiring standalone GRC modules)
   ↓
Phase 10: Testing + Production Readiness (End-to-end integration & performance SLAs)
```

---

## 🏗️ 2. Detailed Phase Breakdown

### Phase 1: Architecture + Data Contracts
- **Goal**: Formally verify Pydantic data contracts (`ExtractedInvoice`, `LineItem`) in `src/domain/ap/models.py` and state attributes in `src/graph/state.py`.
- **Deliverables**: Interface definitions for `InvoiceExtractor` and `DocumentStorageInterface`.
- **Backward Compatibility Gate**: Existing unit tests for `ExtractedInvoice` pass cleanly.

### Phase 2: Document Storage Abstraction
- **Goal**: Implement `DocumentStorageInterface` with local filesystem provider for development.
- **Deliverables**: Storage interface, file streaming helpers, metadata generator.
- **Key Requirement**: `FinanceState` carries `document_id` UUID strings only; no binary blobs in graph state.

### Phase 3: Document Input / Upload API
- **Goal**: Build REST upload endpoint (`POST /api/v1/documents/upload`).
- **Deliverables**: Ingestion controller, file size/MIME validator (PDF, JPEG, PNG, TIFF).
- **Audit Requirement**: Emit `DOCUMENT_RECEIVED` audit event.

### Phase 4: OCR + Multilingual Extraction Adapter
- **Goal**: Build extraction provider adapter (e.g., Azure AI Document Intelligence adapter) and pre-validation normalization pipeline.
- **Deliverables**: Normalization module (Arabic-Indic digit conversion `١٢٣` → `123`, decimal separator parsing, date ISO conversion).
- **Key Requirement**: Normalization occurs BEFORE downstream validation.

### Phase 5: Confidence Evaluation
- **Goal**: Build confidence evaluator module.
- **Deliverables**: Dynamic configuration loader for thresholds (`CONFIDENCE_THRESHOLD_CRITICAL`), field scoring logic.
- **Audit Requirement**: Emit `LOW_CONFIDENCE_ROUTING` when thresholds fail.

### Phase 6: HITL Correction + Re-validation
- **Goal**: Upgrade `human_review` node to accept `CORRECT_DATA` payload.
- **Deliverables**: Data correction state merger, cyclic routing edge back to `validate_invoice`.
- **Audit Requirement**: Emit `HUMAN_CORRECTION_APPLIED` audit event.

### Phase 7: AP LangGraph Integration
- **Goal**: Wire `ingest_document`, `extract_invoice`, `evaluate_confidence`, and cyclic `human_review` into `src/graph/ap/graph.py`.
- **Deliverables**: Updated `ap_graph` definition and compiled state graph.
- **Acceptance Gate**: AP workflow executes end-to-end with full backward compatibility.

### Phase 8: Security Integration
- **Goal**: Integrate file sanitization pre-checks and prompt injection defense on extracted text fields.
- **Deliverables**: Security scanner hook before LLM processing, log PII redaction filter.

### Phase 9: Risk / Compliance / Governance Integration
- **Goal**: Compile standalone modules from `src/grc/` (`risk_assessment`, `compliance_check`, `governance_authorize`) as post-matching nodes in `ap_graph`.
- **Deliverables**: GRC node handlers in `src/graph/ap/nodes.py`, updated conditional routing.

### Phase 10: Testing + Production Readiness
- **Goal**: Execute full test suite specified in `09_Testing.md` (multilingual, handwriting, HITL correction cycle, security injection).
- **Deliverables**: Test reports, SLA verification, deployment documentation.
