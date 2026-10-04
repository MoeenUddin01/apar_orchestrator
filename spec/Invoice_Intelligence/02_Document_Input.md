# 📥 Document Input & Storage Specification

This document defines how multi-format invoice documents enter the AP workflow, how they are managed via a storage abstraction, and how references are maintained in `FinanceState`.

---

## 🎯 1. Overview & Storage Architecture

Binary document content (PDFs, TIFFs, JPEGs) MUST NOT be stored directly inside `FinanceState`. Storing large binary payloads in LangGraph state causes state serialization bloat, database overhead, and memory degradation.

### Ingestion & Storage Flow

```text
Client / REST API
       ↓
Document Upload API  ──► File Validation (MIME, Size, Integrity)
       ↓
Document Storage Abstraction (Local Disk / S3 / Azure Blob - TBD)
       ↓
Generates document_id (UUID) & Storage Reference
       ↓
FinanceState (stores document_id, filename, content_type)
       ↓
AP Workflow Execution (Nodes fetch stream on-demand using document_id)
```

---

## 🏗️ 2. Supported Input Types & Constraints

### 2.1 Format & Media Types
- **PDF Documents**: Born-digital PDFs, scanned single-page and multi-page PDFs (`application/pdf`).
- **Image Formats**: JPEG (`image/jpeg`), PNG (`image/png`), TIFF (`image/tiff`).
- **Physical States**: Born-digital, printed and scanned, handwritten documents.

### 2.2 Ingestion Validation Rules
- **Maximum File Size**: 10MB per file (configurable via system environment).
- **Page Limits**: Maximum 50 pages per PDF document for v1.
- **File Integrity**: Empty files (0 bytes), corrupted headers, or encrypted/password-protected PDFs must be rejected immediately at the Upload API boundary with a descriptive HTTP 400 error.
- **Unsupported Formats**: `.docx`, `.xlsx`, `.zip`, `.txt` files are rejected before storage allocation.

---

## 📦 3. Metadata & State Linkage

### 3.1 Document Metadata Schema
When a document is uploaded, the Document Upload API generates a metadata record:

```json
{
  "document_id": "doc-uuid-1234-5678",
  "original_filename": "vendor_invoice_9942.pdf",
  "mime_type": "application/pdf",
  "file_size_bytes": 1048576,
  "storage_uri": "storage://invoices/2026/10/doc-uuid-1234-5678.pdf",
  "checksum_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "uploaded_at": "2026-10-04T12:00:00Z",
  "uploaded_by": "api_user_01"
}
```

### 3.2 `FinanceState` Integration
`FinanceState` carries only light metadata and the `document_id` reference:

```python
class FinanceState(TypedDict, total=False):
    workflow_id: str
    workflow_type: Literal["AP", "AR"]
    status: str
    document_id: Optional[str]        # References binary file in Document Storage
    raw_document: Optional[str]       # Optional: Extracted plain text / OCR raw text
    extracted_data: Optional[Dict]    # Canonical ExtractedInvoice dict
    ...
```

---

## 🔌 4. Document Access & Storage Abstraction

Nodes in the AP workflow (e.g. `extract_invoice`) access the physical document using an abstract storage interface:

```text
DocumentStorageInterface:
  - store_document(file_bytes, metadata) -> document_id
  - get_document_stream(document_id) -> ReadStream
  - get_document_metadata(document_id) -> MetadataDict
  - delete_document(document_id) -> bool
```

### Storage Provider Status: [DESIGN DECISION / TBD]
- **Development / Local**: Local filesystem storage (e.g., `./data/storage/invoices/`).
- **Production Target**: Object storage (AWS S3, Azure Blob Storage, or GCP Cloud Storage).
- *Decision status*: Storage technology implementation is marked as **TBD**. The pipeline strictly interacts with `DocumentStorageInterface`.

---

## 🔒 5. Document Lifecycle & Error Handling

1. **Upload Failure**: If storage write fails, return HTTP 500. Workflow is not initiated.
2. **Access Failure during Extraction**: If `extract_invoice` node cannot read `document_id` stream, log `EXTERNAL_API_FAILURE`, emit audit event, and transition `FinanceState.status` to `ERROR`.
3. **Retention & Cleanup**: Raw document binary files are retained according to regulatory retention policies (default: 7 years) and access-controlled via RBAC.
