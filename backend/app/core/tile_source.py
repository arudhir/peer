"""Abstract tile source interface and implementations."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Protocol

import numpy as np


class TileSource(Protocol):
    """Protocol for tile sources.

    This defines the interface that all tile sources must implement,
    whether they're backed by TIFF, Zarr, or other formats.
    """

    def get_channel_names(self) -> list[str]:
        """Get list of available channel names.

        Returns:
            List of channel names
        """
        ...

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
        ...

    def get_full_res_shape(self) -> tuple[int, int]:
        """Get shape of full resolution image.

        Returns:
            (height, width) tuple
        """
        ...

    def get_levels(self) -> list[int]:
        """Get available pyramid levels.

        Returns:
            List of available levels (0 = full res)
        """
        ...

    def get_level_shape(self, level: int) -> tuple[int, int]:
        """Get shape at a specific pyramid level.

        Args:
            level: Pyramid level

        Returns:
            (height, width) at that level
        """
        ...

    def close(self):
        """Close any open resources."""
        ...


class BaseTileSource(ABC):
    """Base class for tile sources."""

    def __init__(self, path: str):
        """Initialize tile source.

        Args:
            path: Path to image (local or S3)
        """
        self.path = path

    @abstractmethod
    def get_channel_names(self) -> list[str]:
        """Get list of available channel names."""
        pass

    @abstractmethod
    def get_tile(
        self, channel: str, level: int, x: int, y: int, tile_size: int = 256
    ) -> np.ndarray:
        """Get a tile from the image."""
        pass

    @abstractmethod
    def get_full_res_shape(self) -> tuple[int, int]:
        """Get shape of full resolution image."""
        pass

    @abstractmethod
    def get_levels(self) -> list[int]:
        """Get available pyramid levels."""
        pass

    def get_level_shape(self, level: int) -> tuple[int, int]:
        """Get shape at a specific pyramid level.

        Args:
            level: Pyramid level

        Returns:
            (height, width) at that level
        """
        h, w = self.get_full_res_shape()
        scale = 2**level
        return (h // scale, w // scale)

    @abstractmethod
    def close(self):
        """Close any open resources."""
        pass

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def _extract_tile(
    array: np.ndarray,
    x: int,
    y: int,
    tile_size: int,
) -> np.ndarray:
    """Extract a tile from a 2D array.

    Args:
        array: 2D numpy array
        x: Tile X coordinate (in tiles)
        y: Tile Y coordinate (in tiles)
        tile_size: Size of tile in pixels

    Returns:
        Tile array, padded if necessary
    """
    h, w = array.shape
    x_start = x * tile_size
    y_start = y * tile_size
    x_end = min(x_start + tile_size, w)
    y_end = min(y_start + tile_size, h)

    # Extract tile
    tile = array[y_start:y_end, x_start:x_end]

    # Pad if necessary
    if tile.shape[0] < tile_size or tile.shape[1] < tile_size:
        padded = np.zeros((tile_size, tile_size), dtype=tile.dtype)
        padded[: tile.shape[0], : tile.shape[1]] = tile
        return padded

    return tile


def downsample_array(array: np.ndarray, factor: int) -> np.ndarray:
    """Downsample a 2D array by a factor.

    Args:
        array: 2D numpy array
        factor: Downsampling factor

    Returns:
        Downsampled array
    """
    if factor == 1:
        return array

    h, w = array.shape
    new_h = h // factor
    new_w = w // factor

    # Crop to multiple of factor
    cropped = array[: new_h * factor, : new_w * factor]

    # Reshape and average
    reshaped = cropped.reshape(new_h, factor, new_w, factor)
    return reshaped.mean(axis=(1, 3)).astype(array.dtype)
