"""Endpoints for plate and image metadata."""

import pandas as pd
from fastapi import APIRouter, HTTPException
from loguru import logger

from app.config import config
from app.core.image_loader import get_loader
from app.models.schemas import (
    ChannelInfo,
    ImageInfo,
    MaskInfo,
    PlateMetadata,
    WellMetadata,
)

router = APIRouter()


def load_plate_metadata(experiment: str, sequence: str) -> pd.DataFrame:
    """Load plate metadata from CSV or S3.

    TODO: Implement actual metadata loading.

    Args:
        experiment: Experiment ID
        sequence: Sequence ID

    Returns:
        DataFrame with well metadata
    """
    # Stub implementation - generate sample plate
    rows = "ABCDEFGH"
    cols = range(1, 13)

    data = []
    for row in rows:
        for col in cols:
            well_id = f"{row}{col}"
            # Simulate some wells having data
            has_data = (ord(row) + col) % 3 != 0  # ~67% have data

            data.append(
                {
                    "well_id": well_id,
                    "row": row,
                    "col": col,
                    "has_image": has_data,
                    "has_masks": has_data,
                    "has_processed": has_data,
                    "image_path": f"s3://pb-ome-tiffs/{experiment}/{sequence}/{well_id}/image.ome.tiff"
                    if has_data
                    else None,
                    "preview_path": f"s3://pb-ome-tiffs/{experiment}/{sequence}/{well_id}/preview.png"
                    if has_data
                    else None,
                }
            )

    return pd.DataFrame(data)


@router.get(
    "/experiments/{experiment}/sequences/{sequence}/plate-metadata",
    response_model=PlateMetadata,
)
async def get_plate_metadata(experiment: str, sequence: str):
    """Get plate metadata including well status.

    Args:
        experiment: Experiment ID
        sequence: Sequence ID

    Returns:
        Plate metadata with well information
    """
    try:
        df = load_plate_metadata(experiment, sequence)

        wells = [
            WellMetadata(
                well_id=row["well_id"],
                row=row["row"],
                col=row["col"],
                has_image=row["has_image"],
                has_masks=row["has_masks"],
                has_processed=row["has_processed"],
                image_path=row["image_path"],
                preview_path=row["preview_path"],
            )
            for _, row in df.iterrows()
        ]

        return PlateMetadata(
            experiment_id=experiment,
            sequence_id=sequence,
            wells=wells,
        )

    except Exception as e:
        logger.error(f"Error loading plate metadata for {experiment}/{sequence}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/experiments/{experiment}/sequences/{sequence}/wells/{well}/info",
    response_model=ImageInfo,
)
async def get_image_info(experiment: str, sequence: str, well: str):
    """Get complete information about an image.

    Args:
        experiment: Experiment ID
        sequence: Sequence ID
        well: Well ID

    Returns:
        Image information including channels and masks
    """
    try:
        loader = get_loader()

        # Load main image
        image_path = loader.get_well_path(experiment, sequence, well, "image.ome.tiff")

        # Try to load image to get metadata
        # In production, this might come from cached metadata
        try:
            with loader.load_image(image_path, channel_names=["nuclei", "actin", "mito_mp", "mito_tot"]) as tile_source:
                channels = []
                for i, name in enumerate(tile_source.get_channel_names()):
                    from app.core.composite import CHANNEL_COLORS

                    channels.append(
                        ChannelInfo(
                            name=name,
                            index=i,
                            color=CHANNEL_COLORS.get(name),
                            dtype="uint16",  # Typical for microscopy
                            shape=tile_source.get_full_res_shape(),
                        )
                    )

                # Get mask info
                masks = [
                    MaskInfo(
                        name="nuclei_mask",
                        path=loader.get_well_path(experiment, sequence, well, "nuclei_mask.tif"),
                        is_label_mask=False,
                    ),
                    MaskInfo(
                        name="mito_mask",
                        path=loader.get_well_path(experiment, sequence, well, "mito_mask.tif"),
                        is_label_mask=False,
                    ),
                    MaskInfo(
                        name="microsam_masks",
                        path=loader.get_well_path(experiment, sequence, well, "microsam_masks.tif"),
                        is_label_mask=True,
                    ),
                ]

                return ImageInfo(
                    experiment_id=experiment,
                    sequence_id=sequence,
                    well_id=well,
                    shape=tile_source.get_full_res_shape(),
                    num_levels=len(tile_source.get_levels()),
                    channels=channels,
                    masks=masks,
                    format="zarr" if config.features.use_zarr else "tiff",
                )

        except Exception as e:
            logger.warning(f"Could not load image {image_path}: {e}")
            # Return stub data
            raise HTTPException(status_code=404, detail=f"Image not found: {well}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting image info for {experiment}/{sequence}/{well}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/experiments/{experiment}/sequences/{sequence}/wells/{well}/channels",
    response_model=list[ChannelInfo],
)
async def get_channels(experiment: str, sequence: str, well: str):
    """Get available channels for a well.

    Args:
        experiment: Experiment ID
        sequence: Sequence ID
        well: Well ID

    Returns:
        List of channel information
    """
    try:
        info = await get_image_info(experiment, sequence, well)
        return info.channels
    except Exception as e:
        logger.error(f"Error getting channels for {experiment}/{sequence}/{well}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/experiments/{experiment}/sequences/{sequence}/wells/{well}/masks",
    response_model=list[MaskInfo],
)
async def get_masks(experiment: str, sequence: str, well: str):
    """Get available masks for a well.

    Args:
        experiment: Experiment ID
        sequence: Sequence ID
        well: Well ID

    Returns:
        List of mask information
    """
    try:
        info = await get_image_info(experiment, sequence, well)
        return info.masks
    except Exception as e:
        logger.error(f"Error getting masks for {experiment}/{sequence}/{well}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
