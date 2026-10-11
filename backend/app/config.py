"""
Configuration management for HazardIQ backend.
Reads configuration from environment variables with sensible local defaults.
"""

from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "local.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Server Information
    APP_NAME: str = "HazardIQ Backend"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    # CORS Settings - List of allowed origins
    # Accepts comma-separated string or list from environment
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        """Convert comma-separated ALLOWED_ORIGINS string to list of trimmed strings."""
        if not self.ALLOWED_ORIGINS:
            return ["*"]
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    # Weather Service (Open-Meteo)
    OPEN_METEO_BASE_URL: str = "https://api.open-meteo.com/v1/forecast"
    WEATHER_CACHE_TTL_SECONDS: int = 300
    WEATHER_REQUEST_TIMEOUT_SECONDS: float = 5.0

    # Geographic Defaults (Delhi Target Area)
    DEFAULT_CITY: str = "Delhi"
    DEFAULT_LATITUDE: float = 28.6139
    DEFAULT_LONGITUDE: float = 77.2090

    # Hotspot Data File
    HOTSPOTS_FILE_PATH: str = "app/data/hotspots.json"

    # Citizen Hazard Reports
    MAX_IMAGE_SIZE_BYTES: int = 5 * 1024 * 1024  # 5 Megabytes
    LOCAL_STORAGE_PATH: str = "data/local_reports.json"

    # AWS General & Cloud Integration Settings
    AWS_REGION: str = "us-east-1"
    AWS_ENDPOINT_URL: Optional[str] = None

    # AWS DynamoDB Persistence
    ENABLE_DYNAMODB: bool = False
    DYNAMODB_TABLE_REPORTS: str = "HazardIQ-Reports"

    # AWS S3 Photo Storage
    ENABLE_S3: bool = False
    S3_BUCKET_PHOTOS: str = "hazardiq-hazard-photos"
    S3_PRESIGNED_URL_EXPIRE_SECONDS: int = 3600

    # Amazon Bedrock AI Integration (Amazon Nova Lite)
    ENABLE_BEDROCK: bool = False
    BEDROCK_MODEL_ID: str = "amazon.nova-lite-v1:0"
    BEDROCK_TIMEOUT_SECONDS: float = 10.0

    # Policy Engine
    CEDAR_POLICY_PATH: str = "app/policies/cedar_policy.cedar"


# Global cached settings instance
settings = Settings()
