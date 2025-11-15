#!/usr/bin/env python3
"""
Download and prepare public microscopy datasets for PICA viewer.

This script downloads publicly available OME-TIFF microscopy images and
organizes them into the PICA directory structure for testing.

Data sources:
- OME Bio-Formats test images
- Allen Cell Explorer public datasets
- Image Data Resource (IDR) samples
"""

import io
import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from urllib.request import urlretrieve

import boto3
import numpy as np
import tifffile
from botocore.exceptions import ClientError
from skimage import filters, measure, morphology
from skimage.transform import resize

print("PICA Viewer - Public Dataset Downloader")
print("=" * 60)


def download_file(url: str, filename: str) -> Path:
    """Download a file from URL.

    Args:
        url: URL to download from
        filename: Local filename to save to

    Returns:
        Path to downloaded file
    """
    print(f"\nDownloading: {filename}")
    print(f"From: {url}")

    filepath = Path(filename)
    if filepath.exists():
        print(f"  ✓ Already exists, skipping download")
        return filepath

    try:
        urlretrieve(url, filepath)
        print(f"  ✓ Downloaded successfully ({filepath.stat().st_size / 1024 / 1024:.2f} MB)")
        return filepath
    except Exception as e:
        print(f"  ✗ Failed to download: {e}")
        raise


def generate_masks_from_image(image_data: np.ndarray, channel_idx: int = 0) -> tuple:
    """Generate binary and label masks from an image channel.

    Args:
        image_data: Multi-channel image (C, Y, X)
        channel_idx: Channel to use for segmentation

    Returns:
        (binary_mask, label_mask)
    """
    # Get single channel
    channel = image_data[channel_idx] if image_data.ndim == 3 else image_data

    # Resize if too large for quick processing
    if channel.shape[0] > 2048 or channel.shape[1] > 2048:
        scale = 2048 / max(channel.shape)
        channel = resize(channel, (int(channel.shape[0] * scale), int(channel.shape[1] * scale)))

    # Normalize
    channel = (channel - channel.min()) / (channel.max() - channel.min())

    # Threshold using Otsu's method
    try:
        thresh = filters.threshold_otsu(channel)
        binary = channel > thresh
    except:
        binary = channel > 0.5

    # Clean up with morphology
    binary = morphology.remove_small_objects(binary, min_size=50)
    binary = morphology.remove_small_holes(binary, area_threshold=50)

    # Create label mask
    label_mask = measure.label(binary)

    return binary.astype(np.uint16), label_mask.astype(np.uint16)


def process_ome_tiff(
    input_path: Path,
    output_dir: Path,
    well_id: str,
    generate_masks: bool = True,
) -> dict:
    """Process an OME-TIFF file and organize it into PICA structure.

    Args:
        input_path: Path to input TIFF file
        output_dir: Output directory
        well_id: Well ID (e.g., A1)
        generate_masks: Whether to generate masks

    Returns:
        Dictionary of created files
    """
    print(f"\nProcessing: {input_path.name} -> {well_id}")

    # Read TIFF
    with tifffile.TiffFile(input_path) as tif:
        data = tif.asarray()

        # Handle different shapes
        if data.ndim == 2:
            # Single channel, single frame
            data = data[np.newaxis, :, :]  # Add channel dimension
        elif data.ndim == 3:
            # Could be (C, Y, X) or (Z, Y, X) or (T, Y, X)
            # Assume first dimension is channels if <= 4, otherwise take max projection
            if data.shape[0] > 4:
                data = data.max(axis=0)[np.newaxis, :, :]
        elif data.ndim == 4:
            # (T, C, Y, X) or similar - take max over time/z
            data = data.max(axis=0)
        elif data.ndim == 5:
            # (T, C, Z, Y, X) - take max over T and Z
            data = data.max(axis=(0, 2))

    print(f"  Image shape: {data.shape}, dtype: {data.dtype}")

    # Create output directories
    well_dir = output_dir / well_id
    well_dir.mkdir(parents=True, exist_ok=True)
    processed_dir = well_dir / "processed"
    processed_dir.mkdir(exist_ok=True)
    masks_dir = well_dir / "masks"
    masks_dir.mkdir(exist_ok=True)

    files_created = {}

    # Save main image
    main_path = well_dir / "image.ome.tiff"
    tifffile.imwrite(
        main_path,
        data,
        photometric="minisblack",
        metadata={"axes": "CYX" if data.ndim == 3 else "YX"},
    )
    files_created["image"] = str(main_path)
    print(f"  ✓ Saved main image: {main_path.name}")

    # Split into individual channels
    channel_names = ["nuclei", "actin", "mito_mp", "mito_tot"]
    for i in range(min(data.shape[0], 4)):
        channel_data = data[i] if data.ndim == 3 else data
        channel_path = processed_dir / f"{channel_names[i]}.tif"
        tifffile.imwrite(channel_path, channel_data)
        files_created[f"channel_{i}"] = str(channel_path)

    print(f"  ✓ Saved {min(data.shape[0], 4)} processed channels")

    # Generate masks if requested
    if generate_masks:
        try:
            # Binary mask from first channel
            binary, labels = generate_masks_from_image(data, 0)

            # Save binary mask as nuclei mask
            nuclei_mask_path = masks_dir / "nuclei_mask.tif"
            tifffile.imwrite(nuclei_mask_path, binary)
            files_created["nuclei_mask"] = str(nuclei_mask_path)

            # Save label mask
            label_mask_path = masks_dir / "microsam_masks.tif"
            tifffile.imwrite(label_mask_path, labels)
            files_created["label_mask"] = str(label_mask_path)

            print(f"  ✓ Generated masks ({labels.max()} objects detected)")

            # Create mito mask if we have multiple channels
            if data.shape[0] >= 3:
                binary_mito, _ = generate_masks_from_image(data, 2)
                mito_mask_path = masks_dir / "mito_mask.tif"
                tifffile.imwrite(mito_mask_path, binary_mito)
                files_created["mito_mask"] = str(mito_mask_path)

        except Exception as e:
            print(f"  ⚠ Could not generate masks: {e}")

    return files_created


def upload_to_s3(
    local_dir: Path,
    bucket: str,
    s3_prefix: str,
    endpoint_url: str = "http://localhost:9000",
    access_key: str = "minioadmin",
    secret_key: str = "minioadmin",
):
    """Upload processed data to S3/MinIO.

    Args:
        local_dir: Local directory with processed data
        bucket: S3 bucket name
        s3_prefix: Prefix for S3 keys (e.g., exp001/seq001)
        endpoint_url: S3 endpoint URL
        access_key: Access key
        secret_key: Secret key
    """
    print(f"\nUploading to S3: {bucket}/{s3_prefix}")

    # Create S3 client
    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )

    # Create bucket if needed
    try:
        s3.head_bucket(Bucket=bucket)
    except ClientError:
        s3.create_bucket(Bucket=bucket)
        print(f"  Created bucket: {bucket}")

    # Upload all files
    uploaded = 0
    for root, dirs, files in os.walk(local_dir):
        for file in files:
            local_path = Path(root) / file
            relative_path = local_path.relative_to(local_dir)
            s3_key = f"{s3_prefix}/{relative_path}"

            with open(local_path, "rb") as f:
                s3.put_object(Bucket=bucket, Key=s3_key, Body=f.read())
            uploaded += 1

    print(f"  ✓ Uploaded {uploaded} files")


def download_ome_sample_images():
    """Download OME Bio-Formats sample images."""
    print("\n" + "=" * 60)
    print("Downloading OME Bio-Formats Sample Images")
    print("=" * 60)

    samples = [
        {
            "name": "multi-channel.ome.tif",
            "url": "https://downloads.openmicroscopy.org/images/OME-TIFF/2016-06/bioformats-artificial/multi-channel.ome.tif",
            "wells": ["A1", "A2"],
        },
        {
            "name": "tubhiswt-4D.ome.tif",
            "url": "https://downloads.openmicroscopy.org/images/OME-TIFF/2016-06/tubhiswt-4D/tubhiswt-4D.ome.tif",
            "wells": ["B1", "B2"],
        },
    ]

    download_dir = Path("downloads")
    download_dir.mkdir(exist_ok=True)

    processed_dir = Path("processed_data")
    processed_dir.mkdir(exist_ok=True)

    for sample in samples:
        try:
            # Download
            filepath = download_dir / sample["name"]
            download_file(sample["url"], filepath)

            # Process for each well
            for well in sample["wells"]:
                process_ome_tiff(filepath, processed_dir, well)

        except Exception as e:
            print(f"  ✗ Error processing {sample['name']}: {e}")
            continue

    return processed_dir


def create_experiment_structure(processed_dir: Path, experiment: str, sequence: str):
    """Organize processed data into experiment/sequence structure.

    Args:
        processed_dir: Directory with processed wells
        experiment: Experiment ID
        sequence: Sequence ID

    Returns:
        Path to organized directory
    """
    print("\n" + "=" * 60)
    print(f"Creating experiment structure: {experiment}/{sequence}")
    print("=" * 60)

    exp_dir = Path("data") / experiment / sequence
    exp_dir.mkdir(parents=True, exist_ok=True)

    # Copy well directories
    for well_dir in processed_dir.iterdir():
        if well_dir.is_dir():
            dest = exp_dir / well_dir.name
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(well_dir, dest)
            print(f"  ✓ Organized well: {well_dir.name}")

    return exp_dir.parent.parent  # Return data root


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Download and prepare public microscopy datasets"
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip downloading, use existing files",
    )
    parser.add_argument(
        "--upload-to-s3",
        action="store_true",
        help="Upload to MinIO/S3 after processing",
    )
    parser.add_argument(
        "--s3-endpoint",
        default="http://localhost:9000",
        help="S3 endpoint URL",
    )
    parser.add_argument(
        "--s3-bucket",
        default="pb-ome-tiffs",
        help="S3 bucket name",
    )

    args = parser.parse_args()

    # Download and process
    if not args.skip_download:
        processed_dir = download_ome_sample_images()
    else:
        processed_dir = Path("processed_data")
        if not processed_dir.exists():
            print("Error: processed_data directory not found. Run without --skip-download first.")
            return

    # Organize into experiments
    data_root = create_experiment_structure(processed_dir, "public_demo", "seq001")

    # Upload to S3 if requested
    if args.upload_to_s3:
        print("\n" + "=" * 60)
        print("Uploading to S3/MinIO")
        print("=" * 60)

        for exp_dir in data_root.iterdir():
            if not exp_dir.is_dir():
                continue

            experiment = exp_dir.name

            for seq_dir in exp_dir.iterdir():
                if not seq_dir.is_dir():
                    continue

                sequence = seq_dir.name

                # Upload each well
                for well_dir in seq_dir.iterdir():
                    if not well_dir.is_dir():
                        continue

                    well = well_dir.name
                    s3_prefix = f"{experiment}/{sequence}/{well}"

                    upload_to_s3(
                        well_dir,
                        args.s3_bucket,
                        s3_prefix,
                        endpoint_url=args.s3_endpoint,
                    )

    print("\n" + "=" * 60)
    print("✓ Done!")
    print("=" * 60)
    print(f"\nProcessed data location: {data_root.absolute()}")
    print("\nNext steps:")
    print("1. Start PICA viewer: docker-compose up -d")
    if args.upload_to_s3:
        print("2. Access web UI: http://localhost:3000")
        print("3. Select experiment 'public_demo' and sequence 'seq001'")
    else:
        print("2. Upload to S3: python scripts/download_public_data.py --skip-download --upload-to-s3")
        print("3. Access web UI: http://localhost:3000")

    print("\nSample wells available:")
    if (data_root / "public_demo" / "seq001").exists():
        wells = [d.name for d in (data_root / "public_demo" / "seq001").iterdir() if d.is_dir()]
        print(f"  {', '.join(sorted(wells))}")


if __name__ == "__main__":
    main()
