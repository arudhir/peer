"""Tests for tile sources."""

import numpy as np
import pytest

from app.core.tiff_source import TiffTileSource
from app.core.tile_source import downsample_array, _extract_tile


def test_downsample_array():
    """Test array downsampling."""
    # Create test array
    array = np.arange(16).reshape(4, 4)

    # Downsample by 2
    downsampled = downsample_array(array, 2)

    assert downsampled.shape == (2, 2)


def test_extract_tile():
    """Test tile extraction."""
    # Create test array
    array = np.arange(256).reshape(16, 16)

    # Extract tile
    tile = _extract_tile(array, x=0, y=0, tile_size=8)

    assert tile.shape == (8, 8)
    assert tile[0, 0] == array[0, 0]


def test_extract_tile_with_padding():
    """Test tile extraction with padding."""
    # Create test array
    array = np.arange(100).reshape(10, 10)

    # Extract tile that needs padding
    tile = _extract_tile(array, x=1, y=1, tile_size=8)

    assert tile.shape == (8, 8)
    # Check that padding is zeros
    assert tile[2:, :].sum() == 0  # Bottom rows should be padded


def test_tiff_tile_source(sample_tiff):
    """Test TIFF tile source."""
    source = TiffTileSource(str(sample_tiff))

    # Test properties
    channels = source.get_channel_names()
    assert len(channels) == 4

    shape = source.get_full_res_shape()
    assert shape == (512, 512)

    levels = source.get_levels()
    assert 0 in levels

    # Get a tile
    tile = source.get_tile(channels[0], level=0, x=0, y=0, tile_size=256)
    assert tile.shape == (256, 256)

    # Cleanup
    source.close()


def test_tiff_tile_source_context_manager(sample_tiff):
    """Test TIFF tile source as context manager."""
    with TiffTileSource(str(sample_tiff)) as source:
        channels = source.get_channel_names()
        assert len(channels) == 4

    # Should be closed after context
    assert source._tiff is None
