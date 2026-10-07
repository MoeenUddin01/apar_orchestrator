from abc import ABC, abstractmethod
from typing import BinaryIO
from src.domain.ap.models import ExtractionResult, ExtractedInvoice

class InvoiceExtractor(ABC):
    """
    Interface for document extraction engines to prevent vendor lock-in.
    """
    @abstractmethod
    def extract(self, document_stream: BinaryIO) -> ExtractionResult:
        """
        Extract raw text, fields, and confidence scores from a document stream.
        """
        pass
        
    @abstractmethod
    def map_to_canonical(self, result: ExtractionResult) -> ExtractedInvoice:
        """
        Map provider-specific extraction results to the canonical ExtractedInvoice schema,
        applying any required normalization.
        """
        pass
