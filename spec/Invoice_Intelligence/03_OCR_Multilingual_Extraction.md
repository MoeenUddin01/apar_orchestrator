# 🔍 OCR & Multilingual Extraction Specification

This document details the optical character recognition (OCR), layout extraction, and multilingual normalization requirements for converting unstructured documents into standard invoice structures.

---

## 🎯 1. Capabilities & Scope

The extraction layer processes diverse document types without relying on static coordinate templates.

### 1.1 Multilingual & Localization Requirements
- **English**: Standard LTR processing and Western Arabic numerals (`0-9`).
- **Arabic**: Right-to-Left (RTL) text extraction, Arabic script support, and Arabic-Indic numerals (`٠١٢٣٤٥٦٧٨٩`).
- **Mixed Multilingual**: Invoices containing simultaneous English and Arabic sections (e.g. bilingual VAT invoices in KSA/UAE).
- **Date & Currency Formats**: Localized date representations (Gregorian & Hijri text conversions) and ISO currency codes (`SAR`, `AED`, `USD`, `EUR`).

### 1.2 Document Layout & Physical Variability
- **Digital PDFs**: Text layer extraction with visual layout confirmation.
- **Scanned Documents**: Multi-page layout, key-value pair, and tabular line-item detection.
- **Handwritten Documents**: Best-effort handwriting extraction. If handwriting is illegible or produces low field confidence, it automatically triggers Human-in-the-Loop (HITL) review.

---

## 🔀 2. Normalization Pipeline (Pre-Validation Requirement)

> **CRITICAL RULE**: All character, digit, and format normalizations MUST occur inside the Extraction Adapter / Normalization Layer **BEFORE downstream deterministic validation (`validate_invoice`)**.

Deterministic validation engines expect clean, standard floats and ASCII strings. The normalization pipeline performs:

### 2.1 Digit Normalization
Converts Arabic-Indic digits to standard ASCII numerals:
```text
Arabic-Indic:  ١٢٣٤٥.٦٧  ──►  12345.67
Extended:      ۱۲۳۴۵.۶۷  ──►  12345.67
```

### 2.2 Decimal & Thousand Separator Normalization
Normalizes regional number formats into standard floating-point representation (`12345.67`):
```text
European Format:   12.345,67  ──►  12345.67
Arabic Text:       ١٢,٣٤٥٫٦٧  ──►  12345.67
Space Separator:   12 345.67  ──►  12345.67
```

### 2.3 Date Normalization
Parses localized date strings into ISO 8601 YYYY-MM-DD standard format:
```text
"04/10/2026" / "2026-10-04" / "٠٤/١٠/٢٠٢٦"  ──►  "2026-10-04"
```

---

## 🔌 3. Provider Abstraction & Technology Boundary

Extraction engines are encapsulated behind an `InvoiceExtractor` interface to prevent vendor lock-in.

```text
                        ┌────────────────────────────────────────┐
                        │    InvoiceExtractor (Interface)        │
                        └───────────────────┬────────────────────┘
                                            │
           ┌────────────────────────────────┼────────────────────────────────┐
           ▼                                ▼                                ▼
┌──────────────────────┐        ┌──────────────────────┐        ┌──────────────────────┐
│ Azure DocIntel       │        │ AWS Textract         │        │ LLM Vision Extractor │
│ Adapter (Primary)    │        │ Adapter              │        │ Adapter              │
└──────────────────────┘        └──────────────────────┘        └──────────────────────┘
```

### Extractor Interface Contract
The adapter receives the document stream (from `DocumentStorageInterface`) and returns raw extracted fields along with field-level confidence scores:

```python
class ExtractionResult(BaseModel):
    raw_text: str
    fields: Dict[str, Any]             # Provider extracted dict
    confidence_scores: Dict[str, float]# Field-level confidence scores (0.0 to 1.0)
    language_detected: str             # e.g., "en", "ar", "mixed"
    provider_name: str                 # e.g., "azure_doc_intel"
```

---

## 📝 4. Extraction Fields & Target Mapping

The extraction adapter extracts raw vendor fields and maps them directly into the canonical structure:

| Document Section | Extracted Field Name | Target Internal Field (`ExtractedInvoice`) |
| :--- | :--- | :--- |
| Header | Invoice Number / رقم الفاتورة | `invoice_number` |
| Header | Purchase Order / رقم أمر الشراء | `po_number` |
| Header | Vendor Tax ID / Commercial ID | `vendor_id` (used to lookup `vendor_id`) |
| Financials | Total Amount / المبلغ الإجمالي | `invoice_total` |
| Line Items | Item ID / Code | `line_items[].item_id` |
| Line Items | Item Description | `line_items[].description` |
| Line Items | Quantity / الكمية | `line_items[].quantity` |
| Line Items | Unit Price / سعر الوحدة | `line_items[].unit_price` |
| Line Items | Total Price / إجمالي السطر | `line_items[].total_price` |
