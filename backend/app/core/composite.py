"""Composite image generation for multi-channel visualization."""

from typing import Literal, Optional

import numpy as np
from loguru import logger

from app.core.tile_source import TileSource


# Color mappings for channels (RGB)
CHANNEL_COLORS = {
    "nuclei": (0, 0, 255),  # Blue
    "actin": (0, 255, 0),  # Green
    "mito_mp": (255, 0, 255),  # Magenta
    "mito_tot": (255, 255, 0),  # Yellow
}


def normalize_image(
    image: np.ndarray,
    percentile_range: tuple[float, float] = (1, 99),
    mode: Literal["normalized", "raw"] = "normalized",
) -> np.ndarray:
    """Normalize image intensities.

    Args:
        image: Input image array
        percentile_range: Percentile range for normalization
        mode: "normalized" for percentile-based, "raw" for minimal clipping

    Returns:
        Normalized image (float32, 0-1 range)
    """
    image = image.astype(np.float32)

    if mode == "normalized":
        # Percentile-based normalization
        p_low, p_high = np.percentile(image, percentile_range)

        if p_high > p_low:
            image = (image - p_low) / (p_high - p_low)
            image = np.clip(image, 0, 1)
        else:
            # Constant image
            image = np.zeros_like(image)

    else:  # raw mode
        # Just scale to [0, 1] based on dtype max
        if image.max() > 0:
            image = image / image.max()

    return image


def create_composite(
    tile_source: TileSource,
    level: int,
    x: int,
    y: int,
    tile_size: int = 256,
    mode: Literal["normalized", "raw"] = "normalized",
    percentile_range: tuple[float, float] = (1, 99),
    channel_opacities: Optional[dict[str, float]] = None,
    channel_visibility: Optional[dict[str, bool]] = None,
) -> np.ndarray:
    """Create RGB composite from multi-channel image.

    Args:
        tile_source: Tile source for the image
        level: Pyramid level
        x: Tile X coordinate
        y: Tile Y coordinate
        tile_size: Tile size in pixels
        mode: Intensity mode ("normalized" or "raw")
        percentile_range: Percentile range for normalized mode
        channel_opacities: Dict of channel opacities (0-1)
        channel_visibility: Dict of channel visibility flags

    Returns:
        RGB composite image (uint8)
    """
    # Initialize RGB composite
    composite = np.zeros((tile_size, tile_size, 3), dtype=np.float32)

    # Default opacities and visibility
    if channel_opacities is None:
        channel_opacities = {}
    if channel_visibility is None:
        channel_visibility = {}

    # Get available channels
    channel_names = tile_source.get_channel_names()

    # Process each channel
    for channel_name in channel_names:
        # Check visibility
        if not channel_visibility.get(channel_name, True):
            continue

        # Get channel color
        color = CHANNEL_COLORS.get(channel_name)
        if color is None:
            logger.warning(f"No color mapping for channel: {channel_name}")
            continue

        # Get tile
        try:
            tile = tile_source.get_tile(channel_name, level, x, y, tile_size)

            # Normalize
            tile_norm = normalize_image(tile, percentile_range, mode)

            # Apply color and opacity
            opacity = channel_opacities.get(channel_name, 1.0)

            for i, c in enumerate(color):
                if c > 0:
                    composite[:, :, i] += tile_norm * (c / 255.0) * opacity

        except Exception as e:
            logger.error(f"Error processing channel {channel_name}: {e}")
            continue

    # Clip and convert to uint8
    composite = np.clip(composite, 0, 1)
    composite = (composite * 255).astype(np.uint8)

    return composite


def create_mask_overlay(
    mask_tile: np.ndarray,
    is_label_mask: bool = False,
    opacity: float = 0.5,
    color: Optional[tuple[int, int, int]] = None,
) -> np.ndarray:
    """Create colored overlay from mask.

    Args:
        mask_tile: Mask array (binary or label)
        is_label_mask: If True, use random colors per label
        opacity: Overlay opacity (0-1)
        color: Color for binary masks (RGB)

    Returns:
        RGBA overlay (uint8)
    """
    h, w = mask_tile.shape
    overlay = np.zeros((h, w, 4), dtype=np.uint8)

    if is_label_mask:
        # Label mask - assign random color per label
        labels = np.unique(mask_tile)
        labels = labels[labels != 0]  # Exclude background

        # Generate random colors for each label
        np.random.seed(42)  # Reproducible colors
        for label in labels:
            mask = mask_tile == label
            color_rgb = np.random.randint(0, 256, size=3)
            overlay[mask, :3] = color_rgb
            overlay[mask, 3] = int(opacity * 255)

    else:
        # Binary mask
        if color is None:
            color = (255, 0, 0)  # Red default

        mask = mask_tile > 0
        overlay[mask, :3] = color
        overlay[mask, 3] = int(opacity * 255)

    return overlay


def blend_composite_with_masks(
    composite: np.ndarray,
    mask_overlays: list[np.ndarray],
) -> np.ndarray:
    """Blend composite image with mask overlays.

    Args:
        composite: RGB composite (uint8)
        mask_overlays: List of RGBA mask overlays

    Returns:
        Blended RGB image (uint8)
    """
    # Convert composite to RGBA
    h, w = composite.shape[:2]
    result = np.zeros((h, w, 4), dtype=np.float32)
    result[:, :, :3] = composite.astype(np.float32)
    result[:, :, 3] = 255

    # Alpha blend each mask
    for mask_overlay in mask_overlays:
        alpha = mask_overlay[:, :, 3:4].astype(np.float32) / 255.0
        mask_rgb = mask_overlay[:, :, :3].astype(np.float32)

        result[:, :, :3] = result[:, :, :3] * (1 - alpha) + mask_rgb * alpha

    return result[:, :, :3].astype(np.uint8)
