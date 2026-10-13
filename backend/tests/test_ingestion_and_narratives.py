"""Tests for ingestion, feedback, and narrative endpoints."""

import io
import json
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_file_upload_and_document_listing(client: AsyncClient):
    """Test uploading a JSON dataset to an investigation and listing documents."""
    # 1. Create Investigation
    inv_res = await client.post(
        "/api/investigations",
        json={"title": "Ingestion Test Investigation"},
    )
    assert inv_res.status_code == 201
    inv_id = inv_res.json()["id"]

    # 2. Upload JSON file
    sample_docs = [
        {"title": "Doc 1", "content": "First sample message for narrative processing."},
        {"title": "Doc 2", "content": "Second sample article for hate speech monitoring."},
    ]
    json_bytes = json.dumps(sample_docs).encode("utf-8")
    files = {"file": ("dataset.json", io.BytesIO(json_bytes), "application/json")}
    data = {"investigation_id": inv_id}

    upload_res = await client.post("/api/ingestion/upload", data=data, files=files)
    assert upload_res.status_code == 201, upload_res.text
    upload_data = upload_res.json()
    assert upload_data["documents_ingested"] == 2

    # 3. List Documents
    doc_res = await client.get(f"/api/ingestion/documents?investigation_id={inv_id}")
    assert doc_res.status_code == 200
    docs = doc_res.json()
    assert docs["total"] == 2
    assert len(docs["items"]) == 2


@pytest.mark.asyncio
async def test_feedback_flow(client: AsyncClient):
    """Test submitting and querying human feedback."""
    feedback_payload = {
        "corrected_label": "safe",
        "is_ambiguous": False,
        "explanation": "Context indicates sarcastic usage, not targeted abuse.",
        "reviewer": "analyst_alice",
    }
    post_res = await client.post("/api/feedback", json=feedback_payload)
    assert post_res.status_code == 201
    fb = post_res.json()
    assert fb["reviewer"] == "analyst_alice"
    assert fb["corrected_label"] == "safe"

    # List feedback
    list_res = await client.get("/api/feedback?reviewer=analyst_alice")
    assert list_res.status_code == 200
    fb_list = list_res.json()
    assert fb_list["total"] >= 1
