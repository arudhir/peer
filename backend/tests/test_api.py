"""Tests for API endpoints."""

import pytest


def test_root_endpoint(client):
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data


def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "config" in data


def test_list_experiments(client):
    """Test listing experiments."""
    response = client.get("/api/experiments")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_list_sequences(client):
    """Test listing sequences."""
    response = client.get("/api/experiments/exp001/sequences")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_plate_metadata(client):
    """Test getting plate metadata."""
    response = client.get("/api/experiments/exp001/sequences/seq001/plate-metadata")
    assert response.status_code == 200
    data = response.json()
    assert "wells" in data
    assert "experiment_id" in data
    assert "sequence_id" in data


def test_cache_stats(client):
    """Test cache stats endpoint."""
    response = client.get("/api/cache/stats")
    assert response.status_code == 200
    data = response.json()
    assert "size_bytes" in data
    assert "num_items" in data


def test_cache_clear(client):
    """Test cache clear endpoint."""
    response = client.post("/api/cache/clear")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
