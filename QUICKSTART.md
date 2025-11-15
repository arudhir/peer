# PICA Viewer - Quick Start Guide

Get up and running with PICA in 5 minutes!

## Prerequisites

- Docker Desktop installed and running
- Python 3.11+ installed

## Step 1: Start PICA (1 minute)

```bash
# Clone and enter directory
git clone <repo-url>
cd pica-viewer

# Start all services
docker-compose up -d
```

Wait for services to start (check with `docker-compose logs -f backend`).

## Step 2: Load Real Data (2-3 minutes)

```bash
# Install Python dependencies
cd scripts
pip install -r requirements.txt

# Download and load public microscopy images
python download_public_data.py --upload-to-s3
```

This downloads real OME-TIFF images and uploads them to MinIO.

## Step 3: View Images (30 seconds)

**Web Browser:**
1. Open http://localhost:3000
2. Select `public_demo` from Experiment dropdown
3. Select `seq001` from Sequence dropdown
4. Click on well `A1`, `A2`, `B1`, or `B2`
5. Toggle channels, adjust opacity, pan and zoom!

**Napari Desktop (Optional):**
```bash
cd ../napari_client
pip install -r requirements.txt
python viewer.py --experiment public_demo --sequence seq001 --well A1
```

## What You'll See

- **4 channels**: nuclei (blue), actin (green), mito_mp (magenta), mito_tot (yellow)
- **Composite view**: RGB overlay of all channels
- **Mask overlays**: Auto-generated segmentation masks
- **Smooth pan/zoom**: Multi-scale tile streaming

## Next Steps

- **Explore controls**: Toggle channel visibility, adjust opacity
- **Try composite mode**: Switch between normalized and raw intensities
- **View masks**: Turn on mask overlays to see segmented objects
- **Check other wells**: Each well has different sample data

## Troubleshooting

**Services won't start?**
```bash
# Check Docker is running
docker ps

# View logs
docker-compose logs backend
docker-compose logs frontend
```

**No data showing?**
```bash
# Verify data was uploaded
curl http://localhost:9001  # MinIO console
# Login: minioadmin / minioadmin
# Check pb-ome-tiffs bucket
```

**Port already in use?**
```bash
# Change ports in docker-compose.yml
# Edit ports section for each service
```

## URLs

- Web UI: http://localhost:3000
- API Docs: http://localhost:8000/docs
- MinIO Console: http://localhost:9001 (minioadmin/minioadmin)

## Stop PICA

```bash
docker-compose down
```

To remove all data:
```bash
docker-compose down -v
```

## Learn More

- [Full Documentation](README.md)
- [Architecture Diagrams](docs/)
- [API Reference](http://localhost:8000/docs)

---

**Having issues?** Check the full [README](README.md) or open an issue!
