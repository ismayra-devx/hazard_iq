"""
Storage Service Abstraction for HazardIQ.
Supports local persistent JSON file storage for local development/hackathon,
with seamless AWS DynamoDB & S3 adapters for cloud deployment.
"""

from decimal import Decimal
import json
import logging
import os
import threading
from typing import Any, Dict, List, Optional

from app.config import settings

logger = logging.getLogger(__name__)


def convert_floats_to_decimals(obj: Any) -> Any:
    """Recursively convert float types to Decimal for DynamoDB storage."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: convert_floats_to_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_floats_to_decimals(i) for i in obj]
    return obj


def convert_decimals_to_primitives(obj: Any) -> Any:
    """Recursively convert Decimal types back to float/int for JSON/FastAPI serialization."""
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    elif isinstance(obj, dict):
        return {k: convert_decimals_to_primitives(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals_to_primitives(i) for i in obj]
    return obj


class StorageService:
    def __init__(
        self,
        local_path: Optional[str] = None,
        enable_dynamodb: Optional[bool] = None,
        dynamodb_table: Optional[str] = None,
        enable_s3: Optional[bool] = None,
        s3_bucket: Optional[str] = None,
    ):
        self.local_path = local_path or settings.LOCAL_STORAGE_PATH
        self.enable_dynamodb = settings.ENABLE_DYNAMODB if enable_dynamodb is None else enable_dynamodb
        self.dynamodb_table_name = dynamodb_table or settings.DYNAMODB_TABLE_REPORTS
        self.enable_s3 = settings.ENABLE_S3 if enable_s3 is None else enable_s3
        self.s3_bucket_name = s3_bucket or settings.S3_BUCKET_PHOTOS
        self._lock = threading.Lock()
        self._dynamodb_table = None
        self._s3_client = None

        # Ensure local data directory exists
        local_dir = os.path.dirname(self.local_path)
        if local_dir and not os.path.exists(local_dir):
            os.makedirs(local_dir, exist_ok=True)

    def _get_dynamodb_table(self):
        if self._dynamodb_table is None:
            import boto3
            from botocore.config import Config

            config = Config(
                region_name=settings.AWS_REGION,
                retries={"max_attempts": 3, "mode": "standard"}
            )
            kwargs: Dict[str, Any] = {"region_name": settings.AWS_REGION, "config": config}
            if settings.AWS_ENDPOINT_URL:
                kwargs["endpoint_url"] = settings.AWS_ENDPOINT_URL

            dynamodb = boto3.resource("dynamodb", **kwargs)
            self._dynamodb_table = dynamodb.Table(self.dynamodb_table_name)
        return self._dynamodb_table

    def _get_s3_client(self):
        if self._s3_client is None:
            import boto3
            from botocore.config import Config

            config = Config(
                region_name=settings.AWS_REGION,
                retries={"max_attempts": 3, "mode": "standard"}
            )
            kwargs: Dict[str, Any] = {"region_name": settings.AWS_REGION, "config": config}
            if settings.AWS_ENDPOINT_URL:
                kwargs["endpoint_url"] = settings.AWS_ENDPOINT_URL

            self._s3_client = boto3.client("s3", **kwargs)
        return self._s3_client

    def generate_presigned_photo_url(
        self,
        photo_s3_key: str,
        expiration_seconds: Optional[int] = None
    ) -> Optional[str]:
        """
        Generate a secure temporary pre-signed URL for viewing a private S3 image.
        """
        if not self.enable_s3 or not photo_s3_key:
            return None
        try:
            s3 = self._get_s3_client()
            expires = expiration_seconds or settings.S3_PRESIGNED_URL_EXPIRE_SECONDS
            url = s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.s3_bucket_name, "Key": photo_s3_key},
                ExpiresIn=expires,
            )
            return url
        except Exception as e:
            logger.error("Failed to generate presigned S3 photo URL for %s: %s", photo_s3_key, str(e))
            return None

    async def save_report(
        self,
        report_data: Dict[str, Any],
        photo_bytes: Optional[bytes] = None
    ) -> Dict[str, Any]:
        """
        Persist a report record. Handles S3 photo upload and DynamoDB/local JSON storage.
        """
        report_id = report_data.get("report_id", "")

        # 1. Store photo if S3 is enabled
        photo_s3_key: Optional[str] = None
        if photo_bytes and self.enable_s3:
            try:
                s3 = self._get_s3_client()

                # Infer content type and file extension from magic bytes
                fmt = "jpg"
                content_type = "image/jpeg"
                if photo_bytes.startswith(b"\x89PNG"):
                    fmt = "png"
                    content_type = "image/png"
                elif photo_bytes.startswith(b"RIFF") and b"WEBP" in photo_bytes[:16]:
                    fmt = "webp"
                    content_type = "image/webp"

                photo_s3_key = f"reports/{report_id}/photo.{fmt}"
                s3.put_object(
                    Bucket=self.s3_bucket_name,
                    Key=photo_s3_key,
                    Body=photo_bytes,
                    ContentType=content_type,
                    ServerSideEncryption="AES256"
                )
                report_data["photo_s3_key"] = photo_s3_key
                logger.info("Saved photo to S3: s3://%s/%s", self.s3_bucket_name, photo_s3_key)
            except Exception as e:
                logger.error("Failed to upload photo to S3: %s", str(e))
                report_data["photo_s3_error"] = str(e)

        # 2. DynamoDB persistence if enabled
        if self.enable_dynamodb:
            try:
                table = self._get_dynamodb_table()
                ddb_item = convert_floats_to_decimals(report_data)
                table.put_item(Item=ddb_item)
                logger.info("Saved report %s to DynamoDB table %s", report_id, self.dynamodb_table_name)
                return report_data
            except Exception as e:
                logger.error("DynamoDB save failed (%s), falling back to local storage: %s", self.dynamodb_table_name, str(e))
                report_data["dynamodb_error"] = str(e)

        # 3. Local persistent JSON storage fallback
        with self._lock:
            reports: List[Dict[str, Any]] = []
            if os.path.exists(self.local_path):
                try:
                    with open(self.local_path, "r", encoding="utf-8") as f:
                        reports = json.load(f)
                except Exception:
                    reports = []

            # Append or update
            reports.insert(0, report_data)
            # Keep latest 500 reports in local demo file
            if len(reports) > 500:
                reports = reports[:500]

            with open(self.local_path, "w", encoding="utf-8") as f:
                json.dump(reports, f, indent=2, default=str)

        return report_data

    async def get_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a report by ID."""
        if self.enable_dynamodb:
            try:
                table = self._get_dynamodb_table()
                res = table.get_item(Key={"report_id": report_id})
                item = res.get("Item")
                if item:
                    return convert_decimals_to_primitives(item)
            except Exception as e:
                logger.error("DynamoDB get_item error: %s", str(e))

        with self._lock:
            if not os.path.exists(self.local_path):
                return None
            try:
                with open(self.local_path, "r", encoding="utf-8") as f:
                    reports = json.load(f)
                    for r in reports:
                        if r.get("report_id") == report_id:
                            return r
            except Exception:
                return None
        return None

    async def list_reports(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List recent reports from DynamoDB (or local fallback)."""
        if self.enable_dynamodb:
            try:
                table = self._get_dynamodb_table()
                res = table.scan(Limit=limit)
                items = res.get("Items", [])
                converted = [convert_decimals_to_primitives(i) for i in items]
                converted.sort(key=lambda x: str(x.get("timestamp", "")), reverse=True)
                return converted[:limit]
            except Exception as e:
                logger.error("DynamoDB list_reports error: %s", str(e))

        with self._lock:
            if not os.path.exists(self.local_path):
                return []
            try:
                with open(self.local_path, "r", encoding="utf-8") as f:
                    reports = json.load(f)
                    return reports[:limit]
            except Exception:
                return []


# Singleton instance
storage_service = StorageService()
