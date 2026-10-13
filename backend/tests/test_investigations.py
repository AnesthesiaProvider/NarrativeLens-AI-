"""Tests for Investigation CRUD, pipeline triggers, and operational status endpoints."""

import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_investigation_crud_lifecycle(client: AsyncClient):
    """Test full lifecycle: create, get, update, run, status, list, and delete."""
    # 1. Create Investigation
    payload = {
        "title": "Operation Disinfo Beta",
        "description": "Investigating cross-platform hate speech narratives and coordinated amplification.",
        "keywords": ["target_phrase", "coordinated_tag", "propaganda"],
        "languages": ["en", "es"],
        "source_types": ["url", "rss", "file"],
    }
    create_res = await client.post("/api/investigations", json=payload)
    assert create_res.status_code == 201, create_res.text
    created = create_res.json()
    inv_id = created["id"]
    assert created["title"] == payload["title"]
    assert created["status"] == "active"
    assert created["document_count"] == 0
    assert created["cluster_count"] == 0

    # 2. Get Investigation by ID
    get_res = await client.get(f"/api/investigations/{inv_id}")
    assert get_res.status_code == 200
    fetched = get_res.json()
    assert fetched["id"] == inv_id
    assert fetched["title"] == payload["title"]

    # 3. Update Investigation
    update_payload = {
        "title": "Operation Disinfo Beta Updated",
        "status": "paused",
        "keywords": ["target_phrase", "coordinated_tag", "updated_term"],
    }
    update_res = await client.put(f"/api/investigations/{inv_id}", json=update_payload)
    assert update_res.status_code == 200
    updated = update_res.json()
    assert updated["title"] == "Operation Disinfo Beta Updated"
    assert updated["status"] == "paused"
    assert "updated_term" in updated["keywords"]

    # 4. Trigger Analysis Run
    run_res = await client.post(f"/api/investigations/{inv_id}/run")
    assert run_res.status_code == 202
    run_data = run_res.json()
    assert run_data["investigation_id"] == inv_id
    assert run_data["status"] == "queued"

    # 5. Check Pipeline Status
    status_res = await client.get(f"/api/investigations/{inv_id}/status")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["investigation_id"] == inv_id
    assert status_data["document_count"] == 0

    # 6. List Investigations
    list_res = await client.get("/api/investigations?page=1&size=10")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] >= 1
    assert any(item["id"] == inv_id for item in list_data["items"])

    # 7. Delete Investigation
    delete_res = await client.delete(f"/api/investigations/{inv_id}")
    assert delete_res.status_code == 200
    delete_data = delete_res.json()
    assert delete_data["status"] == "success"

    # 8. Verify 404 after deletion
    verify_res = await client.get(f"/api/investigations/{inv_id}")
    assert verify_res.status_code == 404


@pytest.mark.asyncio
async def test_get_nonexistent_investigation(client: AsyncClient):
    """Test 404 returned for non-existent UUID."""
    random_id = uuid.uuid4()
    response = await client.get(f"/api/investigations/{random_id}")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
