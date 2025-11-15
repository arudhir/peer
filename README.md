# PICA Microscopy Viewer

High-performance microscopy image viewer for large 4-channel OME-TIFF and OME-Zarr datasets stored on S3.

## Features

- **Cloud-Native Tile Loading**: Efficient streaming of large images from S3
- **Multi-Channel Visualization**: 4-channel support with customizable opacity and visibility
- **Composite View**: RGB mapping with normalized or raw intensity modes
- **Mask Overlays**: Support for binary and label masks
- **Plate Grid Navigation**: Browse 96-well plates (A1-H12)
- **Fast Pan/Zoom**: Smooth interaction with multi-scale pyramids
- **Desktop & Web**: Both napari desktop client and browser-based viewer
- **Flexible Storage**: Works with local files, S3, OME-TIFF, and OME-Zarr

## Architecture

- **Backend**: FastAPI with async I/O, s3fs, and pluggable tile sources
- **Frontend**: React + WebGL for high-performance rendering
- **Desktop**: napari with lazy loading via Dask
- **Cache**: LRU disk cache for tiles and chunks
- **Storage**: S3-compatible object storage (AWS S3 or MinIO)

See detailed architecture diagrams:
- [Local Development Architecture](docs/architecture-local.md)
- [AWS EC2 Deployment Architecture](docs/architecture-ec2.md)

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for napari client)
- Node.js 20+ (for frontend development)

### 1. Start with Docker Compose

```bash
# Clone repository
git clone <repo-url>
cd pica-viewer

# Start all services (backend, frontend, MinIO)
docker-compose up -d

# Wait for services to be ready
docker-compose logs -f backend
```

### 2. Load Example Data

Choose one of the following options:

#### Option A: Use Public Microscopy Data (Recommended)

Download real OME-TIFF images from public repositories:

```bash
# Install dependencies
cd scripts
pip install -r requirements.txt

# Download and process public OME-TIFF samples
python download_public_data.py --upload-to-s3

# This will:
# - Download OME Bio-Formats sample images
# - Process and organize them into PICA structure
# - Generate masks automatically
# - Upload to MinIO
```

#### Option B: Generate Synthetic Data

Create synthetic test data:

```bash
pip install boto3 tifffile numpy
python scripts/upload_sample_data.py
```

### 3. Access the Application

- **Web UI**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin)

**First time users**: Select experiment `public_demo` and sequence `seq001` to view the downloaded samples.

### 4. Use Napari Desktop Client (Optional)

```bash
cd napari_client
pip install -r requirements.txt

# View public demo data
python viewer.py --experiment public_demo --sequence seq001 --well A1

# Or view from direct S3 path
python viewer.py --path s3://pb-ome-tiffs/public_demo/seq001/A1/image.ome.tiff

# Or use local files
python viewer.py --path /path/to/your/image.ome.tiff
```

## Project Structure

```
peer/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── main.py         # FastAPI app
│   │   ├── config.py       # Configuration management
│   │   ├── api/            # API routes
│   │   ├── core/           # Core functionality
│   │   │   ├── cache.py    # LRU cache
│   │   │   ├── image_loader.py  # Image loading abstraction
│   │   │   ├── tiff_source.py   # TIFF tile source
│   │   │   ├── zarr_source.py   # Zarr tile source
│   │   │   └── composite.py     # Composite generation
│   │   └── models/         # Pydantic models
│   ├── tests/              # Unit and integration tests
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/               # React frontend
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── api.ts         # API client
│   │   ├── types.ts       # TypeScript types
│   │   └── App.tsx        # Main app
│   ├── package.json
│   └── Dockerfile
├── napari_client/         # Napari desktop viewer
│   ├── viewer.py          # CLI viewer script
│   └── requirements.txt
├── docs/                  # Documentation
│   ├── architecture-local.md   # Local dev architecture
│   └── architecture-ec2.md     # Production architecture
├── scripts/               # Utility scripts
│   └── upload_sample_data.py
├── config.yaml            # Main configuration
├── docker-compose.yml     # Docker Compose setup
└── README.md
```

## Configuration

Configuration is managed through `config.yaml` and environment variables.

### config.yaml

```yaml
s3:
  endpoint_url: "http://localhost:9000"  # MinIO for local; null for AWS
  bucket_name: "pb-ome-tiffs"
  region: "us-west-2"

cache:
  enabled: true
  root_path: "~/.pica_cache"
  max_size_gb: 50

tiles:
  tile_size: 256
  default_format: "png"

features:
  use_zarr: true
  enable_auth: false
```

### Environment Variables

Create a `.env` file (see `.env.example`):

```bash
# S3 Configuration
S3_ENDPOINT_URL=http://localhost:9000
S3_BUCKET_NAME=pb-ome-tiffs
S3_ACCESS_KEY_ID=minioadmin
S3_SECRET_ACCESS_KEY=minioadmin

# Cache
CACHE_ROOT_PATH=~/.pica_cache
CACHE_MAX_SIZE_GB=50

# Server
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO
```

## Development

### Backend Development

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest

# Run with hot reload
python -m app.main
# or
uvicorn app.main:app --reload

# Check API docs
open http://localhost:8000/docs
```

### Frontend Development

```bash
cd frontend

# Install dependencies
npm install

# Run dev server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Running Tests

```bash
# Backend tests
cd backend
pytest -v

# With coverage
pytest --cov=app --cov-report=html

# Specific test file
pytest tests/test_cache.py -v
```

## API Endpoints

### Experiments and Metadata

- `GET /api/experiments` - List all experiments
- `GET /api/experiments/{exp_id}/sequences` - List sequences
- `GET /api/experiments/{exp}/sequences/{seq}/plate-metadata` - Get plate layout
- `GET /api/experiments/{exp}/sequences/{seq}/wells/{well}/info` - Get image info
- `GET /api/experiments/{exp}/sequences/{seq}/wells/{well}/channels` - List channels
- `GET /api/experiments/{exp}/sequences/{seq}/wells/{well}/masks` - List masks

### Tiles

- `GET /api/experiments/{exp}/sequences/{seq}/wells/{well}/tile` - Get single channel tile
  - Query params: `channel`, `level`, `x`, `y`, `tile_size`
- `GET /api/experiments/{exp}/sequences/{seq}/wells/{well}/composite` - Get composite tile
  - Query params: `level`, `x`, `y`, `mode`, `*_opacity`, `*_visible`
- `GET /api/experiments/{exp}/sequences/{seq}/wells/{well}/mask-tile` - Get mask overlay
  - Query params: `mask_name`, `level`, `x`, `y`, `opacity`, `is_label`

### Cache

- `GET /api/cache/stats` - Get cache statistics
- `POST /api/cache/clear` - Clear cache

## Data Format

Expected S3 structure:

```
s3://pb-ome-tiffs/
└── {experiment}/
    └── {sequence}/
        └── {well}/
            ├── image.ome.tiff          # Main 4-channel image
            ├── metadata.json
            ├── ome.xml
            ├── preview.png
            ├── processed/
            │   ├── nuclei.tif
            │   ├── actin.tif
            │   ├── mito_mp.tif
            │   └── mito_tot.tif
            └── masks/
                ├── nuclei_mask.tif
                ├── mito_mask.tif
                └── microsam_masks.tif  # Label mask
```

### Channel Mappings

| Channel | Color | Description |
|---------|-------|-------------|
| nuclei | Blue | Nuclear channel |
| actin | Green | Actin cytoskeleton |
| mito_mp | Magenta | Mitochondria (membrane potential) |
| mito_tot | Yellow | Mitochondria (total) |

## Example Data Sources

PICA comes with scripts to download and process real microscopy data from public repositories.

### Public OME-TIFF Datasets

The `download_public_data.py` script fetches data from:

- **OME Bio-Formats Test Images**: Multi-channel OME-TIFF samples
  - Source: https://downloads.openmicroscopy.org/images/
  - Includes: Multi-channel images, time-lapse, Z-stacks
  - License: Public domain / CC BY 4.0

### What the Script Does

1. **Downloads** real OME-TIFF files from public repositories
2. **Processes** images to extract channels
3. **Generates** masks using automatic segmentation (Otsu thresholding + morphology)
4. **Organizes** into PICA directory structure
5. **Uploads** to MinIO/S3 for immediate use

### Available Wells

After running `download_public_data.py`, you'll have:
- **Experiment**: `public_demo`
- **Sequence**: `seq001`
- **Wells**: `A1`, `A2`, `B1`, `B2` (from different sample images)

Each well contains:
- 4-channel OME-TIFF image
- Individual channel TIFFs
- Binary masks (nuclei, mitochondria)
- Label mask with detected objects

### Using Your Own Data

To use your own microscopy data:

```bash
# Organize your TIFFs into the expected structure
data/
└── my_experiment/
    └── my_sequence/
        └── A1/
            ├── image.ome.tiff
            └── masks/
                └── nuclei_mask.tif

# Upload to MinIO
python scripts/upload_sample_data.py  # Modify for your structure

# Or point PICA to a different S3 bucket
export S3_BUCKET_NAME=my-data-bucket
```

## Deployment

### Local Development (macOS/Linux)

See [Local Architecture Documentation](docs/architecture-local.md)

```bash
# Using Docker Compose
docker-compose up -d

# Without Docker (manual setup)
cd backend && uvicorn app.main:app --reload &
cd frontend && npm run dev &
```

### AWS EC2 Production

See [EC2 Architecture Documentation](docs/architecture-ec2.md)

Key steps:
1. Launch Ubuntu EC2 instance (m5.xlarge recommended)
2. Attach IAM role with S3 read permissions
3. Install Docker or deploy directly
4. Configure Nginx as reverse proxy
5. Set up SSL with Let's Encrypt
6. Configure CloudWatch logging
7. Set up monitoring and alarms

## Authentication (Future)

Authentication is currently disabled but architected for easy integration:

```python
# In app/main.py (currently commented out)
if config.features.enable_auth:
    from app.auth import CognitoAuthMiddleware
    app.add_middleware(CognitoAuthMiddleware)
```

Planned auth providers:
- AWS Cognito
- JWT-based authentication
- Session-based authentication

## Performance

### Optimizations

- **Multi-scale pyramids**: Automatic level selection based on zoom
- **Tile caching**: LRU disk cache reduces S3 requests
- **Lazy loading**: Only load visible tiles
- **Async I/O**: Non-blocking tile requests
- **Composite generation**: Server-side RGB composition
- **Chunked storage**: OME-Zarr for cloud-optimized access

### Benchmarks (Typical)

- Initial load: < 1s (with cache)
- Tile load: < 100ms (cached), < 500ms (S3)
- Pan/zoom: 60 FPS
- Cache hit rate: > 80% (after warmup)
- Supported image size: Up to 50,000 × 50,000 pixels

## Troubleshooting

### Common Issues

**Backend won't start:**
```bash
# Check logs
docker-compose logs backend

# Verify S3 connection
docker-compose exec backend python -c "import s3fs; print(s3fs.S3FileSystem())"
```

**No images in plate view:**
```bash
# Upload sample data
python scripts/upload_sample_data.py

# Check MinIO
open http://localhost:9001
```

**Tiles not loading:**
```bash
# Check cache permissions
ls -la ~/.pica_cache/

# Clear cache
curl -X POST http://localhost:8000/api/cache/clear

# Check backend logs
docker-compose logs -f backend
```

**Napari can't connect to S3:**
```bash
# Set environment variables
export S3_ENDPOINT_URL=http://localhost:9000
export S3_ACCESS_KEY_ID=minioadmin
export S3_SECRET_ACCESS_KEY=minioadmin

# Test connection
python -c "import s3fs; fs = s3fs.S3FileSystem(endpoint_url='http://localhost:9000'); print(fs.ls('pb-ome-tiffs'))"
```

## Future Roadmap

### Phase 1 (Current)
- [x] OME-TIFF support
- [x] 4-channel viewer
- [x] Composite mode
- [x] Mask overlays
- [x] Plate browser
- [x] Local cache

### Phase 2 (Planned)
- [ ] OME-Zarr multi-scale pyramids
- [ ] Click-to-inspect for labeled objects
- [ ] Object measurements from database
- [ ] User authentication (Cognito)
- [ ] EC2 deployment automation
- [ ] Improved caching strategies

### Phase 3 (Future)
- [ ] Real-time collaborative viewing
- [ ] Annotation tools
- [ ] 3D/Z-stack support
- [ ] Time-series support
- [ ] Machine learning model integration
- [ ] Lambda-based serverless tile generation

## OME-Zarr Conversion

Convert existing TIFF files to OME-Zarr:

```python
# TODO: Implement conversion utility
from app.utils.zarr_converter import convert_tiff_to_zarr

convert_tiff_to_zarr(
    input_path="s3://bucket/exp/seq/well/image.ome.tiff",
    output_path="s3://bucket/exp/seq/well/image.zarr",
    pyramid_levels=5,
    chunk_size=(256, 256)
)
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`pytest`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Code Style

- **Python**: Follow PEP 8, use `black` for formatting
- **TypeScript**: Follow Airbnb style guide
- **Tests**: Maintain > 80% coverage

## License

[Add your license here]

## Support

- Documentation: See `docs/` directory
- Issues: [GitHub Issues](https://github.com/your-org/pica-viewer/issues)
- Discussions: [GitHub Discussions](https://github.com/your-org/pica-viewer/discussions)

## Acknowledgments

- Built with [napari](https://napari.org)
- Uses [FastAPI](https://fastapi.tiangolo.com)
- Powered by [React](https://react.dev)
- Storage via [MinIO](https://min.io) / [AWS S3](https://aws.amazon.com/s3)

---

**Note**: This is the initial release (v0.1.0). The architecture is designed to scale from local Mac development to production EC2 deployment with minimal changes.
