"""Configuration management for PICA viewer."""

import os
from pathlib import Path
from typing import Optional

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings


class S3Config(BaseSettings):
    """S3 configuration."""

    endpoint_url: Optional[str] = Field(None, validation_alias="S3_ENDPOINT_URL")
    bucket_name: str = Field("pb-ome-tiffs", validation_alias="S3_BUCKET_NAME")
    region: str = Field("us-west-2", validation_alias="S3_REGION")
    access_key_id: Optional[str] = Field(None, validation_alias="S3_ACCESS_KEY_ID")
    secret_access_key: Optional[str] = Field(None, validation_alias="S3_SECRET_ACCESS_KEY")
    use_ssl: bool = Field(True, validation_alias="S3_USE_SSL")


class CacheConfig(BaseSettings):
    """Cache configuration."""

    enabled: bool = Field(True, validation_alias="CACHE_ENABLED")
    root_path: str = Field("~/.pica_cache", validation_alias="CACHE_ROOT_PATH")
    max_size_gb: int = Field(50, validation_alias="CACHE_MAX_SIZE_GB")
    eviction_policy: str = "lru"


class TileConfig(BaseSettings):
    """Tile configuration."""

    tile_size: int = 256
    default_format: str = "png"
    compression_level: int = 6


class FeatureFlags(BaseSettings):
    """Feature flags."""

    use_zarr: bool = Field(True, validation_alias="USE_ZARR")
    enable_auth: bool = Field(False, validation_alias="ENABLE_AUTH")
    prefetch_tiles: bool = True


class ServerConfig(BaseSettings):
    """Server configuration."""

    host: str = Field("0.0.0.0", validation_alias="HOST")
    port: int = Field(8000, validation_alias="PORT")
    workers: int = Field(4, validation_alias="WORKERS")
    reload: bool = Field(False, validation_alias="RELOAD")


class ProcessingConfig(BaseSettings):
    """Image processing configuration."""

    max_workers: int = 8
    chunk_size: int = 1024
    default_percentile_range: tuple[int, int] = (1, 99)


class Config(BaseSettings):
    """Main application configuration."""

    s3: S3Config = Field(default_factory=S3Config)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    tiles: TileConfig = Field(default_factory=TileConfig)
    features: FeatureFlags = Field(default_factory=FeatureFlags)
    server: ServerConfig = Field(default_factory=ServerConfig)
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)

    log_level: str = Field("INFO", validation_alias="LOG_LEVEL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


def load_config(config_path: Optional[Path] = None) -> Config:
    """Load configuration from YAML and environment variables.

    Environment variables take precedence over YAML configuration.

    Args:
        config_path: Path to YAML config file. Defaults to config.yaml in repo root.

    Returns:
        Loaded configuration object.
    """
    if config_path is None:
        # Try to find config.yaml in repo root
        config_path = Path(__file__).parent.parent.parent / "config.yaml"

    config_dict = {}

    # Load YAML if it exists
    if config_path.exists():
        with open(config_path) as f:
            config_dict = yaml.safe_load(f) or {}

    # Create config objects, env vars will override YAML values
    s3_config = S3Config(**config_dict.get("s3", {}))
    cache_config = CacheConfig(**config_dict.get("cache", {}))
    tile_config = TileConfig(**config_dict.get("tiles", {}))
    feature_flags = FeatureFlags(**config_dict.get("features", {}))
    server_config = ServerConfig(**config_dict.get("server", {}))
    processing_config = ProcessingConfig(**config_dict.get("processing", {}))

    return Config(
        s3=s3_config,
        cache=cache_config,
        tiles=tile_config,
        features=feature_flags,
        server=server_config,
        processing=processing_config,
        log_level=os.getenv("LOG_LEVEL", config_dict.get("logging", {}).get("level", "INFO")),
    )


# Global config instance
config = load_config()
