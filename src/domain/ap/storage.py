import hashlib
import json
import os
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Union

from src.core.logging import logger
from src.domain.ap.models import DocumentMetadata


class DocumentStorageInterface(ABC):
    """
    Abstract interface for Document Storage providers.
    Encapsulates physical storage operations (Local FS, AWS S3, Azure Blob)
    so that FinanceState carries only lightweight UUID document_id references.
    """

    @abstractmethod
    def store_document(
        self,
        file_bytes: bytes,
        filename: str,
        mime_type: str,
        uploaded_by: str = "api_user_01",
    ) -> DocumentMetadata:
        """Stores binary document content and generates metadata record."""
        pass

    @abstractmethod
    def get_document_stream(self, document_id: str) -> Optional[bytes]:
        """Retrieves raw binary file content for a given document_id."""
        pass

    @abstractmethod
    def get_document_metadata(self, document_id: str) -> Optional[DocumentMetadata]:
        """Retrieves DocumentMetadata record for a given document_id."""
        pass

    @abstractmethod
    def delete_document(self, document_id: str) -> bool:
        """Deletes binary document and metadata record for a given document_id."""
        pass


class LocalStorageProvider(DocumentStorageInterface):
    """
    Local filesystem implementation of DocumentStorageInterface.
    Used for development, testing, and local deployment environments.
    """

    def __init__(self, base_dir: Union[str, Path] = "./data/storage/invoices"):
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def store_document(
        self,
        file_bytes: bytes,
        filename: str,
        mime_type: str,
        uploaded_by: str = "api_user_01",
    ) -> DocumentMetadata:
        document_id = f"doc-{uuid.uuid4()}"
        checksum_sha256 = hashlib.sha256(file_bytes).hexdigest()
        uploaded_at = datetime.now(timezone.utc).isoformat()
        
        file_path = self.base_dir / f"{document_id}_{filename}"
        meta_path = self.base_dir / f"{document_id}.meta.json"

        # Write binary content
        with open(file_path, "wb") as f:
            f.write(file_bytes)

        metadata = DocumentMetadata(
            document_id=document_id,
            original_filename=filename,
            mime_type=mime_type,
            file_size_bytes=len(file_bytes),
            storage_uri=f"storage://invoices/{document_id}/{filename}",
            checksum_sha256=checksum_sha256,
            uploaded_at=uploaded_at,
            uploaded_by=uploaded_by,
        )

        # Write sidecar JSON metadata
        with open(meta_path, "w", encoding="utf-8") as f:
            f.write(metadata.model_dump_json(indent=2))

        logger.info(f"Stored document {document_id} ({filename}, {len(file_bytes)} bytes) at {file_path}")
        return metadata

    def get_document_stream(self, document_id: str) -> Optional[bytes]:
        meta = self.get_document_metadata(document_id)
        if not meta:
            logger.warning(f"Document {document_id} metadata not found.")
            return None

        file_path = self.base_dir / f"{document_id}_{meta.original_filename}"
        if not file_path.exists():
            logger.error(f"Binary file for document {document_id} missing at {file_path}")
            return None

        with open(file_path, "rb") as f:
            return f.read()

    def get_document_metadata(self, document_id: str) -> Optional[DocumentMetadata]:
        meta_path = self.base_dir / f"{document_id}.meta.json"
        if not meta_path.exists():
            return None

        with open(meta_path, "r", encoding="utf-8") as f:
            meta_dict = json.load(f)
            return DocumentMetadata(**meta_dict)

    def delete_document(self, document_id: str) -> bool:
        meta = self.get_document_metadata(document_id)
        deleted = False
        if meta:
            file_path = self.base_dir / f"{document_id}_{meta.original_filename}"
            if file_path.exists():
                file_path.unlink()
                deleted = True

        meta_path = self.base_dir / f"{document_id}.meta.json"
        if meta_path.exists():
            meta_path.unlink()
            deleted = True

        if deleted:
            logger.info(f"Deleted document {document_id}")
        return deleted


# Global singleton instance for local development
default_storage_provider = LocalStorageProvider()
