"""Zarr-based tile source implementation."""

from pathlib import Path
from typing import Optional

import numpy as np
import zarr
from loguru import logger
from ome_zarr.io import parse_url
from ome_zarr.reader import Reader

from app.core.tile_source import BaseTileSource, _extract_tile


class ZarrTileSource(BaseTileSource):
    """Tile source for OME-Zarr files.

    Supports:
    - Multi-scale pyramids
    - Multi-channel data
    - Chunked lazy loading
    - S3-backed Zarr stores
    """

    def __init__(self, path: str, channel_names: Optional[list[str]] = None):
        """Initialize Zarr tile source.

        Args:
            path: Path to Zarr store (local or S3)
            channel_names: Optional list of channel names
        """
        super().__init__(path)
        self._store = None
        self._root = None
        self._pyramid = None
        self._channel_names = channel_names
        self._metadata = None

    def _open(self):
        """Open Zarr store lazily."""
        if self._root is None:
            logger.debug(f"Opening Zarr: {self.path}")

            # Parse OME-Zarr
            location = parse_url(self.path)
            reader = Reader(location)

            # Get first node (assumes single image)
            nodes = list(reader())
            if not nodes:
                raise ValueError(f"No OME-Zarr data found at {self.path}")

            node = nodes[0]
            self._pyramid = node.data  # List of arrays at different resolutions
            self._metadata = node.metadata

            # Extract channel names from metadata if available
            if not self._channel_names and self._metadata:
                omero = self._metadata.get("omero", {})
                channels = omero.get("channels", [])
                if channels:
                    self._channel_names = [ch.get("label", f"channel_{i}")
                                          for i, ch in enumerate(channels)]

            logger.info(
                f"Opened Zarr: {len(self._pyramid)} levels, "
                f"shape {self._pyramid[0].shape}"
            )

    def get_channel_names(self) -> list[str]:
        """Get list of available channel names."""
        self._open()

        if self._channel_names:
            return self._channel_names

        # Infer from shape
        shape = self._pyramid[0].shape
        if len(shape) >= 3:
            # Assume first dimension is channels for multi-channel
            num_channels = shape[0] if len(shape) == 3 else shape[-3]
            return [f"channel_{i}" for i in range(num_channels)]

        return ["channel_0"]

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
                try:
                    channel_idx = int(channel)
                except ValueError:
                    raise ValueError(f"Unknown channel: {channel}")
        else:
            channel_idx = channel

        # Get array at requested level
        if level >= len(self._pyramid):
            level = len(self._pyramid) - 1

        array = self._pyramid[level]

        # Handle different shapes
        # Typical OME-Zarr shapes: (C, Y, X) or (T, C, Z, Y, X)
        # We assume single timepoint, single Z
        shape = array.shape

        if len(shape) == 2:
            # (Y, X) - single channel
            channel_data = array
        elif len(shape) == 3:
            # (C, Y, X)
            channel_data = array[channel_idx]
        elif len(shape) == 5:
            # (T, C, Z, Y, X) - take first T and Z
            channel_data = array[0, channel_idx, 0]
        else:
            raise ValueError(f"Unsupported Zarr shape: {shape}")

        # Extract tile (this triggers chunk loading)
        return _extract_tile(channel_data, x, y, tile_size)

    def get_full_res_shape(self) -> tuple[int, int]:
        """Get shape of full resolution image."""
        self._open()

        shape = self._pyramid[0].shape

        # Extract Y, X dimensions
        if len(shape) == 2:
            return shape
        elif len(shape) == 3:
            return shape[1:]  # (C, Y, X) -> (Y, X)
        elif len(shape) == 5:
            return shape[3:]  # (T, C, Z, Y, X) -> (Y, X)
        else:
            raise ValueError(f"Unsupported Zarr shape: {shape}")

    def get_levels(self) -> list[int]:
        """Get available pyramid levels."""
        self._open()
        return list(range(len(self._pyramid)))

    def get_level_shape(self, level: int) -> tuple[int, int]:
        """Get shape at a specific pyramid level."""
        self._open()

        if level >= len(self._pyramid):
            level = len(self._pyramid) - 1

        shape = self._pyramid[level].shape

        # Extract Y, X dimensions
        if len(shape) == 2:
            return shape
        elif len(shape) == 3:
            return shape[1:]
        elif len(shape) == 5:
            return shape[3:]
        else:
            raise ValueError(f"Unsupported Zarr shape: {shape}")

    def close(self):
        """Close Zarr store."""
        self._root = None
        self._pyramid = None
