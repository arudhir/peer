"""Pytest fixtures for tests."""

import tempfile
from pathlib import Path

import numpy as np
import pytest
import tifffile
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def sample_tiff():
    """Create a sample multi-channel TIFF file."""
    with tempfile.NamedTemporaryFile(suffix=".tiff", delete=False) as f:
        # Create 4-channel image
        data = np.random.randint(0, 4096, (4, 512, 512), dtype=np.uint16)
        tifffile.imwrite(f.name, data, photometric="minisblack", metadata={"axes": "CYX"})
        yield Path(f.name)
        # Cleanup
        Path(f.name).unlink()


@pytest.fixture
def sample_mask():
    """Create a sample mask file."""
    with tempfile.NamedTemporaryFile(suffix=".tiff", delete=False) as f:
        # Create label mask
        data = np.random.randint(0, 100, (512, 512), dtype=np.uint16)
        tifffile.imwrite(f.name, data)
        yield Path(f.name)
        # Cleanup
        Path(f.name).unlink()
