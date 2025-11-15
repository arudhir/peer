"""Unified image loader abstraction over TIFF and Zarr."""

import tempfile
from pathlib import Path
from typing import Optional, Union

import s3fs
from loguru import logger

from app.config import config
from app.core.cache import get_cache
from app.core.tiff_source import MaskTiffSource, TiffTileSource
from app.core.tile_source import TileSource
from app.core.zarr_source import ZarrTileSource


class ImageLoader:
    """Unified loader for microscopy images.

    Abstracts over:
    - OME-TIFF files (local or S3)
    - OME-Zarr files (local or S3)
    - Automatic caching
    - Format detection
    """

    def __init__(self):
        """Initialize image loader."""
        self.cache = get_cache() if config.cache.enabled else None

        # Initialize S3 filesystem
        self.s3fs = self._init_s3fs()

    def _init_s3fs(self) -> Optional[s3fs.S3FileSystem]:
        """Initialize S3 filesystem.

        Returns:
            S3FileSystem instance or None if not configured
        """
        try:
            s3_config = {
                "key": config.s3.access_key_id,
                "secret": config.s3.secret_access_key,
                "client_kwargs": {"region_name": config.s3.region},
            }

            if config.s3.endpoint_url:
                s3_config["client_kwargs"]["endpoint_url"] = config.s3.endpoint_url
                s3_config["use_ssl"] = config.s3.use_ssl

            return s3fs.S3FileSystem(**s3_config)
        except Exception as e:
            logger.warning(f"Failed to initialize S3: {e}")
            return None

    def _is_s3_path(self, path: str) -> bool:
        """Check if path is an S3 path.

        Args:
            path: Path to check

        Returns:
            True if S3 path
        """
        return path.startswith("s3://")

    def _get_local_path(self, s3_path: str) -> Path:
        """Get or download file from S3 to local cache.

        Args:
            s3_path: S3 path (e.g., s3://bucket/key)

        Returns:
            Local path to cached file
        """
        if not self._is_s3_path(s3_path):
            return Path(s3_path)

        if self.s3fs is None:
            raise ValueError("S3 not configured")

        # Check cache first
        if self.cache:
            cache_key = self.cache.get_file_key(s3_path)
            file_cache_dir = Path(self.cache.cache_root) / "files"
            file_cache_dir.mkdir(exist_ok=True, parents=True)
            cached_file = file_cache_dir / cache_key

            if cached_file.exists():
                logger.debug(f"Cache hit for {s3_path}")
                return cached_file

        # Download from S3
        logger.info(f"Downloading {s3_path}")

        # Create temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(s3_path).suffix) as tmp:
            tmp_path = Path(tmp.name)

        try:
            self.s3fs.get(s3_path, str(tmp_path))

            # Cache if enabled
            if self.cache:
                cached_path = self.cache.cache_file(s3_path, tmp_path)
                if cached_path:
                    # Remove temp file
                    tmp_path.unlink()
                    return cached_path

            return tmp_path

        except Exception as e:
            if tmp_path.exists():
                tmp_path.unlink()
            raise RuntimeError(f"Failed to download {s3_path}: {e}")

    def _is_zarr(self, path: str) -> bool:
        """Check if path is a Zarr store.

        Args:
            path: Path to check

        Returns:
            True if Zarr store
        """
        # Zarr stores are directories, not files
        if self._is_s3_path(path):
            # Check for .zarray or .zgroup
            try:
                return (
                    self.s3fs.exists(f"{path}/.zarray")
                    or self.s3fs.exists(f"{path}/.zgroup")
                )
            except Exception:
                return False
        else:
            p = Path(path)
            return p.is_dir() and (
                (p / ".zarray").exists() or (p / ".zgroup").exists()
            )

    def load_image(
        self,
        path: str,
        channel_names: Optional[list[str]] = None,
    ) -> TileSource:
        """Load an image from a path.

        Args:
            path: Path to image (local or S3, TIFF or Zarr)
            channel_names: Optional channel names

        Returns:
            TileSource instance
        """
        logger.info(f"Loading image: {path}")

        # Determine format
        if config.features.use_zarr and self._is_zarr(path):
            logger.debug("Detected Zarr format")
            return ZarrTileSource(path, channel_names=channel_names)
        else:
            logger.debug("Using TIFF format")
            # Get local path (download if needed)
            local_path = self._get_local_path(path)
            return TiffTileSource(str(local_path), channel_names=channel_names)

    def load_mask(
        self,
        path: str,
        mask_name: Optional[str] = None,
    ) -> TileSource:
        """Load a mask from a path.

        Args:
            path: Path to mask TIFF
            mask_name: Name of the mask

        Returns:
            TileSource instance for mask
        """
        logger.info(f"Loading mask: {path}")

        # Masks are typically TIFF
        local_path = self._get_local_path(path)
        return MaskTiffSource(str(local_path), mask_name=mask_name)

    def get_well_path(
        self,
        experiment: str,
        sequence: str,
        well: str,
        file_type: str = "image.ome.tiff",
    ) -> str:
        """Construct S3 path for a well.

        Args:
            experiment: Experiment ID
            sequence: Sequence ID
            well: Well ID (e.g., A1)
            file_type: File type (e.g., "image.ome.tiff", "nuclei_mask.tif")

        Returns:
            S3 path
        """
        bucket = config.s3.bucket_name

        # Handle masks and processed images
        if "mask" in file_type:
            return f"s3://{bucket}/{experiment}/{sequence}/{well}/masks/{file_type}"
        elif file_type in ["nuclei.tif", "actin.tif", "mito_mp.tif", "mito_tot.tif"]:
            return f"s3://{bucket}/{experiment}/{sequence}/{well}/processed/{file_type}"
        else:
            return f"s3://{bucket}/{experiment}/{sequence}/{well}/{file_type}"


# Global loader instance
_loader_instance: Optional[ImageLoader] = None


def get_loader() -> ImageLoader:
    """Get global image loader instance.

    Returns:
        ImageLoader instance
    """
    global _loader_instance
    if _loader_instance is None:
        _loader_instance = ImageLoader()
    return _loader_instance
