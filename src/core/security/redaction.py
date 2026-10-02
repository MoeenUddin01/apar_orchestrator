import hashlib
import re
from typing import Any, Dict, List, Optional, Tuple
from src.domain.compliance_state import RedactionResult


# PII Patterns designed to protect personal data while strictly avoiding financial figures, dates, and PO numbers.
DEFAULT_PII_PATTERNS = {
    # SSN: formatted 3-2-4 digit split (e.g. 123-45-6789 or 123 45 6789)
    "SSN": r"\b(?!000|666)\d{3}[- ](?!00)\d{2}[- ](?!0000)\d{4}\b",
    
    # Credit Cards: 13-16 digit cards, option for dash/space separators between 4-digit blocks
    "CREDIT_CARD": r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|6(?:011|5[0-9]{2})[0-9]{12}|3[47][0-9]{13}|\d{4}[- ]\d{4}[- ]\d{4}[- ]\d{4})\b",
    
    # IBAN Bank Accounts: International standard format
    "BANK_ACCOUNT": r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b",
    
    # Emails
    "EMAIL": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    
    # Phone numbers: e.g. +1-800-555-0199 or (555) 019-2834
    "PHONE": r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
}


class Redactor:
    """
    Data Privacy & PII Redactor enforcing GDPR/CCPA compliance.
    Identifies and masks sensitive PII before text payloads leave system boundaries.
    """

    def __init__(
        self,
        custom_patterns: Optional[Dict[str, str]] = None,
        enabled_types: Optional[List[str]] = None,
    ):
        self.patterns = dict(DEFAULT_PII_PATTERNS)
        if custom_patterns:
            self.patterns.update(custom_patterns)

        if enabled_types:
            self.patterns = {k: v for k, v in self.patterns.items() if k in enabled_types}

        # Precompile regexes
        self.compiled_patterns = {
            entity_type: re.compile(pattern)
            for entity_type, pattern in self.patterns.items()
        }

    def redact_text(self, text: str) -> RedactionResult:
        """
        Scans and redacts PII from raw input text.
        Computes SHA-256 hash of original text for auditability.
        """
        if not text or not isinstance(text, str):
            return RedactionResult(
                original_text_hash=None,
                redacted_text="" if text is None else str(text),
                pii_detected=False,
                entities_found={},
                total_redactions=0,
            )

        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        redacted_text = text
        entities_found: Dict[str, int] = {}
        total_redactions = 0

        # Scan text for each entity pattern
        for entity_type, compiled_re in self.compiled_patterns.items():
            matches = list(compiled_re.finditer(redacted_text))
            if matches:
                count = len(matches)
                entities_found[entity_type] = count
                total_redactions += count
                # Replace with placeholder token e.g., [REDACTED_SSN]
                replacement = f"[REDACTED_{entity_type}]"
                redacted_text = compiled_re.sub(replacement, redacted_text)

        return RedactionResult(
            original_text_hash=text_hash,
            redacted_text=redacted_text,
            pii_detected=total_redactions > 0,
            entities_found=entities_found,
            total_redactions=total_redactions,
        )

    def redact_dict(self, data: Dict[str, Any]) -> Tuple[Dict[str, Any], RedactionResult]:
        """
        Recursively redacts string values within dictionaries and nested structures.
        """
        if not data or not isinstance(data, dict):
            res = self.redact_text(str(data) if data is not None else "")
            return {}, res

        combined_entities: Dict[str, int] = {}
        total_count = 0

        def _walk_and_redact(item: Any) -> Any:
            nonlocal total_count
            if isinstance(item, str):
                result = self.redact_text(item)
                if result.pii_detected:
                    for etype, count in result.entities_found.items():
                        combined_entities[etype] = combined_entities.get(etype, 0) + count
                        total_count += count
                return result.redacted_text
            elif isinstance(item, dict):
                return {k: _walk_and_redact(v) for k, v in item.items()}
            elif isinstance(item, list):
                return [_walk_and_redact(elem) for elem in item]
            return item

        redacted_dict = _walk_and_redact(data)

        overall_result = RedactionResult(
            original_text_hash=hashlib.sha256(str(data).encode("utf-8")).hexdigest(),
            redacted_text=str(redacted_dict),
            pii_detected=total_count > 0,
            entities_found=combined_entities,
            total_redactions=total_count,
        )

        return redacted_dict, overall_result


# Singleton default instance for convenient imports
default_redactor = Redactor()
