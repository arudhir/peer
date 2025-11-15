#!/usr/bin/env python3
"""
Upload sample data to MinIO for testing.

This script creates sample OME-TIFF files and uploads them to the MinIO instance.
"""

import io
from pathlib import Path

import boto3
import numpy as np
import tifffile
from botocore.exceptions import ClientError


def create_sample_tiff(channels: int = 4, height: int = 2048, width: int = 2048) -> bytes:
    """Create a sample multi-channel TIFF.

    Args:
        channels: Number of channels
        height: Image height
        width: Image width

    Returns:
        TIFF file as bytes
    """
    # Create random data
    data = np.random.randint(0, 4096, (channels, height, width), dtype=np.uint16)

    # Add some structure
    for c in range(channels):
        # Add some circles
        y, x = np.ogrid[:height, :width]
        for _ in range(10):
            cx, cy = np.random.randint(0, width), np.random.randint(0, height)
            r = np.random.randint(50, 200)
            mask = (x - cx) ** 2 + (y - cy) ** 2 <= r**2
            data[c][mask] = np.random.randint(2000, 4000)

    # Save to bytes
    buffer = io.BytesIO()
    tifffile.imwrite(
        buffer,
        data,
        photometric="minisblack",
        metadata={"axes": "CYX"},
    )
    return buffer.getvalue()


def create_sample_mask(height: int = 2048, width: int = 2048, num_objects: int = 50) -> bytes:
    """Create a sample label mask.

    Args:
        height: Image height
        width: Image width
        num_objects: Number of labeled objects

    Returns:
        TIFF file as bytes
    """
    mask = np.zeros((height, width), dtype=np.uint16)

    y, x = np.ogrid[:height, :width]

    for i in range(num_objects):
        cx, cy = np.random.randint(0, width), np.random.randint(0, height)
        r = np.random.randint(20, 100)
        circle_mask = (x - cx) ** 2 + (y - cy) ** 2 <= r**2
        mask[circle_mask] = i + 1

    buffer = io.BytesIO()
    tifffile.imwrite(buffer, mask)
    return buffer.getvalue()


def upload_sample_data(
    endpoint_url: str = "http://localhost:9000",
    access_key: str = "minioadmin",
    secret_key: str = "minioadmin",
    bucket: str = "pb-ome-tiffs",
):
    """Upload sample data to MinIO.

    Args:
        endpoint_url: MinIO endpoint
        access_key: Access key
        secret_key: Secret key
        bucket: Bucket name
    """
    # Create S3 client
    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )

    # Create bucket if it doesn't exist
    try:
        s3.head_bucket(Bucket=bucket)
        print(f"Bucket {bucket} already exists")
    except ClientError:
        s3.create_bucket(Bucket=bucket)
        print(f"Created bucket {bucket}")

    # Define sample experiments
    experiments = ["exp001", "exp002"]
    sequences = ["seq001", "seq002"]
    wells = ["A1", "A2", "B1", "B2", "C3", "D5", "E7", "F9", "G11", "H12"]

    print("Creating and uploading sample data...")

    for exp in experiments:
        for seq in sequences[:1]:  # Only first sequence to save time
            for well in wells[:5]:  # Only first 5 wells
                print(f"  {exp}/{seq}/{well}")

                # Upload main image
                image_data = create_sample_tiff()
                s3.put_object(
                    Bucket=bucket,
                    Key=f"{exp}/{seq}/{well}/image.ome.tiff",
                    Body=image_data,
                )

                # Upload processed channels
                for channel in ["nuclei.tif", "actin.tif", "mito_mp.tif", "mito_tot.tif"]:
                    channel_data = create_sample_tiff(channels=1, height=1024, width=1024)
                    s3.put_object(
                        Bucket=bucket,
                        Key=f"{exp}/{seq}/{well}/processed/{channel}",
                        Body=channel_data,
                    )

                # Upload masks
                for mask in ["nuclei_mask.tif", "mito_mask.tif"]:
                    mask_data = create_sample_mask(height=1024, width=1024, num_objects=20)
                    s3.put_object(
                        Bucket=bucket,
                        Key=f"{exp}/{seq}/{well}/masks/{mask}",
                        Body=mask_data,
                    )

                # Label mask
                label_mask_data = create_sample_mask(height=1024, width=1024, num_objects=100)
                s3.put_object(
                    Bucket=bucket,
                    Key=f"{exp}/{seq}/{well}/masks/microsam_masks.tif",
                    Body=label_mask_data,
                )

    print(f"\nSample data uploaded to {bucket}")
    print(f"MinIO Console: {endpoint_url.replace('9000', '9001')}")
    print(f"Credentials: {access_key} / {secret_key}")


if __name__ == "__main__":
    upload_sample_data()
