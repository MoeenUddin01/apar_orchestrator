# 📄 Canonical Invoice Schema Specification

This specification defines the canonical schema contract for Invoice Intelligence, ensuring complete backward compatibility with the existing deterministic AP pipeline (`ExtractedInvoice` in `src/domain/ap/models.py`).

---

## 🎯 1. Core Principle & Pipeline Compatibility

> **CRITICAL MANDATE**: Invoice Intelligence MUST NOT break the existing deterministic AP pipeline.

The extraction and normalization boundary transforms raw, un-structured OCR/AI responses into the exact `ExtractedInvoice` data structure expected by downstream nodes (`validate_invoice`, `lookup_db`, and `match_3_way`).

### Data Transformation Architecture

```text
PDF / Image File
       ↓
OCR / Document Intelligence Provider
       ↓
Provider Extraction Result (Raw JSON)
       ↓
Normalization & Adapter Layer (Digit conversion, field mapping)
       ↓
Existing ExtractedInvoice-compatible Structure (Pydantic Model)
       ↓
validate_invoice (Deterministic Node)
       ↓
lookup_db        (Database Lookup Node)
       ↓
match_3_way      (Deterministic 3-Way Match Node)
```

---

## 🏗️ 2. Field Name Alignment & Strict Data Contract

To prevent breaking changes, the schema strictly enforces the exact field names defined in `src/domain/ap/models.py`.

### 2.1 Standard Extracted Invoice Contract (`ExtractedInvoice`)

```python
class LineItem(BaseModel):
    item_id: str
    description: Optional[str] = None
    quantity: float
    unit_price: float
    total_price: float

class ExtractedInvoice(BaseModel):
    invoice_number: str
    vendor_id: str
    po_number: str
    invoice_total: float
    line_items: List[LineItem] = Field(default_factory=list)
```

### 2.2 Strict Field Name Prohibition & Mapping Matrix

| Prohibited / Conflicting Spec Field | Mandatory Code Base Field | Rationale / Source of Truth |
| :--- | :--- | :--- |
| `vendor_name` | `vendor_id` | `lookup_db` and `match_3_way` perform database queries matching `vendor_id` against `PurchaseOrder.vendor_id`. Extracted vendor name strings must be mapped or resolved to `vendor_id`. |
| `total_amount` | `invoice_total` | `validate_invoice` and `match_3_way` strictly inspect `invoice_total`. |
| `line_total` | `total_price` | `LineItem` calculation rules in `validate_invoice` strictly evaluate `quantity * unit_price == total_price`. |
| *(Omitted PO Number)* | `po_number` | `lookup_db` requires `po_number` to retrieve `PurchaseOrder` and `GoodsReceipt` records for 3-way matching. |

---

## 🌐 3. Pre-Validation Multilingual Normalization

Before assigning extracted values to the canonical `ExtractedInvoice` payload, the normalization layer cleanses raw provider text:

1. **Numeral System Standardizing**:
   - Arabic-Indic digits (`١٢٣٤٥٦٧٨٩٠`) are mapped to ASCII digits (`1234567890`).
2. **Numeric Separator Alignment**:
   - Localized thousand separators and decimal marks (e.g. `12.345,67` or `١٢,٣٤٥٫٦٧`) are converted to standard IEEE floating-point numbers (`12345.67`).
3. **Empty / Missing String Defaults**:
   - Null or un-extracted `po_number` or `vendor_id` fields are preserved as empty strings `""` or `UNKNOWN` so that `validate_invoice` can deterministically log explicit validation errors rather than failing with schema deserialization crashes.

---

## 📦 4. Extended Metadata & Confidence Layer

While `ExtractedInvoice` holds the canonical financial fields, additional extraction metadata is carried in `FinanceState` under metadata keys:

```json
{
  "extracted_data": {
    "invoice_number": "INV-2026-001",
    "vendor_id": "VEND-8841",
    "po_number": "PO-9942",
    "invoice_total": 1500.00,
    "line_items": [
      {
        "item_id": "ITEM-01",
        "description": "Consulting Services",
        "quantity": 10.0,
        "unit_price": 150.0,
        "total_price": 1500.0
      }
    ]
  },
  "extraction_metadata": {
    "document_id": "doc-uuid-1234-5678",
    "provider_name": "azure_doc_intel",
    "language_detected": "ar",
    "confidence_scores": {
      "overall": 0.94,
      "invoice_number": 0.98,
      "vendor_id": 0.85,
      "po_number": 0.92,
      "invoice_total": 0.99
    }
  }
}
```

---

## ⚖️ 5. Validation Guarantee

- Data must pass `ExtractedInvoice` Pydantic model validation prior to entering `validate_invoice`.
- Any field-level type mismatch or missing required field caught during normalization will mark extraction confidence as incomplete and trigger confidence evaluation handling.
