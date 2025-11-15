"""Endpoints for experiments and sequences."""

from typing import List

from fastapi import APIRouter, HTTPException
from loguru import logger

from app.config import config
from app.core.image_loader import get_loader
from app.models.schemas import ExperimentInfo, SequenceInfo

router = APIRouter()


# TODO: Replace with actual metadata loading from S3/database
def _get_experiments() -> List[ExperimentInfo]:
    """Get list of available experiments.

    TODO: Implement actual metadata loading from:
    - S3 bucket listing
    - Metadata CSV/database
    - Configuration file
    """
    # Stub implementation
    return [
        ExperimentInfo(
            experiment_id="exp001",
            name="Experiment 001",
            description="Sample microscopy experiment",
            num_sequences=2,
        ),
        ExperimentInfo(
            experiment_id="exp002",
            name="Experiment 002",
            description="Another experiment",
            num_sequences=1,
        ),
    ]


def _get_sequences(experiment_id: str) -> List[SequenceInfo]:
    """Get sequences for an experiment.

    TODO: Implement actual metadata loading.
    """
    # Stub implementation
    return [
        SequenceInfo(
            sequence_id="seq001",
            experiment_id=experiment_id,
            name="Sequence 001",
            num_wells=96,
        ),
        SequenceInfo(
            sequence_id="seq002",
            experiment_id=experiment_id,
            name="Sequence 002",
            num_wells=96,
        ),
    ]


@router.get("/experiments", response_model=List[ExperimentInfo])
async def list_experiments():
    """List all available experiments.

    Returns:
        List of experiment information
    """
    try:
        experiments = _get_experiments()
        return experiments
    except Exception as e:
        logger.error(f"Error listing experiments: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/experiments/{experiment_id}/sequences", response_model=List[SequenceInfo])
async def list_sequences(experiment_id: str):
    """List sequences for an experiment.

    Args:
        experiment_id: Experiment ID

    Returns:
        List of sequence information
    """
    try:
        sequences = _get_sequences(experiment_id)
        return sequences
    except Exception as e:
        logger.error(f"Error listing sequences for {experiment_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
