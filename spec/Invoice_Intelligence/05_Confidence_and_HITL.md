# 🚦 Confidence Evaluation & Human-in-the-Loop (HITL) Specification

This document defines how extraction reliability is calculated, how confidence routing functions, and how human corrections loop back into deterministic validation.

---

## 🎯 1. Overview & Current vs. Target Distinction

Confidence scoring evaluates the reliability of extracted data. Low confidence or missing critical fields trigger human review.

### 1.1 Current Capability (In Codebase)
The existing `human_review_node` in `src/graph/ap/nodes.py` operates as a simple decision gate:
```text
human_review ──► Decision: APPROVE / REJECT ──► END
```
It does NOT currently support arbitrary field correction or re-submitting data back into validation.

### 1.2 Target Capability (To Be Implemented)
The target architecture introduces data correction capabilities, enabling operators to edit extracted fields and re-enter the deterministic validation pipeline.

---

## 🏗️ 2. Target HITL Cyclic Workflow Architecture

```text
               evaluate_confidence
                        │
       ┌────────────────┴────────────────┐
       ▼                                 ▼
HIGH CONFIDENCE                   LOW CONFIDENCE / MISSING CRITICALS
       │                                 │
       │                                 ▼
       │                    human_review (HITL Node)
       │                         │
       │                         ├─► REJECT ──► END (Status: REJECTED)
       │                         │
       │                         └─► CORRECT DATA
       │                                 │
       │                                 ▼
       │                          corrected_data
       │                                 │
       │                                 ▼
       │                     Merge into extracted_data
       │                                 │
       │                     Audit: HUMAN_CORRECTION_APPLIED
       │                                 │
       └─────────────────────────────────┴──► validate_invoice
                                                    ↓
                                                lookup_db
                                                    ↓
                                               match_3_way
```

> **Target Cycle Mandate**: When an operator submits `corrected_data`, the workflow MUST loop back to `validate_invoice` to re-verify mathematical and business rule consistency before DB lookup or 3-way matching.

---

## 📊 3. Confidence Metrics & Field Criticality

### 3.1 Field-Level & Document-Level Scoring
The extraction adapter returns confidence scores for each extracted key (`0.0` to `1.0`):
- **Critical Fields** (Must meet configured thresholds):
  - `invoice_number`
  - `vendor_id`
  - `po_number`
  - `invoice_total`
- **Line-Item Fields**:
  - `item_id`, `quantity`, `unit_price`, `total_price`

### 3.2 Dynamic & Configurable Thresholds
- Thresholds MUST NOT be hardcoded (e.g. `0.95`).
- Thresholds are loaded dynamically from environment/configuration (e.g., `CONFIDENCE_THRESHOLD_CRITICAL=0.90`, `CONFIDENCE_THRESHOLD_OVERALL=0.85`).

### 3.3 Routing Rules
- **Route to `validate_invoice`**: If aggregate score AND all critical field scores exceed configured thresholds.
- **Route to `human_review`**: If document-level score or ANY critical field score is below threshold, or if critical fields are un-extracted.

---

## 🧑‍💻 4. Data Correction & Auditability

### 4.1 `corrected_data` Payload Structure
When a human operator performs data correction, `FinanceState.hitl_input` receives:

```json
{
  "action": "CORRECT_DATA",
  "corrected_by": "user_id_441",
  "timestamp": "2026-10-04T12:30:00Z",
  "corrected_data": {
    "vendor_id": "VEND-8841",
    "invoice_total": 1500.00
  },
  "correction_reason": "OCR misread '8841' as '884I'"
}
```

### 4.2 Audit Event Generation
Upon processing `CORRECT_DATA`:
1. The system merges `corrected_data` into `FinanceState.extracted_data`.
2. Emits an immutable `AuditEvent`:
   - `event_type`: `HUMAN_CORRECTION_APPLIED`
   - `actor_type`: `USER`
   - `actor_id`: `"user_id_441"`
   - `metadata`: Contains diff of original extracted values vs. corrected values.
3. Sets `FinanceState.status` to `"PROCESSING"` and routes to `validate_invoice`.
