import io
import pytest
from httpx import ASGITransport, AsyncClient
from src.api.main import app
from src.domain.ap.storage import default_storage_provider


@pytest.mark.asyncio
async def test_upload_valid_pdf_document():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        pdf_bytes = b"%PDF-1.5 Valid Test PDF Content"
        files = {"file": ("vendor_invoice_1001.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
        response = await client.post("/api/v1/documents/upload", files=files)

        assert response.status_code == 201
        data = response.json()
        assert data["document_id"].startswith("doc-")
        assert data["original_filename"] == "vendor_invoice_1001.pdf"
        assert data["mime_type"] == "application/pdf"
        assert data["file_size_bytes"] == len(pdf_bytes)
        assert "checksum_sha256" in data

        # Cleanup storage
        default_storage_provider.delete_document(data["document_id"])


@pytest.mark.asyncio
async def test_upload_unsupported_format_rejected():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        docx_bytes = b"PK\x03\x04 fake docx binary data"
        files = {"file": ("malicious.docx", io.BytesIO(docx_bytes), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        response = await client.post("/api/v1/documents/upload", files=files)

        assert response.status_code == 400
        assert "Unsupported file format" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_empty_file_rejected():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        empty_bytes = b""
        files = {"file": ("empty.pdf", io.BytesIO(empty_bytes), "application/pdf")}
        response = await client.post("/api/v1/documents/upload", files=files)

        assert response.status_code == 400
        assert "Uploaded file is empty" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_document_metadata_and_download():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR Mock Image"
        files = {"file": ("receipt.png", io.BytesIO(png_bytes), "image/png")}
        upload_res = await client.post("/api/v1/documents/upload", files=files)
        doc_id = upload_res.json()["document_id"]

        # Get metadata
        meta_res = await client.get(f"/api/v1/documents/{doc_id}")
        assert meta_res.status_code == 200
        assert meta_res.json()["original_filename"] == "receipt.png"

        # Download stream
        download_res = await client.get(f"/api/v1/documents/{doc_id}/download")
        assert download_res.status_code == 200
        assert download_res.content == png_bytes

        # Cleanup
        default_storage_provider.delete_document(doc_id)
