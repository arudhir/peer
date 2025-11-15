#!/usr/bin/env python3
"""
Napari Desktop Viewer for PICA Microscopy Data

Launch napari to view microscopy images from local or S3 paths.
Supports both OME-TIFF and OME-Zarr formats.

Usage:
    python viewer.py --experiment exp001 --sequence seq001 --well A1
    python viewer.py --path s3://bucket/path/to/image.ome.tiff
    python viewer.py --path /local/path/to/image.ome.zarr
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

import dask.array as da
import napari
import numpy as np
import s3fs
import tifffile
import yaml
from aicsimageio import AICSImage
from dotenv import load_dotenv
from loguru import logger

# Load environment
load_dotenv()


class NapariImageViewer:
    """Napari-based image viewer for microscopy data."""

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize viewer with configuration.

        Args:
            config_path: Path to config.yaml
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config.yaml"

        self.config = self._load_config(config_path)
        self.s3fs = self._init_s3fs()

    def _load_config(self, config_path: Path) -> dict:
        """Load configuration from YAML file."""
        if config_path.exists():
            with open(config_path) as f:
                return yaml.safe_load(f)
        return {}

    def _init_s3fs(self) -> Optional[s3fs.S3FileSystem]:
        """Initialize S3 filesystem."""
        s3_config = self.config.get("s3", {})

        # Override with environment variables
        endpoint_url = os.getenv("S3_ENDPOINT_URL", s3_config.get("endpoint_url"))
        access_key = os.getenv("S3_ACCESS_KEY_ID", s3_config.get("access_key_id"))
        secret_key = os.getenv("S3_SECRET_ACCESS_KEY", s3_config.get("secret_access_key"))
        region = os.getenv("S3_REGION", s3_config.get("region", "us-west-2"))
        use_ssl = os.getenv("S3_USE_SSL", str(s3_config.get("use_ssl", True))).lower() == "true"

        try:
            fs_config = {
                "key": access_key,
                "secret": secret_key,
                "client_kwargs": {"region_name": region},
            }

            if endpoint_url:
                fs_config["client_kwargs"]["endpoint_url"] = endpoint_url
                fs_config["use_ssl"] = use_ssl

            return s3fs.S3FileSystem(**fs_config)
        except Exception as e:
            logger.warning(f"Failed to initialize S3: {e}")
            return None

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
            well: Well ID
            file_type: File type

        Returns:
            S3 path
        """
        bucket = self.config.get("s3", {}).get("bucket_name", "pb-ome-tiffs")

        if "mask" in file_type:
            return f"s3://{bucket}/{experiment}/{sequence}/{well}/masks/{file_type}"
        elif file_type in ["nuclei.tif", "actin.tif", "mito_mp.tif", "mito_tot.tif"]:
            return f"s3://{bucket}/{experiment}/{sequence}/{well}/processed/{file_type}"
        else:
            return f"s3://{bucket}/{experiment}/{sequence}/{well}/{file_type}"

    def load_image(
        self,
        path: str,
        use_dask: bool = True,
    ) -> tuple[np.ndarray | da.Array, dict]:
        """Load image from path (local or S3).

        Args:
            path: Path to image
            use_dask: Use dask for lazy loading

        Returns:
            (image_array, metadata)
        """
        logger.info(f"Loading image: {path}")

        # Detect format
        is_zarr = path.endswith(".zarr") or "/.zgroup" in path or "/.zarray" in path

        if is_zarr:
            # Load OME-Zarr
            import zarr
            from ome_zarr.io import parse_url
            from ome_zarr.reader import Reader

            location = parse_url(path, mode="r")
            reader = Reader(location)
            nodes = list(reader())

            if not nodes:
                raise ValueError(f"No data found in Zarr: {path}")

            node = nodes[0]
            # Get highest resolution
            data = node.data[0]  # First pyramid level

            metadata = node.metadata or {}

            # Convert to numpy if small enough, else keep as dask
            if not use_dask or data.nbytes < 1e9:  # < 1 GB
                data = np.array(data)

            return data, metadata

        else:
            # Load TIFF using aicsimageio
            img = AICSImage(path)

            # Get data as dask or numpy
            if use_dask:
                data = img.dask_data
            else:
                data = img.data

            # Squeeze singleton dimensions
            data = np.squeeze(data)

            metadata = {
                "shape": img.shape,
                "dims": img.dims,
                "channel_names": img.channel_names,
                "physical_pixel_sizes": img.physical_pixel_sizes,
            }

            return data, metadata

    def view_well(
        self,
        experiment: str,
        sequence: str,
        well: str,
        load_masks: bool = True,
    ):
        """View a well in napari.

        Args:
            experiment: Experiment ID
            sequence: Sequence ID
            well: Well ID
            load_masks: Load masks as well
        """
        viewer = napari.Viewer(title=f"PICA Viewer - {experiment}/{sequence}/{well}")

        # Load main image
        image_path = self.get_well_path(experiment, sequence, well, "image.ome.tiff")

        try:
            image_data, metadata = self.load_image(image_path)

            # Channel names
            channel_names = ["nuclei", "actin", "mito_mp", "mito_tot"]

            # Handle different shapes
            if image_data.ndim == 2:
                # Single channel
                viewer.add_image(image_data, name=channel_names[0])
            elif image_data.ndim == 3:
                # Multi-channel (C, Y, X)
                for i, name in enumerate(channel_names):
                    if i < image_data.shape[0]:
                        viewer.add_image(
                            image_data[i],
                            name=name,
                            colormap={
                                "nuclei": "blue",
                                "actin": "green",
                                "mito_mp": "magenta",
                                "mito_tot": "yellow",
                            }.get(name, "gray"),
                            blending="additive",
                        )
            else:
                # Higher dimensional - add as is
                viewer.add_image(image_data, name="image", channel_axis=0)

            logger.info(f"Loaded image: {image_data.shape}")

        except Exception as e:
            logger.error(f"Failed to load image: {e}")
            logger.exception(e)

        # Load masks
        if load_masks:
            mask_files = [
                ("nuclei_mask.tif", False),
                ("mito_mask.tif", False),
                ("microsam_masks.tif", True),  # Label mask
            ]

            for mask_file, is_label in mask_files:
                try:
                    mask_path = self.get_well_path(experiment, sequence, well, mask_file)
                    mask_data, _ = self.load_image(mask_path)

                    if is_label:
                        viewer.add_labels(mask_data, name=mask_file)
                    else:
                        viewer.add_image(
                            mask_data,
                            name=mask_file,
                            colormap="red",
                            blending="additive",
                            opacity=0.5,
                        )

                    logger.info(f"Loaded mask: {mask_file}")

                except Exception as e:
                    logger.warning(f"Could not load mask {mask_file}: {e}")

        napari.run()

    def view_path(self, path: str):
        """View an image from a direct path.

        Args:
            path: Path to image (local or S3)
        """
        viewer = napari.Viewer(title=f"PICA Viewer - {Path(path).name}")

        try:
            image_data, metadata = self.load_image(path)

            viewer.add_image(image_data, name="image")

            logger.info(f"Loaded image: {image_data.shape}")
            logger.info(f"Metadata: {metadata}")

        except Exception as e:
            logger.error(f"Failed to load image: {e}")
            logger.exception(e)
            return

        napari.run()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="PICA Napari Viewer - View microscopy images from local or S3"
    )

    parser.add_argument("--experiment", help="Experiment ID")
    parser.add_argument("--sequence", help="Sequence ID")
    parser.add_argument("--well", help="Well ID (e.g., A1)")
    parser.add_argument("--path", help="Direct path to image (local or S3)")
    parser.add_argument(
        "--no-masks", action="store_true", help="Don't load masks"
    )
    parser.add_argument("--config", type=Path, help="Path to config.yaml")

    args = parser.parse_args()

    # Initialize viewer
    viewer = NapariImageViewer(config_path=args.config)

    # View based on arguments
    if args.path:
        viewer.view_path(args.path)
    elif args.experiment and args.sequence and args.well:
        viewer.view_well(
            args.experiment,
            args.sequence,
            args.well,
            load_masks=not args.no_masks,
        )
    else:
        parser.print_help()
        print("\nError: Must provide either --path or --experiment/--sequence/--well")
        sys.exit(1)


if __name__ == "__main__":
    main()
