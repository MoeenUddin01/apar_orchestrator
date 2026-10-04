# ⚠️ Error Handling Specification

This document defines how exceptions, extraction failures, and operational edge cases are handled across the Invoice Intelligence lifecycle.

---

## 🎯 1. Guiding Principles

> **CRITICAL RULE**: System MUST NEVER silently proceed with unverified, malformed, or low-confidence financial data.

1. **Deterministic Halting**: Technical errors (storage failures, corrupted binaries, unhandled exceptions) set `FinanceState.status = "ERROR"` and halt execution.
2. **Confidence Escalation**: Extracted data containing missing critical fields or low confidence score MUST escalate to `human_review` (HITL), never to payment execution.
3. **Immutable Audit Logging**: Every failure scenario emits an `AuditEvent` to preserve end-to-end traceability.

---

## 🏗️ 2. Failure Scenarios & Handling Rules

### 2.1 File & Ingestion Failures (Upload API Boundary)

| Scenario | System Behavior | Workflow Status | Audit Event Emitted |
| :--- | :--- | :--- | :--- |
| **Corrupted File / Header Mismatch** | Upload API rejects file with HTTP 400. Workflow is not initiated. | N/A | `EXTERNAL_API_FAILURE` |
| **File Exceeds 10MB** | Upload API rejects with HTTP 413 Payload Too Large. | N/A | `EXTERNAL_API_FAILURE` |
| **Storage Write Failure** | Storage abstraction throws I/O exception. API returns HTTP 500. | N/A | `ERROR` |

---

### 2.2 Storage Access Failures (During Workflow Execution)

| Scenario | System Behavior | Workflow Status | Audit Event Emitted |
| :--- | :--- | :--- | :--- |
| **`document_id` Not Found** | Node catches missing stream exception. | `"ERROR"` | `ERROR` |
| **Storage Stream Read Timeout** | Node retries up to 3 times with exponential backoff before throwing. | `"ERROR"` | `EXTERNAL_API_FAILURE` |

---

### 2.3 Provider & OCR Extraction Failures

| Scenario | System Behavior | Workflow Status | Audit Event Emitted |
| :--- | :--- | :--- | :--- |
| **OCR Provider Timeout / Unavailable** | Node executes retry policy (3 retries). If retries fail, workflow halts. | `"ERROR"` | `EXTERNAL_API_FAILURE` |
| **Malformed / Invalid JSON Response** | Extraction Adapter fails deserialization into `ExtractionResult`. | `"ERROR"` | `EXTRACTION_FAILED` |
| **Illegible Handwriting / Unreadable Scan** | Best-effort OCR yields low confidence. Scores fall below threshold. | `"REQUIRES_APPROVAL"` | `LOW_CONFIDENCE_ROUTING` |

---

### 2.4 Data Contract & Normalization Failures

| Scenario | System Behavior | Workflow Status | Audit Event Emitted |
| :--- | :--- | :--- | :--- |
| **Missing Critical Field (`po_number`, `vendor_id`)** | Normalization layer populates empty string. Confidence evaluation flags field. Routes to HITL. | `"REQUIRES_APPROVAL"` | `LOW_CONFIDENCE_ROUTING` |
| **Unparseable Numeric String** | Normalization fails float conversion. Field confidence set to `0.0`. Routes to HITL. | `"REQUIRES_APPROVAL"` | `LOW_CONFIDENCE_ROUTING` |

---

## 🔁 3. Retry Strategy & Node Resilience

For transient provider errors (e.g. rate limits or brief network glitches on Azure Document Intelligence API):

```python
# Conceptual retry pattern for extraction node
RETRY_POLICY = {
    "max_attempts": 3,
    "initial_interval_seconds": 2,
    "backoff_factor": 2.0,
    "retryable_exceptions": ["ProviderTimeoutError", "RateLimitError"]
}
```

If max retries are exceeded:
1. Log detailed stack trace in application logs.
2. Emit `AuditEvent` with `event_type = "EXTRACTION_FAILED"`.
3. Set `FinanceState.status = "ERROR"`.
