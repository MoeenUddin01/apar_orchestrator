from typing import Any, Dict, Optional
from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import Response

from src.core.logging import logger
from src.database.audit_repository import default_audit_repository
from src.domain.ap.models import DocumentMetadata
from src.domain.ap.storage import default_storage_provider
from src.domain.audit_schema import ActorType, AuditEvent, EventType, GRCDomain

router = APIRouter(prefix="/api/v1/documents", tags=["Document Storage & Ingestion"])

ALLOWED_MIME_TYPES = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/tiff": ".tiff",
}

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10MB limit


@router.post("/upload", response_model=DocumentMetadata, status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile = File(...)) -> DocumentMetadata:
    """
    Ingest multi-format invoice documents (PDF, JPEG, PNG, TIFF) into the storage abstraction.
    Validates file MIME type, size limit (10MB max), and non-empty file content.
    Returns lightweight DocumentMetadata carrying document_id UUID.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file must have a valid filename.")

    mime_type = file.content_type or ""
    if mime_type not in ALLOWED_MIME_TYPES:
        # Fallback extension check if content-type header is generic
        ext = f".{file.filename.split('.')[-1].lower()}" if "." in file.filename else ""
        valid_exts = [".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".tif"]
        if ext not in valid_exts:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format '{mime_type}'. Supported formats: PDF, JPEG, PNG, TIFF.",
            )
        # Assign best-effort MIME
        if ext == ".pdf":
            mime_type = "application/pdf"
        elif ext in [".jpg", ".jpeg"]:
            mime_type = "image/jpeg"
        elif ext == ".png":
            mime_type = "image/png"
        elif ext in [".tiff", ".tif"]:
            mime_type = "image/tiff"

    file_bytes = await file.read()
    if not file_bytes or len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty (0 bytes).")

    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File size ({len(file_bytes)} bytes) exceeds maximum limit of 10MB (10,485,760 bytes).",
        )

    # Store file using storage provider abstraction
    metadata = default_storage_provider.store_document(
        file_bytes=file_bytes,
        filename=file.filename,
        mime_type=mime_type,
        uploaded_by="api_user_01",
    )

    # Emit DOCUMENT_RECEIVED audit event
    audit_event = AuditEvent(
        workflow_id=f"wf-doc-ingest-{metadata.document_id[:8]}",
        actor_type=ActorType.USER,
        actor_id="api_user_01",
        event_type=EventType.DOCUMENT_RECEIVED,
        grc_domain=GRCDomain.WORKFLOW,
        action="STORE_DOCUMENT",
        status="SUCCESS",
        summary=f"Ingested document '{file.filename}' ({len(file_bytes)} bytes) with document_id {metadata.document_id}",
        evidence_refs=[metadata.storage_uri],
        metadata={
            "document_id": metadata.document_id,
            "filename": metadata.original_filename,
            "checksum_sha256": metadata.checksum_sha256,
            "mime_type": metadata.mime_type,
            "file_size_bytes": metadata.file_size_bytes,
        },
    )
    default_audit_repository.log_event(audit_event)

    return metadata


@router.get("/{document_id}", response_model=DocumentMetadata)
async def get_document_metadata(document_id: str) -> DocumentMetadata:
    """Retrieve metadata record for a stored document by document_id."""
    meta = default_storage_provider.get_document_metadata(document_id)
    if not meta:
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found.")
    return meta


@router.get("/{document_id}/download")
async def download_document(document_id: str) -> Response:
    """Download binary content stream of a stored document by document_id."""
    meta = default_storage_provider.get_document_metadata(document_id)
    if not meta:
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found.")

    file_bytes = default_storage_provider.get_document_stream(document_id)
    if file_bytes is None:
        raise HTTPException(status_code=404, detail=f"Binary stream for document '{document_id}' not found.")

    return Response(content=file_bytes, media_type=meta.mime_type)
