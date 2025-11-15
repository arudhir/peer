"""Disk-based LRU cache for image data."""

import hashlib
import os
from pathlib import Path
from typing import Optional, Union

from diskcache import Cache
from loguru import logger


class ImageCache:
    """Disk-based LRU cache for image tiles and chunks.

    This cache stores:
    - Raw TIFF files or memory-mappable equivalents
    - OME-Zarr chunks
    - Pre-computed tiles
    """

    def __init__(
        self,
        cache_root: Union[str, Path],
        max_size_bytes: int,
        eviction_policy: str = "least-recently-used",
    ):
        """Initialize the image cache.

        Args:
            cache_root: Root directory for cache storage
            max_size_bytes: Maximum cache size in bytes
            eviction_policy: Eviction policy (default: LRU)
        """
        self.cache_root = Path(cache_root).expanduser()
        self.cache_root.mkdir(parents=True, exist_ok=True)

        # Initialize diskcache with size limit
        self.cache = Cache(
            str(self.cache_root),
            size_limit=max_size_bytes,
            eviction_policy=eviction_policy,
        )

        logger.info(
            f"Initialized cache at {self.cache_root} "
            f"with max size {max_size_bytes / 1e9:.2f} GB"
        )

    def _make_key(self, *args) -> str:
        """Create a cache key from arguments.

        Args:
            *args: Components to create key from

        Returns:
            SHA256 hash as hex string
        """
        key_string = ":".join(str(arg) for arg in args)
        return hashlib.sha256(key_string.encode()).hexdigest()

    def get(self, key: str) -> Optional[bytes]:
        """Get item from cache.

        Args:
            key: Cache key

        Returns:
            Cached bytes or None if not found
        """
        try:
            return self.cache.get(key)
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None

    def set(self, key: str, value: bytes, tag: Optional[str] = None) -> bool:
        """Set item in cache.

        Args:
            key: Cache key
            value: Bytes to cache
            tag: Optional tag for organization/eviction

        Returns:
            True if successful
        """
        try:
            self.cache.set(key, value, tag=tag)
            return True
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False

    def get_tile_key(
        self,
        experiment: str,
        sequence: str,
        well: str,
        channel: str,
        level: int,
        x: int,
        y: int,
    ) -> str:
        """Generate cache key for a tile.

        Args:
            experiment: Experiment ID
            sequence: Sequence ID
            well: Well ID (e.g., A1)
            channel: Channel name
            level: Pyramid level
            x: Tile X coordinate
            y: Tile Y coordinate

        Returns:
            Cache key
        """
        return self._make_key("tile", experiment, sequence, well, channel, level, x, y)

    def get_file_key(self, s3_path: str) -> str:
        """Generate cache key for a file.

        Args:
            s3_path: S3 path to file

        Returns:
            Cache key
        """
        return self._make_key("file", s3_path)

    def get_zarr_chunk_key(self, zarr_path: str, chunk_coords: tuple) -> str:
        """Generate cache key for a Zarr chunk.

        Args:
            zarr_path: Path to Zarr array
            chunk_coords: Chunk coordinates

        Returns:
            Cache key
        """
        return self._make_key("zarr", zarr_path, *chunk_coords)

    def cache_file(self, s3_path: str, local_path: Path) -> Optional[Path]:
        """Cache a file and return cached path.

        Args:
            s3_path: S3 path
            local_path: Local path to cache

        Returns:
            Path to cached file or None on error
        """
        key = self.get_file_key(s3_path)

        # Create a subdirectory for files
        file_cache_dir = self.cache_root / "files"
        file_cache_dir.mkdir(exist_ok=True)

        # Use hash as filename
        cached_file = file_cache_dir / key

        try:
            # If file exists in cache, return it
            if cached_file.exists():
                logger.debug(f"Cache hit for file: {s3_path}")
                # Touch to update LRU
                self.cache.touch(key)
                return cached_file

            # Read file and cache it
            with open(local_path, "rb") as f:
                data = f.read()

            # Store in diskcache for LRU tracking
            self.cache.set(key, s3_path, tag="file")

            # Also save to file for memory mapping
            with open(cached_file, "wb") as f:
                f.write(data)

            logger.debug(f"Cached file: {s3_path}")
            return cached_file

        except Exception as e:
            logger.error(f"Error caching file {s3_path}: {e}")
            return None

    def clear(self):
        """Clear all cache entries."""
        self.cache.clear()
        logger.info("Cache cleared")

    def stats(self) -> dict:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        return {
            "size": self.cache.volume(),
            "count": len(self.cache),
            "max_size": self.cache.size_limit,
            "hit_rate": getattr(self.cache, "hit_rate", 0),
        }


# Global cache instance (initialized in main.py)
_cache_instance: Optional[ImageCache] = None


def get_cache() -> ImageCache:
    """Get global cache instance.

    Returns:
        ImageCache instance
    """
    global _cache_instance
    if _cache_instance is None:
        from app.config import config

        max_size = config.cache.max_size_gb * 1024**3  # Convert GB to bytes
        _cache_instance = ImageCache(
            cache_root=config.cache.root_path,
            max_size_bytes=int(max_size),
            eviction_policy=config.cache.eviction_policy,
        )
    return _cache_instance
