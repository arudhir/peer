"""Tests for composite generation."""

import numpy as np
import pytest

from app.core.composite import normalize_image, create_mask_overlay


def test_normalize_image_normalized_mode():
    """Test image normalization in normalized mode."""
    # Create test image
    image = np.random.randint(0, 4096, (100, 100), dtype=np.uint16)

    # Normalize
    normalized = normalize_image(image, percentile_range=(1, 99), mode="normalized")

    assert normalized.dtype == np.float32
    assert normalized.min() >= 0
    assert normalized.max() <= 1


def test_normalize_image_raw_mode():
    """Test image normalization in raw mode."""
    # Create test image
    image = np.random.randint(0, 4096, (100, 100), dtype=np.uint16)

    # Normalize
    normalized = normalize_image(image, mode="raw")

    assert normalized.dtype == np.float32
    assert normalized.min() >= 0
    assert normalized.max() <= 1


def test_create_mask_overlay_binary():
    """Test creating binary mask overlay."""
    # Create binary mask
    mask = np.zeros((100, 100), dtype=np.uint16)
    mask[25:75, 25:75] = 1

    # Create overlay
    overlay = create_mask_overlay(mask, is_label_mask=False, opacity=0.5)

    assert overlay.shape == (100, 100, 4)
    assert overlay.dtype == np.uint8

    # Check that masked region has alpha
    assert overlay[50, 50, 3] > 0
    # Check that unmasked region has no alpha
    assert overlay[10, 10, 3] == 0


def test_create_mask_overlay_label():
    """Test creating label mask overlay."""
    # Create label mask
    mask = np.zeros((100, 100), dtype=np.uint16)
    mask[10:20, 10:20] = 1
    mask[30:40, 30:40] = 2
    mask[50:60, 50:60] = 3

    # Create overlay
    overlay = create_mask_overlay(mask, is_label_mask=True, opacity=0.5)

    assert overlay.shape == (100, 100, 4)
    assert overlay.dtype == np.uint8

    # Check that different labels have colors
    assert overlay[15, 15, 3] > 0
    assert overlay[35, 35, 3] > 0
    assert overlay[55, 55, 3] > 0
