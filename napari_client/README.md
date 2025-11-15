# PICA Napari Desktop Client

Desktop viewer for PICA microscopy data using napari.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### View by Experiment/Sequence/Well

```bash
python viewer.py --experiment exp001 --sequence seq001 --well A1
```

### View from Direct Path

Local file:
```bash
python viewer.py --path /local/path/to/image.ome.tiff
```

S3 path:
```bash
python viewer.py --path s3://pb-ome-tiffs/exp001/seq001/A1/image.ome.tiff
```

OME-Zarr:
```bash
python viewer.py --path s3://pb-ome-tiffs/exp001/seq001/A1/image.zarr
```

### Options

- `--no-masks`: Don't load masks
- `--config`: Path to custom config.yaml

## Configuration

The viewer uses the same `config.yaml` as the backend. You can also set environment variables:

```bash
export S3_ENDPOINT_URL=http://localhost:9000
export S3_ACCESS_KEY_ID=minioadmin
export S3_SECRET_ACCESS_KEY=minioadmin
export S3_BUCKET_NAME=pb-ome-tiffs
```

## Features

- Lazy loading with Dask for large images
- Multi-channel support with proper color mapping
- Mask overlay support
- Works with both local and S3 paths
- Supports OME-TIFF and OME-Zarr formats
