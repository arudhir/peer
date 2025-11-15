# PICA Scripts

Utility scripts for data management and testing.

## Available Scripts

### 1. download_public_data.py

Download and process real microscopy images from public repositories.

**What it does:**
- Downloads OME-TIFF files from OME Bio-Formats repository
- Processes multi-channel images
- Generates masks automatically using image segmentation
- Organizes data into PICA structure
- Optionally uploads to MinIO/S3

**Usage:**

```bash
# Install dependencies first
pip install -r requirements.txt

# Download, process, and upload to MinIO
python download_public_data.py --upload-to-s3

# Just download and process (don't upload)
python download_public_data.py

# Skip download, use existing files
python download_public_data.py --skip-download --upload-to-s3

# Custom S3 endpoint
python download_public_data.py --upload-to-s3 --s3-endpoint http://localhost:9000

# Custom bucket
python download_public_data.py --upload-to-s3 --s3-bucket my-bucket
```

**Output:**
- Downloaded files: `downloads/` directory
- Processed data: `processed_data/` directory
- Organized data: `data/public_demo/seq001/` directory

**Example wells created:**
- `A1`, `A2` - Multi-channel samples
- `B1`, `B2` - Time-lapse samples (max projected)

### 2. upload_sample_data.py

Generate synthetic test data with random patterns.

**What it does:**
- Creates synthetic multi-channel TIFFs
- Generates random circles to simulate cells
- Creates binary and label masks
- Uploads directly to MinIO/S3

**Usage:**

```bash
# Install dependencies
pip install boto3 tifffile numpy

# Generate and upload synthetic data
python upload_sample_data.py
```

**Output:**
- Experiment: `exp001`, `exp002`
- Sequences: `seq001`, `seq002`
- Wells: `A1`, `A2`, `B1`, `B2`, `C3`, `D5`, `E7`, `F9`, `G11`, `H12`

**Image properties:**
- Size: 2048 × 2048 (main), 1024 × 1024 (processed)
- Channels: 4 (nuclei, actin, mito_mp, mito_tot)
- Dtype: uint16
- Masks: Binary and label masks with ~50 objects

## Data Sources

### OME Bio-Formats Test Images

Public repository of sample microscopy images maintained by the OME team.

- **URL**: https://downloads.openmicroscopy.org/images/
- **License**: Public domain / CC BY 4.0
- **Formats**: OME-TIFF, various dimensions
- **Types**: Multi-channel, Z-stacks, time-lapse, various microscopy modalities

**Sample images used:**
1. `multi-channel.ome.tif` - Multi-channel fluorescence
2. `tubhiswt-4D.ome.tif` - 4D time-lapse

### Other Public Datasets (Future)

Potential sources to add:

- **Image Data Resource (IDR)**: https://idr.openmicroscopy.org/
  - Large collection of published imaging datasets
  - Requires API access

- **Allen Cell Explorer**: https://www.allencell.org/
  - Segmented human cell images
  - High-quality 3D data

- **Cell Image Library**: http://www.cellimagelibrary.org/
  - Diverse cell biology images
  - Various organisms and conditions

## Advanced Usage

### Customize Data Processing

Modify `download_public_data.py` to:

1. **Add more data sources:**
```python
samples = [
    {
        "name": "your-image.ome.tif",
        "url": "https://your-repo.com/image.ome.tif",
        "wells": ["C1", "C2"],
    },
]
```

2. **Adjust mask generation:**
```python
# In generate_masks_from_image()
thresh = filters.threshold_otsu(channel)  # Change threshold method
binary = morphology.remove_small_objects(binary, min_size=100)  # Adjust size
```

3. **Change output organization:**
```python
# Customize experiment/sequence names
create_experiment_structure(processed_dir, "my_exp", "my_seq")
```

### Batch Upload Existing Data

If you have existing organized data:

```python
import boto3
from pathlib import Path

s3 = boto3.client('s3', endpoint_url='http://localhost:9000')

data_root = Path('data')
for exp_dir in data_root.iterdir():
    for seq_dir in exp_dir.iterdir():
        for well_dir in seq_dir.iterdir():
            for file in well_dir.rglob('*.tif*'):
                key = str(file.relative_to(data_root))
                s3.upload_file(str(file), 'pb-ome-tiffs', key)
```

## Troubleshooting

### Download Fails

```bash
# Check internet connection
curl -I https://downloads.openmicroscopy.org/images/

# Try with proxy
export HTTP_PROXY=http://proxy:port
export HTTPS_PROXY=http://proxy:port
python download_public_data.py
```

### Upload Fails

```bash
# Check MinIO is running
curl http://localhost:9000/minio/health/live

# Verify credentials
docker-compose exec backend python -c "import s3fs; print(s3fs.S3FileSystem(endpoint_url='http://minio:9000'))"

# Check bucket exists
aws --endpoint-url http://localhost:9000 s3 ls s3://pb-ome-tiffs/
```

### Out of Memory

```bash
# Reduce image size in download_public_data.py
# Around line 50, adjust resize threshold:
if channel.shape[0] > 1024 or channel.shape[1] > 1024:  # Smaller threshold
    scale = 1024 / max(channel.shape)
```

### Mask Generation Issues

```bash
# Install scikit-image
pip install scikit-image>=0.22.0

# If segmentation fails, check image values
python -c "import tifffile; img=tifffile.imread('file.tif'); print(img.min(), img.max())"
```

## Performance Tips

1. **Use `--skip-download`** for repeated testing
2. **Run upload in background** for large datasets
3. **Adjust MinIO memory** in docker-compose.yml if needed
4. **Use SSD storage** for cache and downloads

## Contributing

To add new data sources:

1. Add download URL to `samples` list
2. Test with `--skip-upload` first
3. Verify masks are generated correctly
4. Update this README with new source info
5. Submit PR with sample output

## License

Scripts are MIT licensed. Downloaded data retains original licenses (check source repositories).
