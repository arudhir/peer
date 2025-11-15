"""TIFF-based tile source implementation."""

from pathlib import Path
from typing import Optional

import numpy as np
import tifffile
from loguru import logger

from app.core.tile_source import BaseTileSource, _extract_tile, downsample_array


class TiffTileSource(BaseTileSource):
    """Tile source for OME-TIFF files.

    Supports:
    - Multi-channel TIFFs
    - Lazy loading via memory mapping
    - On-the-fly downsampling for multi-scale access
    """

    def __init__(self, path: str, channel_names: Optional[list[str]] = None):
        """Initialize TIFF tile source.

        Args:
            path: Path to TIFF file (local or will be cached from S3)
            channel_names: Optional list of channel names
        """
        super().__init__(path)
        self._tiff = None
        self._channel_names = channel_names
        self._shape = None
        self._num_channels = None
        self._data = None

    def _open(self):
        """Open TIFF file lazily."""
        if self._tiff is None:
            logger.debug(f"Opening TIFF: {self.path}")
            self._tiff = tifffile.TiffFile(self.path)

            # Get shape information
            # Assuming shape is (C, Y, X) or (Y, X) for single channel
            series = self._tiff.series[0]
            shape = series.shape

            if len(shape) == 2:
                # Single channel
                self._num_channels = 1
                self._shape = shape  # (H, W)
            elif len(shape) == 3:
                # Multi-channel (C, H, W)
                self._num_channels = shape[0]
                self._shape = shape[1:]  # (H, W)
            else:
                raise ValueError(f"Unsupported TIFF shape: {shape}")

            # Load data with memory mapping for efficiency
            self._data = series.asarray()

            logger.info(
                f"Opened TIFF: {self._num_channels} channels, "
                f"shape {self._shape}, dtype {self._data.dtype}"
            )

    def get_channel_names(self) -> list[str]:
        """Get list of available channel names."""
        self._open()

        if self._channel_names:
            return self._channel_names

        # Default channel names
        return [f"channel_{i}" for i in range(self._num_channels)]

    def get_tile(
        self, channel: str, level: int, x: int, y: int, tile_size: int = 256
    ) -> np.ndarray:
        """Get a tile from the image.

        Args:
            channel: Channel name or index
            level: Pyramid level (0 = full resolution)
            x: Tile X coordinate (in tiles)
            y: Tile Y coordinate (in tiles)
            tile_size: Size of tile in pixels

        Returns:
            Tile as numpy array
        """
        self._open()

        # Convert channel name to index
        if isinstance(channel, str):
            try:
                channel_names = self.get_channel_names()
                channel_idx = channel_names.index(channel)
            except ValueError:
                # Try as integer
                try:
                    channel_idx = int(channel)
                except ValueError:
                    raise ValueError(f"Unknown channel: {channel}")
        else:
            channel_idx = channel

        # Get channel data
        if self._num_channels == 1:
            channel_data = self._data
        else:
            channel_data = self._data[channel_idx]

        # Downsample if needed
        if level > 0:
            scale = 2**level
            channel_data = downsample_array(channel_data, scale)

        # Extract tile
        return _extract_tile(channel_data, x, y, tile_size)

    def get_full_res_shape(self) -> tuple[int, int]:
        """Get shape of full resolution image."""
        self._open()
        return self._shape

    def get_levels(self) -> list[int]:
        """Get available pyramid levels.

        For TIFF without pyramids, we emulate levels via downsampling.
        """
        self._open()
        h, w = self._shape

        # Calculate number of levels based on image size
        max_dim = max(h, w)
        num_levels = 0
        while max_dim > 256:
            max_dim //= 2
            num_levels += 1

        return list(range(num_levels + 1))

    def close(self):
        """Close TIFF file."""
        if self._tiff is not None:
            self._tiff.close()
            self._tiff = None
            self._data = None


class MaskTiffSource(TiffTileSource):
    """Specialized tile source for mask TIFFs.

    Masks are typically single-channel label images.
    """

    def __init__(self, path: str, mask_name: Optional[str] = None):
        """Initialize mask TIFF source.

        Args:
            path: Path to mask TIFF
            mask_name: Name of the mask
        """
        channel_names = [mask_name] if mask_name else ["mask"]
        super().__init__(path, channel_names=channel_names)
