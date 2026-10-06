import pytest
import shutil
from pathlib import Path
from src.domain.ap.storage import LocalStorageProvider


@pytest.fixture
def temp_storage_provider(tmp_path):
    storage_dir = tmp_path / "invoices_storage"
    provider = LocalStorageProvider(base_dir=storage_dir)
    yield provider
    shutil.rmtree(storage_dir, ignore_errors=True)


def test_store_and_retrieve_document(temp_storage_provider):
    sample_content = b"%PDF-1.4 Mock Invoice Content"
    filename = "invoice_test.pdf"
    mime_type = "application/pdf"

    # Store document
    meta = temp_storage_provider.store_document(
        file_bytes=sample_content,
        filename=filename,
        mime_type=mime_type,
        uploaded_by="test_user",
    )

    assert meta.document_id.startswith("doc-")
    assert meta.original_filename == filename
    assert meta.mime_type == mime_type
    assert meta.file_size_bytes == len(sample_content)
    assert meta.checksum_sha256 is not None

    # Retrieve metadata
    retrieved_meta = temp_storage_provider.get_document_metadata(meta.document_id)
    assert retrieved_meta is not None
    assert retrieved_meta.document_id == meta.document_id
    assert retrieved_meta.checksum_sha256 == meta.checksum_sha256

    # Retrieve content stream
    retrieved_stream = temp_storage_provider.get_document_stream(meta.document_id)
    assert retrieved_stream == sample_content


def test_delete_document(temp_storage_provider):
    sample_content = b"Fake PNG Content"
    meta = temp_storage_provider.store_document(
        file_bytes=sample_content,
        filename="image.png",
        mime_type="image/png",
    )

    assert temp_storage_provider.get_document_metadata(meta.document_id) is not None

    deleted = temp_storage_provider.delete_document(meta.document_id)
    assert deleted is True

    assert temp_storage_provider.get_document_metadata(meta.document_id) is None
    assert temp_storage_provider.get_document_stream(meta.document_id) is None


def test_nonexistent_document(temp_storage_provider):
    assert temp_storage_provider.get_document_metadata("doc-nonexistent-1234") is None
    assert temp_storage_provider.get_document_stream("doc-nonexistent-1234") is None
    assert temp_storage_provider.delete_document("doc-nonexistent-1234") is False
