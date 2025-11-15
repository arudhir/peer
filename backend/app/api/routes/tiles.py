"""Endpoints for serving image tiles."""

import io
from typing import Optional

import numpy as np
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from loguru import logger
from PIL import Image

from app.config import config
from app.core.cache import get_cache
from app.core.composite import (
    CHANNEL_COLORS,
    create_composite,
    create_mask_overlay,
    blend_composite_with_masks,
)
from app.core.image_loader import get_loader
from app.models.schemas import CacheStats

router = APIRouter()


def _encode_tile_png(tile: np.ndarray, format: str = "png") -> bytes:
    """Encode tile as PNG.

    Args:
        tile: Numpy array (grayscale or RGB)
        format: Output format (png, jpeg)

    Returns:
        Encoded image bytes
    """
    # Convert to appropriate format for PIL
    if tile.dtype != np.uint8:
        # Normalize to uint8
        if tile.max() > 0:
            tile = ((tile / tile.max()) * 255).astype(np.uint8)
        else:
            tile = tile.astype(np.uint8)

    # Create PIL image
    if len(tile.shape) == 2:
        # Grayscale
        img = Image.fromarray(tile, mode="L")
    elif len(tile.shape) == 3 and tile.shape[2] == 3:
        # RGB
        img = Image.fromarray(tile, mode="RGB")
    elif len(tile.shape) == 3 and tile.shape[2] == 4:
        # RGBA
        img = Image.fromarray(tile, mode="RGBA")
    else:
        raise ValueError(f"Unsupported tile shape: {tile.shape}")

    # Encode
    buffer = io.BytesIO()
    img.save(buffer, format=format.upper(), compress_level=config.tiles.compression_level)
    return buffer.getvalue()


@router.get("/experiments/{experiment}/sequences/{sequence}/wells/{well}/tile")
async def get_tile(
    experiment: str,
    sequence: str,
    well: str,
    channel: str = Query(..., description="Channel name"),
    level: int = Query(0, ge=0, description="Pyramid level"),
    x: int = Query(..., ge=0, description="Tile X coordinate"),
    y: int = Query(..., ge=0, description="Tile Y coordinate"),
    tile_size: int = Query(256, gt=0, le=1024, description="Tile size"),
    format: str = Query("png", description="Output format"),
):
    """Get a single channel tile.

    Args:
        experiment: Experiment ID
        sequence: Sequence ID
        well: Well ID
        channel: Channel name
        level: Pyramid level (0 = full resolution)
        x: Tile X coordinate
        y: Tile Y coordinate
        tile_size: Tile size in pixels
        format: Output format (png, jpeg)

    Returns:
        Encoded tile image
    """
    try:
        loader = get_loader()
        cache = get_cache() if config.cache.enabled else None

        # Check cache first
        cache_key = None
        if cache:
            cache_key = cache.get_tile_key(
                experiment, sequence, well, channel, level, x, y
            )
            cached_tile = cache.get(cache_key)
            if cached_tile:
                logger.debug(f"Cache hit for tile {well}/{channel}/{level}/{x}/{y}")
                return Response(content=cached_tile, media_type=f"image/{format}")

        # Load image
        image_path = loader.get_well_path(experiment, sequence, well, "image.ome.tiff")

        # Use context manager to ensure cleanup
        with loader.load_image(
            image_path, channel_names=["nuclei", "actin", "mito_mp", "mito_tot"]
        ) as tile_source:
            # Get tile
            tile = tile_source.get_tile(channel, level, x, y, tile_size)

            # Encode
            encoded = _encode_tile_png(tile, format)

            # Cache if enabled
            if cache and cache_key:
                cache.set(cache_key, encoded, tag="tile")

            return Response(content=encoded, media_type=f"image/{format}")

    except ValueError as e:
        logger.error(f"Invalid request: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting tile: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/experiments/{experiment}/sequences/{sequence}/wells/{well}/composite")
async def get_composite_tile(
    experiment: str,
    sequence: str,
    well: str,
    level: int = Query(0, ge=0),
    x: int = Query(..., ge=0),
    y: int = Query(..., ge=0),
    tile_size: int = Query(256, gt=0, le=1024),
    mode: str = Query("normalized", description="Intensity mode: normalized or raw"),
    format: str = Query("png"),
    # Optional channel controls
    nuclei_opacity: float = Query(1.0, ge=0.0, le=1.0),
    actin_opacity: float = Query(1.0, ge=0.0, le=1.0),
    mito_mp_opacity: float = Query(1.0, ge=0.0, le=1.0),
    mito_tot_opacity: float = Query(1.0, ge=0.0, le=1.0),
    nuclei_visible: bool = Query(True),
    actin_visible: bool = Query(True),
    mito_mp_visible: bool = Query(True),
    mito_tot_visible: bool = Query(True),
):
    """Get a composite RGB tile.

    Args:
        experiment: Experiment ID
        sequence: Sequence ID
        well: Well ID
        level: Pyramid level
        x: Tile X coordinate
        y: Tile Y coordinate
        tile_size: Tile size
        mode: Intensity mode (normalized or raw)
        format: Output format
        *_opacity: Per-channel opacity
        *_visible: Per-channel visibility

    Returns:
        Composite RGB tile
    """
    try:
        loader = get_loader()

        # Build opacity and visibility dicts
        channel_opacities = {
            "nuclei": nuclei_opacity,
            "actin": actin_opacity,
            "mito_mp": mito_mp_opacity,
            "mito_tot": mito_tot_opacity,
        }
        channel_visibility = {
            "nuclei": nuclei_visible,
            "actin": actin_visible,
            "mito_mp": mito_mp_visible,
            "mito_tot": mito_tot_visible,
        }

        # Load image
        image_path = loader.get_well_path(experiment, sequence, well, "image.ome.tiff")

        with loader.load_image(
            image_path, channel_names=["nuclei", "actin", "mito_mp", "mito_tot"]
        ) as tile_source:
            # Create composite
            composite = create_composite(
                tile_source,
                level,
                x,
                y,
                tile_size,
                mode=mode,
                channel_opacities=channel_opacities,
                channel_visibility=channel_visibility,
            )

            # Encode
            encoded = _encode_tile_png(composite, format)

            return Response(content=encoded, media_type=f"image/{format}")

    except Exception as e:
        logger.error(f"Error creating composite tile: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/experiments/{experiment}/sequences/{sequence}/wells/{well}/mask-tile")
async def get_mask_tile(
    experiment: str,
    sequence: str,
    well: str,
    mask_name: str = Query(..., description="Mask name"),
    level: int = Query(0, ge=0),
    x: int = Query(..., ge=0),
    y: int = Query(..., ge=0),
    tile_size: int = Query(256, gt=0, le=1024),
    opacity: float = Query(0.5, ge=0.0, le=1.0),
    is_label: bool = Query(False, description="Is this a label mask?"),
    format: str = Query("png"),
):
    """Get a mask tile with colored overlay.

    Args:
        experiment: Experiment ID
        sequence: Sequence ID
        well: Well ID
        mask_name: Name of mask file
        level: Pyramid level
        x: Tile X coordinate
        y: Tile Y coordinate
        tile_size: Tile size
        opacity: Mask opacity
        is_label: True if label mask with multiple objects
        format: Output format

    Returns:
        RGBA mask overlay
    """
    try:
        loader = get_loader()

        # Load mask
        mask_path = loader.get_well_path(experiment, sequence, well, mask_name)

        with loader.load_mask(mask_path, mask_name=mask_name) as mask_source:
            # Get mask tile
            mask_tile = mask_source.get_tile(mask_name, level, x, y, tile_size)

            # Create overlay
            overlay = create_mask_overlay(mask_tile, is_label_mask=is_label, opacity=opacity)

            # Encode as PNG with alpha
            encoded = _encode_tile_png(overlay, format)

            return Response(content=encoded, media_type=f"image/{format}")

    except Exception as e:
        logger.error(f"Error getting mask tile: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cache/stats", response_model=CacheStats)
async def get_cache_stats():
    """Get cache statistics.

    Returns:
        Cache statistics
    """
    try:
        if not config.cache.enabled:
            return CacheStats(
                size_bytes=0,
                size_gb=0.0,
                num_items=0,
                max_size_gb=0.0,
                hit_rate=0.0,
            )

        cache = get_cache()
        stats = cache.stats()

        return CacheStats(
            size_bytes=stats["size"],
            size_gb=stats["size"] / 1e9,
            num_items=stats["count"],
            max_size_gb=stats["max_size"] / 1e9,
            hit_rate=stats.get("hit_rate", 0.0),
        )

    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cache/clear")
async def clear_cache():
    """Clear the tile cache.

    Returns:
        Success message
    """
    try:
        if not config.cache.enabled:
            return {"message": "Cache not enabled"}

        cache = get_cache()
        cache.clear()

        return {"message": "Cache cleared successfully"}

    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))
