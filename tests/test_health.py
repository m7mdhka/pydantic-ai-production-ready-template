"""Tests for health check endpoint."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check_success(client_no_db: AsyncClient) -> None:
    """Test successful health check returns correct status."""
    response = await client_no_db.get("/v1/health/")

    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert "status" in data
    assert data["status"] == "Healthy"
    assert isinstance(data["version"], str)
    assert len(data["version"]) > 0


@pytest.mark.asyncio
async def test_health_check_response_structure(client_no_db: AsyncClient) -> None:
    """Test health check response has correct structure."""
    response = await client_no_db.get("/v1/health/")

    assert response.status_code == 200
    data = response.json()

    # Verify all required fields are present
    assert "version" in data
    assert "status" in data

    # Verify field types
    assert isinstance(data["version"], str)
    assert isinstance(data["status"], str)

    # Verify no extra fields
    assert len(data) == 2


@pytest.mark.asyncio
async def test_health_check_no_authentication_required(
    client_no_db: AsyncClient,
) -> None:
    """Test health check endpoint does not require authentication."""
    # Make request without authorization header
    response = await client_no_db.get("/v1/health/")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "Healthy"


@pytest.mark.asyncio
async def test_health_check_version_format(client_no_db: AsyncClient) -> None:
    """Test health check version follows semantic versioning format."""
    response = await client_no_db.get("/v1/health/")

    assert response.status_code == 200
    data = response.json()
    version = data["version"]

    # Version should be in format X.Y.Z or similar
    # Split by dots and check each part is numeric or valid
    parts = version.split(".")
    assert len(parts) >= 1  # At least one part

    # Each part should be alphanumeric
    for part in parts:
        assert len(part) > 0
        assert part.replace("-", "").replace("_", "").isalnum()


@pytest.mark.asyncio
async def test_health_check_multiple_requests(client_no_db: AsyncClient) -> None:
    """Test health check endpoint can handle multiple requests."""
    # Make multiple requests
    for _ in range(5):
        response = await client_no_db.get("/v1/health/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "Healthy"


@pytest.mark.asyncio
async def test_health_check_method_not_allowed(client_no_db: AsyncClient) -> None:
    """Test health check endpoint only accepts GET requests."""
    # Try POST request
    response = await client_no_db.post("/v1/health/")
    assert response.status_code == 405  # Method Not Allowed

    # Try PUT request
    response = await client_no_db.put("/v1/health/")
    assert response.status_code == 405

    # Try DELETE request
    response = await client_no_db.delete("/v1/health/")
    assert response.status_code == 405
