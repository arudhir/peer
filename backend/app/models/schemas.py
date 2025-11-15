"""Pydantic schemas for API request/response models."""

from typing import Literal, Optional

from pydantic import BaseModel, Field


# ============================================================================
# Metadata Models
# ============================================================================


class ExperimentInfo(BaseModel):
    """Information about an experiment."""

    experiment_id: str
    name: str
    description: Optional[str] = None
    num_sequences: int


class SequenceInfo(BaseModel):
    """Information about a sequence."""

    sequence_id: str
    experiment_id: str
    name: str
    num_wells: int


class WellMetadata(BaseModel):
    """Metadata for a well in the plate."""

    well_id: str = Field(..., description="Well ID (e.g., A1)")
    row: str = Field(..., description="Row letter (A-H)")
    col: int = Field(..., description="Column number (1-12)")
    has_image: bool = Field(True, description="Has main image")
    has_masks: bool = Field(False, description="Has mask data")
    has_processed: bool = Field(False, description="Has processed channels")
    image_path: Optional[str] = None
    preview_path: Optional[str] = None


class PlateMetadata(BaseModel):
    """Metadata for a complete plate."""

    experiment_id: str
    sequence_id: str
    wells: list[WellMetadata]
    rows: int = 8
    cols: int = 12


# ============================================================================
# Channel and Mask Models
# ============================================================================


class ChannelInfo(BaseModel):
    """Information about an image channel."""

    name: str
    index: int
    color: Optional[tuple[int, int, int]] = None
    dtype: str
    shape: tuple[int, int]


class MaskInfo(BaseModel):
    """Information about a mask."""

    name: str
    path: str
    is_label_mask: bool = Field(
        False, description="True if label mask with multiple objects"
    )
    num_objects: Optional[int] = Field(None, description="Number of labeled objects")


class ImageInfo(BaseModel):
    """Complete image information."""

    experiment_id: str
    sequence_id: str
    well_id: str
    shape: tuple[int, int]
    num_levels: int
    channels: list[ChannelInfo]
    masks: list[MaskInfo]
    format: Literal["tiff", "zarr"]


# ============================================================================
# Tile Request/Response Models
# ============================================================================


class TileRequest(BaseModel):
    """Request for an image tile."""

    experiment: str
    sequence: str
    well: str
    channel: str
    level: int = Field(0, ge=0, description="Pyramid level (0 = full res)")
    x: int = Field(..., ge=0, description="Tile X coordinate")
    y: int = Field(..., ge=0, description="Tile Y coordinate")
    tile_size: int = Field(256, gt=0, le=1024)


class CompositeTileRequest(BaseModel):
    """Request for a composite tile."""

    experiment: str
    sequence: str
    well: str
    level: int = Field(0, ge=0)
    x: int = Field(..., ge=0)
    y: int = Field(..., ge=0)
    tile_size: int = Field(256, gt=0, le=1024)
    mode: Literal["normalized", "raw"] = "normalized"
    percentile_range: tuple[float, float] = Field((1, 99))
    channel_opacities: Optional[dict[str, float]] = None
    channel_visibility: Optional[dict[str, bool]] = None
    include_masks: bool = False
    mask_opacities: Optional[dict[str, float]] = None


class MaskTileRequest(BaseModel):
    """Request for a mask tile."""

    experiment: str
    sequence: str
    well: str
    mask_name: str
    level: int = Field(0, ge=0)
    x: int = Field(..., ge=0)
    y: int = Field(..., ge=0)
    tile_size: int = Field(256, gt=0, le=1024)


# ============================================================================
# Object Inspection Models (Future)
# ============================================================================


class ObjectMeasurement(BaseModel):
    """Measurements for a single object."""

    object_id: int
    label: int
    area: float
    mean_intensity: dict[str, float]
    centroid: tuple[float, float]
    bbox: tuple[int, int, int, int]  # (min_row, min_col, max_row, max_col)
    # TODO: Add more measurements as needed


class ObjectInspectionRequest(BaseModel):
    """Request to inspect an object in a mask."""

    experiment: str
    sequence: str
    well: str
    mask_name: str
    object_id: int


class ObjectInspectionResponse(BaseModel):
    """Response with object measurements."""

    object_id: int
    measurements: ObjectMeasurement
    # TODO: Link to external measurement database


# ============================================================================
# Cache Models
# ============================================================================


class CacheStats(BaseModel):
    """Cache statistics."""

    size_bytes: int
    size_gb: float
    num_items: int
    max_size_gb: float
    hit_rate: float


# ============================================================================
# Error Models
# ============================================================================


class ErrorResponse(BaseModel):
    """Error response."""

    error: str
    detail: Optional[str] = None
    path: Optional[str] = None
