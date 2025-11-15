"""Tests for cache module."""

import tempfile
from pathlib import Path

import pytest

from app.core.cache import ImageCache


def test_cache_initialization():
    """Test cache initialization."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = ImageCache(tmpdir, max_size_bytes=1024 * 1024 * 100)  # 100 MB

        assert cache.cache_root == Path(tmpdir)
        assert cache.cache is not None


def test_cache_set_get():
    """Test cache set and get."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = ImageCache(tmpdir, max_size_bytes=1024 * 1024 * 100)

        key = "test_key"
        value = b"test_value"

        # Set
        assert cache.set(key, value)

        # Get
        retrieved = cache.get(key)
        assert retrieved == value


def test_cache_tile_key():
    """Test tile key generation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = ImageCache(tmpdir, max_size_bytes=1024 * 1024 * 100)

        key1 = cache.get_tile_key("exp1", "seq1", "A1", "nuclei", 0, 0, 0)
        key2 = cache.get_tile_key("exp1", "seq1", "A1", "nuclei", 0, 0, 0)
        key3 = cache.get_tile_key("exp1", "seq1", "A1", "actin", 0, 0, 0)

        # Same parameters should give same key
        assert key1 == key2

        # Different parameters should give different key
        assert key1 != key3


def test_cache_stats():
    """Test cache statistics."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = ImageCache(tmpdir, max_size_bytes=1024 * 1024 * 100)

        # Initially empty
        stats = cache.stats()
        assert stats["count"] == 0

        # Add items
        cache.set("key1", b"value1")
        cache.set("key2", b"value2")

        stats = cache.stats()
        assert stats["count"] == 2


def test_cache_clear():
    """Test cache clearing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = ImageCache(tmpdir, max_size_bytes=1024 * 1024 * 100)

        # Add items
        cache.set("key1", b"value1")
        cache.set("key2", b"value2")

        assert cache.stats()["count"] == 2

        # Clear
        cache.clear()

        assert cache.stats()["count"] == 0
