"""
Amazon S3 Image Storage Service.
Securely uploads validated citizen hazard photographs to private S3 storage.

Security and Architecture Rules:
- Never makes uploaded hazard images publicly accessible by default (no public ACL).
- Uses server-generated UUID object keys: reports/<report_uuid>.jpg.
- Never accepts client-provided arbitrary object keys.
- When AWS is disabled, returns 'not_configured' without faking success.
"""

import logging
import os
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class S3StorageService:
    def __init__(
        self,
        bucket_name: Optional[str] = None,
        region_name: Optional[str] = None,
        aws_integration_enabled: Optional[bool] = None,
    ):
        self.bucket_name = bucket_name or os.getenv("S3_BUCKET_NAME", "")
        self.region_name = region_name or os.getenv("AWS_REGION", "ap-southeast-2")
        self.aws_enabled = (
            aws_integration_enabled
            if aws_integration_enabled is not None
            else os.getenv("AWS_INTEGRATION_ENABLED", "false").lower() == "true"
        )
        self._client = None

    def get_client(self):
        """Lazy load boto3 S3 client when AWS integration is enabled."""
        if not self.aws_enabled or not self.bucket_name:
            return None
        if self._client is None:
            try:
                import boto3
                self._client = boto3.client("s3", region_name=self.region_name)
            except Exception as e:
                logger.warning("Could not initialize S3 client: %s", str(e))
                self._client = None
        return self._client

    async def upload_image(
        self,
        report_uuid: str,
        image_bytes: bytes,
        content_type: str = "image/jpeg",
    ) -> Dict[str, str]:
        """
        Upload validated image to private S3 bucket.

        Returns:
            Dict containing:
            - status: 'stored', 'not_configured', or 'failed'
            - object_key: 'reports/<report_uuid>.jpg' or ''
            - bucket: configured bucket name or ''
        """
        if not self.aws_enabled or not self.bucket_name or self.bucket_name == "replace_with_your_bucket_name":
            return {
                "status": "not_configured",
                "object_key": "",
                "bucket": "",
            }

        client = self.get_client()
        if client is None:
            return {
                "status": "failed",
                "object_key": "",
                "bucket": self.bucket_name,
                "error": "S3 client initialization failed",
            }

        safe_key = f"reports/{report_uuid}.jpg"

        try:
            client.put_object(
                Bucket=self.bucket_name,
                Key=safe_key,
                Body=image_bytes,
                ContentType=content_type,
                # Private by default; no public ACLs
            )
            return {
                "status": "stored",
                "object_key": safe_key,
                "bucket": self.bucket_name,
            }
        except Exception as e:
            logger.error("Failed to upload image to S3 (bucket: %s, key: %s): %s", self.bucket_name, safe_key, str(e))
            return {
                "status": "failed",
                "object_key": safe_key,
                "bucket": self.bucket_name,
                "error": type(e).__name__,
            }


# Singleton instance
s3_service = S3StorageService()
